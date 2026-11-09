"""Downloads with a disk cache under DataItems/Cache.

- Fresh cached copies are used without touching the network.
- If a download fails (or AniDB refuses / bans), the last cached copy is used regardless of age.
- AniDB requests go through anidb_limiter.
- URLs that returned 404 are remembered (across restarts) and not requested again for NOT_FOUND_RETRY.
"""
import os
import re
import ssl
import time
import gzip
import zlib
import urllib2
import StringIO

from lxml import etree

import environment
import settings
import textutil
import anidb_limiter

try:
    import threading
    new_lock = threading.Lock
except ImportError:          # Fall back to Plex's own lock API if the sandbox refuses the module
    new_lock = lambda: Thread.Lock()

SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_SSLv23)   # Created once; unverified on purpose for older Windows/NAS Plex installs
ERROR_RESPONSE = re.compile(r"^\s*(<\?xml[^>]*\?>\s*)?<error\b", re.IGNORECASE)
NOT_FOUND_FILE = "not-found.txt"
NOT_FOUND_LOCK = new_lock()
URL_LOCKS_LOCK = new_lock()
URL_LOCKS = {}                # url -> lock held while that file downloads (file_from_url)
NOT_FOUND = {}               # url -> time of the last 404
NOT_FOUND_LOADED = [False]


# Cache paths ##########################################################################################################################################################
def cache_path(filename="", directory=""):
    """Path (relative to DataItems unless directory is absolute) used for a cached file by load, save and stale fallback alike."""
    return os.path.join(str(settings.CACHE_DIR), str(directory), str(filename))


FORCED = {}                      # cache directory -> time until which fresh copies there are ignored (early re-download, see refresher.py)


def force_refresh(directory, seconds=600):
    """Treat cached files in this directory as expired for a while, so the next request downloads them (the old copy stays as fallback)."""
    FORCED[str(directory)] = time.time() + seconds


def end_refresh(directory):
    if str(directory) in FORCED:
        del FORCED[str(directory)]


def is_forced(directory):
    until = FORCED.get(str(directory))
    return until is not None and until > time.time()


def cache_age_of(filename, directory=""):
    """Seconds since a cached file was saved, or None if it isn't cached."""
    try:
        full_path = os.path.abspath(os.path.join(settings.CACHE_PATH, "..", cache_path(filename, directory)))
        if os.path.isfile(full_path):
            return time.time() - os.stat(full_path).st_mtime
    except Exception:
        pass
    return None


def load_cached(filename="", directory="", max_age=settings.DEFAULT_CACHE):
    """Cached file contents if younger than max_age seconds, else None."""
    if not filename:
        return None
    if is_forced(directory):
        return None
    path = cache_path(filename, directory)
    try:
        if Data.Exists(path):
            full_path = os.path.abspath(os.path.join(settings.CACHE_PATH, "..", path))
            if os.path.isfile(full_path) and os.stat(full_path).st_mtime > (time.time() - max_age):
                return Data.Load(path)
    except Exception as e:
        Log.Debug("Downloader - load_cached() - '%s': %s" % (path, e))
    return None


def load_stale(filename="", directory="", quiet=False):
    """Cached file contents regardless of age; used when a download fails or is not allowed.
       quiet: AMSA's own state files (not downloads), so no "download unavailable" log line."""
    if not filename:
        return None
    path = cache_path(filename, directory)
    try:
        if Data.Exists(path):
            if not quiet:
                Log.Info("Downloader - Using cached copy (download unavailable): '%s'" % (path))
            return Data.Load(path)
    except Exception as e:
        Log.Debug("Downloader - load_stale() - '%s': %s" % (path, e))
    return None


def save_file(content, filename="", directory="", export=False):
    root_path = settings.EXPORT_PATH if export else settings.CACHE_PATH
    root_dir = settings.EXPORT_DIR if export else settings.CACHE_DIR
    absolute_dir = os.path.join(root_path, directory)
    if not os.path.exists(absolute_dir):
        try:
            os.makedirs(absolute_dir)
        except OSError:
            pass  # Another thread created it first
    try:
        Data.Save(os.path.join(root_dir, directory, filename), content)
    except Exception as e:
        environment.write_failed(os.path.join(absolute_dir, filename), e)   # A warning with path, error, owner and user (first per folder each hour)
        raise


# Remembered 404s ######################################################################################################################################################
def load_not_found():
    if NOT_FOUND_LOADED[0]:
        return
    NOT_FOUND_LOADED[0] = True
    try:
        path = cache_path(NOT_FOUND_FILE)
        if Data.Exists(path):
            content = Data.Load(path)
            if not isinstance(content, basestring):
                content = content.decode("utf-8")
            cutoff = time.time() - settings.NOT_FOUND_RETRY
            for line in content.splitlines():
                parts = line.split("\t", 1)
                if len(parts) == 2 and textutil.safe_float(parts[0]) > cutoff:
                    NOT_FOUND[parts[1]] = textutil.safe_float(parts[0])
    except Exception as e:
        Log.Debug("Downloader - Could not read %s: %s" % (NOT_FOUND_FILE, e))


def save_not_found():
    cutoff = time.time() - settings.NOT_FOUND_RETRY
    lines = ["%.0f\t%s" % (when, url) for url, when in NOT_FOUND.items() if when > cutoff]
    try:
        Data.Save(cache_path(NOT_FOUND_FILE), "\n".join(lines))
    except Exception as e:
        environment.write_failed(os.path.join(settings.CACHE_PATH, NOT_FOUND_FILE), e)


def is_known_missing(url):
    NOT_FOUND_LOCK.acquire()
    try:
        load_not_found()
        when = NOT_FOUND.get(url)
        return when is not None and when > time.time() - settings.NOT_FOUND_RETRY
    finally:
        NOT_FOUND_LOCK.release()


def mark_missing(url):
    NOT_FOUND_LOCK.acquire()
    try:
        load_not_found()
        NOT_FOUND[url] = time.time()
        save_not_found()
    finally:
        NOT_FOUND_LOCK.release()


# Network ##############################################################################################################################################################
def is_anidb_url(url):
    return url.startswith(settings.ANIDB_API_URL) or url.startswith(settings.ANIDB_TITLES_URL)


def get_url(url, timeout=settings.DEFAULT_TIMEOUT, extra_headers=None, post_data=None):
    """Raw response body (decompressed). extra_headers are added to the defaults; post_data makes it a POST."""
    headers = {}
    for key in settings.HTTP_HEADERS:
        headers[key] = settings.HTTP_HEADERS[key]
    for key in (extra_headers or {}):
        headers[key] = extra_headers[key]
    if post_data is not None:
        request = urllib2.Request(url, data=post_data, headers=headers)
    else:
        request = urllib2.Request(url, headers=headers)
    response = urllib2.urlopen(request, context=SSL_CONTEXT, timeout=timeout)
    try:
        content = response.read()
        encoding = (response.info().get("Content-Encoding") or "").lower()
    finally:
        response.close()
    if encoding == "gzip":
        return gzip.GzipFile(fileobj=StringIO.StringIO(content)).read()
    if encoding == "deflate":
        try:
            return zlib.decompress(content)
        except zlib.error:
            return zlib.decompress(content, -zlib.MAX_WBITS)
    return content


def xml_from_url(url, filename="", directory="", max_age=settings.DEFAULT_CACHE, timeout=settings.DEFAULT_TIMEOUT, network=True):
    """Parsed XML for url: fresh cache, else download, else stale cache. Returns None (never raises) when nothing is available.
       network=False uses the cache only (automatic matching must not spend AniDB requests);
       network="quick" (manual search) may request AniDB only if that needs no queueing or long wait;
       network="background" (background refresh) also only at background spacing (anidb_limiter.acquire)."""
    is_anidb = is_anidb_url(url)
    result = load_cached(filename, directory, max_age)
    # Small AniDB responses are still valid data; re-requesting them would count against AniDB's limits
    from_cache = bool(result and (len(result) > 1024 or is_anidb))

    if not from_cache:
        result = None
        try:
            if not network:
                Log.Debug("Downloader - Cache only, not requesting '%s'" % (url))
            elif is_anidb and not anidb_limiter.acquire(url, network == "quick", network == "background"):
                pass   # Limiter refused (ban, hourly limit, titles fetched recently): use the cached copy below
            else:
                Log.Debug("Downloader - Requesting '%s'" % (url))
                result = get_url(url, timeout)
                head = result[:300] if result else ""
                if not isinstance(head, basestring):
                    head = head.decode("utf-8", "replace")
                if ERROR_RESPONSE.match(head):
                    message = re.sub(r"<[^>]+>", " ", head).strip()
                    Log.Warn("Downloader - Server returned an error for '%s': %s" % (url, message))
                    result = None
                    if is_anidb:
                        anidb_limiter.report_error(url, message)
                elif is_anidb and result:
                    anidb_limiter.success(url)
        except Exception as e:
            result = None
            Log.Warn("Downloader - Download failed for '%s': %s" % (url, e))
            if is_anidb and network:
                anidb_limiter.report_failure(url, e)

        if result and (len(result) > 1024 or is_anidb) and filename:
            try:
                save_file(result, os.path.basename(filename), directory)
            except Exception as e:
                Log.Debug("Downloader - Saving '%s' failed: %s" % (filename, e))
        elif not result or len(result) <= 1024:
            stale = load_stale(filename, directory)
            if stale:
                result = stale

    if not result:
        if network:
            Log.Error("Downloader - No data available for '%s'" % (url))
        else:
            Log.Debug("Downloader - Not cached yet, and this lookup uses the cache only: '%s'" % (url))   # Expected (e.g. matching, entries without files)
        return None
    try:
        return etree.fromstring(result)
    except Exception as e:
        Log.Error("Downloader - Invalid XML from '%s' (%s): %s" % (url, filename, e))
        return None


def url_lock(url):
    URL_LOCKS_LOCK.acquire()
    try:
        lock = URL_LOCKS.get(url)
        if lock is None:
            if len(URL_LOCKS) > 2000:
                URL_LOCKS.clear()                  # Keep memory bounded; threads already waiting keep their own reference
            lock = new_lock()
            URL_LOCKS[url] = lock
        return lock
    finally:
        URL_LOCKS_LOCK.release()


def file_from_url(url, filename="", directory="", max_age=settings.DEFAULT_CACHE, timeout=settings.DEFAULT_TIMEOUT):
    """File contents for url (images, themes), cached on disk. Returns None (never raises) when unavailable.
       One download per url at a time: several Plex episodes can share one TVDB episode (and its thumbnail), and two
       threads saving the same file at once made Plex's Data.Save fail ("release unlocked lock"). A thread that waited
       uses the file the first one saved."""
    result = load_cached(filename, directory, max_age)
    if result:
        return result
    if not url:
        return None
    lock = url_lock(url)
    lock.acquire()
    try:
        result = load_cached(filename, directory, max_age)
        if result:
            return result
        return download_file(url, filename, directory, timeout)
    finally:
        lock.release()


def download_file(url, filename, directory, timeout):
    """file_from_url's download (its url lock held)."""
    result = None
    if is_known_missing(url):
        return load_stale(filename, directory)
    Log.Debug("Downloader - Requesting '%s'" % (url))
    try:
        result = get_url(url, timeout)
    except urllib2.HTTPError as e:
        result = None
        if e.code == 404:
            mark_missing(url)
            Log.Debug("Downloader - Not found (404), will not retry for %sh: '%s'" % (int(settings.NOT_FOUND_RETRY / 3600), url))
        else:
            Log.Info("Downloader - HTTP error %s for '%s'" % (e.code, url))
    except Exception as e:
        result = None
        Log.Info("Downloader - Download failed for '%s': %s" % (url, e))
    if result and filename:
        try:
            save_file(result, os.path.basename(filename), directory)
        except Exception as e:
            Log.Debug("Downloader - Saving '%s' failed: %s" % (filename, e))
    elif not result:
        result = load_stale(filename, directory)
    return result or None
