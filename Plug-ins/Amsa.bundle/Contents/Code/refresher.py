"""Partial refreshes: re-download a source early when episodes on disk have no data yet.

A weekly release often arrives before the cached AniDB / TVDB copy knows about it (the copy can be up to 2 days old for
airing shows). After building the bundle, the updater asks metadata_writer.episode_report() which episodes on disk would
be written without data:
  * "unwritten": on disk but not mapped at all (e.g. AniDB's cached copy still lists 6 episodes and you added episode 7);
  * "empty": mapped, but no source has a real title or summary yet (only "Episode 7").
For those, the sources involved are downloaded again, but only if their cached copy is older than
settings.REFETCH_ANIDB_AFTER (24h, AniDB bans clients that fetch the same anime more than once a day) or
settings.REFETCH_TVDB_AFTER (6h). Each source is tried at most once per that period, even if the download fails.
"""
import os
import time

import settings
import textutil
import downloader
import sources
import anidb
import anidb_limiter
import anidb_retry
import offline_db

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

LOCK = new_lock()
TRIED = {}                       # "anidb-<id>" / "tvdb-<id>" -> time of the last early re-download (memory only)


def anidb_directory(anidb_id):
    return os.path.join("AniDB", str(anidb_id))


def tvdb_directories(tvdb_id):
    return [os.path.join("TvDB4", str(tvdb_id)), os.path.join("TvDB", str(tvdb_id))]


def anidb_age(anidb_id):
    return downloader.cache_age_of("%s.xml" % (anidb_id), anidb_directory(anidb_id))


def tvdb_age(tvdb_id):
    ages = [downloader.cache_age_of("episodes-%s.json" % (settings.TVDB4_LANGUAGE), os.path.join("TvDB4", str(tvdb_id))),
            downloader.cache_age_of("%s.xml" % (tvdb_id), os.path.join("TvDB", str(tvdb_id)))]
    ages = [age for age in ages if age is not None]
    return sorted(ages)[0] if ages else None


def may_try(key, after):
    """True (and remembered) if this source wasn't re-downloaded early within `after` seconds."""
    LOCK.acquire()
    try:
        last = TRIED.get(key)
        if last is not None and last > time.time() - after:
            return False
        TRIED[key] = time.time()
        return True
    finally:
        LOCK.release()


def is_airing(anidb_id):
    """AniDB entries that can still gain episodes: airing or upcoming (anime-offline-database), recently ended or without an
       end date (their cache age is the short one); not ones the dataset lists as finished long ago."""
    state = offline_db.status(anidb_id)
    if state in ("ONGOING", "UPCOMING"):
        return True
    short_cache = anidb.cache_age(str(anidb_id)) <= settings.DEFAULT_CACHE
    if state == "FINISHED" and not anidb_has_end_date(anidb_id):
        return False                                       # Finished, AniDB just never recorded an end date
    return short_cache


def refetch_after(anidb_id):
    """How old a cached AniDB entry must be before Refresh Metadata downloads it again: 24h for shows that can still gain
       episodes (is_airing), 7 days for finished ones, whose AniDB data rarely changes, so a library refresh doesn't
       re-download nearly every AniDB entry."""
    floor = getattr(settings, "REFRESH_SKIP_RECENT", 0)    # The setting can make it longer, never shorter than AniDB's rules
    try:
        if is_airing(anidb_id):
            return max(settings.REFETCH_ANIDB_AFTER, floor)
    except Exception:
        return max(settings.REFETCH_ANIDB_AFTER, floor)
    return max(settings.REFETCH_FINISHED_ANIDB_AFTER, floor)


def age_text(age):
    if age < 3600:
        return "%d min" % (age // 60)
    return ("%.0fh" % (age / 3600.0)) if age < 48 * 3600 else ("%.0f days" % (age / 86400.0))


def anidb_has_end_date(anidb_id):
    record = sources.get_anidb(anidb_id, False)
    return bool(record.valid and getattr(record, "end_date", None))


def wanted_sources(report, mapping):
    """(AniDB ids, TVDB ids) to re-download for the episodes in the report."""
    anidb_ids = []
    tvdb_ids = []
    for node in report.get("empty") or []:
        for mapped in node.xpath("./Mapped/anidb"):
            if textutil.is_digits(mapped.get("series")) and mapped.get("series") not in anidb_ids:
                anidb_ids.append(mapped.get("series"))
        for mapped in node.xpath("./Mapped/tvdb"):
            if textutil.is_digits(mapped.get("series")) and mapped.get("series") not in tvdb_ids:
                tvdb_ids.append(mapped.get("series"))
    if report.get("unwritten"):
        # Not mapped at all: the episode is most likely new, so check the entries that can still gain episodes, and TVDB
        for item in mapping.series_list or []:
            anidb_id = item.get("anidbid")
            if textutil.is_digits(anidb_id) and anidb_id not in anidb_ids and is_airing(anidb_id):
                anidb_ids.append(anidb_id)
        if textutil.is_digits(mapping.tvdb_id) and str(mapping.tvdb_id) not in tvdb_ids:
            tvdb_ids.append(str(mapping.tvdb_id))
    return anidb_ids, tvdb_ids


def refetch_anidb(anidb_id, rating_key):
    """Download one AniDB entry again (through the limiter). True if a new copy was saved."""
    age = anidb_age(anidb_id)
    if age is None or age < settings.REFETCH_ANIDB_AFTER or not may_try("anidb-%s" % (anidb_id), settings.REFETCH_ANIDB_AFTER):
        return False
    directory = anidb_directory(anidb_id)
    downloader.force_refresh(directory)
    try:
        sources.forget("Anidb", anidb_id)
        sources.get_anidb(anidb_id, True)
    finally:
        downloader.end_refresh(directory)
    new_age = anidb_age(anidb_id)
    if new_age is not None and new_age < 300:
        Log.Info("Refresher - AniDB '%s' downloaded again (episodes on disk had no data; the copy was %.0fh old)" % (anidb_id, age / 3600.0))
        return True
    if anidb_limiter.was_deferred(settings.ANIDB_API_URL + str(anidb_id)):
        anidb_retry.add(anidb_id, rating_key, True)
    return False


def refetch_tvdb(tvdb_id):
    """Download one TVDB series again. True if a new copy was saved."""
    age = tvdb_age(tvdb_id)
    if age is None or age < settings.REFETCH_TVDB_AFTER or not may_try("tvdb-%s" % (tvdb_id), settings.REFETCH_TVDB_AFTER):
        return False
    directories = tvdb_directories(tvdb_id)
    for directory in directories:
        downloader.force_refresh(directory)
    try:
        sources.forget("Tvdb", tvdb_id)
        sources.forget("Plex", tvdb_id)
        sources.get_tvdb(tvdb_id)
    finally:
        for directory in directories:
            downloader.end_refresh(directory)
    new_age = tvdb_age(tvdb_id)
    if new_age is not None and new_age < 300:
        Log.Info("Refresher - TVDB '%s' downloaded again (episodes on disk had no data; the copy was %.0fh old)" % (tvdb_id, age / 3600.0))
        return True
    return False


def due_in_background(anidb_ids, tvdb_ids):
    """The ids refetch_anidb / refetch_tvdb would download now (old enough, not tried within their period)."""
    anidb_due = []
    for anidb_id in anidb_ids:
        age = anidb_age(anidb_id)
        if age is not None and age >= settings.REFETCH_ANIDB_AFTER and may_try("anidb-%s" % (anidb_id), settings.REFETCH_ANIDB_AFTER):
            anidb_due.append(anidb_id)
    tvdb_due = []
    for tvdb_id in tvdb_ids:
        age = tvdb_age(tvdb_id)
        if age is not None and age >= settings.REFETCH_TVDB_AFTER and may_try("tvdb-%s" % (tvdb_id), settings.REFETCH_TVDB_AFTER):
            tvdb_due.append(tvdb_id)
    return anidb_due, tvdb_due


def refetch(report, mapping, rating_key=None, label=None):
    """Re-download what the report's episodes need. True if anything new was downloaded (then the bundle is rebuilt).
       With settings.REFRESH_IN_BACKGROUND the downloads are queued in background_refresh instead (returns False): the
       episodes are written with what's known now and the show is refreshed again if the new copies add anything."""
    if not report.get("unwritten") and not report.get("empty"):
        return False
    anidb_ids, tvdb_ids = wanted_sources(report, mapping)
    Log.Debug("Refresher - %s episodes on disk not mapped, %s without title/summary; candidates AniDB %s, TVDB %s"
              % (len(report.get("unwritten") or []), len(report.get("empty") or []), anidb_ids, tvdb_ids))
    if settings.REFRESH_IN_BACKGROUND and rating_key:
        anidb_due, tvdb_due = due_in_background(anidb_ids, tvdb_ids)
        if anidb_due or tvdb_due:
            import background_refresh
            background_refresh.add(rating_key, label, anidb_due, tvdb_due, [], "new episodes without data")
        return False
    changed = False
    for anidb_id in anidb_ids:
        try:
            changed = refetch_anidb(anidb_id, rating_key) or changed
        except Exception:
            Log.Warn("Refresher - AniDB '%s' failed: %s" % (anidb_id, textutil.exception_text()))
    for tvdb_id in tvdb_ids:
        try:
            changed = refetch_tvdb(tvdb_id) or changed
        except Exception:
            Log.Warn("Refresher - TVDB '%s' failed: %s" % (tvdb_id, textutil.exception_text()))
    return changed
