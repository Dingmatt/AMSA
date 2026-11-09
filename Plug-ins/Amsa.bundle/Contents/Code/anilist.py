"""AniList source (GraphQL API, no key needed).

Each AniDB entry is matched to its AniList entry through the MyAnimeList id AniDB lists (resource type 2); entries without one
fall back to the arm.haglund.dev id mapping (as HAMA does). Because AniList, like AniDB, has one entry per season/cour, its
values sit next to AniDB's in the bundle and work per season too.

Provides: title (English / romaji / native, ranked with the series title languages), original title, description, start date,
score (0-10), main animation studio, genres, tags, episode length, country, adult flag, cover image (poster), banner, and the
Japanese voice cast. Answers are cached in Cache/AniList/ for as long as the AniDB entry (2 days while airing, longer once ended).
"""
import os
import time

from lxml import etree

import settings
import textutil
import models
import downloader
import anidb
import tvdb_v4
import offline_db

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

QUERY = (u"query ($id: Int, $idMal: Int) { Media(id: $id, idMal: $idMal, type: ANIME) { id idMal "
         u"title { romaji english native } description(asHtml: false) startDate { year month day } averageScore stats { scoreDistribution { amount } } genres "
         u"tags { name rank isMediaSpoiler isAdult } studios(isMain: true) { nodes { name isAnimationStudio } } duration "
         u"countryOfOrigin isAdult coverImage { extraLarge large } bannerImage "
         u"characters(sort: [ROLE, RELEVANCE, ID], perPage: 25) { edges { role node { name { full } image { large } } "
         u"ja: voiceActors(language: JAPANESE, sort: [RELEVANCE, ID]) { name { full } image { large } } "
         u"en: voiceActors(language: ENGLISH, sort: [RELEVANCE, ID]) { name { full } image { large } } } } } }")
COUNTRIES = {"JP": "Japan", "KR": "South Korea", "CN": "China", "TW": "Taiwan", "US": "United States"}
REQUEST_LOCK = new_lock()
LAST_REQUEST = [0.0]
PAUSED_UNTIL = [0.0]                 # After a network failure AniList is skipped for a while (cached data is still used)
PAUSE_AFTER_FAILURE = 15 * 60
TIMEOUT = 15


def value(data, key, default=None):
    if hasattr(data, "get"):
        found = data.get(key)
        return default if found is None else found
    return default


def wait_turn():
    """Space AniList requests out (AniList limits requests per minute)."""
    REQUEST_LOCK.acquire()
    try:
        delay = LAST_REQUEST[0] + settings.ANILIST_REQUEST_DELAY - time.time()
        if delay > 0:
            time.sleep(delay)
        LAST_REQUEST[0] = time.time()
    finally:
        REQUEST_LOCK.release()


def current_media(media):
    """False for a cached answer without vote counts (stats.scoreDistribution), so it's downloaded again once; without
       them AniList's rating would count fully in "Weighted by votes". A "not found" answer ({}) is current."""
    return not value(media, "id") or "stats" in media


def cached_json(filename, directory, max_age, fetch, label, current=None):
    """JSON from the disk cache, else fetch() (saved; a "not found" answer is saved as {} so it isn't asked again), else stale.
       current(data): False if a cached copy lacks something the query now asks for; it's then downloaded again (the old
       copy is still used if AniList can't be reached)."""
    cached = downloader.load_cached(filename, directory, max_age)
    if cached:
        try:
            data = tvdb_v4.parse_json(cached)
            if current is None or current(data):
                return data
            Log.Debug("AniList - %s: cached copy is from an older query, downloading it again" % (label))
        except Exception:
            pass
    try:
        if PAUSED_UNTIL[0] > time.time():
            raise Exception("paused after an earlier failure")
        wait_turn()
        data = fetch()
    except Exception as e:
        if getattr(e, "code", None) == 404:
            data = {}
        else:
            if PAUSED_UNTIL[0] <= time.time():
                PAUSED_UNTIL[0] = time.time() + PAUSE_AFTER_FAILURE
                Log.Info("AniList - Not reachable (%s): skipping AniList requests for 15 minutes; cached data is still used" % (e))
            Log.Debug("AniList - %s unavailable: %s" % (label, e))
            stale = downloader.load_stale(filename, directory)
            if stale:
                try:
                    return tvdb_v4.parse_json(stale)
                except Exception:
                    pass
            return None
    try:
        downloader.save_file(tvdb_v4.dump_json(data), filename, directory)
    except Exception as e:
        Log.Debug("AniList - Could not cache %s: %s" % (label, e))
    return data


def query_media(variables):
    body = tvdb_v4.dump_json({"query": QUERY, "variables": variables})
    if isinstance(body, unicode):
        body = body.encode("utf-8")
    response = tvdb_v4.parse_json(downloader.get_url(settings.ANILIST_API_URL, TIMEOUT,
                                                     {"Content-Type": "application/json", "Accept": "application/json"}, body))
    return value(value(response, "data", {}), "Media", {}) or {}


def anilist_id_from_arm(anidb_id, max_age):
    directory = os.path.join("AniList", str(anidb_id))
    data = cached_json("arm.json", directory, max_age, lambda: tvdb_v4.parse_json(downloader.get_url(settings.ANILIST_ARM_URL % (anidb_id), TIMEOUT)) or {},
                       "id mapping for AniDB '%s'" % (anidb_id))
    found = value(data, "anilist")
    return str(found) if textutil.is_digits(found) else None


def reuse_cached(anidb_id, anilist_id, cache_name, max_age):
    """Dataset-based lookups have their own cache file. If an answer cached under another name (from the MAL id or the id
       mapping) is still fresh and for the same AniList id, copy it instead of asking AniList again."""
    directory = os.path.join("AniList", str(anidb_id))
    if downloader.cache_age_of(cache_name, directory) is not None:
        return
    for old_name in ("media.json", "media-mapped.json"):
        try:
            text = downloader.load_cached(old_name, directory, max_age)
            if not text:
                continue
            data = tvdb_v4.parse_json(text)
            if str(value(data, "id") or "") == str(anilist_id):
                downloader.save_file(text, cache_name, directory)
                Log.Debug("AniList - AniDB '%s': reusing the cached answer for AniList %s (%s)" % (anidb_id, anilist_id, old_name))
                return
        except Exception:
            pass


class AniListSeries(models.Series):
    def __init__(self, anidb_id, anidb_record=None):
        models.Series.__init__(self, anidb_id, "Anilist")
        anidb_id = self.id
        if not textutil.is_digits(anidb_id):
            return
        max_age = anidb.cache_age(anidb_id)
        mal_id = anidb_record.mal_id if anidb_record is not None and anidb_record.valid else None
        offline_id = offline_db.anilist_id(anidb_id)
        if offline_id:
            variables, how = {"id": int(offline_id)}, "AniList id %s via anime-offline-database" % (offline_id)
            mal_id = None                                  # Not needed; skips the MAL-id retry below
        elif mal_id:
            variables, how = {"idMal": int(mal_id)}, "MAL id %s" % (mal_id)
        else:
            anilist_id = anilist_id_from_arm(anidb_id, max_age)
            if not anilist_id:
                Log.Debug("AniList - No AniList entry known for AniDB '%s'" % (anidb_id))
                return
            variables, how = {"id": int(anilist_id)}, "AniList id %s" % (anilist_id)
        cache_name = "media-anilist-%s.json" % (offline_id) if offline_id else "media.json"      # Own file: an older MAL-id answer may differ
        if offline_id:
            reuse_cached(anidb_id, offline_id, cache_name, max_age)
        media = cached_json(cache_name, os.path.join("AniList", anidb_id), max_age, lambda: query_media(variables), "AniDB '%s' (%s)" % (anidb_id, how), current_media)
        if mal_id and (not media or not value(media, "id")):
            # AniDB's MAL id can be wrong or missing from AniList: try the id mapping service instead
            anilist_id = anilist_id_from_arm(anidb_id, max_age)
            if anilist_id:
                variables, how = {"id": int(anilist_id)}, "AniList id %s via id mapping" % (anilist_id)
                media = cached_json("media-mapped.json", os.path.join("AniList", anidb_id), max_age, lambda: query_media(variables), "AniDB '%s' (%s)" % (anidb_id, how), current_media)
        if not media or not value(media, "id"):
            Log.Debug("AniList - No data for AniDB '%s' (%s)" % (anidb_id, how))
            return
        self.valid = True
        self.parse(media)
        if "anime-offline-database" not in how:
            Log.Debug("AniList - AniDB '%s' -> AniList %s (%s): '%s'" % (anidb_id, value(media, "id"), how, self.title))

    def parse(self, media):
        anidb_id = self.id
        titles = value(media, "title", {})
        candidates = [(value(titles, "english"), "en", False), (value(titles, "romaji"), "x-jat", True), (value(titles, "native"), "ja", False)]
        candidates = [c for c in candidates if c[0]]
        if candidates:
            best = sorted(candidates, key=lambda c: textutil.title_rank(c[1], c[2], settings.SERIES_LANGUAGE_PRIORITY))[0]
            self.title = textutil.clean_text(best[0])
            self.title_lang = best[1]
            self.title_main = best[2]
            for text, lang, is_main in candidates:
                if lang == settings.ORIGINAL_TITLE_LANGUAGE:
                    self.original_title = textutil.clean_text(text)
        self.summary = textutil.clean_summary(textutil.strip_html(value(media, "description")))
        start = value(media, "startDate", {})
        if value(start, "year"):
            self.originally_available_at = "%04d-%02d-%02d" % (value(start, "year"), value(start, "month") or 1, value(start, "day") or 1)
        if value(media, "averageScore"):
            self.rating = value(media, "averageScore") / 10.0
            scored = 0
            for bucket in value(value(media, "stats", {}), "scoreDistribution", []):
                scored = scored + (value(bucket, "amount") or 0)          # Users who scored it
            if scored:
                self.rating_votes = scored
        studios = value(value(media, "studios", {}), "nodes", [])
        animation = [s for s in studios if value(s, "isAnimationStudio") and value(s, "name")] or [s for s in studios if value(s, "name")]
        if animation:
            self.studio = value(animation[0], "name")
        self.genres = value(media, "genres") or None
        tags = [value(t, "name") for t in value(media, "tags", []) if value(t, "name") and not value(t, "isMediaSpoiler") and not value(t, "isAdult")
                and (value(t, "rank") or 0) >= settings.ANILIST_MINIMUM_TAG_RANK]
        self.tags = tags or None
        if textutil.is_digits(value(media, "duration")):
            self.duration = int(value(media, "duration")) * 60000
        if COUNTRIES.get(value(media, "countryOfOrigin")):
            self.countries = [COUNTRIES[value(media, "countryOfOrigin")]]
        if value(media, "isAdult"):
            self.content_rating = "X"
            self.content_rating_adult = True                 # AniList's adult flag: a fact, not an estimate

        cover = value(media, "coverImage", {})
        poster = value(cover, "extraLarge") or value(cover, "large")
        if poster:
            posters = models.new_images()
            models.add_image(posters, poster, "", os.path.join("AniList", anidb_id, "posters"), None, {"id": "1"})
            self.posters = posters
            season = models.new_images()
            models.add_image(season, poster, "", os.path.join("AniList", anidb_id, "posters"), None, {"id": "1", "season": "1"})   # Same file as the show poster: one download (AniDB does the same)
            self.season = season
        if value(media, "bannerImage"):
            banners = models.new_images()
            models.add_image(banners, value(media, "bannerImage"), "", os.path.join("AniList", anidb_id, "banners"), None, {"id": "1"})
            self.banners = banners

        roles = etree.Element("Roles")
        for edge in value(value(media, "characters", {}), "edges", []):
            node = value(edge, "node", {})
            character = textutil.clean_text(value(value(node, "name", {}), "full", ""))
            character_pic = value(value(node, "image", {}), "large", "") or ""
            # "ja"/"en"; an older cached copy has "voiceActors" (Japanese only) until AniList is downloaded again
            for language, actors in (("ja", value(edge, "ja", None) or value(edge, "voiceActors", [])), ("en", value(edge, "en", []))):
                for actor in (actors or [])[:1]:
                    name = textutil.clean_text(value(value(actor, "name", {}), "full", ""))
                    if name:
                        etree.SubElement(roles, "Role", character_name=character or "", seiyuu_name=name, lang=language, character_pic=character_pic,
                                         seiyuu_pic=value(value(actor, "image", {}), "large", "") or "")
        if len(roles):
            self.roles = roles
