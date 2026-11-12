"""Postponed AniDB downloads.

When an update needs an AniDB anime that isn't cached and the AniDB limiter refuses the request (hourly budget used up, or
a ban), the show is written without AniDB data, and the anime is queued here: a background job downloads it as soon as
the limiter allows (still through the limiter, so no extra risk of a ban), then asks the local Plex server to refresh the
show so the AniDB data is written. If Plex refuses the refresh request, the data is still cached and the next refresh of
that show uses it. The queue is saved to Cache/anidb-retry.json and picked up again after a Plex restart.

The same queue also prefetches (no Plex item to refresh: related AniDB entries for seasons that have no files yet, so
their data is cached when the files arrive) and re-downloads entries early (force: see refresher.py).
Each run downloads one anime, at the limiter's background spacing (36s at 100 an hour), and refreshes the shows that are
complete. The queue goes newest request first (the show you just refreshed doesn't wait behind a library refresh's
backlog), prefetches last.
"""
import os
import time

import settings
import textutil
import anidb_limiter
import downloader
import sources
import title_index
import tvdb_v4

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

MAX_ATTEMPTS = 6                 # Give up on an anime after this many postponed tries
MIN_DELAY = 30                   # Seconds; never check more often than this
LOCK = new_lock()
PENDING = {}                     # anidb id -> {"keys": [Plex rating keys to refresh], "attempts": n, "force": bool, "queued": time}
SCHEDULED = [False]
LATER = []                       # Plex rating keys whose refresh waits for another queued anime of the same show
STATE_FILE = "anidb-retry.json"


def save_state():
    """Write the queue to disk (call with LOCK held)."""
    try:
        downloader.save_file(tvdb_v4.dump_json({"pending": PENDING, "later": LATER, "refresh": REFRESH_WAITING}), STATE_FILE)
    except Exception as e:
        Log.Debug("AniDB retry - Saving the queue failed: %s" % (e))


def load_state():
    """Called from Start(): restore the queue saved before a restart and schedule it."""
    LOCK.acquire()
    try:
        try:
            path = downloader.cache_path(STATE_FILE)
            if not Data.Exists(path):
                return
            data = tvdb_v4.parse_json(Data.Load(path)) or {}
        except Exception as e:
            Log.Warn("AniDB retry - Reading the saved queue failed: %s" % (e))
            return
        pending = data.get("pending") or {}
        for anidb_id in pending:
            item = pending[anidb_id] or {}
            PENDING[str(anidb_id)] = {"keys": [str(x) for x in (item.get("keys") or [])], "attempts": int(item.get("attempts") or 0),
                                      "force": bool(item.get("force")), "queued": float(item.get("queued") or 0)}
        for key in data.get("later") or []:
            if str(key) not in LATER:
                LATER.append(str(key))
        waiting = data.get("refresh") or {}
        for key in waiting:
            REFRESH_WAITING[str(key)] = waiting[key]
        start = (len(PENDING) > 0 or len(LATER) > 0) and not SCHEDULED[0]
        if start:
            SCHEDULED[0] = True
    finally:
        LOCK.release()
    if start:
        Log.Info("AniDB retry - %s queued AniDB downloads restored from before the restart" % (len(PENDING)))
        schedule()
    if REFRESH_WAITING:
        Log.Info("AniDB retry - %s refreshes Plex didn't answer before the restart are asked again in a minute" % (len(REFRESH_WAITING)))
        schedule_waiting(60)


def add(anidb_id, rating_key, force=False):
    """Queue an AniDB anime for a background download; rating_key is the Plex item to refresh once it's downloaded
       (None = prefetch only). force: download even if the cached copy is still fresh (early re-download)."""
    anidb_id = str(anidb_id)
    LOCK.acquire()
    try:
        entry = PENDING.get(anidb_id)
        if entry is None:
            entry = {"keys": [], "attempts": 0, "force": False, "queued": time.time()}
            PENDING[anidb_id] = entry
        if rating_key:
            entry["queued"] = time.time()                  # Asked for again: moves to the front
            if str(rating_key) not in entry["keys"]:
                entry["keys"].append(str(rating_key))
        if force:
            entry["force"] = True
        start = not SCHEDULED[0]
        SCHEDULED[0] = True
        save_state()
    finally:
        LOCK.release()
    when = schedule() if start else anidb_limiter.next_slot(True)
    LOCK.acquire()
    try:
        queue = order(PENDING)
        position = queue.index(anidb_id) + 1 if anidb_id in queue else 1
    finally:
        LOCK.release()
    when = max(when, time.time() + MIN_DELAY) + (position - 1) * max(MIN_DELAY + 5, anidb_limiter.background_delay())
    after = textutil.when_text(when)
    if rating_key:
        Log.Info("AniDB retry - AniDB '%s' postponed by the AniDB limiter (%s of %s in the queue); it will be downloaded around %s and the show refreshed"
                 % (anidb_id, position, len(queue), after))
    else:
        Log.Info("AniDB retry - AniDB '%s' (no files yet) queued for a background download after %s" % (anidb_id, after))


def pending_count():
    LOCK.acquire()
    try:
        return len(PENDING)
    finally:
        LOCK.release()


def order(pending):
    """Queue order: anime a show is waiting for, most recently requested first; then prefetches, oldest first."""
    shows = sorted([x for x in pending if pending[x].get("keys")], key=lambda x: -(pending[x].get("queued") or 0))
    others = sorted([x for x in pending if not pending[x].get("keys")], key=lambda x: pending[x].get("queued") or 0)
    return shows + others


def schedule():
    when = anidb_limiter.next_slot(True)
    delay = max(MIN_DELAY, when - time.time() + 5)
    title_index.run_later(delay, anidb_retry_downloads)
    return when


def anidb_retry_downloads():
    """Named for Plex's log ("Scheduled a timed thread named 'anidb_retry_downloads'")."""
    run()


def run():
    """Background job: download the next queued anime if the limiter allows it at background spacing, then refresh the shows
       whose anime are all in (once per show). One download per run; the next run is scheduled for the next background slot."""
    ready = []
    try:
        LOCK.acquire()
        try:
            queued = order(PENDING)
        finally:
            LOCK.release()
        for anidb_id in queued:
            if anidb_limiter.next_slot(True) > time.time() + 1:
                break                                      # Not yet: the next run is scheduled for the next free slot
            LOCK.acquire()
            try:
                force = (PENDING.get(anidb_id) or {}).get("force")
                prefetch = not (PENDING.get(anidb_id) or {}).get("keys") and not force
            finally:
                LOCK.release()
            if prefetch and len(anidb_limiter.recent_requests()) >= settings.ANIDB_HOURLY_LIMIT // 2:
                continue                                   # Prefetches only use the first half of the hourly budget; updates come first
            sources.forget("Anidb", anidb_id)
            directory = os.path.join("AniDB", anidb_id)
            if force:
                downloader.force_refresh(directory)
            try:
                record = sources.get_anidb(anidb_id, True)
            finally:
                if force:
                    downloader.end_refresh(directory)
            fresh = downloader.cache_age_of("%s.xml" % (anidb_id), directory)
            if force and not (fresh is not None and fresh < 300):
                record = None                              # Forced re-download refused again: the cached copy doesn't count
            LOCK.acquire()
            try:
                entry = PENDING.get(anidb_id) or {"keys": [], "attempts": 0, "force": False}
                entry["attempts"] = entry["attempts"] + 1
                done = (record is not None and record.valid) or entry["attempts"] >= MAX_ATTEMPTS
                if done and anidb_id in PENDING:
                    del PENDING[anidb_id]
            finally:
                LOCK.release()
            if record is not None and record.valid:
                Log.Info("AniDB retry - AniDB '%s' downloaded" % (anidb_id))
                for rating_key in entry["keys"]:
                    if rating_key not in ready:
                        ready.append(rating_key)
            elif done:
                Log.Warn("AniDB retry - Giving up on AniDB '%s' after %s tries; refresh the show later" % (anidb_id, entry["attempts"]))
            break                                          # One download per run
    except Exception:
        Log.Error("AniDB retry - Failed: %s" % (textutil.exception_text()))
    LOCK.acquire()
    try:
        waiting = []
        for anidb_id in PENDING:
            waiting.extend(PENDING[anidb_id]["keys"])
        more = len(PENDING) > 0
        SCHEDULED[0] = more
    finally:
        LOCK.release()
    for rating_key in ready:
        if rating_key in waiting:
            if rating_key not in LATER:
                LATER.append(rating_key)           # Another anime of this show is still queued: refresh once that one is in
        else:
            if rating_key in LATER:
                LATER.remove(rating_key)
            refresh(rating_key)
    for rating_key in list(LATER):
        if rating_key not in waiting and rating_key not in ready:
            LATER.remove(rating_key)
            refresh(rating_key)
    LOCK.acquire()
    try:
        save_state()
    finally:
        LOCK.release()
    if more:
        schedule()


def plex_token():
    try:
        return os.environ.get("PLEXTOKEN") or ""
    except Exception:
        return ""


OWN_REFRESHES = {}               # rating key -> time AMSA asked Plex to refresh it (such refreshes may arrive with force=True)


def own_refresh(rating_key):
    """True if AMSA itself asked Plex to refresh this item in the last 15 minutes (then it's not your Refresh Metadata)."""
    asked = OWN_REFRESHES.get(str(rating_key))
    if asked is None:
        return False
    del OWN_REFRESHES[str(rating_key)]
    return asked > time.time() - 900


def refresh(rating_key, label="AniDB retry"):
    """Ask the local Plex server to refresh one library item. Returns True if Plex accepted the request. If Plex isn't
       answering, the request is kept and asked again when it is (refresh_waiting)."""
    url = "%s/library/metadata/%s/refresh?force=0" % (settings.PMS_URL, rating_key)
    OWN_REFRESHES[str(rating_key)] = time.time()
    headers = {"Accept": "application/json"}
    token = plex_token()
    if token:
        headers["X-Plex-Token"] = token
    try:
        HTTP.Request(url, headers=headers, method="PUT", cacheTime=0, immediate=True)
        Log.Info("%s - Asked Plex to refresh item %s" % (label, rating_key))
        return True
    except Exception as e:
        if plex_unreachable(e):
            plex_down()
            LOCK.acquire()
            try:
                REFRESH_WAITING[str(rating_key)] = label
                save_state()
            finally:
                LOCK.release()
            Log.Warn("%s - Plex isn't answering (%s): the refresh of item %s is asked again when it does" % (label, e, rating_key))
            schedule_waiting(PLEX_PAUSE)
        else:
            Log.Warn("%s - Plex refused the refresh of item %s (%s); cached data is used on the show's next refresh" % (label, rating_key, e))
        return False


# Plex not answering ###########################################################################################################
# A busy or restarting Plex server times out or refuses AMSA's requests (its resizer, refreshes, edits). That says nothing
# about the image or show asked for, so nothing is recorded as failed: background work that needs Plex waits PLEX_PAUSE and
# tries again, and refreshes that couldn't be asked are asked again once Plex answers.
PLEX_PAUSE = 300                 # Seconds background work that needs Plex waits after Plex didn't answer
PLEX_STATE = {"down_until": 0, "waiting_scheduled": False}
REFRESH_WAITING = {}             # rating key -> log label: refreshes to ask again once Plex answers (saved with the queue)


def plex_unreachable(error):
    """True if this error means the local Plex server didn't answer at all (timeout, refused, reset), not a refusal."""
    text = textutil.safe_unicode(error).lower()
    for word in ("timed out", "timeout", "10061", "10054", "10060", "refused", "connection reset", "errno 111", "errno 104", "errno 110"):
        if word in text:
            return True
    return False


def plex_down():
    PLEX_STATE["down_until"] = time.time() + PLEX_PAUSE


def plex_answering():
    """False for PLEX_PAUSE seconds after Plex last didn't answer."""
    return time.time() >= PLEX_STATE["down_until"]


def plex_wait():
    """Seconds left before Plex is tried again (0 if it's answering)."""
    return max(0, int(PLEX_STATE["down_until"] - time.time()) + 1) if not plex_answering() else 0


def schedule_waiting(delay):
    """Ask again for the waiting refreshes after delay seconds (one timer at a time)."""
    if PLEX_STATE["waiting_scheduled"]:
        return
    PLEX_STATE["waiting_scheduled"] = True
    title_index.run_later(delay, refresh_waiting)


def refresh_waiting():
    """Ask again for the refreshes Plex didn't answer; while it still doesn't, try again after PLEX_PAUSE. Named for
       Plex's log (a timed thread)."""
    PLEX_STATE["waiting_scheduled"] = False
    if not REFRESH_WAITING:
        return
    if not plex_answering():
        schedule_waiting(plex_wait())
        return
    LOCK.acquire()
    try:
        waiting = list(REFRESH_WAITING.items())
        REFRESH_WAITING.clear()
        save_state()
    finally:
        LOCK.release()
    for rating_key, label in waiting:
        refresh(rating_key, label)                        # Not answering again: refresh() keeps it and schedules the next try
