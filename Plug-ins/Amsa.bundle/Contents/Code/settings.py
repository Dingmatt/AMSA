"""AMSA settings: version, paths, source URLs and the user's preferences (DefaultPrefs.json).

Preferences are read once when the agent loads; Plex restarts the agent when they are saved.
"""
import os
import re
import inspect

VERSION = "2.0.0"


# Preferences ##########################################################################################################################################################
# Read defensively: a missing or malformed value must never stop the agent loading.
def pref_str(key, default=""):
    try:
        value = Prefs[key]
        if value is None:
            value = page_default(key)         # No valid saved value: the default, as the settings page shows it
        if value is None:
            return default
        if not isinstance(value, basestring):
            value = str(value)
        return value.strip()
    except Exception:
        return default


def pref_token(key, default=""):
    """First word of a setting: dropdowns show "en - English" or "v4 - current"; older saved values are just "en" / "v4"."""
    value = pref_str(key, default) or default
    return value.split(" ")[0] if value else default


def pref_list(key, default="anidb,tvdb,plex"):
    """Sources in order from a source dropdown ("AniDB > TVDB", "TVDB only", "Off") or an older text value ("AniDB,TVDB,Plex")."""
    value = pref_str(key, default) or default
    return re.findall(r"anidb|anilist|tvdb|plex", value.lower())


def pref_int(key, default):
    """First number in a setting ("4 seconds (recommended)" -> 4)."""
    found = re.search(r"[0-9]+", pref_str(key, str(default)))
    return int(found.group(0)) if found else default


def pref_seconds(key, default):
    """A duration setting in seconds ("10 minutes (testing)" -> 600, "24 hours" -> 86400, "3 days" -> 259200)."""
    found = re.search(r"([0-9]+)\s*(minute|hour|day)", pref_str(key, "").lower())
    if not found:
        return default
    return int(found.group(1)) * {"minute": 60, "hour": 3600, "day": 86400}[found.group(2)]


def pref_bool(key, default=False):
    try:
        value = Prefs[key]
        if value is None:
            value = page_default(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes")
    except Exception:
        return default


# Defaults as the settings page shows them #############################################################################################################################
# Plex's Prefs[key] is None when the saved value isn't one of the setting's options (e.g. text saved when settings were text
# boxes: "AniDB,TVDB,Plex"). Plex's settings page then shows the setting's default, so AMSA uses that default too: what you
# see on the page is what AMSA uses. Saving the page once stores it properly.
PAGE = {"defaults": None, "entries": [], "unset": {}, "errors": []}


def page_entries():
    """DefaultPrefs.json's settings (id, type, values, default), read once."""
    load_page()
    return PAGE["entries"]


def page_default(key):
    """The setting's default from DefaultPrefs.json (what Plex's settings page shows when no valid value is saved)."""
    load_page()
    PAGE["unset"][key] = True
    return PAGE["defaults"].get(key)


def load_page():
    if PAGE["defaults"] is None:
        PAGE["defaults"] = {}
        try:
            import json
            descriptor = os.open(os.path.join(CODE_DIR, "..", "DefaultPrefs.json"), os.O_RDONLY | getattr(os, "O_BINARY", 0))   # os.open: builtin open() is unproven in Plex's sandbox
            try:
                content = os.read(descriptor, os.fstat(descriptor).st_size + 1)
            finally:
                os.close(descriptor)
            PAGE["entries"] = json.loads(content)
            for item in PAGE["entries"]:
                PAGE["defaults"][item.get("id")] = item.get("default")
        except Exception as e:
            PAGE["errors"].append("DefaultPrefs.json not readable (%s)" % (e))


# Paths and caching ####################################################################################################################################################
CODE_DIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
DATA_ITEMS_PATH = os.path.abspath(os.path.join(CODE_DIR, "..", "..", "..", "..", "Plug-in Support", "Data", "com.plexapp.agents.amsa", "DataItems"))
CACHE_DIR = "Cache"                                  # Relative to DataItems (Plex's Data API root)
CACHE_PATH = os.path.join(DATA_ITEMS_PATH, CACHE_DIR)
# TVDB images are the same files whichever API (v1 or v4) listed them, so both keep them in one place, under TvDB4: when v1 is
# shut down, the whole TvDB folder (v1's XML only) can be deleted without touching anything v4 uses.
TVDB_IMAGES_FOLDER = "TvDB4"
EXPORT_DIR = "Export"
EXPORT_PATH = os.path.join(DATA_ITEMS_PATH, EXPORT_DIR)
EXPORT_BUNDLES = False

DEFAULT_TIMEOUT = 30
DEFAULT_CACHE = CACHE_1HOUR * 24 * 2                 # Source XML / images are re-downloaded after 2 days
NOT_FOUND_RETRY = CACHE_1HOUR * 24                   # A URL that returned 404 is not requested again for 24h
REFERENCE_RELOAD = CACHE_1HOUR * 24                  # Reference lists held in memory are re-read from cache/network after 24h
SOURCE_MEMORY_TTL = 15 * 60                          # Parsed AniDB/TVDB records are reused for 15 minutes (one parse per update)
HTTP_HEADERS = {"Accept-Encoding": "gzip",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"}

# Bundle tags: one element per field in Cache/Bundles/*.bundle.xml. Source objects expose the same fields as lower-case attributes.
SERIES_FIELDS = ["Title", "Original_Title", "Summary", "Originally_Available_At", "Rating", "Studio", "Countries", "Duration", "Genres", "Tags", "Collections", "Content_Rating",
                 "Roles", "Art", "Posters", "Banners", "Season", "Themes", "Links"]
EPISODE_FIELDS = ["Title", "Summary", "Originally_Available_At", "Rating", "Absolute_Index", "Writers", "Directors", "Producers", "Thumbs"]


# Search ###############################################################################################################################################################
FILTER_SEARCH_WORDS = ['to', 'wa', 'ga', 'no', 'age', 'da', 'chou', 'super', 'yo', 'de', 'chan', 'hime', 'ni', 'sekai',                                                                 # Jp
                       'a', 'of', 'an', 'the', 'motion', 'picture', 'special', 'oav', 'ova', 'tv', 'special', 'eternal', 'final', 'last', 'one', 'movie', 'me', 'princess', 'theater',  # En
                       'le', 'la', 'un', 'les', 'nos', 'vos', 'des', 'ses',                                                                                                            # Fr
                       'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi']                                                           # Roman digits
FILTER_REGEX = r'\b' + r'\b|\b'.join(map(re.escape, FILTER_SEARCH_WORDS)) + r'\b'
SEARCH_TITLE_TYPES = ("main", "official", "syn", "short")


# Metadata priorities (which source wins for each field) ##################################################################################################################
SERIES_TYPE_PRIORITY = ["main", "official", "syn", "synonym", "short"]
SERIES_PRIORITY = {}
EPISODE_PRIORITY = {}


def collections_exclude():
    """Setting CollectionsExclude: "" (include all), "explicit" or "mature" shows left out of English Dubbed / English Subbed."""
    value = pref_str("CollectionsExclude", "Include all shows").lower()
    if "mature" in value:
        return "mature"
    if "explicit" in value:
        return "explicit"
    return ""


def content_rating_rule():
    """Setting ContentRatingRule: "official" (default), "strictest" or "order"."""
    value = pref_str("ContentRatingRule", "Official rating first").lower()
    if "strict" in value:
        return "strictest"
    if "order" in value:
        return "order"
    return "official"


def title_from_tvdb_alias():
    """Setting SeriesTitleAlias: "several" (default: shows spanning several AniDB entries), "all" or "" (off)."""
    value = pref_str("SeriesTitleAlias", "Shows with several AniDB entries").lower()
    if value.startswith("all"):
        return "all"
    if value.startswith("off") or value.startswith("never"):
        return ""
    return "several"


def content_rating_country():
    """Setting ContentRatingCountry: Plex's country code for content ratings ("us" = US TV ratings)."""
    value = pref_str("ContentRatingCountry", "United States").lower()
    for name, code in (("united kingdom", "gb"), ("germany", "de"), ("france", "fr"), ("japan", "jp"), ("canada", "ca"),
                       ("australia", "au"), ("brazil", "br"), ("spain", "es"), ("italy", "it")):
        if value.startswith(name):
            return code
    return "us"


def season_name_mode():
    """What goes in a season's title. Titles and summaries are applied through Plex's API (see season_editor.py)."""
    value = pref_str("SeasonTitle", "Season 2: Name of Season").lower()
    if value.startswith("season 2"):
        return "number-name"                    # Title "Season 2: Name of Season"
    if value.startswith("name"):
        return "name"                           # Title "Name of Season"
    return "off"


def images_max():
    """Most posters / backgrounds / banners / season posters (per season) offered to Plex; 0 = all."""
    if pref_str("ImagesMax", "20").lower().startswith("all"):
        return 0
    return max(1, pref_int("ImagesMax", 20))


SEARCH_MAX_RESULTS = 20                              # AniDB results returned to Plex per search (best first); TVDB results: 10


# AniDB ################################################################################################################################################################
ANIDB_TITLES_URL = "https://anidb.net/api/anime-titles.xml"
ANIDB_API_URL = "http://api.anidb.net:9001/httpapi?request=anime&client=amsa&clientver=1&protover=1&aid="
ANIDB_IMAGE_DOMAIN = "https://cdn.anidb.net/"
ANIDB_PIC_BASE_URL = "images/main/"
ANIDB_PIC_THUMB_URL = "images/150/%s.jpg-thumb.jpg"
ANIDB_BAD_TITLES = ["^TV Special$", "^Part [0-9]+ of [0-9]+$", "^Episode S?[0-9]+$", "^Special S?[0-9]+$", "Complete Movie",
                    "^(Opening|Ending)( [0-9]+[a-z]?)?$",
                    "^Vol(ume|\\.)? ?[0-9]+$"]               # Generic titles: a real title from another source wins (OVAs: "Volume 1")
ANIDB_RESOURCES = {          # resource type -> (link type, url template or None for a plain URL)
    "1": ("ANN", "http://www.animenewsnetwork.com/encyclopedia/anime.php?id=%s"),
    "2": ("MAL", "http://myanimelist.net/anime/%s"),
    "4": ("OfficialJP", None),
    "5": ("OfficialEN", None),
    "6": ("WikiEN", "http://en.wikipedia.org/wiki/%s"),
    "7": ("WikiJP", "http://ja.wikipedia.org/wiki/%s"),
    "8": ("Schedule", "http://cal.syoboi.jp/tid/%s/time"),
    "9": ("AllCinema", "http://www.allcinema.net/prog/show_c.php?num_c=%s"),
    "10": ("Anison", "http://anison.info/data/program/%s.html"),
    "11": ("Lain", "http://lain.gr.jp/%s"),
    "14": ("VNDB", "http://vndb.org/v%s"),
    "15": ("Marumegane", "http://www.anime.marumegane.com/%s.html"),
}
ANIDB_RESOURCE_ANIMENFO = "http://www.animenfo.com/animetitle,%s,%s,a.html"


# TVDB (v1 XML API) ####################################################################################################################################################
TVDB_SERIES_URL = "http://thetvdb.com/api/DC6295EB0E09E931/series/%s/all/en.xml"
TVDB_BANNERS_URL = "http://thetvdb.com/api/DC6295EB0E09E931/series/%s/banners.xml"
TVDB_IMAGES_URL = "http://thetvdb.com/banners/"

# TVDB v4 (JSON API). v4 is used by default; if it fails for a show, the v1 XML API above is used for that show instead.
TVDB4_API_URL = "https://api4.thetvdb.com/v4/"
TVDB4_API_KEY = "72fd062a-c5d8-43ac-a97c-cabda42dd4ab"             # Project key from the original AMSA tvdbv4.py; no subscriber PIN
TVDB4_TOKEN_TTL = 25 * 24 * 3600                                    # Tokens last one month; renew a little earlier
TVDB4_LANGUAGE = "eng"
TVDB4_ART_SERIES_BANNER = 1                                         # /artwork/types ids
TVDB4_ART_SERIES_POSTER = 2
TVDB4_ART_SERIES_BACKGROUND = 3
TVDB4_ART_SEASON_BANNER = 6                                         # Season-wide banners: v1 listed these with the series banners
TVDB4_ART_SEASON_POSTER = 7
TVDB4_CREW_CACHE = 14 * 24 * 3600                                   # Episode writers/directors (one request per episode) are re-checked every 2 weeks
TVDB4_ARTWORK_URL = "https://artworks.thetvdb.com"                # Prefix for v4 image paths given without a host
TVDB4_SEARCH_TIMEOUT = 10                                           # Searches must not keep Plex waiting long
TVDB4_CREW_LIMIT = 300                                              # Most episode crew requests per update; the rest are fetched on the next refresh


# Anime-Lists (ScudLee) ################################################################################################################################################
MAPPING_URL = "https://raw.githubusercontent.com/Anime-Lists/anime-lists/master/anime-list-master.xml"
COLLECTION_URL = "https://raw.githubusercontent.com/Anime-Lists/anime-lists/master/anime-movieset-list.xml"
MAPPING_CUSTOM_FILE = os.path.join(CACHE_DIR, "anime-list-custom.xml")
MAPPING_CORRECTIONS_URL = "https://raw.githubusercontent.com/Dingmatt/AMSA/master/Plug-in%20Support/Data/com.plexapp.agents.amsa/DataItems/Cache/anime-list-corrections.xml"
APPLY_CORRECTIONS = False    # The old remote corrections file predates many upstream fixes; earlier versions never applied it either


# Plex #################################################################################################################################################################
THEME_URL = "http://tvthemes.plexapp.com/%s.mp3"
PMS_URL = "http://127.0.0.1:32400"                                  # Local Plex Media Server, used to re-refresh a show after a postponed AniDB download

# AniDB cache age by series end date (idea from HAMA): airing or recently ended shows are re-checked every DEFAULT_CACHE;
# a show that ended long ago changes rarely, so it is kept up to a year, which keeps AniDB requests (and ban risk) low
ANIDB_CACHE_ENDED_MAX = 365 * 24 * 3600

# anime-offline-database (offline_db.py): weekly continuation of manami-project's dataset, ODbL 1.0
OFFLINE_DB_URL = "https://github.com/cedya77/anime-offline-database/releases/download/latest/anime-offline-database.jsonl"
OFFLINE_DB_RELOAD = 7 * 24 * CACHE_1HOUR

# Partial refreshes (refresher.py / airing.py)
REFETCH_FINISHED_ANIDB_AFTER = 7 * 24 * CACHE_1HOUR   # Refresh Metadata re-downloads a finished show's AniDB entry only if older
REFETCH_ANIDB_AFTER = 24 * CACHE_1HOUR      # An episode on disk without data re-downloads its AniDB entry early, if the copy is this old
REFETCH_TVDB_AFTER = 6 * CACHE_1HOUR        # ... and its TVDB series
AIRING_REFRESH_AFTER = 20 * CACHE_1HOUR     # Airing shows not updated for this long are refreshed by the daily job
AIRING_KEEP_AFTER_END = 30 * 24 * CACHE_1HOUR   # Shows stay on the airing list for 30 days after their end date
AIRING_PER_RUN = 10                         # Refreshes per hourly run, AIRING_GAP seconds apart
AIRING_GAP = 120

# AniList (GraphQL, no API key). Entries are found through the MAL id AniDB lists, falling back to the arm.haglund.dev id mapping
ANILIST_API_URL = "https://graphql.anilist.co"
ANILIST_ARM_URL = "https://arm.haglund.dev/api/v2/ids?source=anidb&include=anilist&id=%s"
ANILIST_REQUEST_DELAY = 2.0                # Seconds between AniList requests (AniList currently allows about 30 per minute)
ANILIST_MINIMUM_TAG_RANK = 60              # AniList tag relevance (0-100) needed to become a Plex tag; spoiler and adult tags are skipped

# Plex's saved copy of this agent's settings; deleted by "Reset settings to defaults"
PREFS_FILE = os.path.abspath(os.path.join(CODE_DIR, "..", "..", "..", "..", "Plug-in Support", "Preferences", "com.plexapp.agents.amsa.xml"))


def fallback_order():
    """Setting EpisodeFallback: ["mal", "kitsu"], ["kitsu", "mal"], one of them, or [] for Off."""
    value = pref_str("EpisodeFallback", "MyAnimeList > Kitsu").lower()
    if value.startswith("off"):
        return []
    return [{"myanimelist": "mal", "kitsu": "kitsu"}[x] for x in re.findall(r"myanimelist|kitsu", value)]


def source_settings():
    """{setting id: [sources in order]} for every source setting, as loaded (episode lists include the gap fillers)."""
    found = {"SeriesImages": SERIES_IMAGES_PRIORITY, "SeriesThemes": SERIES_THEMES_PRIORITY, "SeasonText": SEASON_PRIORITY}
    for field_name in SERIES_PRIORITY:
        found["Series" + field_name] = SERIES_PRIORITY[field_name]
    for field_name in EPISODE_PRIORITY:
        found["Episode" + field_name] = EPISODE_PRIORITY[field_name]
    return found


def source_used(source):
    for value in source_settings().values():
        if source in value:
            return True
    return False


def source_plan():
    """Log lines: which sources an update contacts, in order, and which it skips and why (logged with the settings)."""
    order = ["Anime-Lists (episode mapping)"]
    skipped = []
    if ANILIST_ENABLED:
        order.append("AniList (started first, in the background)")
    else:
        skipped.append("AniList (no setting lists it)")
    order.append("AniDB (each related entry, one at a time within the AniDB limits%s)" % ("" if source_used("anidb") else "; no setting shows its data, but episode mapping needs it"))
    together = ["TVDB" + ("" if source_used("tvdb") else " (no setting shows its data, but season and episode numbering needs it)")]
    if PLEX_THEMES_USED:
        together.append("Plex theme music")
    else:
        skipped.append("Plex theme music (Theme music from is Off)")
    order.append(" and ".join(together) + (" (together)" if len(together) > 1 else ""))
    names = {"mal": "MyAnimeList", "kitsu": "Kitsu"}
    if FALLBACK_ORDER:
        order.append("fallback: %s (only for episodes still missing a title, summary or air date%s)"
                     % (" > ".join([names[x] for x in FALLBACK_ORDER]), "" if "kitsu" in FALLBACK_ORDER else "; summaries need Kitsu"))
    for source in ("mal", "kitsu"):
        if source not in FALLBACK_ORDER:
            skipped.append("%s (not in the Fallback setting)" % (names[source]))
    if CREDIT_TITLES:
        order.append("AnimeThemes (only for opening/ending specials)")
    else:
        skipped.append("AnimeThemes (Song names is off)")
    lines = ["Sources - An update contacts: %s" % (" -> ".join(order))]
    if skipped:
        lines.append("Sources - Not contacted: %s" % ("; ".join(skipped)))
    matching = ["AniDB title list" + (" + anime-offline-database titles" if OFFLINE_DB_ENABLED else "")]
    if SEARCH_USE_ANIDB:
        matching.append("aired year from AniDB (cached copies only, unless you search manually)")
    if SEARCH_USE_TVDB:
        matching.append("aired year from TVDB > TVDB title search if there's no exact AniDB match")
    lines.append("Sources - Matching a new show: %s" % (" -> ".join(matching)))
    return lines


def anilist_enabled():
    """AniList is only asked when at least one setting lists it."""
    lists = [SERIES_IMAGES_PRIORITY, SEASON_PRIORITY]
    for field_name in SERIES_PRIORITY:
        lists.append(SERIES_PRIORITY[field_name])
    for found in lists:
        if "anilist" in found:
            return True
    return False


# Settings read from Plex's preferences ###############################################################################################################################
def load_prefs():
    """(Re)compute every setting that comes from Plex's preferences. Run at import, and again from ValidatePrefs when the
       settings page is saved, so a change applies straight away, without restarting Plex Media Server."""
    global SEARCH_USE_ANIDB, SEARCH_USE_TVDB, SERIES_LANGUAGE_PRIORITY, EPISODE_LANGUAGE_PRIORITY, field_name, COLLECTIONS_EXCLUDE
    global CONTENT_RATING_RULE, TITLE_FROM_TVDB_ALIAS, CONTENT_RATING_COUNTRY, CAST_LANGUAGE, CAST_PHOTOS, REFRESH_IN_BACKGROUND, REFRESH_SKIP_RECENT
    global EPISODE_FILL, FALLBACK_ORDER, CREDIT_TITLES, fillers, filler, SERIES_IMAGES_PRIORITY, SERIES_THEMES_PRIORITY, ORIGINAL_TITLE_LANGUAGE
    global SUMMARY_REPEAT, RATING_COMBINE
    global SEASON_PRIORITY, TITLE_LANGUAGE_FIRST, SEASON_NAME_MODE, SEASON_NAME_IN_SUMMARY, SEASON_PARTS_COMBINED, PREFER_LOCAL_ART, PREFER_POSTER_SETS, IMAGES_MAX, REFRESH_AIRING
    global OFFLINE_DB_ENABLED, ANIDB_REQUEST_DELAY, ANIDB_HOURLY_LIMIT, ANIDB_DAILY_LIMIT, ANIDB_MINIMUM_WEIGHT, ANILIST_ENABLED, PLEX_THEMES_USED
    SEARCH_USE_ANIDB = pref_bool("UseAniDBForAdvancedSearch", True)
    SEARCH_USE_TVDB = pref_bool("UseTVDBForAdvancedSearch", True)
    SERIES_LANGUAGE_PRIORITY = [pref_token("SerieLanguage1", "main"), pref_token("SerieLanguage2", "x-jat"), pref_token("SerieLanguage3", "en"), "main"]
    EPISODE_LANGUAGE_PRIORITY = [pref_token("EpisodeLanguage1", "en"), pref_token("EpisodeLanguage2", "x-jat")]
    for field_name in SERIES_FIELDS:
        SERIES_PRIORITY[field_name] = pref_list("Series" + field_name)
    for field_name in EPISODE_FIELDS:
        EPISODE_PRIORITY[field_name] = pref_list("Episode" + field_name)
    COLLECTIONS_EXCLUDE = collections_exclude()
    CONTENT_RATING_RULE = content_rating_rule()
    TITLE_FROM_TVDB_ALIAS = title_from_tvdb_alias()
    CONTENT_RATING_COUNTRY = content_rating_country()
    CAST_LANGUAGE = {"english": "en", "both": "both"}.get(pref_str("CastLanguage", "Japanese").split(" ")[0].lower(), "ja")   # ja / en / both
    CAST_PHOTOS = "character" if pref_str("CastPhotos", "Voice actor").lower().startswith("character") else "actor"
    REFRESH_IN_BACKGROUND = not pref_str("RefreshMode", "Apply cached data first").lower().startswith("wait")   # background_refresh.py
    REFRESH_SKIP_RECENT = pref_seconds("RefreshSkipRecent", 86400)   # Refresh Metadata leaves sources this fresh alone
    FALLBACK_ORDER = fallback_order()                    # Second tier after the episode sources: ["mal", "kitsu"], in the chosen order
    EPISODE_FILL = bool(FALLBACK_ORDER)
    CREDIT_TITLES = pref_bool("CreditTitles", True)      # AnimeThemes: song and artist for opening/ending specials
    # Gap fillers (episode_fill.py): appended after the chosen sources, so they only show where those have nothing better.
    # A field set to "Off" stays off.
    for field_name, fillers in (("Title", FALLBACK_ORDER), ("Summary", [x for x in FALLBACK_ORDER if x == "kitsu"]), ("Originally_Available_At", FALLBACK_ORDER)):   # MAL has no summaries
        if EPISODE_PRIORITY.get(field_name) and EPISODE_FILL and "fallback" in pref_str("Episode" + field_name, "fallback").lower():   # "AniDB only": no fallback
            for filler in fillers:
                if filler not in EPISODE_PRIORITY[field_name]:
                    EPISODE_PRIORITY[field_name].append(filler)
    if EPISODE_PRIORITY.get("Title") and CREDIT_TITLES and "animethemes" not in EPISODE_PRIORITY["Title"]:
        EPISODE_PRIORITY["Title"].append("animethemes")
    SERIES_IMAGES_PRIORITY = pref_list("SeriesImages")
    SERIES_THEMES_PRIORITY = pref_list("SeriesThemes")
    ORIGINAL_TITLE_LANGUAGE = pref_token("OriginalTitle", "ja").lower()   # AniDB title language for Plex's "original title"; "off" = leave empty
    combine = pref_str("RatingCombine", "weighted").lower()                 # metadata_writer.combined_rating
    RATING_COMBINE = "first" if combine.startswith("first") else ("average" if combine.startswith("average") else "weighted")
    repeat = pref_str("SummaryRepeat", "show").lower()                     # metadata_writer.repeated_summary
    SUMMARY_REPEAT = "season" if repeat.startswith("season") else ("both" if repeat.startswith("leave") else "show")
    SEASON_PRIORITY = pref_list("SeasonText", "anidb,anilist,tvdb")       # Season names and summaries: that season's AniDB/AniList entry / TVDB season text
    TITLE_LANGUAGE_FIRST = pref_bool("TitleLanguageFirst", True)          # Titles: language beats source order (see metadata_writer.title_text)
    SEASON_NAME_MODE = season_name_mode()
    SEASON_NAME_IN_SUMMARY = pref_bool("SeasonNameInSummary", False)     # Season summary starts with the season's name (independent of the title)
    SEASON_PARTS_COMBINED = not pref_str("SeasonParts", "Combine").lower().startswith("first")   # Several AniDB entries in one season: summaries combined in episode order
    PREFER_LOCAL_ART = pref_bool("localart", True)        # Images in the library's language first, then images without text, then the rest
    PREFER_POSTER_SETS = pref_bool("SeasonPosterSets", False)   # Season posters: the set covering most seasons first (metadata_writer.mark_poster_sets)
    IMAGES_MAX = images_max()
    REFRESH_AIRING = pref_bool("RefreshAiring", True)    # Ask Plex once a day to refresh shows that are airing or ended in the last 30 days
    OFFLINE_DB_ENABLED = pref_bool("OfflineDatabase", True)   # anime-offline-database: AniList ids, airing status, extra search titles
    ANIDB_REQUEST_DELAY = max(3, pref_int("AniDbAntiBanDelay", 4))     # AniDB allows 1 request per 2s; 4s matches their long-term guidance
    ANIDB_HOURLY_LIMIT = max(10, pref_int("AniDbHourlyLimit", 100))    # Requests per rolling hour
    ANIDB_DAILY_LIMIT = max(50, pref_int("AniDbDailyLimit", 500))      # Requests per rolling 24 hours
    ANIDB_MINIMUM_WEIGHT = str(pref_int("MinimumWeight", 400))
    ANILIST_ENABLED = anilist_enabled()
    PLEX_THEMES_USED = source_used("plex")                # Plex's theme service is only asked when a setting lists it


load_prefs()
