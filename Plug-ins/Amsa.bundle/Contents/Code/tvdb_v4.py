"""TVDB source using TheTVDB's v4 JSON API (https://api4.thetvdb.com/v4/).

Produces the same fields as tvdb.TvDBSeries (the v1 XML source) so the rest of AMSA doesn't care which API was used.
Responses are cached on disk under Cache/TvDB4/<id>/ like every other source; if v4 can't provide a series at all,
sources.py falls back to the v1 API for that series.

Episode writers/directors need one request per episode (episodes/<id>/extended); bundle.map_crew() asks for them only for
episodes on disk, via episode_crew(), and caches each answer for settings.TVDB4_CREW_CACHE.
Not provided: a 0-10 rating (v4's "score" is a popularity count, not a rating).
"""
import os
import re
import time
import urllib2

from lxml import etree

import environment
import settings
import textutil
import models
import downloader
import tvdb

try:
    import json
    def parse_json(text):
        return json.loads(text)
    def dump_json(value):
        return json.dumps(value)
except ImportError:          # Plex's own JSON API if the sandbox refuses the module
    def parse_json(text):
        return JSON.ObjectFromString(text)
    def dump_json(value):
        return JSON.StringFromObject(value)

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

TOKEN_FILE = "tvdb4-token.txt"
TOKEN_LOCK = new_lock()
TOKEN = {"value": None, "expires": 0.0, "login_blocked_until": 0.0, "paused_until": 0.0}
LOGIN_RETRY = 3600           # After a failed login, use v1 for an hour instead of retrying on every show
NETWORK_RETRY = 15 * 60      # After a network failure (server down/unreachable), use v1 for 15 minutes instead of waiting on timeouts
MAX_EPISODE_PAGES = 20       # 500 episodes per page


def image_url(path):
    """v4 gives some images as full URLs and others (notably episode images) as paths like '/banners/episodes/1/2.jpg'."""
    if not path:
        return path
    if path.startswith("//"):
        return "https:" + path
    if path.startswith("/"):
        return settings.TVDB4_ARTWORK_URL + path
    return path


class TvdbV4Error(Exception):
    def __init__(self, message, code=None):
        Exception.__init__(self, message)
        self.code = code              # HTTP status when the server answered with an error, else None


# Authentication ######################################################################################################################################################
def token(force_new=False):
    """Bearer token: memory, then Cache/tvdb4-token.txt, then a new login. Raises TvdbV4Error if v4 is unavailable."""
    TOKEN_LOCK.acquire()
    try:
        now = time.time()
        if not force_new and TOKEN["value"] and TOKEN["expires"] > now:
            return TOKEN["value"]
        if not force_new:
            try:
                path = downloader.cache_path(TOKEN_FILE)
                if Data.Exists(path):
                    content = Data.Load(path)
                    if not isinstance(content, basestring):
                        content = content.decode("utf-8")
                    parts = content.strip().split("\t", 1)
                    if len(parts) == 2 and textutil.safe_float(parts[0]) > now:
                        TOKEN["value"] = parts[1]
                        TOKEN["expires"] = textutil.safe_float(parts[0])
                        return TOKEN["value"]
            except Exception as e:
                Log.Debug("TvDB4 - Could not read saved token: %s" % (e))
        if TOKEN["login_blocked_until"] > now:
            raise TvdbV4Error("login failed recently; using TVDB v1 until %s" % (textutil.when_text(TOKEN["login_blocked_until"])))
        try:
            body = downloader.get_url(settings.TVDB4_API_URL + "login", settings.DEFAULT_TIMEOUT, {"Content-Type": "application/json", "Accept": "application/json"},
                                      dump_json({"apikey": settings.TVDB4_API_KEY}))
            value = parse_json(body)["data"]["token"]
        except Exception as e:
            TOKEN["login_blocked_until"] = now + LOGIN_RETRY
            Log.Warn("TvDB4 - Login failed (%s); using TVDB v1 for the next hour" % (e))
            raise TvdbV4Error("login failed: %s" % (e))
        TOKEN["value"] = value
        TOKEN["expires"] = now + settings.TVDB4_TOKEN_TTL
        try:
            Data.Save(downloader.cache_path(TOKEN_FILE), "%.0f\t%s" % (TOKEN["expires"], value))
        except Exception as e:
            environment.write_failed(os.path.join(settings.DATA_ITEMS_PATH, downloader.cache_path(TOKEN_FILE)), e, "TvDB4")
        Log.Info("TvDB4 - Logged in")
        return value
    finally:
        TOKEN_LOCK.release()


def api_get(path, timeout=settings.DEFAULT_TIMEOUT):
    """Parsed JSON response for an API path (e.g. 'series/123/extended'). Renews the token once on 401. Raises on failure."""
    url = settings.TVDB4_API_URL + path
    if TOKEN["paused_until"] > time.time():
        raise TvdbV4Error("TVDB v4 unreachable recently; using v1 until %s" % (textutil.when_text(TOKEN["paused_until"])))
    for attempt in (1, 2):
        headers = {"Authorization": "Bearer %s" % (token(attempt == 2)), "Accept": "application/json"}
        try:
            Log.Debug("TvDB4 - Requesting '%s'" % (url))
            response = parse_json(downloader.get_url(url, timeout, headers))
        except urllib2.HTTPError as e:
            if e.code == 401 and attempt == 1:
                Log.Debug("TvDB4 - Token rejected, logging in again")
                continue
            raise TvdbV4Error("HTTP %s for %s" % (e.code, path), e.code)
        except TvdbV4Error:
            raise
        except Exception as e:
            TOKEN["paused_until"] = time.time() + NETWORK_RETRY
            Log.Warn("TvDB4 - Network error (%s); using TVDB v1 for the next %s minutes" % (e, int(NETWORK_RETRY / 60)))
            raise TvdbV4Error("network error: %s" % (e))
        if response.get("status") == "failure" or response.get("data") is None:
            raise TvdbV4Error("no data for %s: %s" % (path, response.get("message")))
        return response
    raise TvdbV4Error("authentication failed for %s" % (path))


STALE_OK = {}                     # TVDB series id -> time until which an expired cached copy may be used as it is (allow_stale)
STALE_USED = {}                   # TVDB series ids an update used an expired copy of (end_stale)


def allow_stale(series_ids, seconds=900):
    """Background mode: while an update runs, an expired cached copy of these series (older than the 2-day cache)
       is used as it is instead of being downloaded during the update; the updater then queues the download in the
       background (end_stale), which refreshes the show if anything changed. A copy that was never cached is still
       downloaded, and a forced directory (a background refresh downloading it) is never served stale."""
    until = time.time() + seconds
    for series_id in series_ids or []:
        STALE_OK[str(series_id)] = until
        if str(series_id) in STALE_USED:
            del STALE_USED[str(series_id)]


def end_stale(series_ids):
    """The ids among these whose expired copy the update used (to download in the background); forgets them."""
    used = []
    for series_id in series_ids or []:
        series_id = str(series_id)
        if series_id in STALE_OK:
            del STALE_OK[series_id]
        if series_id in STALE_USED:
            del STALE_USED[series_id]
            used.append(series_id)
    return used


def series_of(directory):
    """'TvDB4/81797' or 'TvDB4/81797/seasons' -> '81797'; anything else -> None."""
    parts = str(directory).replace("\\", "/").split("/")
    if len(parts) > 1 and parts[0] == "TvDB4" and textutil.is_digits(parts[1]):
        return parts[1]
    return None


def load_cached_or_stale(filename, directory, max_age):
    """Fresh cached copy; else, for a series allow_stale() covers, the expired copy (noted for end_stale); else None."""
    cached = downloader.load_cached(filename, directory, max_age)
    if cached:
        return cached
    series_id = series_of(directory)
    if series_id and STALE_OK.get(series_id, 0) > time.time() and not downloader.is_forced(directory):
        stale = downloader.load_stale(filename, directory, True)
        if stale:
            STALE_USED[series_id] = True
            return stale
    return None


def cached_api(path, filename, directory, fetch=None):
    """Like downloader.xml_from_url for JSON: fresh cache, else the API, else a stale cached copy. Returns parsed data or None."""
    cached = load_cached_or_stale(filename, directory, settings.DEFAULT_CACHE)
    if cached:
        try:
            return parse_json(cached)
        except Exception:
            pass
    try:
        data = fetch() if fetch else api_get(path)["data"]
        downloader.save_file(dump_json(data), filename, directory)
        return data
    except Exception as e:
        Log.Info("TvDB4 - %s unavailable: %s" % (path, e))
        stale = downloader.load_stale(filename, directory)
        if stale:
            try:
                return parse_json(stale)
            except Exception:
                pass
    return None


def fetch_episodes(tvdb_id):
    """All aired-order episodes with English titles where available (paged, 500 per page)."""
    episodes = []
    for language_path in ("/" + settings.TVDB4_LANGUAGE, ""):
        try:
            for page in range(MAX_EPISODE_PAGES):
                response = api_get("series/%s/episodes/default%s?page=%s" % (tvdb_id, language_path, page))
                episodes.extend(response["data"].get("episodes") or [])
                links = response.get("links") or {}
                if not links.get("next"):
                    break
            return {"episodes": episodes}
        except TvdbV4Error as e:
            if language_path == "":
                raise
            Log.Debug("TvDB4 - English episode list unavailable for %s (%s), trying original language" % (tvdb_id, e))
            episodes = []


# Series ##############################################################################################################################################################
def value(record, key, default=None):
    """record[key] for JSON objects, tolerating missing keys, nulls and non-objects."""
    if record is None or not hasattr(record, "get"):
        return default
    found = record.get(key)
    return default if found is None else found


class TvDB4Series(models.Series):
    def __init__(self, tvdb_id):
        models.Series.__init__(self, tvdb_id, "Tvdb")
        self.api = "v4"
        self.log_parts = []                             # Logged as one line by series()
        tvdb_id = self.id
        if not textutil.is_digits(tvdb_id):
            return
        directory = os.path.join("TvDB4", tvdb_id)
        data = cached_api("series/%s/extended" % (tvdb_id), "series.json", directory)
        if not data or not value(data, "name"):
            Log.Info("TvDB4 - No v4 data for TVDB id '%s'" % (tvdb_id))
            return
        self.valid = True
        translation = cached_api("series/%s/translations/%s" % (tvdb_id, settings.TVDB4_LANGUAGE), "translation-%s.json" % (settings.TVDB4_LANGUAGE), directory) or {}

        self.title = textutil.clean_text(value(translation, "name") or value(data, "name"))
        self.title_lang = textutil.anidb_language(settings.TVDB4_LANGUAGE) if value(translation, "name") else None   # Untranslated names are in an unknown language
        self.summary = value(translation, "overview") or value(data, "overview")
        self.aliases = self.parse_aliases(data)
        self.originally_available_at = value(data, "firstAired")
        self.studio = self.pick_studio(data)
        country = textutil.country_name(value(data, "originalCountry"))
        if country:
            self.countries = [country]
        genres = [value(genre, "name") for genre in value(data, "genres", []) if value(genre, "name")]
        self.genres = genres or None
        self.content_rating = self.pick_content_rating(value(data, "contentRatings", []))
        self.content_ratings = {}                       # Country (TVDB's 3 letters, e.g. "gbr") -> official rating there
        for rating in value(data, "contentRatings", []) or []:
            if value(rating, "country") and value(rating, "name") and value(rating, "country").lower() not in self.content_ratings:
                self.content_ratings[value(rating, "country").lower()] = textutil.clean_text(value(rating, "name"))
        self.parse_roles(value(data, "characters", []))
        self.parse_artwork(data)
        for season in value(data, "seasons", []):
            if value(value(season, "type"), "type", "official") == "official" and value(season, "number") is not None and value(season, "id") is not None:
                self.season_ids[str(value(season, "number"))] = str(value(season, "id"))

        episodes = value(cached_api("series/%s/episodes" % (tvdb_id), "episodes-%s.json" % (settings.TVDB4_LANGUAGE), directory, lambda: fetch_episodes(tvdb_id)), "episodes", [])
        for item in episodes:
            try:
                episode = TvDB4Episode(item, tvdb_id)
                if episode.season is not None and episode.number is not None:
                    self.episodes.append(episode)
            except Exception as e:
                Log.Debug("TvDB4 - Skipping malformed episode in '%s': %s" % (tvdb_id, e))
        self.episode_count = len([e for e in self.episodes if e.season != "00"])
        self.special_count = len([e for e in self.episodes if e.season == "00"])
        runtime = value(data, "averageRuntime")
        if textutil.is_digits(runtime):
            self.duration = int(runtime) * 60000                # Plex: one episode's length in milliseconds

    def parse_aliases(self, data):
        """TVDB's other names for the series: its aliases ({"language", "name"} or plain text) and its untranslated name."""
        names = []
        for alias in value(data, "aliases", []) or []:
            name = value(alias, "name") if hasattr(alias, "get") else alias
            if name and name not in names:
                names.append(textutil.clean_text(name))
        if value(data, "name") and value(data, "name") != self.title:
            names.append(textutil.clean_text(value(data, "name")))
        return names

    def pick_studio(self, data):
        """The animation studio from v4's company list (companyType "Studio"), else the original TV network as before."""
        studios = []
        for company in value(data, "companies", []):
            company_type = value(company, "companyType", {})
            type_name = (value(company_type, "companyTypeName") or "").lower()
            if (type_name == "studio" or value(company_type, "companyTypeId") == 2 or value(company, "primaryCompanyType") == 2) and value(company, "name"):
                studios.append(value(company, "name"))
        network = value(value(data, "originalNetwork") or value(data, "latestNetwork"), "name")
        self.log_parts.append("studio %s (network %s)" % (", ".join(studios) or "none listed", network))
        return studios[0] if studios else network

    def pick_content_rating(self, ratings):
        """US rating if there is one (v1 gave US TV ratings such as TV-14), else the first."""
        names = [(value(r, "country", ""), value(r, "name")) for r in ratings if value(r, "name")]
        for country, name in names:
            if country.lower() == "usa":
                return name
        return names[0][1] if names else None

    def parse_roles(self, characters):
        """Cast (actors and their characters) in TVDB's order; same <Role> format as AniDB's seiyuu list."""
        actors = [c for c in characters if is_person_type(c, "Actor", 3) and value(c, "personName")]
        actors = sorted(actors, key=lambda c: (0 if value(c, "isFeatured") else 1, textutil.safe_float(value(c, "sort", 999))))
        roles = etree.Element("Roles")
        seen = set()
        for character in actors:
            person = textutil.clean_text(value(character, "personName"))
            role = textutil.clean_text(value(character, "name", ""))
            if (person, role) in seen:
                continue
            seen.add((person, role))
            etree.SubElement(roles, "Role", character_name=role, seiyuu_name=person, seiyuu_pic=image_url(value(character, "personImgURL", "")) or "",
                             character_pic=image_url(value(character, "image", "")) or "")
        if len(roles):
            self.roles = roles

    def parse_artwork(self, data):
        tvdb_id = self.id
        images = {"art": models.new_images(), "posters": models.new_images(), "banners": models.new_images(), "season": models.new_images()}
        kinds = {settings.TVDB4_ART_SERIES_BACKGROUND: "art", settings.TVDB4_ART_SERIES_POSTER: "posters", settings.TVDB4_ART_SERIES_BANNER: "banners",
                 settings.TVDB4_ART_SEASON_BANNER: "banners"}
        counters = {"art": 2, "posters": 2, "banners": 2}          # id 1 is reserved for the series' main poster
        main_poster = image_url(value(data, "image"))
        seen = set()
        season_numbers = {}
        for season in value(data, "seasons", []):
            if value(value(season, "type"), "type", "official") == "official" and value(season, "number") is not None:
                season_numbers[value(season, "id")] = value(season, "number")
        season_seen = []
        artworks = sorted(value(data, "artworks", []), key=lambda a: -textutil.safe_float(value(a, "score", 0)))
        for artwork in artworks:
            url = image_url(value(artwork, "image"))
            art_type = value(artwork, "type")
            if not url or url in seen:
                continue
            thumb = image_url(value(artwork, "thumbnail")) or None
            language = textutil.short_language(value(artwork, "language", ""))
            # What TVDB says about the image, for the image checks (image_choice): text or not, and size
            facts = {"text": {True: "1", False: "0"}.get(value(artwork, "includesText"), ""),
                     "width": value(artwork, "width") or "", "height": value(artwork, "height") or ""}
            if art_type in kinds:
                kind = kinds[art_type]
                if kind == "posters" and url == main_poster:
                    image_id = 1
                else:
                    image_id = counters[kind]
                    counters[kind] = counters[kind] + 1
                extra = {"id": image_id, "lang": language}
                extra.update(facts)
                models.add_image(images[kind], url, "", os.path.join(settings.TVDB_IMAGES_FOLDER, tvdb_id, kind), thumb, extra)
                seen.add(url)
            elif art_type == settings.TVDB4_ART_SEASON_POSTER and value(artwork, "seasonId") in season_numbers:
                number = str(season_numbers[value(artwork, "seasonId")])
                season_seen.append(number)
                models.add_image(images["season"], url, "", os.path.join(settings.TVDB_IMAGES_FOLDER, tvdb_id, "season"), thumb,
                                 {"id": season_seen.count(number), "season": number, "lang": language,
                                  # Hints for matching sets (metadata_writer.mark_poster_sets): upload order and time, text flag
                                  "artwork_id": value(artwork, "id") or "", "updated": value(artwork, "updatedAt") or "",
                                  "text": facts["text"], "width": facts["width"], "height": facts["height"]})
                seen.add(url)
        # Season records carry their own poster even when the artwork list doesn't link it to a season
        for season in value(data, "seasons", []):
            number = season_numbers.get(value(season, "id"))
            url = image_url(value(season, "image"))
            if number is not None and url and url not in seen:
                season_seen.append(str(number))
                models.add_image(images["season"], url, "", os.path.join(settings.TVDB_IMAGES_FOLDER, tvdb_id, "season"), None, {"id": season_seen.count(str(number)), "season": str(number)})
                seen.add(url)
        if main_poster and main_poster not in seen:
            models.add_image(images["posters"], main_poster, "", os.path.join(settings.TVDB_IMAGES_FOLDER, tvdb_id, "posters"), None, {"id": 1})
        self.log_parts.append("artwork %s posters, %s backgrounds, %s banners, %s season posters"
                              % (len(images["posters"]), len(images["art"]), len(images["banners"]), len(images["season"])))
        if len(images["art"]) or len(images["posters"]) or len(images["banners"]) or len(images["season"]):
            self.art = images["art"]
            self.posters = images["posters"]
            self.banners = images["banners"]
            self.season = images["season"]


class TvDB4Episode(models.Episode):
    def __init__(self, data, tvdb_id):
        models.Episode.__init__(self)
        if value(data, "id") is not None:
            self.source_id = str(value(data, "id"))
        if value(data, "name"):
            self.title = textutil.clean_text(value(data, "name"))
            self.title_lang = textutil.anidb_language(settings.TVDB4_LANGUAGE)      # Episodes are requested in the agent language
        if value(data, "overview"):
            self.summary = value(data, "overview")
        if value(data, "aired"):
            self.originally_available_at = value(data, "aired")
        absolute = value(data, "absoluteNumber")
        if textutil.is_digits(absolute) and int(absolute) > 0:
            self.absolute_index = int(absolute)
        image = image_url(value(data, "image"))
        if image:
            thumbs = models.new_images()
            root, extension = os.path.splitext(image)
            models.add_image(thumbs, image, "", os.path.join(settings.TVDB_IMAGES_FOLDER, tvdb_id, "thumbs"), root + "_t" + extension, {"id": "1"})
            self.thumbs = thumbs
        if value(data, "number") is not None:
            self.number = str(value(data, "number")).zfill(2)
        if value(data, "seasonNumber") is not None:
            self.season = str(value(data, "seasonNumber")).zfill(2)


# Episode crew ########################################################################################################################################################
def is_person_type(character, name, type_id):
    """v4 'characters' entries cover cast and crew; peopleType is e.g. "Actor"/"Writer"/"Director" (type ids 3/2/1)."""
    people_type = value(character, "peopleType")
    if people_type:
        return people_type.lower() == name.lower()
    return value(character, "type") == type_id


def crew_names(characters, name, type_id):
    names = []
    for character in sorted(characters, key=lambda c: textutil.safe_float(value(c, "sort", 999))):
        person = value(character, "personName")
        if person and is_person_type(character, name, type_id):
            person = textutil.clean_text(person)
            if person not in names:
                names.append(person)
    return names


def season_text(series_id, season_id):
    """{"name": .., "overview": ..} for one v4 season in the agent's language, cached on disk; None if unavailable right now."""
    directory = os.path.join("TvDB4", str(series_id), "seasons")
    filename = "%s-%s.json" % (season_id, settings.TVDB4_LANGUAGE)
    cached = load_cached_or_stale(filename, directory, settings.DEFAULT_CACHE)
    if cached:
        try:
            return parse_json(cached)
        except Exception:
            pass
    try:
        data = api_get("seasons/%s/translations/%s" % (season_id, settings.TVDB4_LANGUAGE))["data"]
        text = {"name": textutil.clean_text(value(data, "name") or ""), "overview": value(data, "overview") or ""}
    except TvdbV4Error as e:
        if e.code != 404:
            Log.Debug("TvDB4 - Season %s text unavailable: %s" % (season_id, e))
            stale = downloader.load_stale(filename, directory)
            if stale:
                try:
                    return parse_json(stale)
                except Exception:
                    pass
            return None
        text = {"name": "", "overview": ""}             # No English text for this season: remember that
    try:
        downloader.save_file(dump_json(text), filename, directory)
    except Exception as e:
        Log.Debug("TvDB4 - Could not save season %s text: %s" % (season_id, e))
    return text


def cached_crew(series_id, episode_id):
    """(crew, fresh) from the cache only, never downloading: crew is None if there's no copy; fresh is False if the copy is
       older than settings.TVDB4_CREW_CACHE (still used, and downloaded again in the background)."""
    directory = os.path.join("TvDB4", str(series_id), "crew")
    filename = "%s.json" % (episode_id)
    text = downloader.load_cached(filename, directory, settings.TVDB4_CREW_CACHE)
    fresh = bool(text)
    if not text:
        text = downloader.load_stale(filename, directory, True)
    if not text:
        return None, False
    try:
        return parse_json(text), fresh
    except Exception:
        return None, False


def episode_crew(series_id, episode_id):
    """{"writers": [...], "directors": [...]} for one episode, cached on disk; None if unavailable right now."""
    directory = os.path.join("TvDB4", str(series_id), "crew")
    filename = "%s.json" % (episode_id)
    cached = downloader.load_cached(filename, directory, settings.TVDB4_CREW_CACHE)
    if cached:
        try:
            return parse_json(cached)
        except Exception:
            pass
    try:
        data = api_get("episodes/%s/extended" % (episode_id))["data"]
        characters = value(data, "characters", [])
        crew = {"writers": crew_names(characters, "Writer", 2), "directors": crew_names(characters, "Director", 1)}
    except TvdbV4Error as e:
        if e.code != 404:
            Log.Debug("TvDB4 - Crew for episode %s unavailable: %s" % (episode_id, e))
            stale = downloader.load_stale(filename, directory)
            if stale:
                try:
                    return parse_json(stale)
                except Exception:
                    pass
            return None
        crew = {"writers": [], "directors": []}         # Episode unknown to v4: remember that instead of asking again on every refresh
    try:
        downloader.save_file(dump_json(crew), filename, directory)
    except Exception as e:
        Log.Debug("TvDB4 - Could not save crew for episode %s: %s" % (episode_id, e))
    return crew


# Search ##############################################################################################################################################################
def search_series(query):
    """TVDB series matching query: [{"id", "name", "year", "titles": [name, aliases, translations]}], cached on disk for 2 days.
       Returns [] if TVDB v4 is unavailable (never raises)."""
    if not query:
        return []
    encoded = textutil.safe_unicode(query).encode("utf-8")
    filename = re.sub(r"[^a-z0-9]+", "_", textutil.safe_unicode(query).lower().encode("ascii", "replace").decode("ascii"))[:80].strip("_") or "query"
    path = "search?query=%s&type=series" % (urllib2.quote(encoded))
    try:
        data = cached_api(path, "%s.json" % (filename), os.path.join("TvDB4", "search"), lambda: api_get(path, settings.TVDB4_SEARCH_TIMEOUT)["data"])
    except Exception:
        Log.Debug("TvDB4 - Search for '%s' failed: %s" % (query, textutil.exception_text()))
        data = None
    found = []
    for item in data or []:
        tvdb_id = str(value(item, "tvdb_id") or "")
        if not tvdb_id:
            tvdb_id = str(value(item, "id", "")).replace("series-", "")
        if not textutil.is_digits(tvdb_id):
            continue
        titles = [value(item, "name")]
        translations = value(item, "translations", {})
        if hasattr(translations, "get"):
            titles.append(translations.get(settings.TVDB4_LANGUAGE))
            for language in translations:
                titles.append(translations[language])
        titles.extend(value(item, "aliases", []))
        unique = []
        for title in titles:
            if title and hasattr(title, "strip") and title not in unique:
                unique.append(title)
        name = value(translations, settings.TVDB4_LANGUAGE) or value(item, "name")
        year = value(item, "year") or (value(item, "first_air_time") or "")[:4]
        found.append({"id": tvdb_id, "name": textutil.clean_text(name or tvdb_id), "year": str(year) if textutil.is_digits(year) else None, "titles": unique})
    return found


# Choosing the API ####################################################################################################################################################
def series(tvdb_id):
    """TVDB record from v4, falling back to v1 for this series if v4 can't provide it (login failed, server down, no data)."""
    try:
        record = TvDB4Series(tvdb_id)
        if record.valid:
            Log.Debug("TvDB4 - %s: %s" % (tvdb_id, "; ".join(getattr(record, "log_parts", None) or ["loaded"])))
            return record
    except Exception:
        Log.Warn("TvDB4 - v4 failed for %s: %s" % (tvdb_id, textutil.exception_text()))
    Log.Info("TvDB4 - Falling back to TVDB v1 for %s" % (tvdb_id))
    record = tvdb.TvDBSeries(tvdb_id)
    record.api = "v1"
    return record
