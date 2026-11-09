"""Refresh Metadata: download the show's sources again instead of reusing the cache.

Plex calls the agent with force=True when you choose Refresh Metadata (for one show or a whole library); new files from a
scan come with force=False. For a forced update, the show's cached source files are treated as expired while it runs:
  * AniDB entries: only copies older than 24h (AniDB bans clients that fetch the same anime more than once a day), or 7
    days for finished shows (refresher.refetch_after), downloaded through the limiter. One the limiter postpones is downloaded later (anidb_retry)
    and the show refreshed again then.
  * TVDB (v4 series, episodes and seasons; v1), AniList, MAL, Kitsu and AnimeThemes: unless downloaded within the setting
    "Skip sources downloaded within" (default 24 hours; 10 minutes for testing).
Images, crew, themes and the shared lists (mapping, titles, dataset) keep their usual cache times.
With "RefreshMode" set to background (the default), nothing is forced during the update: the show is written from the
cache and the same downloads are queued in background_refresh.py, which refreshes the show again only if something changed.
Repeated refreshes of the same show (DEBOUNCE_SECONDS, 2 minutes, from its last forced update starting or finishing) use the
cache as usual, so clicking Refresh Metadata twice, or Plex sending two refreshes for one show, doesn't download twice.
Different shows are independent, so a whole-library refresh downloads every show again (AniDB still through the limiter).
"""
import os
import time

import settings
import textutil
import downloader
import sources
import anidb_limiter
import anidb_retry
import refresher
import background_refresh

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

FORCE_SECONDS = 900               # Upper bound on how long a forced update can keep its directories forced
DEBOUNCE_SECONDS = 120
LOCK = new_lock()
LAST = {}                         # Show key -> time its last forced update started or finished
OWN = {}                          # Rating keys of forced updates AMSA asked for itself (not counted)


def debounced(key, now=None):
    """True if this show had a forced update start or finish within DEBOUNCE_SECONDS; records this call either way."""
    now = now or time.time()
    LOCK.acquire()
    try:
        quiet = LAST.get(key, 0) > now - DEBOUNCE_SECONDS
        LAST[key] = now
        if len(LAST) > 2000:                                   # Keep memory bounded on big library refreshes
            for old in [k for k in LAST if LAST[k] < now - DEBOUNCE_SECONDS]:
                del LAST[old]
        return quiet
    finally:
        LOCK.release()


def show_key(mapping, rating_key):
    return str(rating_key or getattr(mapping, "anidb_id", None) or getattr(mapping, "tvdb_id", None))


def done(mapping, rating_key=None):
    """Called when a forced update ends (downloaded or not): the show's 2 minutes run from here."""
    if rating_key is not None and str(rating_key) in OWN:
        del OWN[str(rating_key)]
        return
    LOCK.acquire()
    try:
        LAST[show_key(mapping, rating_key)] = time.time()
    finally:
        LOCK.release()


def anidb_ids(mapping):
    found = []
    for item in mapping.series_list or []:
        anidb_id = item.get("anidbid")
        if textutil.is_digits(anidb_id) and anidb_id not in found:
            found.append(anidb_id)
    return found


def tvdb_ids(mapping):
    found = []
    for value in [mapping.tvdb_id] + [x.get("tvdbid") for x in mapping.series_list or []]:
        if textutil.is_digits(value) and str(value) not in found:
            found.append(str(value))
    return found


def recent(directory):
    """True if this cache directory was downloaded within the setting "Refresh Metadata leaves sources downloaded within"."""
    age = background_refresh.newest_age(directory)
    return age is not None and age < settings.REFRESH_SKIP_RECENT


def kept_text(kept):
    return "Kept, downloaded recently (setting: %s; AniDB at least 24h for airing shows, 7 days for finished ones): %s" % (
        refresher.age_text(settings.REFRESH_SKIP_RECENT) if settings.REFRESH_SKIP_RECENT >= 3600 else "%d minutes" % (settings.REFRESH_SKIP_RECENT // 60), ", ".join(kept))


class Refresh:
    """The directories and records one forced update made stale; finish() puts things back."""
    def __init__(self, mapping):
        self.directories = []
        self.anidb = []
        self.kept = []
        for anidb_id in anidb_ids(mapping):
            age = refresher.anidb_age(anidb_id)
            if age is None:
                pass                                       # Not cached: downloaded as usual
            elif age >= refresher.refetch_after(anidb_id):
                self.anidb.append(anidb_id)
                self.directories.append(refresher.anidb_directory(anidb_id))
                sources.forget("Anidb", anidb_id)
            else:
                self.kept.append("AniDB %s (%s old)" % (anidb_id, refresher.age_text(age)))
            for provider, folder in (("Anilist", "AniList"), ("Mal", "MAL"), ("Kitsu", "Kitsu"), ("Animethemes", "AnimeThemes")):
                directory = os.path.join(folder, anidb_id)
                if recent(directory):
                    continue
                self.directories.append(directory)
                sources.forget(provider, anidb_id)
        self.tvdb = []
        for tvdb_id in tvdb_ids(mapping):
            age = background_refresh.newest_age(os.path.join("TvDB4", tvdb_id))
            if age is not None and age < settings.REFRESH_SKIP_RECENT:
                self.kept.append("TVDB %s (%s old)" % (tvdb_id, refresher.age_text(age)))
                continue
            self.tvdb.append(tvdb_id)
            self.directories.extend(refresher.tvdb_directories(tvdb_id))
            self.directories.append(os.path.join("TvDB4", tvdb_id, "seasons"))
            sources.forget("Tvdb", tvdb_id)
            sources.forget("Plex", tvdb_id)
        for directory in self.directories:
            downloader.force_refresh(directory, FORCE_SECONDS)
        Log.Info("ForcedRefresh - Refresh Metadata: cached copies ignored for AniDB %s, TVDB %s, AniList/MAL/Kitsu/AnimeThemes for every AniDB entry%s"
                 % (", ".join(self.anidb) or "none", ", ".join(self.tvdb) or "none",
                    ("; " + kept_text(self.kept)) if self.kept else ""))

    def finish(self, rating_key=None):
        for directory in self.directories:
            downloader.end_refresh(directory)
        for anidb_id in self.anidb:
            age = refresher.anidb_age(anidb_id)
            if (age is None or age >= 300) and anidb_limiter.was_deferred(settings.ANIDB_API_URL + anidb_id):
                anidb_retry.add(anidb_id, rating_key, True)


BACKGROUND = "background"         # start(): write from the cache now, queue the downloads in background_refresh afterwards


def queue_background(mapping, rating_key, label):
    """After a forced update written from the cache: queue its downloads (background_refresh.py)."""
    anidb_ids, tvdb_ids, extra, kept = background_refresh.forced_sources(mapping)
    if kept:
        Log.Debug("ForcedRefresh - %s" % (kept_text(kept)))
    background_refresh.add(rating_key, label, anidb_ids, tvdb_ids, extra, "Refresh Metadata")


def start(mapping, rating_key=None, own=False):
    """A Refresh for this forced update, or None if AMSA asked for this refresh itself (postponed AniDB download, airing check)
       or the same show had a forced update within the last 2 minutes. Call done() when the update ends.
       own: anidb_retry.own_refresh(rating_key), checked by the updater on every update (forced or not), so AMSA's mark is
       always used up by the update it asked for and can't swallow a later Refresh Metadata of yours."""
    if own:
        OWN[str(rating_key)] = True
        Log.Debug("ForcedRefresh - Refresh requested by AMSA itself: the cache is used as usual")
        return None
    if debounced(show_key(mapping, rating_key)):
        Log.Info("ForcedRefresh - This show was refreshed less than %d minutes ago: the cache is used as usual" % (DEBOUNCE_SECONDS // 60))
        return None
    if settings.REFRESH_IN_BACKGROUND and rating_key:
        Log.Info("ForcedRefresh - Refresh Metadata: cached data applied now; fresh copies are downloaded in the background afterwards")
        return BACKGROUND
    try:
        return Refresh(mapping)
    except Exception:
        Log.Warn("ForcedRefresh - Preparing the forced refresh failed: %s" % (textutil.exception_text()))
        return None
