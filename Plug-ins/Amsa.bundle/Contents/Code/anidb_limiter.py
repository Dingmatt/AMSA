"""AniDB request limiter (anti-ban).

AniDB's HTTP API rules (wiki.anidb.net/HTTP_API_Definition):
  - no more than one request every 2 seconds
  - heavy local caching; requesting the same anime more than once a day can get you banned
  - bulk "downloading" of AniDB is treated as abuse and banned
  - a ban is returned as <error>Banned</error> (no HTTP status codes)
The UDP API page adds a long-term average of one request per 4 seconds, and that requests sent while banned
count against you (they extend the ban). This module enforces all of that for every AniDB request AMSA makes:
  1. Spacing:        at least ANIDB_REQUEST_DELAY seconds (default 4, minimum 3) between requests, across all threads.
  2. Hourly budget:  at most ANIDB_HOURLY_LIMIT requests per rolling hour. When it's used up, a request that would wait
                     more than MAX_WAIT seconds is skipped and the cached copy (if any) is used instead.
     Daily budget:   at most ANIDB_DAILY_LIMIT requests per rolling 24 hours, the same way.
     Background:     requests nobody is waiting for (background refresh, the retry queue) are spaced by the hourly budget
                     spread over the hour (3600 / limit: 36s at 100), not the 4s minimum. A rolling hour on its own frees
                     its slots exactly an hour after the old requests, so without this a burst would come back an hour
                     later as another burst, which is enough to get banned.
  3. Ban handling:   after <error>Banned</error> no AniDB request is sent at all for 1h, doubling on repeat bans up to 24h.
                     Repeated network failures pause requests for 15 minutes.
  4. Titles dump:    anime-titles.xml is downloaded at most once per 24h (retried after 6h if a download fails).
  5. Persistence:    the state survives Plex restarts (DataItems/Cache/anidb-limiter.txt), so restarting Plex
                     during a ban does not start hammering AniDB again.
"""
import os
import time

import environment
import settings
import textutil

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

MAX_WAIT = 60                       # Longest a single request may wait for the hourly budget before being skipped (seconds)
QUICK_MAX_WAIT = 5                  # Searches ("quick" requests) never wait longer than this, and skip AniDB if another request holds the queue
SOFT_BAN_FAILURES = 3               # Consecutive network failures before pausing
SOFT_BAN_SECONDS = 15 * 60
BAN_STEPS_HOURS = [1, 2, 4, 8, 16, 24]
BAN_RESET_SECONDS = 48 * 3600       # Forget earlier bans after this long without a new one
TITLES_INTERVAL = 24 * 3600
TITLES_RETRY = 6 * 3600
STATE_FILE = "anidb-limiter.txt"

DEFERRED_MEMORY = 15 * 60          # How long a refused request is remembered for was_deferred()

LOCK = new_lock()
DEFERRED = {}                       # url -> time a (non-search) request was refused by a ban or the hourly limit
STATE = {"ban_until": 0.0, "ban_count": 0, "last_ban": 0.0, "fail_streak": 0, "titles_next": 0.0, "recent": []}
LOADED = [False]


### Persistence #########################################################################################################################################################
def state_path():
    return os.path.join(settings.CACHE_DIR, STATE_FILE)

def load_state():
    if LOADED[0]:
        return
    LOADED[0] = True
    try:
        if not Data.Exists(state_path()):
            return
        content = Data.Load(state_path())
        if not isinstance(content, basestring): content = content.decode("utf-8")
        for line in content.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key == "recent":
                STATE["recent"] = [float(x) for x in value.split(",") if x.strip()]
            elif key in ("ban_count", "fail_streak"):
                STATE[key] = int(value)
            elif key in STATE:
                STATE[key] = float(value)
        Log.Info("AniDB limiter - State loaded: %s requests in the last hour, %s in 24 hours, %s" % (len(recent_requests()), len(day_requests()), status()))
    except Exception as e:
        Log.Warn("AniDB limiter - Could not read state file, starting fresh: %s" % (e))

def save_state():
    try:
        lines = []
        for key in ("ban_until", "ban_count", "last_ban", "fail_streak", "titles_next"):
            lines.append("%s=%s" % (key, STATE[key]))
        lines.append("recent=%s" % (",".join(["%.0f" % x for x in day_requests()])))     # 24 hours, for the daily budget
        Data.Save(state_path(), "\n".join(lines))
    except Exception as e:
        environment.write_failed(os.path.join(settings.DATA_ITEMS_PATH, state_path()), e, "AniDB limiter")


### Helpers #############################################################################################################################################################
def day_requests():
    """Request times within the last 24 hours (oldest first); older ones are forgotten."""
    cutoff = time.time() - 86400
    STATE["recent"] = [x for x in STATE["recent"] if x > cutoff]
    return STATE["recent"]

def recent_requests():
    """Request times within the last hour (oldest first)."""
    cutoff = time.time() - 3600
    return [x for x in day_requests() if x > cutoff]

def background_delay():
    """Seconds between requests nobody is waiting for: the hourly budget spread evenly over the hour."""
    return max(float(settings.ANIDB_REQUEST_DELAY), 3600.0 / settings.ANIDB_HOURLY_LIMIT)

def budget_free_at(now=None):
    """Earliest time the hourly and daily budgets allow another request (now if they do)."""
    now = now or time.time()
    when = now
    day = day_requests()
    if len(day) >= settings.ANIDB_DAILY_LIMIT:
        when = max(when, day[len(day) - settings.ANIDB_DAILY_LIMIT] + 86400)
    hour = recent_requests()
    if len(hour) >= settings.ANIDB_HOURLY_LIMIT:
        when = max(when, hour[len(hour) - settings.ANIDB_HOURLY_LIMIT] + 3600)
    return when

def clock(epoch):
    return textutil.when_text(epoch)                     # With the date (next slots and bans can be tomorrow)

def status():
    if STATE["ban_until"] > time.time():
        return "AniDB requests paused until %s" % (clock(STATE["ban_until"]))
    return "not paused"

def is_titles_url(url):
    return url.startswith(settings.ANIDB_TITLES_URL)


### Public API ##########################################################################################################################################################
def acquire(url, quick=False, background=False):
    """Call before every AniDB request. Waits for the next allowed slot and returns True,
       or returns False (without waiting long) if the request must not be sent now - the caller should use its cache.
       quick=True (searches): never queue behind other requests and never wait more than QUICK_MAX_WAIT seconds.
       background=True (background refresh): like quick, and only once background_delay() has passed since the last
       request; otherwise refused at once, so the caller hands it to the retry queue (anidb_retry), which waits for it."""
    max_wait = MAX_WAIT
    remember = background or not quick                     # Refusals was_deferred() reports (searches' aren't)
    if background:
        quick = True
    if quick:
        max_wait = QUICK_MAX_WAIT
        if not LOCK.acquire(0):
            Log.Debug("AniDB limiter - Queue busy, using cached data for '%s'" % (url))
            return False
    else:
        LOCK.acquire()
    try:
        load_state()
        now = time.time()

        if STATE["ban_until"] > now:
            Log.Debug("AniDB limiter - Skipping '%s': %s" % (url, status()))
            if remember:
                DEFERRED[url] = now
            return False

        if is_titles_url(url):
            if STATE["titles_next"] > now:
                Log.Debug("AniDB limiter - Titles dump already fetched recently; next allowed at %s" % (clock(STATE["titles_next"])))
                return False
            STATE["titles_next"] = now + TITLES_RETRY     # Becomes 24h once the download succeeds
            save_state()
            return True                                   # Static file on anidb.net, not counted against the API budget

        day = day_requests()
        if len(day) >= settings.ANIDB_DAILY_LIMIT:
            free = day[len(day) - settings.ANIDB_DAILY_LIMIT] + 86400
            if free - now > max_wait:
                Log.Warn("AniDB limiter - Daily limit of %s requests reached; next slot at %s. Using cached data for '%s'" % (settings.ANIDB_DAILY_LIMIT, clock(free), url))
                if remember:
                    DEFERRED[url] = now
                return False
        recent = recent_requests()
        if len(recent) >= settings.ANIDB_HOURLY_LIMIT:
            wait = recent[len(recent) - settings.ANIDB_HOURLY_LIMIT] + 3600 - now
            if wait > max_wait:
                Log.Warn("AniDB limiter - Hourly limit of %s requests reached; next slot at %s. Using cached data for '%s'" % (settings.ANIDB_HOURLY_LIMIT, clock(now + wait), url))
                if remember:
                    DEFERRED[url] = now
                return False
            Log.Info("AniDB limiter - Hourly limit: next slot free in %.0fs, waiting" % (wait))
            time.sleep(wait)
            recent = recent_requests()

        if background and recent and recent[-1] + background_delay() > time.time():
            Log.Debug("AniDB limiter - Background request '%s' left to the retry queue (background requests are %.0fs apart)" % (url, background_delay()))
            DEFERRED[url] = now
            return False

        if recent:
            wait = recent[-1] + settings.ANIDB_REQUEST_DELAY - time.time()
            if wait > max_wait:
                return False
            if wait > 0:
                Log.Debug("AniDB limiter - Waiting %.1fs before '%s'" % (wait, url))
                time.sleep(wait)

        STATE["recent"].append(time.time())
        save_state()
        return True
    finally:
        LOCK.release()

def next_slot(background=False):
    """Earliest time a new AniDB API request would be allowed (now, the end of a ban, or when the hourly/daily budget frees
       up). background: for a request nobody is waiting for, also background_delay() after the last request."""
    LOCK.acquire()
    try:
        load_state()
        when = budget_free_at()
        if STATE["ban_until"] > when:
            when = STATE["ban_until"]
        recent = recent_requests()
        if background and recent:
            when = max(when, recent[-1] + background_delay())
        return when
    finally:
        LOCK.release()

def was_deferred(url):
    """True if a request for url was recently refused (ban or hourly limit) rather than sent."""
    when = DEFERRED.get(url)
    return when is not None and when > time.time() - DEFERRED_MEMORY

def success(url):
    LOCK.acquire()
    try:
        if url in DEFERRED:
            del DEFERRED[url]
        STATE["fail_streak"] = 0
        if is_titles_url(url):
            STATE["titles_next"] = time.time() + TITLES_INTERVAL
        save_state()
    finally:
        LOCK.release()

def report_error(url, message):
    """AniDB answered with an error. A ban pauses all AniDB requests; other errors (e.g. unknown anime) don't."""
    LOCK.acquire()
    try:
        now = time.time()
        if "banned" not in (message or "").lower():
            Log.Warn("AniDB limiter - AniDB returned an error for '%s': %s" % (url, message))
            return
        if STATE["last_ban"] and now - STATE["last_ban"] > BAN_RESET_SECONDS:
            STATE["ban_count"] = 0
        step = STATE["ban_count"] if STATE["ban_count"] < len(BAN_STEPS_HOURS) else len(BAN_STEPS_HOURS) - 1
        STATE["ban_count"] = STATE["ban_count"] + 1
        STATE["last_ban"] = now
        STATE["ban_until"] = now + BAN_STEPS_HOURS[step] * 3600
        save_state()
        Log.Error("AniDB limiter - AniDB has BANNED this IP (ban #%s). No AniDB requests until %s; cached data will be used meanwhile." % (STATE["ban_count"], clock(STATE["ban_until"])))
    finally:
        LOCK.release()

def report_failure(url, error):
    """Network-level failure (timeout, connection refused)."""
    LOCK.acquire()
    try:
        STATE["fail_streak"] = STATE["fail_streak"] + 1
        if STATE["fail_streak"] >= SOFT_BAN_FAILURES and not is_titles_url(url):
            STATE["ban_until"] = time.time() + SOFT_BAN_SECONDS
            STATE["fail_streak"] = 0
            Log.Warn("AniDB limiter - %s consecutive AniDB failures (last: %s); pausing AniDB requests until %s" % (SOFT_BAN_FAILURES, error, clock(STATE["ban_until"])))
        save_state()
    finally:
        LOCK.release()
