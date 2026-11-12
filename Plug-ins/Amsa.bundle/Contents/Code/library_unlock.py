"""Setting "Maintenance: Unlock all images on save": the "unlock-images" search word (season_editor) for every show.

Plex Web can't unlock a poster, background or banner once one is picked. Saving the settings with this ticked:
  1. switches the setting off again (and reads it back), so the next save doesn't repeat it;
  2. unlocks the poster, background and banner of every show, and the poster and background of every season, in each
     library that uses AMSA (Plex's edit API, as for one show);
  3. saves the list of shows unlocked (Cache/unlock-pending.json, kept over a restart). Each show's next update counts
     none of its images as picked in Plex (uploads and earlier picks included), so every list follows the settings,
     then takes the show off the list and logs how many are left. When the list is empty, the log says the unlock is
     finished.
The refresh itself is Plex's ("Refresh all metadata" on the library).
"""
import time

import textutil
import downloader
import tvdb_v4
import season_editor
import title_index

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

IDENTIFIER = "com.plexapp.agents.amsa"
SETTING = "UnlockAllImages"
STATE_FILE = "unlock-pending.json"
START_DELAY = 5                  # Seconds after the save: Plex stores the page's values first, then AMSA switches this one off
LIST_TIMEOUT = 60                # Seconds for a library listing (a whole library's seasons in one answer)
LOCK = new_lock()
STATE = {"loaded": False, "shows": {}, "total": 0}    # shows: Plex rating key -> show title, still to refresh
RUNNING = {"now": False}


def requested():
    """True if the settings were saved with the box ticked."""
    try:
        return bool(Prefs[SETTING])
    except Exception:
        return False


def start():
    """From ValidatePrefs: unlock in the background, so saving the settings page doesn't wait for it."""
    title_index.run_later(START_DELAY, unlock_library)


def unlock_library():
    if RUNNING["now"]:
        Log.Info("Unlock - Already unlocking; the second request is ignored")
        return
    RUNNING["now"] = True
    try:
        switch_off()
        started = time.time()
        shows = {}
        seasons = 0
        failed = 0
        sections = amsa_sections()
        if not sections:
            Log.Warn("Unlock - No library uses AMSA (or Plex didn't list them); nothing unlocked")
            return
        for section in sections:
            key = section.get("key")
            for item in listing(key, 2):
                try:
                    season_editor.plex_request("/library/sections/%s/all?type=2&id=%s&thumb.locked=0&art.locked=0&banner.locked=0"
                                               % (key, item.get("ratingKey")), "PUT")
                    shows[str(item.get("ratingKey"))] = textutil.safe_unicode(item.get("title") or "")
                except Exception as e:
                    failed += 1
                    Log.Debug("Unlock - Show '%s' (%s): %s" % (item.get("title"), item.get("ratingKey"), e))
            for item in listing(key, 3):
                try:
                    season_editor.plex_request("/library/sections/%s/all?type=3&id=%s&thumb.locked=0&art.locked=0"
                                               % (key, item.get("ratingKey")), "PUT")
                    seasons += 1
                except Exception as e:
                    failed += 1
                    Log.Debug("Unlock - Season %s of '%s' (%s): %s" % (item.get("index"), item.get("parentTitle"), item.get("ratingKey"), e))
        add(shows)
        Log.Info("Unlock - %s shows and %s seasons unlocked in %s librar%s (%s) in %.0fs%s. Refresh the librar%s (Refresh all metadata): "
                 "each show's next update ignores earlier picks, and the log counts down the shows left"
                 % (len(shows), seasons, len(sections), "y" if len(sections) == 1 else "ies", ", ".join([textutil.safe_unicode(s.get("title") or "?") for s in sections]),
                    time.time() - started, ("; %s couldn't be unlocked (details at Debug)" % (failed)) if failed else "",
                    "y" if len(sections) == 1 else "ies"))
    except Exception:
        Log.Error("Unlock - Unlocking the libraries failed: %s" % (textutil.exception_text()))
    finally:
        RUNNING["now"] = False


def switch_off():
    """Untick the setting through Plex (as prefs_repair stores settings) and check Plex took it."""
    try:
        season_editor.plex_request("/:/plugins/%s/prefs/set?%s=false" % (IDENTIFIER, SETTING))
    except Exception as e:
        Log.Warn("Unlock - Couldn't switch '%s' off (%s): untick it on the settings page so the next save doesn't unlock again" % (SETTING, e))
        return
    if requested():
        Log.Warn("Unlock - Plex still has '%s' ticked: untick it on the settings page so the next save doesn't unlock again" % (SETTING))
    else:
        Log.Info("Unlock - Setting switched off again (Plex confirms it); reopen the settings page to see it unticked")


def amsa_sections():
    """Plex's TV libraries that use AMSA."""
    container = tvdb_v4.parse_json(season_editor.plex_request("/library/sections", timeout=LIST_TIMEOUT)).get("MediaContainer") or {}
    return [section for section in container.get("Directory") or [] if section.get("agent") == IDENTIFIER and section.get("type", "show") == "show"]


def listing(section_key, kind):
    """Every show (kind 2) or season (kind 3) in a library. Tried twice: a busy Plex can be slow to answer."""
    for attempt in (1, 2):
        try:
            container = tvdb_v4.parse_json(season_editor.plex_request("/library/sections/%s/all?type=%s" % (section_key, kind), timeout=LIST_TIMEOUT))
            return (container.get("MediaContainer") or {}).get("Metadata") or []
        except Exception as e:
            if attempt == 2:
                Log.Warn("Unlock - Couldn't list the %s of library %s (%s); save the settings with the box ticked again to retry"
                         % ("shows" if kind == 2 else "seasons", section_key, e))
                return []
            Log.Debug("Unlock - Listing library %s failed (%s); trying again" % (section_key, e))
    return []


# Shows still to refresh ##########################################################################################################
def load():
    if STATE["loaded"]:
        return
    STATE["loaded"] = True
    try:
        text = downloader.load_stale(STATE_FILE, "", True)
        saved = tvdb_v4.parse_json(text) if text else {}
        STATE["shows"] = saved.get("shows") or {}
        STATE["total"] = saved.get("total") or len(STATE["shows"])
    except Exception as e:
        Log.Debug("Unlock - Couldn't read %s (%s)" % (STATE_FILE, e))


def save():
    try:
        downloader.save_file(tvdb_v4.dump_json({"shows": STATE["shows"], "total": STATE["total"]}), STATE_FILE, "")
    except Exception as e:
        Log.Warn("Unlock - Couldn't save the shows still to refresh (%s)" % (e))


def add(shows):
    LOCK.acquire()
    try:
        load()
        STATE["shows"].update(shows)
        STATE["total"] = len(STATE["shows"])
        save()
    finally:
        LOCK.release()


def begin_update(show_key):
    """At the start of a show's update: True if it was unlocked and hasn't refreshed since. Its images then count as
       AMSA's for this update (season_editor.resetting)."""
    if not show_key:
        return False
    LOCK.acquire()
    try:
        load()
        waiting = str(show_key) in STATE["shows"]
    finally:
        LOCK.release()
    if waiting:
        season_editor.RESETS[str(show_key)] = time.time()
    return waiting


def finished(show_key, title):
    """After the show's update succeeded: off the list, and the countdown logged."""
    LOCK.acquire()
    try:
        load()
        if STATE["shows"].pop(str(show_key), None) is None:
            return
        left = len(STATE["shows"])
        total = STATE["total"]
        if not left:
            STATE["total"] = 0
        save()
    finally:
        LOCK.release()
    if left:
        Log.Info("Unlock - '%s' refreshed with its images unlocked (%s of %s shows left)" % (title, left, total))
    else:
        Log.Info("Unlock - '%s' refreshed: all %s shows have refreshed since the unlock, so it's finished" % (title, total))


def pending_count():
    LOCK.acquire()
    try:
        load()
        return len(STATE["shows"])
    finally:
        LOCK.release()
