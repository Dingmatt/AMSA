"""Anime Multi Source Agent (AMSA) - Plex entry points.

Module overview:
    settings.py          version, paths, URLs, user preferences
    textutil.py          unicode, title cleaning, dates
    downloader.py        HTTP + disk cache (uses anidb_limiter for AniDB)
    anidb_limiter.py     AniDB anti-ban rate limiting
    anilist.py           AniList source (GraphQL, found via AniDB's MAL id)
    anidb_retry.py       postponed AniDB downloads (fetched when the limiter allows, then the show is refreshed)
    models.py            Series/Episode base classes shared by all sources
    anidb.py / tvdb_v4.py / tvdb.py / plex_themes.py   metadata sources (TVDB: v4, falling back to v1)
    sources.py           parse-once cache of source records
    anime_lists.py       AniDB titles dump + Anime-Lists AniDB<->TVDB mapping
    title_index.py       fast in-memory title search
    matcher.py           search(): folder name -> AniDB id
    bundle.py            per-show bundle tree (mapping, local files, source values)
    metadata_writer.py   bundle -> Plex metadata by source priority
    updater.py           update(): builds the bundle and writes it
    refresher.py         early re-download of a source when episodes on disk have no data yet
    airing.py            daily refresh of airing shows
    offline_db.py        anime-offline-database: AniList ids, airing status, extra search titles
    episode_sources.py   MyAnimeList (Jikan), Kitsu and AnimeThemes episode data
    episode_fill.py      fills gaps in the episodes on disk from those sources
    season_editor.py     season titles/summaries, image choices and unlocks through Plex's own API
    library_unlock.py    setting "Unlock all images on save": every AMSA library, then a countdown of shows to refresh
"""
import os

import settings
import textutil
import anidb_limiter
import downloader
import matcher
import title_index
import updater
import airing
import anidb_retry
import background_refresh
import library_unlock
import cache_cleaner
import health_report
import environment
import prefs_repair


# In the settings page's order (DefaultPrefs.json)
PREF_IDS = ("SeriesTitle", "SerieLanguage1", "SerieLanguage2", "SerieLanguage3", "OriginalTitle", "SeriesTitleAlias", "EpisodeTitle",
            "EpisodeLanguage1", "EpisodeLanguage2", "TitleLanguageFirst", "SeriesSummary", "SeriesOriginally_Available_At", "SeriesRating", "RatingCombine",
            "SeriesStudio", "SeriesDuration", "SeriesCountries", "SeriesGenres", "SeriesTags", "MinimumWeight", "SeriesCollections",
            "CollectionsExclude", "SeriesContent_Rating", "ContentRatingRule", "ContentRatingCountry", "SeriesRoles", "CastLanguage",
            "CastPhotos", "SeriesImages", "ImageLanguage", "SeasonPosterSets", "ImagesMax", "SeasonPostersMax", "ImageDuplicates", "SeriesThemes", "SeasonTitle", "SeasonNameInSummary", "SeasonText", "SeasonParts",
            "SummaryRepeat", "EpisodeSummary", "EpisodeOriginally_Available_At", "EpisodeRating", "EpisodeAbsolute_Index",
            "EpisodeWriters", "EpisodeDirectors", "EpisodeProducers", "EpisodeThumbs", "EpisodeFallback", "CreditTitles",
            "UseAniDBForAdvancedSearch", "UseTVDBForAdvancedSearch", "OfflineDatabase", "AniDbAntiBanDelay", "AniDbHourlyLimit",
            "AniDbDailyLimit", "RefreshMode", "RefreshSkipRecent", "RefreshAiring", "DebugBundles")


def log_prefs():
    """The settings in effect, in one log block (makes logs from different setups easy to compare)."""
    lines = []
    for key in PREF_IDS:
        try:
            value = Prefs[key]
            if value is None:
                lines.append("%s = %s (default)" % (key, settings.page_default(key)))
            else:
                lines.append("%s = %s" % (key, value))
        except Exception:
            lines.append("%s = (missing from DefaultPrefs.json)" % (key))
    Log.Info("Settings - " + "; ".join(lines))
    unset = [key for key in PREF_IDS if key in settings.PAGE["unset"]]
    if unset:
        Log.Info("Settings - %s settings have no valid saved value, so their defaults (as the settings page shows them) are used: %s. Save the settings page once to store them"
                 % (len(unset), ", ".join(unset)))
    for error in settings.PAGE["errors"]:
        Log.Warn("Settings - %s" % (error))
    try:
        for line in settings.source_plan():   # Which sources an update contacts, in order, and which it skips
            Log.Info(line)
    except Exception:
        Log.Warn("Sources - Describing the sources failed: %s" % (textutil.exception_text()))


def Start():
    anidb_limiter.load_state()
    downloader.load_not_found()
    title_index.start_warm_up()        # Lists + title index load in the background so the first search is fast
    Log.Info("--- AmsaTVAgent Start - AMSA v%s ------------------------------------------------------------------------------" % (settings.VERSION))
    environment.report()               # System, user, and whether AMSA can read/write where it needs to (NAS/Linux permission issues)
    log_prefs()
    airing.start()                     # Hourly check for airing shows due their daily refresh (setting RefreshAiring)
    anidb_retry.load_state()           # Queued AniDB downloads from before a restart
    background_refresh.load_state()    # Shows queued for a background download from before a restart
    health_report.start()              # Library health report: 5 minutes after start, then daily
    prefs_repair.start()               # A minute later: settings Plex can't read are stored as the default the page shows


def ValidatePrefs():
    """Called by Plex when preferences are saved (Settings > Agents > AMSA)."""
    try:
        reset = Prefs["ResetSettings"]
    except Exception:
        reset = False
    if reset:
        try:
            if os.path.isfile(settings.PREFS_FILE):
                os.remove(settings.PREFS_FILE)
            Log.Info("ValidatePrefs - Settings reset to defaults (deleted '%s'); restart Plex Media Server to load them" % (settings.PREFS_FILE))
            return MessageContainer("Success", "AMSA - Settings reset to defaults. Restart Plex Media Server to finish.")
        except Exception as e:
            Log.Error("ValidatePrefs - Could not reset settings ('%s'): %s" % (settings.PREFS_FILE, e))
            return MessageContainer("Error", "AMSA - Could not reset settings: %s" % (e))
    missing = []
    for key in PREF_IDS:
        try:
            Prefs[key]
        except Exception:
            missing.append(key)
    if missing:
        Log.Error("ValidatePrefs - Missing from DefaultPrefs.json: %s" % (", ".join(missing)))
        return MessageContainer("Error", "Value(s) %s missing from 'DefaultPrefs.json', update it" % (", ".join(missing)))
    try:
        settings.load_prefs()                # Apply the saved values now, without a restart
        Log.Info("ValidatePrefs - Settings saved and applied")
    except Exception:
        Log.Error("ValidatePrefs - Applying the settings failed (restart Plex Media Server to load them): %s" % (textutil.exception_text()))
    log_prefs()
    if not settings.DEBUG_BUNDLES:
        title_index.run_later(1, cache_cleaner.bundles_clean_up)     # Debug bundles off: the saved ones are deleted
    if library_unlock.requested():
        Log.Info("ValidatePrefs - Unlock all images: starting in the background")
        library_unlock.start()
        return MessageContainer("Success", "AMSA - Settings saved. Unlocking all images in the background; then refresh your AMSA libraries (the log shows progress)")
    return MessageContainer("Success", "AMSA - Provided preference values are ok")


class AmsaTVAgent(Agent.TV_Shows):
    name = "Anime Multi Source Agent"
    primary_provider = True
    fallback_agent = False
    contributes_to = None
    languages = [Locale.Language.English, 'fr', 'zh', 'sv', 'no', 'da', 'fi', 'nl', 'de', 'it', 'es', 'pl', 'hu', 'el', 'tr', 'ru', 'he', 'ja', 'pt', 'cs', 'ko', 'sl', 'hr']
    accepts_from = ["com.plexapp.agents.localmedia"]

    def search(self, results, media, lang, manual=False):
        Log.Info("==== Search: '%s' ====================================================================" % (getattr(media, "show", None) or getattr(media, "name", None) or "?"))
        matcher.search(results, media, manual)

    def update(self, metadata, media, lang, force=False):
        updater.update(metadata, media, force, lang)        # Logs "==== Update: 'Name' (anidb-1, TVDB 2, AniList 3) ====" once the ids are known
