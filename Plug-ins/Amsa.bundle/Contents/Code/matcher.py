"""Search: match a Plex show folder name to AniDB ids."""
import re
import urllib2

import settings
import textutil
import anime_lists
import title_index
import sources
import tvdb_v4
import season_editor

FORCED_ID = re.compile(r"(?P<show>.*?) ?\[(?P<source>(.*))-(tt)?(?P<id>[0-9]{1,7})\]", re.IGNORECASE)
FOLDER_YEAR = re.compile(r"\((19|20)[0-9]{2}\)\s*$")
TRAILING_YEAR = re.compile(r" (19|20)[0-9]{2}$")                  # The folder year after clean_title(): "show name 2025"
CLEAR_WORD = "clear-cache"                                         # In a manual search: clear Plex's HTTP cache for AMSA
FORCED_SOURCES = ["anidb", "anidb2", "tvdb", "tvdb2", "tvdb3", "tvdb4", "tvdb5"]


def exact_without_year(title, search_title):
    """True if title matches the folder name exactly once its trailing year is removed ("show 2025" vs "Show")."""
    without_year = TRAILING_YEAR.sub("", search_title)
    return without_year != search_title and textutil.clean_title(title).lower() == without_year.lower()


def title_score(title, search_title):
    """100 for an exact (cleaned) match, otherwise 90 minus a Levenshtein penalty."""
    matched = textutil.clean_title(title)
    if matched.lower() == search_title.lower():
        return 100
    # Ignore year suffixes and a leading "BBC" that would otherwise skew the distance
    search = re.sub(r"([ ]+\(?[0-9]{4}\)?)", "", search_title) if len(search_title) > 8 else search_title
    found = re.sub(r"([ ]+\(?[0-9]{4}\)?)", "", matched) if len(matched) > 8 else matched
    search = re.sub("^[Bb][Bb][Cc] ", "", search)
    found = re.sub("^[Bb][Bb][Cc] ", "", found)
    return 90 - int(30 * (1 - textutil.similarity(search, found)))


class TitleMatch():
    """Score for one matching AniDB title."""
    def __init__(self, title_element, search_title):
        anime = title_element.getparent()
        self.anidb_id = anime.get("aid")
        self.title = textutil.clean_text(textutil.preferred_title(anime)) or title_element.text
        self.score = title_score(title_element.text, search_title)
        self.exact_without_year = self.score < 100 and exact_without_year(title_element.text, search_title)


def aired_year(record):
    try:
        return textutil.parse_date(record.originally_available_at).year     # None (no date) raises, which means no year
    except Exception:
        return None


def start_year(anidb_id, manual):
    """(year, source) for one AniDB entry, or (None, None).
       AniDB first: each season has its own AniDB entry and start date, so consecutive seasons are told apart.
       TVDB only as a fallback and only for entries mapped to TVDB season 1: its date covers the whole show
       (and can be an early special's, e.g. a pilot a year before the series)."""
    if settings.SEARCH_USE_ANIDB:
        # Automatic matching never requests AniDB; manual searches only if no waiting is needed (bans/limits fall back to the cache)
        record = sources.get_anidb(anidb_id, network="quick" if manual else False)
        if record.valid and aired_year(record):
            return aired_year(record), "AniDB"
    if settings.SEARCH_USE_TVDB:
        mapping = anime_lists.AnimeListEntry(anidb_id)
        if mapping.tvdb_id and mapping.default_tvdb_season == 1 and not mapping.absolute and not mapping.episode_offset:
            record = sources.get_tvdb(mapping.tvdb_id)
            if record.valid and aired_year(record):
                return aired_year(record), "TVDB"
    return None, None


def search(results, media, manual):
    """Fill Plex's results with MetadataSearchResult entries (ids 'anidb-<aid>' or forced '<source>-<id>')."""
    anime_lists.refresh()
    show = media.show or ""
    # Search words (anywhere in a manual search, any case), taken out of the title before matching
    if CLEAR_WORD in show.lower():
        show = re.sub(r"(?i)\s*%s\s*" % (CLEAR_WORD), " ", show).strip()
        HTTP.ClearCache()
        Log.Info("Search - '%s': Plex's download cache for AMSA cleared" % (CLEAR_WORD))
    unlock = season_editor.UNLOCK_WORD in show.lower()
    if unlock:
        show = re.sub(r"(?i)\s*%s\s*" % (season_editor.UNLOCK_WORD), " ", show).strip()
        Log.Info("Search - '%s': the result you pick has its show and season images unlocked in Plex on its update" % (season_editor.UNLOCK_WORD))
    Log.Info("Search - Show: '%s', name: '%s', filename: '%s', manual: '%s'" % (show, media.name, urllib2.unquote(media.filename) if media.filename else "", manual))

    search_title = show
    match = FORCED_ID.search(show)
    if match:
        title = match.group("show")
        source = match.group("source").lower()
        if source in FORCED_SOURCES:
            source_id = match.group("id")
            if source in ("anidb", "anidb2"):
                title = textutil.preferred_title(anime_lists.titles_for_anime(source_id)) or title
            Log.Debug("Search - Forced id '%s-%s' from folder name, title: '%s'" % (source, source_id, title))
            results.Append(MetadataSearchResult(id="%s-%s" % (source, source_id), name=title, year=None, lang=Locale.Language.English, score=100))
            if unlock:
                season_editor.request_unlock("%s-%s" % (source, source_id))
            return
        search_title = textutil.clean_title(title)

    # Use the year from the folder name, e.g. "Show (2025)", when Plex doesn't supply one; it lets the aired-year check pick the right season
    year = media.year
    strict_year = bool(media.year)
    year_match = FOLDER_YEAR.search(show)
    if not year and year_match:
        year = year_match.group(0).strip()[1:-1]
        Log.Debug("Search - Using year '%s' from the folder name" % (year))
    search_title = textutil.clean_title(search_title)

    # 1. Matching titles. Folder names like "Show (2025)" rarely appear verbatim in AniDB, so retry without the trailing year
    #    before falling back to fuzzy matching (which compares all ~100k titles). Scores still use the full folder name.
    elements = title_index.find(search_title, fuzzy=False)
    without_year = TRAILING_YEAR.sub("", search_title)
    if not elements and without_year != search_title:
        elements = title_index.find(without_year, fuzzy=False)
    if not elements:
        elements = title_index.find(search_title)

    # 2. Best-scoring title per anime (an anime can match through several of its titles)
    candidates = {}
    for title_element in elements:
        try:
            candidate = TitleMatch(title_element, search_title)
        except Exception:
            Log.Error("Search - Scoring a title failed: %s" % (textutil.exception_text()))
            continue
        current = candidates.get(candidate.anidb_id)
        if current is None or candidate.score > current.score or (candidate.score == current.score and candidate.exact_without_year):
            candidates[candidate.anidb_id] = candidate

    # 3. Year check once per anime, on its best title (so a weaker alternative title can't skip the penalty)
    checks = {}

    @parallelize
    def check_years():
        for anidb_id in candidates:
            @task
            def check_year(anidb_id=anidb_id, checks=checks):
                candidate = candidates[anidb_id]
                is_valid = True
                started = None
                strong = candidate.score >= 90
                if year and strong:
                    try:
                        started, source = start_year(anidb_id, manual)
                    except Exception:
                        started, source = None, None
                        Log.Error("Search - Year check for anidb-%s failed: %s" % (anidb_id, textutil.exception_text()))
                    if started is not None:
                        if str(started) == str(year) and candidate.exact_without_year:
                            candidate.score = 100                  # Exact title and the folder year matches the start year
                        if str(started) != str(year):
                            if strict_year:
                                is_valid = False
                            else:
                                candidate.score = candidate.score - 10   # Folder-name year: demote rather than drop, in case it's mislabelled
                        Log.Debug("Search - anidb-%s: year %s, %s start year %s -> %s" % (anidb_id, year, source, started, "match" if str(started) == str(year) else ("dropped" if strict_year else "-10")))
                    else:
                        Log.Debug("Search - anidb-%s: no start date available (AniDB not cached and no usable TVDB date); year not checked" % (anidb_id))
                checks[anidb_id] = (is_valid, started, strong)

    elite = []
    perfect = []
    found = []
    for anidb_id in candidates:
        candidate = candidates[anidb_id]
        is_valid, started, strong = checks.get(anidb_id, (True, None, candidate.score >= 90))
        if strong:
            elite.append(is_valid)     # If every strong candidate fails a Plex-supplied year, results are cleared
        if is_valid:
            if candidate.score == 100:
                perfect.append(anidb_id)
            found.append([anidb_id, candidate.title, started, candidate.score])

    ranked = sorted(found, key=lambda x: -x[3])
    if len(ranked) > settings.SEARCH_MAX_RESULTS:
        Log.Debug("Search - %s AniDB matches; returning the best %s" % (len(ranked), settings.SEARCH_MAX_RESULTS))
        ranked = ranked[:settings.SEARCH_MAX_RESULTS]
    listed = 0
    for item in ranked:
        anidb_id = item[0]
        score = item[3]
        if len(set(perfect)) > 1 and score == 100:
            record = sources.get_anidb(anidb_id, network="quick" if manual else False)
            if record.valid and record.type != "TV Series":
                score = score - 1      # Prefer the TV series when a movie/OVA has the same title
        listed = listed + 1
        if listed <= 5:
            Log.Debug("Search - Result 'anidb-%s', title: '%s', score: %s" % (anidb_id, item[1], score))
        elif listed == 6:
            Log.Debug("Search - ... and %s more AniDB results (not listed here)" % (len(ranked) - 5))
        results.Append(MetadataSearchResult(id="anidb-%s" % (anidb_id), name="%s [anidb-%s]" % (item[1], anidb_id), year=item[2], lang=Locale.Language.English, score=score))
        if unlock:
            season_editor.request_unlock("anidb-%s" % (anidb_id))

    if elite and True not in elite:
        del results[:]

    # 4. TVDB: when no AniDB title matches exactly (e.g. a franchise name AniDB only has as its individual series), ask TVDB's search
    #    and keep shows that the Anime-Lists mapping links to AniDB. Updating a "tvdb-<id>" result uses all its mapped AniDB entries.
    if not perfect and settings.SEARCH_USE_TVDB:
        try:
            search_tvdb(results, show, search_title, year, strict_year, unlock)
        except Exception:
            Log.Error("Search - TVDB search failed: %s" % (textutil.exception_text()))
    results.Sort("score", descending=True)


def search_tvdb(results, show, search_title, year, strict_year, unlock=False):
    query = FOLDER_YEAR.sub("", FORCED_ID.sub(r"\g<show>", show)).strip()
    found = tvdb_v4.search_series(query)
    kept = 0
    tvdb_results = []
    for item in found:
        if not anime_lists.mapping_entries("tvdb", item["id"]):
            continue                                  # Not an anime known to Anime-Lists: it couldn't be updated
        score = 0
        exact = False
        for title in item["titles"]:
            score = max(score, title_score(title, search_title))
            exact = exact or exact_without_year(title, search_title)
        note = ""
        if exact and score < 100 and item["year"] and str(item["year"]) == str(year):
            score = 100                                   # Exact title and the folder year matches TVDB's
        if year and item["year"] and score >= 90 and str(item["year"]) != str(year):
            if strict_year:
                Log.Debug("Search - tvdb-%s: year %s, TVDB year %s -> dropped" % (item["id"], year, item["year"]))
                continue
            score = score - 10
            note = " (year %s, TVDB %s: -10)" % (year, item["year"])
        kept = kept + 1
        tvdb_results.append((score, item, note))
    for score, item, note in sorted(tvdb_results, key=lambda x: -x[0])[:10]:     # The best 10 mapped TVDB shows
        Log.Debug("Search - Result 'tvdb-%s', title: '%s', score: %s%s" % (item["id"], item["name"], score, note))
        results.Append(MetadataSearchResult(id="tvdb-%s" % (item["id"]), name="%s [tvdb-%s]" % (item["name"], item["id"]),
                                            year=item["year"], lang=Locale.Language.English, score=score))
        if unlock:
            season_editor.request_unlock("tvdb-%s" % (item["id"]))
    Log.Debug("Search - TVDB search '%s': %s results, %s mapped to AniDB" % (query, len(found), kept))
