"""Daily refresh of airing shows (setting "Maintenance: Refresh airing shows once a day").

Metadata changes while a season airs (titles and summaries of new episodes, air dates, images). Plex only asks AMSA for
metadata when files change or someone refreshes the show, so AMSA keeps a list of the shows it updated that are airing,
or ended in the last 30 days (Cache/airing-shows.json, from the cached AniDB end dates), and once a day asks the local Plex
server to refresh each of them. The refresh is a normal update: sources are only downloaded again when their cache is old
enough (AniDB: 2 days while airing), so the cost is small.

Pacing: checked hourly; at most settings.AIRING_PER_RUN shows per run, settings.AIRING_GAP seconds apart. If Plex refuses
three refreshes in a row (e.g. no access to Plex's API), the job pauses for 24 hours.
"""
import re
import time

import settings
import textutil
import downloader
import sources
import anidb_retry
import title_index
import tvdb_v4
import offline_db

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

STATE_FILE = "airing-shows.json"
LOCK = new_lock()
SHOWS = {}                       # Plex rating key -> {"id": "anidb-123", "title": .., "updated": time, "until": time}
STATE = {"loaded": False, "failures": 0, "paused_until": 0.0, "started": False}
FIRST_RUN = 10 * 60              # First check 10 minutes after Plex starts
RUN_EVERY = 60 * 60


def date_time(value):
    found = re.match(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})", value or "")
    if not found:
        return None
    try:
        return time.mktime((int(found.group(1)), int(found.group(2)), int(found.group(3)), 0, 0, 0, 0, 0, -1))
    except Exception:
        return None


def airing_until(mapping):
    """Time until which the show counts as airing (its latest AniDB end date + 30 days), or 0 if it ended long ago.
       anime-offline-database's status decides first (ONGOING/UPCOMING = airing, FINISHED without an AniDB end date = ended);
       without it, entries without an end date count as airing if they started in the last 2 years (or start in the future)."""
    until = 0
    now = time.time()
    for item in mapping.series_list or []:
        anidb_id = item.get("anidbid")
        if not textutil.is_digits(anidb_id):
            continue
        state = offline_db.status(anidb_id)
        if state in ("ONGOING", "UPCOMING"):
            candidate = now + settings.AIRING_KEEP_AFTER_END
            if candidate > until:
                until = candidate
            continue
        record = sources.get_anidb(anidb_id, False)
        if not record.valid:
            continue
        ended = date_time(getattr(record, "end_date", None))
        started = date_time(getattr(record, "originally_available_at", None))
        if ended is None and state == "FINISHED":
            candidate = 0
        elif ended is not None:
            candidate = ended + settings.AIRING_KEEP_AFTER_END
        elif started is not None and started > now - 2 * 365 * 86400:
            candidate = now + settings.AIRING_KEEP_AFTER_END
        else:
            candidate = 0
        if candidate > until:
            until = candidate
    return until


def load():
    if STATE["loaded"]:
        return
    STATE["loaded"] = True
    try:
        path = downloader.cache_path(STATE_FILE)
        if Data.Exists(path):
            data = tvdb_v4.parse_json(Data.Load(path))
            for key in data:
                SHOWS[str(key)] = data[key]
    except Exception:
        Log.Warn("Airing - Reading %s failed: %s" % (STATE_FILE, textutil.exception_text()))


def save():
    try:
        downloader.save_file(tvdb_v4.dump_json(SHOWS), STATE_FILE)
    except Exception:
        Log.Warn("Airing - Saving %s failed: %s" % (STATE_FILE, textutil.exception_text()))


def record(rating_key, metadata_id, title, mapping):
    """Called after each update: add, refresh or remove the show on the airing list."""
    if not rating_key:
        return
    rating_key = str(rating_key)
    try:
        until = airing_until(mapping)
    except Exception:
        Log.Debug("Airing - End date check failed: %s" % (textutil.exception_text()))
        return
    LOCK.acquire()
    try:
        load()
        if until > time.time():
            if rating_key not in SHOWS:
                Log.Info("Airing - '%s' added to the daily refresh (airing until %s)" % (title, time.strftime("%Y-%m-%d", time.localtime(until))))
            SHOWS[rating_key] = {"id": metadata_id, "title": title or "", "updated": time.time(), "until": until}
            save()
        elif rating_key in SHOWS:
            del SHOWS[rating_key]
            save()
            Log.Info("Airing - '%s' no longer airing; removed from the daily refresh" % (title))
    finally:
        LOCK.release()


def due():
    """Rating keys of airing shows not updated for settings.AIRING_REFRESH_AFTER, oldest first."""
    now = time.time()
    LOCK.acquire()
    try:
        load()
        expired = [key for key in SHOWS if (SHOWS[key].get("until") or 0) < now]
        for key in expired:
            del SHOWS[key]
        if expired:
            save()
        keys = [key for key in SHOWS if (SHOWS[key].get("updated") or 0) < now - settings.AIRING_REFRESH_AFTER]
        return sorted(keys, key=lambda x: SHOWS[x].get("updated") or 0)
    finally:
        LOCK.release()


def start():
    """Called from Start(): schedule the hourly check (once per agent process)."""
    if STATE["started"] or not settings.REFRESH_AIRING:
        return
    STATE["started"] = True
    title_index.run_later(FIRST_RUN, airing_check)


def airing_check():
    """Named for Plex's log ("Scheduled a timed thread named 'airing_check'")."""
    run()


def run():
    try:
        if time.time() < STATE["paused_until"]:
            return
        keys = due()[:settings.AIRING_PER_RUN]
        if keys:
            Log.Info("Airing - %s airing shows due for their daily refresh" % (len(keys)))
            refresh_next(keys)
    except Exception:
        Log.Error("Airing - Failed: %s" % (textutil.exception_text()))
    finally:
        title_index.run_later(RUN_EVERY, airing_check)


def refresh_next(keys):
    """Refresh keys[0] now and the rest AIRING_GAP seconds apart."""
    if not keys or time.time() < STATE["paused_until"]:
        return
    key = keys[0]
    LOCK.acquire()
    try:
        show = SHOWS.get(key)
        if show is not None:
            show["updated"] = time.time()        # Don't ask again within a day even if Plex never calls the update
    finally:
        LOCK.release()
    if show is not None:
        if anidb_retry.refresh(key, "Airing"):
            STATE["failures"] = 0
        else:
            STATE["failures"] = STATE["failures"] + 1
            LOCK.acquire()
            try:
                if key in SHOWS:
                    del SHOWS[key]               # Deleted from Plex, or no access: it is added again on its next update
            finally:
                LOCK.release()
            if STATE["failures"] >= 3:
                STATE["paused_until"] = time.time() + 24 * 3600
                Log.Warn("Airing - Plex refused 3 refreshes in a row; daily refresh paused for 24 hours")
                return
    LOCK.acquire()
    try:
        save()
    finally:
        LOCK.release()
    if len(keys) > 1:
        rest = keys[1:]

        def airing_refresh_next():
            refresh_next(rest)
        title_index.run_later(settings.AIRING_GAP, airing_refresh_next)
