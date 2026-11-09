"""Extra episode sources, used to fill gaps only (episode_fill.py decides when):

  * MyAnimeList through Jikan (https://api.jikan.moe/v4, no key): episode titles in English, romaji and Japanese, air dates.
    GET anime/<MAL id>/episodes?page=N (100 per page). Jikan allows 3 requests/second and 60/minute; AMSA waits 1.2s.
  * Kitsu (https://kitsu.io/api/edge, no key): episode titles (en / en_jp / ja_jp), synopses, air dates.
    GET anime/<Kitsu id>/episodes?page[limit]=20&page[offset]=N&sort=number. AMSA waits 0.5s between requests.
  * AnimeThemes (https://api.animethemes.moe, no key): opening/ending song titles and artists, for the credit specials.
    GET anime?filter[has]=resources&filter[site]=AniDB&filter[external_id]=<AniDB id>&include=animethemes.song.artists

All three are keyed by AniDB id. MAL and Kitsu ids come from anime-offline-database (MAL also from AniDB itself).
Episode numbers are the AniDB entry's own regular episode numbers (MAL and Kitsu number each entry from 1, like AniDB);
openings/endings are matched to the AniDB entry's credit episodes in order (1st OP theme -> 1st AniDB opening, ...).
Answers are cached per AniDB entry for the AniDB cache age (2 days while airing, longer once ended); a failed source is
skipped for 15 minutes.
"""
import os
import time

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

JIKAN_URL = "https://api.jikan.moe/v4/anime/%s/episodes?page=%s"
KITSU_URL = "https://kitsu.io/api/edge/anime/%s/episodes?page%%5Blimit%%5D=20&page%%5Boffset%%5D=%s&sort=number"
ANIMETHEMES_URL = ("https://api.animethemes.moe/anime?filter%%5Bhas%%5D=resources&filter%%5Bsite%%5D=AniDB"
                   "&filter%%5Bexternal_id%%5D=%s&include=animethemes.song.artists")
TIMEOUT = 15
PAUSE_AFTER_FAILURE = 15 * 60
MAX_PAGES = 30


def value(data, key, default=None):
    if hasattr(data, "get"):
        found = data.get(key)
        return default if found is None else found
    return default


class Throttle():
    """Request spacing and a pause after failures, per source."""
    def __init__(self, name, delay):
        self.name = name
        self.delay = delay
        self.lock = new_lock()
        self.last = 0.0
        self.paused_until = 0.0

    def wait(self):
        self.lock.acquire()
        try:
            pause = self.last + self.delay - time.time()
            if pause > 0:
                time.sleep(pause)
            self.last = time.time()
        finally:
            self.lock.release()

    def available(self):
        return self.paused_until <= time.time()

    def failed(self, error):
        if self.available():
            Log.Info("%s - Not reachable (%s): skipped for 15 minutes; cached data is still used" % (self.name, error))
        self.paused_until = time.time() + PAUSE_AFTER_FAILURE


JIKAN = Throttle("MyAnimeList", 1.2)
KITSU = Throttle("Kitsu", 0.5)
ANIMETHEMES = Throttle("AnimeThemes", 1.0)


def get_json(throttle, url, headers=None):
    throttle.wait()
    return tvdb_v4.parse_json(downloader.get_url(url, TIMEOUT, headers))


def cached_json(throttle, filename, directory, max_age, fetch):
    """JSON from the disk cache, else fetch() (saved; "not found" is saved as {}), else the stale copy, else None."""
    cached = downloader.load_cached(filename, directory, max_age)
    if cached:
        try:
            return tvdb_v4.parse_json(cached)
        except Exception:
            pass
    try:
        if not throttle.available():
            raise Exception("paused after an earlier failure")
        data = fetch()
    except Exception as e:
        if getattr(e, "code", None) == 404:
            data = {}
        else:
            throttle.failed(e)
            stale = downloader.load_stale(filename, directory, True)
            if stale:
                try:
                    return tvdb_v4.parse_json(stale)
                except Exception:
                    pass
            return None
    try:
        downloader.save_file(tvdb_v4.dump_json(data), filename, directory)
    except Exception:
        pass
    return data


def best_title(candidates):
    """(title, lang) by the episode title languages; candidates = [(text, lang)]."""
    candidates = [c for c in candidates if c[0]]
    if not candidates:
        return None, None
    best = sorted(candidates, key=lambda c: textutil.title_rank(c[1], False, settings.EPISODE_LANGUAGE_PRIORITY))[0]
    return textutil.clean_text(best[0]), best[1]


def air_date(text):
    return text[:10] if text and len(text) >= 10 and text[4] == "-" else None


class MalEpisodes(models.Series):
    """Episode titles and air dates from MyAnimeList (Jikan) for one AniDB entry."""
    def __init__(self, anidb_id, anidb_record=None):
        models.Series.__init__(self, anidb_id, "Mal")
        anidb_id = self.id
        mal = offline_db.mal_id(anidb_id) or (anidb_record.mal_id if anidb_record is not None and anidb_record.valid else None)
        if not textutil.is_digits(mal):
            return
        directory = os.path.join("MAL", anidb_id)

        def fetch():
            items = []
            page = 1
            while page <= MAX_PAGES:
                data = get_json(JIKAN, JIKAN_URL % (mal, page))
                items.extend(value(data, "data", []))
                if not value(value(data, "pagination", {}), "has_next_page"):
                    break
                page = page + 1
            return {"mal_id": int(mal), "episodes": items}

        data = cached_json(JIKAN, "episodes-%s.json" % (mal), directory, anidb.cache_age(anidb_id), fetch)
        if not data:
            return
        for item in value(data, "episodes", []):
            if not textutil.is_digits(value(item, "mal_id")):
                continue
            episode = models.Episode()
            episode.number = str(value(item, "mal_id"))
            episode.title, episode.title_lang = best_title([(value(item, "title"), "en"), (value(item, "title_romanji"), "x-jat"),
                                                            (value(item, "title_japanese"), "ja")])
            episode.originally_available_at = air_date(value(item, "aired"))
            self.episodes.append(episode)
        self.valid = len(self.episodes) > 0
        Log.Debug("MyAnimeList - AniDB '%s' -> MAL %s: %s episodes" % (anidb_id, mal, len(self.episodes)))


class KitsuEpisodes(models.Series):
    """Episode titles, synopses and air dates from Kitsu for one AniDB entry."""
    def __init__(self, anidb_id):
        models.Series.__init__(self, anidb_id, "Kitsu")
        anidb_id = self.id
        kitsu = offline_db.kitsu_id(anidb_id)
        if not kitsu:
            return
        directory = os.path.join("Kitsu", anidb_id)

        def fetch():
            items = []
            offset = 0
            pages = 0
            while pages < MAX_PAGES * 5:
                data = get_json(KITSU, KITSU_URL % (kitsu, offset), {"Accept": "application/vnd.api+json"})
                batch = value(data, "data", [])
                items.extend(batch)
                pages = pages + 1
                if not batch or not value(value(data, "links", {}), "next"):
                    break
                offset = offset + len(batch)
            return {"kitsu_id": int(kitsu), "episodes": items}

        data = cached_json(KITSU, "episodes-%s.json" % (kitsu), directory, anidb.cache_age(anidb_id), fetch)
        if not data:
            return
        for item in value(data, "episodes", []):
            attributes = value(item, "attributes", {})
            number = value(attributes, "number")
            if not textutil.is_digits(number):
                continue
            titles = value(attributes, "titles", {}) or {}
            episode = models.Episode()
            episode.number = str(number)
            episode.title, episode.title_lang = best_title([(value(titles, "en") or value(titles, "en_us"), "en"), (value(titles, "en_jp"), "x-jat"),
                                                            (value(titles, "ja_jp"), "ja")])
            if not episode.title and value(attributes, "canonicalTitle"):
                episode.title = textutil.clean_text(value(attributes, "canonicalTitle"))
            summary = value(attributes, "synopsis") or value(attributes, "description")
            episode.summary = textutil.clean_summary(summary) if summary else None
            episode.originally_available_at = air_date(value(attributes, "airdate") or value(attributes, "airDate"))
            self.episodes.append(episode)
        self.valid = len(self.episodes) > 0
        Log.Debug("Kitsu - AniDB '%s' -> Kitsu %s: %s episodes" % (anidb_id, kitsu, len(self.episodes)))


def theme_title(theme):
    """'Opening 2: Song - Artist, Artist' (AnimeThemes theme -> credit episode title)."""
    kind = u"Opening" if value(theme, "type") == "OP" else u"Ending"
    sequence = value(theme, "sequence")
    song = value(theme, "song", {}) or {}
    name = value(song, "title")
    if not name:
        return None
    artists = [value(a, "name") for a in value(song, "artists", []) or [] if value(a, "name")]
    label = u"%s %s" % (kind, sequence) if sequence else kind
    title = u"%s: %s" % (label, textutil.safe_unicode(name))
    if artists:
        title = u"%s - %s" % (title, u", ".join([textutil.safe_unicode(a) for a in artists]))
    return title


class AnimeThemesSeries(models.Series):
    """Opening/ending song titles from AnimeThemes, as titles of the AniDB entry's credit episodes (C1, C2, ...)."""
    def __init__(self, anidb_id, anidb_record=None):
        models.Series.__init__(self, anidb_id, "Animethemes")
        anidb_id = self.id
        if anidb_record is None or not anidb_record.valid or not (anidb_record.op_list or anidb_record.ed_list):
            return
        directory = os.path.join("AnimeThemes", anidb_id)
        data = cached_json(ANIMETHEMES, "themes.json", directory, anidb.cache_age(anidb_id), lambda: get_json(ANIMETHEMES, ANIMETHEMES_URL % (anidb_id)))
        anime = value(data, "anime", []) if data else []
        if not anime:
            return
        themes = value(anime[0], "animethemes", []) or []
        for kind, credits in (("OP", anidb_record.op_list), ("ED", anidb_record.ed_list)):
            ordered = sorted([t for t in themes if value(t, "type") == kind], key=lambda t: value(t, "sequence") or 1)
            for index, theme in enumerate(ordered):
                if index >= len(credits):
                    break
                title = theme_title(theme)
                if title:
                    episode = models.Episode()
                    episode.number = str(credits[index])
                    episode.title = title
                    self.episodes.append(episode)
        self.valid = len(self.episodes) > 0
        Log.Debug("AnimeThemes - AniDB '%s': %s openings/endings named" % (anidb_id, len(self.episodes)))
