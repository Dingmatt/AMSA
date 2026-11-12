"""Cache clean-up and size report.

Runs in the background shortly after the first search/update and then every 3 days. It only ever looks inside AMSA's own
cache folder (Plug-in Support/Data/com.plexapp.agents.amsa/DataItems/Cache): every path is checked to be inside it after
resolving links, links themselves are skipped, and only files directly managed by a known source folder are candidates.

Kept for good:
  * AniDB data (AniDB/<id>/<id>.xml): small, and the most expensive to get back (AniDB bans clients that over-fetch);
  * image fingerprints and saved poster sets (Fingerprints): small, and slow to work out again (about 0.3s each);
  * AMSA's own memory and state: Seasons (season titles AMSA set), OfflineDB, files at the top of the cache
    (queues, limiter state, mapping lists), and any folder AMSA doesn't know.
Debug bundles (Bundles): kept while the setting "Generate debug bundles" is on, all deleted when it's off (here, and
when the settings are saved: remove_bundles).
Deleted when not refreshed for a while:
  * images and theme music (any source): after IMAGE_DAYS (30) - cheap to download again, and Plex keeps its own copies;
  * other sources' data (TVDB, AniList, MAL, Kitsu, AnimeThemes, Plex): after DATA_DAYS (180), long past their cache
    periods (up to 2 days to a few weeks), so the stale copy is still there as a fallback while a show is in use.
"""
import os
import time

import settings
import textutil

IMAGE_DAYS = 30
DATA_DAYS = 180
BUNDLES = "Bundles"                # Debug bundles (setting "Generate debug bundles")
SOURCE_FOLDERS = ("AniDB", "AniList", "MAL", "Kitsu", "AnimeThemes", "TvDB", "TvDB4", "Plex", "Fingerprints")
MEDIA_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".mp3", ".m4a", ".ogg", ".flac", ".webm")
STATE = {"next": 0, "running": False}
RUN_EVERY = 3 * 86400


def plain_path(path):
    """Without Windows' long-path prefix: Plex's file functions on Windows return '\\\\?\\D:\\...' (and '\\\\?\\UNC\\server\\...'
       for network shares) while AMSA's cache path has no prefix, so the same folder looked like two different places."""
    text = path
    if text[:8].upper() == "\\\\?\\UNC\\":
        return "\\\\" + text[8:]
    if text[:4] in ("\\\\?\\", "\\\\.\\", "//?/"):
        return text[4:]
    return text


def resolved(path):
    """Absolute, normalised form of a path; links resolved where the platform and Plex's sandbox allow it."""
    for name in ("realpath", "abspath", "normpath"):
        try:
            return os.path.normcase(plain_path(getattr(os.path, name)(path)))
        except Exception:
            continue                                       # Not available here (sandbox) or failed: try the next one
    return os.path.normcase(plain_path(path))


def inside(path, base):
    """True if path is somewhere inside base (never base itself). Links are never followed by the walk and are skipped,
       so this is a second check against paths escaping the cache."""
    try:
        real = resolved(path)
        root = resolved(base).rstrip("\\/")
    except Exception as e:
        STATE["rejected_example"] = STATE.get("rejected_example") or "%s (%s)" % (path, e)
        return False
    if real.startswith(root + os.sep) or real.startswith(root + "/"):
        return True
    STATE["rejected_example"] = STATE.get("rejected_example") or "%s -> %s (cache %s)" % (path, real, root)
    return False


def is_media(name):
    return os.path.splitext(name)[1].lower() in MEDIA_EXTENSIONS


def max_age_days(folder, name):
    """Days a file may go unrefreshed before it is deleted, or None to keep it for good."""
    if folder == BUNDLES:
        return None if getattr(settings, "DEBUG_BUNDLES", False) else 0
    if folder not in SOURCE_FOLDERS:
        return None
    if is_media(name):
        return IMAGE_DAYS
    if folder in ("AniDB", "Fingerprints"):
        return None
    return DATA_DAYS


def remove_bundles():
    """Setting "Generate debug bundles" off: delete the saved bundles (Cache/Bundles) now, not at the next clean-up.
       Returns the number of files deleted."""
    if getattr(settings, "DEBUG_BUNDLES", False):
        return 0
    base = settings.CACHE_PATH
    folder = os.path.join(base, BUNDLES)
    deleted = 0
    try:
        if os.path.islink(folder) or not os.path.isdir(folder):
            return 0
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            try:
                if name.endswith(".bundle.xml") and not os.path.islink(path) and os.path.isfile(path) and inside(path, base):
                    os.remove(path)
                    deleted += 1
            except OSError:
                pass                                       # In use: the next clean-up removes it
    except Exception as e:
        Log.Debug("CacheCleaner - Couldn't remove the debug bundles: %s" % (e))
    if deleted:
        Log.Info("CacheCleaner - %s debug bundles removed (setting \"Generate debug bundles\" is off)" % (deleted))
    return deleted


def bundles_clean_up():
    """Named for Plex's log ("Scheduled a timed thread named 'bundles_clean_up'")."""
    remove_bundles()


def megabytes(size):
    return "%.1f MB" % (size / 1048576.0)


def due():
    return not STATE["running"] and STATE["next"] < time.time()


def cache_clean_up():
    """Named for Plex's log ("Scheduled a timed thread named 'cache_clean_up'")."""
    run()


def start_later(delay):
    """Claim the next run now and do it in a background thread after delay seconds (Plex's timer API, else a plain thread)."""
    STATE["next"] = time.time() + RUN_EVERY
    try:
        Thread.CreateTimer(delay, cache_clean_up)
    except Exception:
        import threading
        timer = threading.Timer(delay, cache_clean_up)
        timer.daemon = True
        timer.start()


def run(delete=True, now=None):
    """Walk the cache: delete what the rules allow (delete=False: count only) and log the sizes per folder.
       Returns {"folders": {folder: [files, bytes]}, "removed": [files, bytes], "would_remove": [files, bytes]}."""
    if STATE["running"]:
        return None
    STATE["running"] = True
    STATE["next"] = time.time() + RUN_EVERY
    now = now or time.time()
    base = settings.CACHE_PATH
    folders = {}
    removed = [0, 0]
    would = [0, 0]
    failed = 0
    rejected = 0
    STATE["rejected_example"] = None
    started = time.time()
    try:
        if not os.path.isdir(base):
            return None
        for top in sorted(os.listdir(base)):
            top_path = os.path.join(base, top)
            if os.path.islink(top_path):
                continue
            if os.path.isfile(top_path):
                count = folders.setdefault("(top level)", [0, 0])
                count[0] = count[0] + 1
                count[1] = count[1] + os.path.getsize(top_path)
                continue
            count = folders.setdefault(top, [0, 0])
            for root, dirs, files in os.walk(top_path, topdown=False):
                for name in files:
                    path = os.path.join(root, name)
                    try:
                        if os.path.islink(path) or not os.path.isfile(path):
                            continue
                        if not inside(path, base):
                            rejected = rejected + 1
                            continue
                        size = os.path.getsize(path)
                        days = max_age_days(top, name)
                        if days is not None and os.stat(path).st_mtime <= now - days * 86400:
                            would[0] = would[0] + 1
                            would[1] = would[1] + size
                            if delete:
                                os.remove(path)
                                removed[0] = removed[0] + 1
                                removed[1] = removed[1] + size
                                continue
                        count[0] = count[0] + 1
                        count[1] = count[1] + size
                    except OSError:
                        failed = failed + 1             # In use (Windows) or vanished: try again next time
                if delete and top in SOURCE_FOLDERS:
                    for name in dirs:
                        path = os.path.join(root, name)
                        try:
                            if not os.path.islink(path) and inside(path, base) and not os.listdir(path):
                                os.rmdir(path)
                        except OSError:
                            pass
        total = [0, 0]
        parts = []
        for folder in sorted(folders.keys(), key=lambda x: -folders[x][1]):
            total[0] = total[0] + folders[folder][0]
            total[1] = total[1] + folders[folder][1]
            parts.append("%s %s (%s files)" % (folder, megabytes(folders[folder][1]), folders[folder][0]))
        Log.Info("CacheCleaner - Cache: %s in %s files: %s" % (megabytes(total[1]), total[0], ", ".join(parts) or "empty"))
        if rejected:
            Log.Warn("CacheCleaner - %s files skipped: not confirmed to be inside the cache folder (e.g. %s)" % (rejected, STATE["rejected_example"]))
        if delete:
            Log.Info("CacheCleaner - Removed %s files (%s): images not refreshed for %s days, data other than AniDB and fingerprints for %s days%s%s; scan took %.1fs"
                     % (removed[0], megabytes(removed[1]), IMAGE_DAYS, DATA_DAYS, "" if getattr(settings, "DEBUG_BUNDLES", False) else ", debug bundles (setting off)",
                        (", %s files in use, skipped" % (failed)) if failed else "", time.time() - started))
        else:
            Log.Info("CacheCleaner - Would remove %s files (%s)" % (would[0], megabytes(would[1])))
        return {"folders": folders, "removed": removed, "would_remove": would}
    except Exception:
        Log.Warn("CacheCleaner - Failed: %s" % (textutil.exception_text()))
        return None
    finally:
        STATE["running"] = False
