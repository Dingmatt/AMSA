"""What AMSA is running on, and whether it can read and write where it needs to, for debugging installs (NAS, Linux, Docker).

At start: one line describing the system (platform, Python, the user Plex runs AMSA as) and one line per place AMSA uses,
saying whether it can be read or written. A problem is a warning naming the path, the error (e.g. EACCES), the path's owner
and permissions, and the user AMSA runs as, so a fix like `chown -R plex:plex '<path>'` can be read straight off the log.

During use: write_failed() turns the first failed save in each folder (per hour) into a warning with the same details, so
a cache that can't be written isn't hidden at debug level.
"""
import os
import sys
import time
import errno

import settings

REPORTED = {}                   # folder -> time its last failed write was reported as a warning
REPORT_EVERY = 3600
USER = {"text": None}


def user_text():
    """'plex (uid 999, gid 999)' on Linux/NAS; the account name on Windows."""
    if USER["text"] is None:
        name = ""
        ids = ""
        try:
            uid = os.getuid()
            gid = os.getgid()
            ids = "uid %s, gid %s" % (uid, gid)
            try:
                import pwd
                name = pwd.getpwuid(uid)[0]
            except Exception:
                name = ""
        except Exception:
            ids = ""
        if not name:
            for key in ("USER", "USERNAME", "LOGNAME"):
                try:
                    name = os.environ.get(key) or ""
                except Exception:
                    name = ""
                if name:
                    break
        USER["text"] = ("%s (%s)" % (name or "unknown user", ids)) if ids else (name or "unknown user")
    return USER["text"]


def error_text(error):
    """'EACCES: Permission denied' for an OS error; the message otherwise."""
    number = getattr(error, "errno", None)
    if number:
        try:
            return "%s: %s" % (errno.errorcode.get(number, "errno %s" % (number)), os.strerror(number))
        except Exception:
            pass
    return "%s" % (error)


def owner_text(path):
    """'owner uid 0, gid 0, mode 755' for the path, or the nearest folder above it that exists."""
    probe = path
    for attempt in range(10):
        try:
            info = os.stat(probe)
            text = "owner uid %s, gid %s, mode %03o" % (info.st_uid, info.st_gid, info.st_mode & 511)
            if probe != path:
                text = "'%s' doesn't exist; nearest folder '%s': %s" % (path, probe, text)
            return text
        except Exception:
            parent = os.path.dirname(probe)
            if not parent or parent == probe:
                break
            probe = parent
    return "owner unknown"


def describe(path, error):
    return "'%s' (%s; %s; AMSA runs as %s)" % (path, error_text(error), owner_text(path), user_text())


def write_failed(path, error, label="Downloader"):
    """A save failed: a warning with the details for the first failure in this folder each hour, debug after that."""
    folder = os.path.dirname(path) or path
    now = time.time()
    if now - REPORTED.get(folder, 0) >= REPORT_EVERY:
        REPORTED[folder] = now
        Log.Warn("%s - Couldn't write %s. Check that the folder is writable by the user Plex runs as (more failures in this folder this hour are logged at debug level)"
                 % (label, describe(path, error)))
    else:
        Log.Debug("%s - Couldn't write '%s': %s" % (label, path, error_text(error)))


def check_read(label, path, folder=False):
    try:
        if folder:
            os.listdir(path)
        else:
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            os.close(descriptor)
        return None
    except Exception as e:
        return "%s: can't read %s" % (label, describe(path, e))


def check_write(label, path, relative):
    """Writes and deletes a small file with Plex's Data.Save, the way AMSA saves everything (os.access is unreliable on
       network shares and ACLs, so a real write is the only trustworthy test). relative: the folder under DataItems."""
    probe = os.path.join(relative, "amsa-write-test.tmp")
    try:
        if not os.path.isdir(path):
            os.makedirs(path)
        Data.Save(probe, "ok")
    except Exception as e:
        return "%s: can't write in %s" % (label, describe(path, e))
    try:
        Data.Remove(probe)
    except Exception:
        try:
            os.remove(os.path.join(path, "amsa-write-test.tmp"))
        except Exception as e:
            return "%s: can write but can't delete %s (the cache cleaner needs to delete)" % (label, describe(os.path.join(path, "amsa-write-test.tmp"), e))
    return None


def system_text():
    try:
        python = sys.version.split()[0]
    except Exception:
        python = "unknown"
    try:
        token = "set" if os.environ.get("PLEXTOKEN") else "not set"
    except Exception:
        token = "unknown"
    return "%s (%s), Python %s, running as %s, Plex token %s, Plex at %s" % (sys.platform, os.name, python, user_text(), token, settings.PMS_URL)


def report():
    """Called from Start(): the system line, then each place AMSA uses."""
    try:
        Log.Info("Environment - %s" % (system_text()))
        plugin_support = os.path.dirname(os.path.dirname(settings.PREFS_FILE))
        checks = [
            ("AMSA's code", check_read("AMSA's code", settings.CODE_DIR, True), settings.CODE_DIR),
            ("Settings page (DefaultPrefs.json)", check_read("Settings page (DefaultPrefs.json)", os.path.join(settings.CODE_DIR, "..", "DefaultPrefs.json")), os.path.join(settings.CODE_DIR, "..", "DefaultPrefs.json")),
            ("Plex's Plug-in Support folder", check_read("Plex's Plug-in Support folder", plugin_support, True), plugin_support),
            ("Cache", check_write("Cache", settings.CACHE_PATH, settings.CACHE_DIR), settings.CACHE_PATH),
        ]
        if os.path.exists(settings.PREFS_FILE):
            checks.append(("Saved settings", check_read("Saved settings", settings.PREFS_FILE), settings.PREFS_FILE))
        problems = []
        fine = []
        for label, problem, path in checks:
            if problem:
                problems.append(problem)
            else:
                fine.append("%s '%s'" % (label, os.path.normpath(path)))
        Log.Info("Environment - OK: %s" % ("; ".join(fine) if fine else "nothing"))
        if not os.path.exists(settings.PREFS_FILE):
            Log.Info("Environment - No saved settings yet at '%s' (normal until AMSA's settings are first saved)" % (settings.PREFS_FILE))
        for problem in problems:
            Log.Warn("Environment - %s" % (problem))
    except Exception as e:
        Log.Warn("Environment - Checking the environment failed: %s" % (e))
