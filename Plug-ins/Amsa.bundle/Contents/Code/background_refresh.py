"""Background refresh: apply the cached data at once, download fresh copies afterwards, refresh the show only if they changed.

Setting "Refreshing: Refresh Metadata mode" ("RefreshMode"):
  * "Cached first, update in background (recommended)": a Refresh Metadata (forced_refresh.py) and the early re-download
    for new episodes (refresher.py) don't make the update wait. The show is written from the cache, then its sources are
    queued here.
  * "Wait for fresh data": the downloads happen during the update.

Every source has its own lane (queue and worker): TVDB, AniList, MAL, Kitsu, AnimeThemes and AniDB run side by
side at their own pace, so a slow source never holds up the others or other shows. Each download is compared with the old
copy (what AMSA writes from it). A show is refreshed in Plex (anidb_retry.refresh: AMSA's own, non-forced refresh, which
reads the fresh cache and doesn't queue anything again) as soon as its TVDB/AniList/gap-filler downloads are done and one of
them changed; if its AniDB downloads finish later with a change, it is refreshed once more then.
AniDB never waits for the hourly budget here: an entry that can't be downloaded at once goes to the AniDB retry queue, which
downloads it when the budget allows and refreshes the show then.
A source already queued or downloading for a show isn't queued again. Sources downloaded during the update itself (not cached
before) are left alone: they are already fresh. The queue is saved to Cache/background-refresh.json and resumes after a restart.
"""
import os
import time

from lxml import etree

import settings
import textutil
import models
import downloader
import sources
import anidb_retry
import refresher
import title_index
import tvdb_v4

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

STATE_FILE = "background-refresh.json"
START_DELAY = 5                   # Seconds after queueing, so the update that queued it has been applied
FORCE_SECONDS = 900
LOCK = new_lock()
LANE_ORDER = ["Tvdb", "Anilist", "Mal", "Kitsu", "Animethemes", "Files", "Anidb"]
# "Files": episode writers/directors and thumbnails an update left out because they weren't cached yet
# (metadata_writer.write's lazy mode); tasks "crew|<TVDB series>|<TVDB episode>" and "image|<thumb url>|<path>|<url>|<path>"
FOLDERS = {"Anilist": "AniList", "Mal": "MAL", "Kitsu": "Kitsu", "Animethemes": "AnimeThemes"}
JOBS = []                         # [{"key", "label", "reason", "pending": {lane: [ids]}, "changed": [], "checked": n, "started": t}]
LANES = {}                        # lane -> {"queue": [(rating key, id)], "running": bool}
for lane_name in LANE_ORDER:
    LANES[lane_name] = {"queue": [], "running": False}


# One named function per lane, so Plex's log names the thread ("Scheduled a timed thread named 'background_tvdb'")
def background_tvdb():
    run_lane("Tvdb")


def background_anilist():
    run_lane("Anilist")


def background_mal():
    run_lane("Mal")


def background_kitsu():
    run_lane("Kitsu")


def background_animethemes():
    run_lane("Animethemes")


def background_anidb():
    run_lane("Anidb")


def background_files():
    run_lane("Files")


LANE_WORKERS = {"Tvdb": background_tvdb, "Anilist": background_anilist, "Mal": background_mal, "Kitsu": background_kitsu,
                "Animethemes": background_animethemes, "Files": background_files, "Anidb": background_anidb}


def find_job(rating_key):
    for job in JOBS:
        if job["key"] == str(rating_key):
            return job
    return None


def save_state():
    """Write the queue to disk (call with LOCK held). Lane queues are rebuilt from the jobs' pending ids on load."""
    try:
        downloader.save_file(tvdb_v4.dump_json({"version": 2, "jobs": JOBS}), STATE_FILE)
    except Exception as e:
        Log.Debug("Background refresh - Saving the queue failed: %s" % (e))


def load_state():
    """Called from Start(): restore the queue saved before a restart (the older per-kind format too)."""
    restored = []
    LOCK.acquire()
    try:
        try:
            path = downloader.cache_path(STATE_FILE)
            if not Data.Exists(path):
                return
            data = tvdb_v4.parse_json(Data.Load(path)) or {}
        except Exception as e:
            Log.Warn("Background refresh - Reading the saved queue failed: %s" % (e))
            return
        for saved in data.get("jobs") or []:
            if not saved.get("key"):
                continue
            pending = saved.get("pending")
            if pending is None:                            # Older format: {"anidb", "tvdb", "extra"}
                pending = {"Anidb": saved.get("anidb") or [], "Tvdb": saved.get("tvdb") or []}
                for lane in ("Anilist", "Mal", "Kitsu", "Animethemes"):
                    pending[lane] = saved.get("extra") or []
            restored.append((str(saved.get("key")), saved.get("label") or "", saved.get("reason") or "refresh", pending))
    finally:
        LOCK.release()
    for key, label, reason, pending in restored:
        queue_tasks(key, label, reason, pending)
    if restored:
        Log.Info("Background refresh - %s queued shows restored from before the restart" % (len(restored)))


def add(rating_key, label, anidb_ids, tvdb_ids, extra_ids, reason):
    """Queue a show (Plex rating key) for a background download of these sources. True if anything new was queued."""
    if not rating_key:
        return False
    pending = {"Anidb": anidb_ids or [], "Tvdb": tvdb_ids or []}
    for lane in ("Anilist", "Mal", "Kitsu", "Animethemes"):
        pending[lane] = [] if (lane == "Anilist" and not settings.ANILIST_ENABLED) else (extra_ids or [])
    added = queue_tasks(str(rating_key), label, reason, pending)
    if added:
        Log.Info("Background refresh - '%s' queued (%s): AniDB %s, TVDB %s, AniList/MAL/Kitsu/AnimeThemes %s"
                 % (label, reason, ", ".join(anidb_ids or []) or "none", ", ".join(tvdb_ids or []) or "none", ", ".join(extra_ids or []) or "none"))
    elif anidb_ids or tvdb_ids or extra_ids:
        Log.Debug("Background refresh - '%s': everything asked for is already queued or downloading" % (label))
    return added > 0


def add_files(rating_key, label, lazy):
    """After an update in lazy mode: download what it left out (metadata_writer.write), then refresh the show."""
    tasks = (lazy.get("crew") or []) + (lazy.get("images") or [])
    if not rating_key or not tasks:
        return False
    added = queue_tasks(str(rating_key), label, "files left out of the update", {"Files": tasks})
    if added:
        Log.Info("Background refresh - '%s': %s episode thumbnails and %s episode writer/director lists left to the background; the show is refreshed when they're in"
                 % (label, len(lazy.get("images") or []), len(lazy.get("crew") or [])))
    return added > 0


def queue_tasks(key, label, reason, pending):
    """Add the not yet queued (lane, id) tasks of one show; returns how many were added."""
    added = 0
    woken = []
    LOCK.acquire()
    try:
        job = find_job(key)
        if job is None:
            job = {"key": key, "label": label or "", "reason": reason, "pending": {}, "changed": [], "checked": 0, "started": time.time()}
            JOBS.append(job)
        for lane in LANE_ORDER:
            for source_id in pending.get(lane) or []:
                source_id = str(source_id)
                waiting = job["pending"].setdefault(lane, [])
                if source_id in waiting:
                    continue                               # Already queued, or downloading right now (that copy is fresh)
                waiting.append(source_id)
                LANES[lane]["queue"].append((key, source_id))
                added = added + 1
                if lane not in woken:
                    woken.append(lane)
        if not pending_count(job):
            JOBS.remove(job)
        save_state()
    finally:
        LOCK.release()
    for lane in woken:
        wake(lane)
    return added


def pending_count(job, lanes=None):
    total = 0
    for lane in lanes or LANE_ORDER:
        total = total + len(job["pending"].get(lane) or [])
    return total


def queue_length():
    LOCK.acquire()
    try:
        return len(JOBS)
    finally:
        LOCK.release()


def wake(lane):
    LOCK.acquire()
    try:
        if LANES[lane]["running"]:
            return
        LANES[lane]["running"] = True
    finally:
        LOCK.release()
    title_index.run_later(START_DELAY, LANE_WORKERS[lane])


# What to download ######################################################################################################################################################
def newest_age(directory):
    """Seconds since the newest file in a cache directory was saved, or None if it has no files."""
    newest = None
    try:
        for name in os.listdir(os.path.join(settings.CACHE_PATH, directory)):
            age = downloader.cache_age_of(name, directory)
            if age is not None and (newest is None or age < newest):
                newest = age
    except Exception:
        return None
    return newest


def forced_sources(mapping):
    """(AniDB ids, TVDB ids, extra ids, kept) a Refresh Metadata should download again: AniDB copies over 24h old (7 days for
       finished shows: refresher.refetch_after), TVDB series not downloaded within settings.REFRESH_SKIP_RECENT (setting,
       default 24h), and every AniDB entry for AniList/MAL/Kitsu/AnimeThemes (run_task skips
       the copies downloaded within the same setting)."""
    anidb_ids = []
    extra = []
    kept = []
    for item in mapping.series_list or []:
        anidb_id = item.get("anidbid")
        if not textutil.is_digits(anidb_id) or anidb_id in extra:
            continue
        extra.append(anidb_id)
        age = refresher.anidb_age(anidb_id)
        if age is not None and age >= refresher.refetch_after(anidb_id):
            anidb_ids.append(anidb_id)
        elif age is not None:
            kept.append("AniDB %s (%s old)" % (anidb_id, refresher.age_text(age)))
    tvdb_ids = []
    for value in [mapping.tvdb_id] + [x.get("tvdbid") for x in mapping.series_list or []]:
        if textutil.is_digits(value) and str(value) not in tvdb_ids:
            age = newest_age(os.path.join("TvDB4", str(value)))
            if age is None or age >= settings.REFRESH_SKIP_RECENT:
                tvdb_ids.append(str(value))
            elif "TVDB %s " % (value) not in " ".join(kept) + " ":
                kept.append("TVDB %s (%s old)" % (value, refresher.age_text(age)))   # Once, however many entries share it
    return anidb_ids, tvdb_ids, extra, kept


# Workers ################################################################################################################################################################
def run_lane(lane):
    """One lane's worker: its tasks in order until its queue is empty."""
    try:
        while True:
            LOCK.acquire()
            try:
                task = LANES[lane]["queue"].pop(0) if LANES[lane]["queue"] else None
            finally:
                LOCK.release()
            if task is None:
                break
            key, source_id = task
            result = False
            try:
                result = run_task(lane, source_id, key)
            except Exception:
                Log.Error("Background refresh - %s '%s' failed: %s" % (lane, source_id, textutil.exception_text()))
            task_done(lane, source_id, key, result)
    finally:
        LOCK.acquire()
        try:
            LANES[lane]["running"] = False
            again = len(LANES[lane]["queue"]) > 0
        finally:
            LOCK.release()
        if again:
            wake(lane)


def run_task(lane, source_id, key):
    """Download one source again. True = what AMSA writes from it changed; False = unchanged or skipped; None = handed on."""
    if lane == "Anidb":
        return refresh_anidb(source_id, key)
    if lane == "Tvdb":
        return refresh_tvdb(source_id)
    if lane == "Files":
        return download_file_task(source_id)
    directory = os.path.join(FOLDERS[lane], source_id)
    age = newest_age(directory)
    if age is None and lane != "Anilist":
        return False                                       # Gap fillers are only downloaded again if they were used before
    if age is not None and age < settings.REFRESH_SKIP_RECENT:
        Log.Debug("Background refresh - %s %s kept (%s old)" % (lane, source_id, refresher.age_text(age)))
        return False                                       # Setting "Refresh Metadata leaves sources downloaded within"
    return refresh_provider(lane, source_id, [directory])


def task_done(lane, source_id, key, result):
    """Record one finished download; refresh the show in Plex when its fast sources are done and something changed."""
    refresh = False
    summary = None
    LOCK.acquire()
    try:
        job = find_job(key)
        if job is None:
            return
        waiting = job["pending"].get(lane) or []
        if source_id in waiting:
            waiting.remove(source_id)
        job["checked"] = job["checked"] + 1
        if result:
            job["changed"].append(change_label(lane, source_id))
        fast_left = pending_count(job, [x for x in LANE_ORDER if x != "Anidb"])
        anidb_left = pending_count(job, ["Anidb"])
        if job["changed"] and fast_left == 0 and (lane != "Anidb" or anidb_left == 0):
            refresh = list(job["changed"])
            job["changed"] = []
        label = job["label"] or key
        if fast_left == 0 and anidb_left == 0:
            JOBS.remove(job)
            summary = (job["checked"], time.time() - job["started"])
        save_state()
    finally:
        LOCK.release()
    if refresh:
        Log.Info("Background refresh - '%s': %s changed; asking Plex to refresh the show%s"
                 % (label, changes_text(refresh), "" if summary else " (AniDB still downloading)"))
        anidb_retry.refresh(key, "Background refresh")
    if summary:
        Log.Info("Background refresh - '%s': done (%s sources checked in %.1fs)" % (label, summary[0], summary[1]))


def change_label(lane, source_id):
    if lane == "Files":
        return "episode thumbnails" if source_id.startswith("image|") else "episode writers/directors"
    return "%s %s" % (lane, source_id)


def changes_text(changes):
    """"Tvdb 81797, 50 x episode thumbnails" from the list of changes."""
    counts = {}
    order = []
    for change in changes:
        if change not in counts:
            counts[change] = 0
            order.append(change)
        counts[change] = counts[change] + 1
    return ", ".join([("%s x %s" % (counts[x], x)) if counts[x] > 1 else x for x in order])


def download_file_task(task):
    """One "Files" task. True if something new is now cached (the show is refreshed to write it)."""
    parts = task.split("|")
    if parts[0] == "crew" and len(parts) == 3:
        before, fresh = tvdb_v4.cached_crew(parts[1], parts[2])
        if fresh:
            return False                                   # Downloaded meanwhile (another update)
        after = tvdb_v4.episode_crew(parts[1], parts[2])
        return after is not None and after != before
    if parts[0] == "image" and len(parts) == 5:
        for url, path in ((parts[1], parts[2]), (parts[3], parts[4])):
            if url and path:
                if downloader.file_from_url(url, os.path.basename(path), os.path.dirname(path)):
                    return True                            # Thumbnail, else the full-size image (as download_image)
        return False
    return False


def refresh_provider(provider, source_id, directories, loader=None):
    """Download a source again; True if what AMSA writes from it changed."""
    loader = loader or (lambda: sources.get(provider, source_id))
    before = digest(loader())
    for directory in directories:
        downloader.force_refresh(directory, FORCE_SECONDS)
    try:
        sources.forget(provider, source_id)
        after = digest(loader())
    finally:
        for directory in directories:
            downloader.end_refresh(directory)
    return after is not None and after != before


def refresh_anidb(anidb_id, rating_key):
    """True/False = changed or not; None = not possible right now: handed to anidb_retry (it downloads and refreshes later)."""
    age = refresher.anidb_age(anidb_id)
    if age is None or age < refresher.refetch_after(anidb_id):
        return False
    directory = refresher.anidb_directory(anidb_id)
    before = digest(sources.get_anidb(anidb_id, False))
    downloader.force_refresh(directory, FORCE_SECONDS)
    try:
        sources.forget("Anidb", anidb_id)
        record = sources.get_anidb(anidb_id, "background") # Never waits; only at background spacing, else the retry queue takes it
    finally:
        downloader.end_refresh(directory)
        sources.forget("Anidb", anidb_id)                 # A refused "quick" load mustn't stay in memory as the fresh record
    new_age = refresher.anidb_age(anidb_id)
    if new_age is None or new_age >= 300:
        anidb_retry.add(anidb_id, rating_key, True)        # Downloads it when the limiter allows, then refreshes the show
        return None
    after = digest(record)
    return after is not None and after != before


def refresh_tvdb(tvdb_id):
    """TVDB series (v4, v1 fallback) and its cached season texts. True if anything AMSA writes changed."""
    changed = refresh_provider("Tvdb", tvdb_id, refresher.tvdb_directories(tvdb_id), lambda: sources.get_tvdb(tvdb_id))
    sources.forget("Plex", tvdb_id)
    directory = os.path.join("TvDB4", str(tvdb_id), "seasons")
    try:
        names = os.listdir(os.path.join(settings.CACHE_PATH, directory))
    except Exception:
        names = []
    suffix = "-%s.json" % (settings.TVDB4_LANGUAGE)
    for name in names:
        if not name.endswith(suffix) or not textutil.is_digits(name[:-len(suffix)]):
            continue
        season_id = name[:-len(suffix)]
        before = downloader.load_stale(name, directory, True)
        downloader.force_refresh(directory, FORCE_SECONDS)
        try:
            tvdb_v4.season_text(tvdb_id, season_id)
        finally:
            downloader.end_refresh(directory)
        if downloader.load_stale(name, directory, True) != before:
            changed = True
    return changed


# Comparing ##############################################################################################################################################################
def value_text(value):
    """A comparable form of one source value (text, number, list, or an XML element such as images or roles)."""
    if value is None:
        return None
    if etree.iselement(value):
        return etree.tostring(value)
    if isinstance(value, float):
        return "%.1f" % (value)                 # Ratings move a little with every vote: only a visible change counts
    if isinstance(value, (list, tuple)):
        items = value
        return [value_text(x) for x in items]
    return textutil.safe_unicode(value)


def digest(record):
    """Everything AMSA writes from a source record (settings.SERIES_FIELDS and EPISODE_FIELDS), or None if it isn't valid."""
    if record is None or not getattr(record, "valid", False):
        return None
    parts = []
    for field in settings.SERIES_FIELDS:
        parts.append(value_text(getattr(record, models.field_attr(field), None)))
    for episode in getattr(record, "episodes", None) or []:
        parts.append([getattr(episode, "season", None), getattr(episode, "number", None)] +
                     [value_text(getattr(episode, models.field_attr(field), None)) for field in settings.EPISODE_FIELDS])
    return parts
