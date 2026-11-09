"""Parsed source records, reused for settings.SOURCE_MEMORY_TTL so each AniDB/TVDB record is parsed once per update
(not again in the mapping step, the metadata step and during search)."""
import time

import settings
import anidb
import tvdb_v4
import plex_themes
import anilist
import episode_sources

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

PROVIDERS = {"Anidb": anidb.AniDBSeries, "Tvdb": tvdb_v4.series, "Plex": plex_themes.PlexThemes,      # TVDB: v4 with v1 fallback
             "Anilist": lambda source_id: anilist.AniListSeries(source_id, get_anidb(source_id, False)),  # AniList: found via the (cached) AniDB entry
             # Gap fillers (episode_fill.py), keyed by AniDB id like AniList:
             "Mal": lambda source_id: episode_sources.MalEpisodes(source_id, get_anidb(source_id, False)),
             "Kitsu": lambda source_id: episode_sources.KitsuEpisodes(source_id),
             "Animethemes": lambda source_id: episode_sources.AnimeThemesSeries(source_id, get_anidb(source_id, False))}
FAILED_TTL = 120                 # A record that could not be loaded is retried after 2 minutes
CACHE = {}                       # (provider, id) -> (loaded_at, record, used_network)
CACHE_LOCK = new_lock()
ANIDB_LOCK = new_lock()          # Never load the same AniDB anime twice at once (would cost two AniDB requests)
LOADING = {}                     # (provider, id) -> lock held while that record loads (other providers)


def loading_lock(key):
    CACHE_LOCK.acquire()
    try:
        lock = LOADING.get(key)
        if lock is None:
            if len(LOADING) > 2000:
                LOADING.clear()
            lock = new_lock()
            LOADING[key] = lock
        return lock
    finally:
        CACHE_LOCK.release()


def cached(key, network):
    CACHE_LOCK.acquire()
    try:
        entry = CACHE.get(key)
    finally:
        CACHE_LOCK.release()
    if not entry:
        return None
    loaded_at, record, used_network = entry
    ttl = settings.SOURCE_MEMORY_TTL if record.valid else FAILED_TTL
    if loaded_at < time.time() - ttl:
        return None
    if not record.valid and network and not used_network:
        return None      # A cache-only miss must not block a later request that may use the network
    return record


def store(key, record, network):
    CACHE_LOCK.acquire()
    try:
        CACHE[key] = (time.time(), record, network)
        if len(CACHE) > 500:     # Keep memory bounded on big libraries
            cutoff = time.time() - settings.SOURCE_MEMORY_TTL
            for old_key in [k for k in CACHE if CACHE[k][0] < cutoff]:
                del CACHE[old_key]
    finally:
        CACHE_LOCK.release()


def forget(provider, source_id):
    """Drop a record from memory so the next get() loads it again (used after a postponed AniDB download)."""
    CACHE_LOCK.acquire()
    try:
        key = (provider, str(source_id))
        if key in CACHE:
            del CACHE[key]
    finally:
        CACHE_LOCK.release()


def get(provider, source_id, network=True):
    """Parsed record for provider ("Anidb", "Tvdb", "Plex") and id. Always returns a record; check record.valid."""
    key = (provider, str(source_id))
    record = cached(key, network)
    if record is not None:
        return record
    if provider == "Anidb":
        if network is True:
            ANIDB_LOCK.acquire()
        elif not ANIDB_LOCK.acquire(0):
            # Search must not wait behind an update's AniDB download: use whatever is cached instead
            return anidb.AniDBSeries(source_id, network=False)
        try:
            record = cached(key, network)          # Another thread may have loaded it while we waited
            if record is None:
                record = anidb.AniDBSeries(source_id, network=network)
                store(key, record, network)
        finally:
            ANIDB_LOCK.release()
        return record
    lock = loading_lock(key)
    lock.acquire()
    try:
        record = cached(key, network)              # Loaded by another thread (e.g. the AniList prefetch) while we waited
        if record is None:
            record = PROVIDERS[provider](source_id)
            store(key, record, network)
    finally:
        lock.release()
    return record


def get_anidb(anidb_id, network=True):
    """network: True (updates), "quick" (manual search: only if no waiting is needed), "background" (like quick, and only
       at background spacing; see anidb_limiter) or False (cache only)."""
    return get("Anidb", anidb_id, network)


def get_tvdb(tvdb_id):
    return get("Tvdb", tvdb_id)
