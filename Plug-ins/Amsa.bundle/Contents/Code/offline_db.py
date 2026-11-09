"""anime-offline-database: cross-site ids, airing status and extra titles for AniDB entries (setting OfflineDatabase).

The dataset (https://github.com/cedya77/anime-offline-database, a weekly continuation of manami-project's archived
anime-offline-database; ODbL 1.0 / DbCL 1.0) links each anime's pages on AniDB, AniList, MyAnimeList, Kitsu and others,
with its status (FINISHED / ONGOING / UPCOMING), episode count, year and synonyms from all those sites.

The JSONL file (~60 MB) is downloaded at most once a week, in the background warm-up only, and read line by line straight
from the network, so it never sits in memory or on disk. Only entries with an AniDB page are kept, in a compact index
(Cache/OfflineDB/index.json, about 10 MB): AniDB id -> [AniList id, MAL id, status, episodes, year, [titles and synonyms], Kitsu id].
Searches and updates only read that index and never download.

Used for:
  * AniList: the AniList id for an AniDB entry, before AniDB's MAL id and the arm.haglund.dev lookup (anilist.py);
  * airing status for the daily refresh list and early re-downloads (airing.py, refresher.py);
  * extra search titles: synonyms the AniDB titles dump doesn't have (title_index.py).
"""
import re
import time
import urllib2

import settings
import textutil
import downloader
import tvdb_v4

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

DIRECTORY = "OfflineDB"
INDEX_FILE = "index.json"
SOURCE_RX = re.compile(r"^https?://(?:www\.)?(anidb\.net|anilist\.co|myanimelist\.net|kitsu\.app|kitsu\.io)/anime/([0-9]+)")
INDEX_FORMAT = 2                  # 2: with Kitsu ids. An index in an older format is rebuilt at the next warm-up
LOCK = new_lock()
STATE = {"index": None, "loaded_at": 0.0, "version": 0, "next_try": 0.0}
RETRY_AFTER = 24 * 3600           # After a failed download


def enabled():
    return settings.OFFLINE_DB_ENABLED


def index_age():
    return downloader.cache_age_of(INDEX_FILE, DIRECTORY)


def compact(entry):
    """One dataset line -> (AniDB id, [AniList id, MAL id, status, episodes, year, [titles], Kitsu id]) or (None, None)."""
    ids = {}
    for source in entry.get("sources") or []:
        found = SOURCE_RX.match(source or "")
        if found:
            ids[found.group(1)] = found.group(2)
    anidb_id = ids.get("anidb.net")
    if not anidb_id:
        return None, None
    titles = []
    for title in [entry.get("title")] + (entry.get("synonyms") or []):
        if title and title not in titles:
            titles.append(title)
    season = entry.get("animeSeason") or {}
    return anidb_id, [ids.get("anilist.co"), ids.get("myanimelist.net"), entry.get("status") or "", entry.get("episodes") or 0,
                      season.get("year") or 0, titles, ids.get("kitsu.app") or ids.get("kitsu.io")]


def build_from_lines(read_line):
    """Index from JSONL lines returned one by one by read_line() ("" at the end); the first line is the dataset's metadata."""
    anime = {}
    updated = ""
    count = 0
    while True:
        line = read_line()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            entry = tvdb_v4.parse_json(line)
        except Exception:
            continue
        if count == 0 and "sources" not in entry:
            updated = entry.get("lastUpdate") or ""
            count = count + 1
            continue
        count = count + 1
        anidb_id, data = compact(entry)
        if anidb_id and anidb_id not in anime:
            anime[anidb_id] = data
    return {"updated": updated, "built": time.time(), "format": INDEX_FORMAT, "anime": anime}


def download():
    """Stream the dataset and save the compact index. True on success."""
    started = time.time()
    request = urllib2.Request(settings.OFFLINE_DB_URL, headers={"User-Agent": "AMSA/%s" % (settings.VERSION)})
    response = urllib2.urlopen(request, context=downloader.SSL_CONTEXT, timeout=60)
    try:
        built = build_from_lines(response.readline)
    finally:
        response.close()
    if len(built["anime"]) < 1000:
        Log.Warn("OfflineDB - Download looked incomplete (%s AniDB entries); keeping the previous index" % (len(built["anime"])))
        return False
    downloader.save_file(tvdb_v4.dump_json(built), INDEX_FILE, DIRECTORY)
    LOCK.acquire()
    try:
        STATE["index"] = built
        STATE["loaded_at"] = time.time()
        STATE["version"] = STATE["version"] + 1
    finally:
        LOCK.release()
    Log.Info("OfflineDB - Dataset of %s indexed: %s AniDB entries in %.1fs" % (built["updated"] or "unknown date", len(built["anime"]), time.time() - started))
    return True


def refresh():
    """Background warm-up only: download the dataset if the index is missing or older than a week."""
    if not enabled():
        return
    age = index_age()
    current = index()
    if age is not None and age < settings.OFFLINE_DB_RELOAD and current and current.get("format") == INDEX_FORMAT:
        return
    if time.time() < STATE["next_try"]:
        return
    try:
        if not download():
            STATE["next_try"] = time.time() + RETRY_AFTER
    except Exception as e:
        STATE["next_try"] = time.time() + RETRY_AFTER
        Log.Warn("OfflineDB - Download failed (%s); the previous index is used, next try in 24 hours" % (e))


def index():
    """The index from memory or disk (never downloads); None if unavailable or switched off."""
    if not enabled():
        return None
    LOCK.acquire()
    try:
        if STATE["index"] is None and STATE["loaded_at"] < time.time() - 3600:
            STATE["loaded_at"] = time.time()                 # Don't retry a missing/broken file more than once an hour
            path = downloader.cache_path(INDEX_FILE, DIRECTORY)
            try:
                if Data.Exists(path):
                    STATE["index"] = tvdb_v4.parse_json(Data.Load(path))
                    STATE["version"] = STATE["version"] + 1
            except Exception as e:
                Log.Warn("OfflineDB - Reading the index failed: %s" % (e))
        return STATE["index"]
    finally:
        LOCK.release()


def version():
    """Changes whenever a different index is loaded (title_index rebuilds then)."""
    return STATE["version"]


def entry(anidb_id):
    data = index()
    if not data:
        return None
    return (data.get("anime") or {}).get(str(anidb_id))


def anilist_id(anidb_id):
    found = entry(anidb_id)
    return str(found[0]) if found and textutil.is_digits(found[0]) else None


def mal_id(anidb_id):
    found = entry(anidb_id)
    return str(found[1]) if found and textutil.is_digits(found[1]) else None


def kitsu_id(anidb_id):
    found = entry(anidb_id)
    return str(found[6]) if found and len(found) > 6 and textutil.is_digits(found[6]) else None


def status(anidb_id):
    """"FINISHED", "ONGOING", "UPCOMING", "UNKNOWN" or None."""
    found = entry(anidb_id)
    return found[2] if found and found[2] else None


def titles():
    """{AniDB id: [titles and synonyms]} for the search index."""
    data = index()
    result = {}
    if data:
        anime = data.get("anime") or {}
        for anidb_id in anime:
            result[anidb_id] = anime[anidb_id][5] or []
    return result
