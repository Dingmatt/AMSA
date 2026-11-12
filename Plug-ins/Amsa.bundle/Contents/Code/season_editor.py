"""Season titles and summaries through the local Plex Media Server API.

Plex ignores season titles and summaries that a legacy agent writes into its metadata (the framework's season model has no
title, and the summary isn't applied), but Plex's own edit API accepts both - it is what Plex Web's "Edit season" uses.
So after an update, AMSA waits for Plex to finish applying it, then edits each season:
  PUT /library/sections/<section>/all?type=3&id=<season>&title.value=..&title.locked=1&summary.value=..&summary.locked=1
The fields are locked so Plex's next refresh doesn't blank them; AMSA re-applies them itself on later refreshes.
A title or summary the user typed is never overwritten: AMSA only replaces a field that is empty, still Plex's default
("Season 2", "Specials") or exactly what AMSA wrote last time (remembered in Cache/Seasons/).
"""
import re
import time
import urllib2

import settings
import textutil
import downloader
import tvdb_v4
import title_index
import anidb_retry

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

DELAY = 30                       # Seconds after the update before editing (Plex applies the agent's data first)
LOCK = new_lock()
PENDING = {}                     # show rating key -> {plex season number (str): (title or None, summary or None, [source summaries])}
POSTERS_PENDING = {}             # show rating key -> [plex season numbers AMSA wrote posters for]
SHOW_IMAGES_PENDING = {}         # show rating key -> ["posters", "art", "banners"] AMSA wrote
PICKS_PENDING = {}               # show rating key -> [(item key, endpoint, [keys your pick may be listed under], label, [its 40-digit names])]
SCHEDULED = {}                   # show rating keys with a season_titles run scheduled
UNLOCK_WORD = "unlock-images"    # In a manual search (Fix Match): unlock the images of the show then matched
UNLOCK_REQUESTS = {}             # search result id ("anidb-2369") -> time of the search asking for the unlock
RESETS = {}                      # show rating key -> time its images were unlocked: none of its images count as chosen
UNLOCK_WAIT = 900                # Seconds a search's unlock request waits for the update of the result picked
RESET_FOR = 300                  # Seconds an unlocked show's images count as AMSA's (the update right after the unlock)
DEFAULT_TITLE = re.compile(r"^(season [0-9]+|specials)?$", re.IGNORECASE)


def request_unlock(result_id):
    """A manual search with "unlock-images" returned this result: its next update unlocks the show's images."""
    LOCK.acquire()
    try:
        UNLOCK_REQUESTS[result_id] = time.time()
    finally:
        LOCK.release()


def unlock_requested(result_id):
    """True once (used up) if a search asked to unlock this result's images within UNLOCK_WAIT seconds."""
    LOCK.acquire()
    try:
        asked = UNLOCK_REQUESTS.pop(result_id, None)
    finally:
        LOCK.release()
    return asked is not None and time.time() - asked < UNLOCK_WAIT


def resetting(show_key):
    """True during the update right after this show's images were unlocked: no image counts as chosen in Plex."""
    asked = RESETS.get(str(show_key))
    return asked is not None and time.time() - asked < RESET_FOR


def unlock_images(show_key):
    """Unlock the show's poster, background and banner and each season's poster and background in Plex (Plex Web can't),
       so they follow AMSA's settings again. Same edit API as the season titles. Returns the number of items unlocked."""
    show = (tvdb_v4.parse_json(plex_request("/library/metadata/%s" % (show_key))).get("MediaContainer") or {})
    section = show.get("librarySectionID") or ((show.get("Metadata") or [{}])[0]).get("librarySectionID")
    if not section:
        Log.Warn("Seasons - Couldn't unlock the images: Plex didn't say which library item %s is in" % (show_key))
        return 0
    plex_request("/library/sections/%s/all?type=2&id=%s&thumb.locked=0&art.locked=0&banner.locked=0" % (section, show_key), "PUT")
    unlocked = 1
    children = (tvdb_v4.parse_json(plex_request("/library/metadata/%s/children" % (show_key))).get("MediaContainer") or {})
    for item in children.get("Metadata", []) or []:
        if item.get("type", "season") != "season" or item.get("ratingKey") is None:
            continue
        try:
            plex_request("/library/sections/%s/all?type=3&id=%s&thumb.locked=0&art.locked=0" % (section, item.get("ratingKey")), "PUT")
            unlocked += 1
        except Exception as e:
            Log.Debug("Seasons - Couldn't unlock season %s's images (%s)" % (item.get("index"), e))
    RESETS[str(show_key)] = time.time()
    return unlocked


def queue(show_key, seasons):
    """Remember the season texts for one show and apply them shortly (a later update of the same show replaces them)."""
    if not show_key or not seasons:
        return
    LOCK.acquire()
    try:
        PENDING[str(show_key)] = seasons
    finally:
        LOCK.release()
    schedule(str(show_key))
    Log.Debug("Seasons - %s season titles/summaries for item %s will be applied through Plex in %ss" % (len(seasons), show_key, DELAY))


def queue_show_images(show_key, kinds):
    """AMSA wrote the show's posters / art / banners: remember which ones Plex shows once the update is applied."""
    if not show_key or not kinds:
        return
    LOCK.acquire()
    try:
        SHOW_IMAGES_PENDING[str(show_key)] = kinds[:]
    finally:
        LOCK.release()
    schedule(str(show_key))


def queue_posters(show_key, numbers):
    """AMSA wrote these seasons' posters: remember which one Plex shows once the update is applied (remember_posters)."""
    if not show_key or not numbers:
        return
    LOCK.acquire()
    try:
        POSTERS_PENDING[str(show_key)] = numbers[:]
    finally:
        LOCK.release()
    schedule(str(show_key))


def queue_picks(show_key, picks):
    """Your locked picks (show and seasons) as Plex showed them before the update: selected again afterwards if Plex
       switched to AMSA's first image while the list was rewritten (restore_picks)."""
    if not show_key or not picks:
        return
    LOCK.acquire()
    try:
        PICKS_PENDING[str(show_key)] = picks[:]
    finally:
        LOCK.release()
    schedule(str(show_key))


SELECT_PATH = {"posters": "poster", "arts": "art", "banners": "banner"}


def names_in(entry):
    """The 40-digit names in an image entry's keys (Plex names an agent's image <agent>_<40 hex digits>)."""
    text = u" ".join([textutil.safe_unicode(entry.get(name) or "") for name in ("ratingKey", "key", "thumb")])
    return re.findall(r"([0-9a-f]{40})", text)


def is_pick(entry, pick_keys, names):
    """True if this image entry is your pick: one of its keys, or the same 40-digit name under another prefix."""
    if entry.get("ratingKey") in pick_keys:
        return True
    for name in names_in(entry):
        if name in names:
            return True
    return False


def restore_picks(picks):
    """Select each pick again where Plex now shows another image; one Info line for the ones changed back, and for any
       pick not found in Plex's list, what Plex shows instead (so it can be checked)."""
    restored = []
    gone = []
    for item_key, endpoint, pick_keys, label, names in picks:
        if not pick_keys and not names:
            continue
        try:
            listed = images_of(item_key, endpoint)
            selected = selected_poster(item_key, endpoint, listed)
            if selected is not None and is_pick(selected, pick_keys, names):
                continue
            found = [entry.get("ratingKey") for entry in listed if entry.get("ratingKey") and is_pick(entry, pick_keys, names)]
            if not found:
                gone.append(label)
                Log.Debug("Seasons - %s: your pick (%s) isn't among the %s images Plex lists; Plex shows %s" % (label, ", ".join(pick_keys),
                          len(listed), selected.get("ratingKey") if selected is not None else "none selected"))
                continue
            plex_request("/library/metadata/%s/%s?url=%s" % (item_key, SELECT_PATH.get(endpoint, "poster"), quote(found[0])), "PUT")
            restored.append(label)
            Log.Debug("Seasons - %s: Plex showed %s; selected your pick %s again" % (label, selected.get("ratingKey") if selected is not None else "none", found[0]))
        except Exception as e:
            Log.Debug("Seasons - Couldn't check your pick for %s (%s)" % (label, e))
    if restored:
        Log.Info("Seasons - Plex had switched away from your locked pick; selected again: %s" % (", ".join(restored)))
    if gone:
        Log.Info("Seasons - Your locked pick wasn't found in Plex's list (details at Debug): %s" % (", ".join(gone)))


def schedule(key):
    """Run season_titles for this show DELAY seconds from now, once."""
    LOCK.acquire()
    try:
        if key in SCHEDULED:
            return
        SCHEDULED[key] = True
    finally:
        LOCK.release()

    def season_titles():
        apply_show(key)
    title_index.run_later(DELAY, season_titles)


def plex_request(path, method=None, timeout=None):
    """A request to the local Plex server; the answer's text (a GET) or the response (with method). timeout: seconds,
       for a long answer (Plex's own default is 20)."""
    headers = {"Accept": "application/json"}
    token = anidb_retry.plex_token()
    if token:
        headers["X-Plex-Token"] = token
    if method:
        return HTTP.Request(settings.PMS_URL + path, headers=headers, method=method, cacheTime=0, immediate=True)
    if timeout:
        return HTTP.Request(settings.PMS_URL + path, headers=headers, cacheTime=0, immediate=True, timeout=timeout).content
    return HTTP.Request(settings.PMS_URL + path, headers=headers, cacheTime=0, immediate=True).content


def quote(value):
    return urllib2.quote(textutil.safe_unicode(value).encode("utf-8"), "")


def remembered(season_key):
    try:
        text = downloader.load_stale("%s.json" % (season_key), "Seasons", True)
        return tvdb_v4.parse_json(text) if text else {}
    except Exception:
        return {}


def same_text(one, two):
    """Equal apart from spacing and line breaks (Plex tidies those, so an exact comparison saw AMSA's own summaries as
       "edited in Plex")."""
    return re.sub(r"\s+", " ", textutil.safe_unicode(one or "")).strip() == re.sub(r"\s+", " ", textutil.safe_unicode(two or "")).strip()


def images_of(item_key, endpoint="posters"):
    """Every image entry Plex holds for an item (from every agent, and uploads). endpoint: posters, arts or banners."""
    return tvdb_v4.parse_json(plex_request("/library/metadata/%s/%s" % (item_key, endpoint))).get("MediaContainer", {}).get("Metadata") or []


def selected_poster(season_key, endpoint="posters", posters=None):
    """The image entry Plex shows for an item ({"ratingKey": ..., ...}), or None. endpoint: posters, arts or banners.
       posters: images_of() already read."""
    if posters is None:
        posters = images_of(season_key, endpoint)
    for poster in posters:
        if str(poster.get("selected")).lower() in ("1", "true"):
            return poster
    return None


# The show's own images: Plex resets a poster / background / banner you pick to AMSA's first choice too.
# kind -> (Plex endpoint, Plex's lock field, memory key)
SHOW_IMAGES = {"posters": ("posters", "thumb", "poster_key"), "art": ("arts", "art", "art_key"), "banners": ("banners", "banner", "banner_key")}


def image_choice(item_key, kind, fields):
    """Why AMSA should leave this item's images of this kind alone, or None to write them. Same rules as season posters:
       locked, an uploaded / other agent's image, or a different AMSA image than right after AMSA's last update -> leave."""
    endpoint, lock_field, memory_key = SHOW_IMAGES[kind]
    for field in fields or []:
        if field.get("name") == lock_field and str(field.get("locked")).lower() in ("1", "true"):
            return "locked in Plex"
    selected = selected_poster(item_key, endpoint)
    if selected is None:
        return None
    text = u" ".join([textutil.safe_unicode(selected.get(name) or "") for name in ("ratingKey", "key", "thumb", "provider")])
    if "com.plexapp.agents.amsa" not in text:
        return "an uploaded or other image is selected in Plex"
    last = remembered(item_key).get(memory_key)
    if last and selected.get("ratingKey") != last:
        return "you chose another one in Plex"
    return None


def chosen_show_images(show_key, kinds):
    """{kind: reason} for the show's posters / art / banners AMSA should leave alone. On any doubt, nothing is left alone."""
    leave = {}
    if resetting(show_key):
        return leave
    try:
        details = tvdb_v4.parse_json(plex_request("/library/metadata/%s" % (show_key))).get("MediaContainer", {})
        fields = ((details.get("Metadata") or [{}])[0]).get("Field") or []
    except Exception as e:
        Log.Debug("Seasons - Couldn't read item %s to check for chosen images (%s)" % (show_key, e))
        return leave
    for kind in kinds:
        try:
            reason = image_choice(show_key, kind, fields)
            if reason:
                leave[kind] = reason
        except Exception as e:
            Log.Debug("Seasons - Couldn't check item %s's %s (%s)" % (show_key, kind, e))
    return leave


def remember_show_images(show_key, kinds):
    """Right after an update that wrote these kinds: remember which image Plex shows for each."""
    memory = remembered(show_key)
    changed = False
    for kind in kinds:
        endpoint, lock_field, memory_key = SHOW_IMAGES[kind]
        try:
            selected = selected_poster(show_key, endpoint)
            if selected is not None and selected.get("ratingKey") and memory.get(memory_key) != selected.get("ratingKey"):
                memory[memory_key] = selected.get("ratingKey")
                changed = True
        except Exception as e:
            Log.Debug("Seasons - Couldn't remember item %s's %s (%s)" % (show_key, kind, e))
    if changed:
        try:
            downloader.save_file(tvdb_v4.dump_json(memory), "%s.json" % (show_key), "Seasons")
        except Exception as e:
            Log.Debug("Seasons - Couldn't save item %s's images (%s)" % (show_key, e))


def chosen_posters(show_key, numbers, keys=None):
    """Seasons whose poster AMSA should leave alone: {plex season number: reason}. Plex doesn't lock a season poster you pick
       from its list, so besides a locked poster this compares the poster Plex shows with the one it showed right after
       AMSA's last update (remembered by remember_posters):
         * locked, an uploaded poster or another agent's -> yours;
         * a different AMSA poster than last time -> you picked it -> yours;
         * the same one, or nothing remembered yet, or none selected -> AMSA's, so it is updated.
       numbers: Plex season numbers AMSA has posters for. On any doubt, nothing is left alone.
       keys: a dict that gets {plex season number: Plex's key for the season} of the locked ones (to read the pick)."""
    leave = {}
    if resetting(show_key):
        return leave
    try:
        container = tvdb_v4.parse_json(plex_request("/library/metadata/%s/children" % (show_key))).get("MediaContainer", {})
    except Exception as e:
        Log.Debug("Seasons - Couldn't read the seasons of item %s to check for chosen posters (%s)" % (show_key, e))
        return leave
    for item in container.get("Metadata", []) or []:
        number = str(item.get("index"))
        season_key = item.get("ratingKey")
        if item.get("type", "season") != "season" or season_key is None or number not in numbers:
            continue
        try:
            details = tvdb_v4.parse_json(plex_request("/library/metadata/%s" % (season_key))).get("MediaContainer", {})
            locked = False
            for field in ((details.get("Metadata") or [{}])[0]).get("Field") or []:
                if field.get("name") == "thumb" and str(field.get("locked")).lower() in ("1", "true"):
                    locked = True
            if locked:
                leave[number] = "poster locked in Plex"
                if keys is not None:
                    keys[number] = season_key
                continue
            selected = selected_poster(season_key)
            if selected is None:
                continue
            text = u" ".join([textutil.safe_unicode(selected.get(name) or "") for name in ("ratingKey", "key", "thumb", "provider")])
            if "com.plexapp.agents.amsa" not in text:
                leave[number] = "an uploaded or other poster is selected in Plex"
                continue
            last = remembered(season_key).get("poster_key")
            if last and selected.get("ratingKey") != last:
                leave[number] = "you chose another poster in Plex"
                Log.Debug("Seasons - Season %s: Plex shows %s, AMSA's last update left %s" % (number, selected.get("ratingKey"), last))
            elif not last:
                Log.Debug("Seasons - Season %s: no poster remembered yet; AMSA's choice is applied and remembered" % (number))
        except Exception as e:
            Log.Debug("Seasons - Couldn't check season %s of item %s for a chosen poster (%s)" % (number, show_key, e))
    return leave


def remember_posters(container, numbers):
    """Right after an update AMSA wrote season posters for (season_titles, 30s later): remember which poster Plex shows
       now, so a different one next time means you picked it."""
    for item in container.get("Metadata", []) or []:
        number = str(item.get("index"))
        season_key = item.get("ratingKey")
        if item.get("type", "season") != "season" or season_key is None or number not in numbers:
            continue
        try:
            selected = selected_poster(season_key)
            if selected is None or not selected.get("ratingKey"):
                continue
            memory = remembered(season_key)
            if memory.get("poster_key") != selected.get("ratingKey"):
                memory["poster_key"] = selected.get("ratingKey")
                if "poster" in memory:
                    del memory["poster"]                   # Older URL-based memory
                downloader.save_file(tvdb_v4.dump_json(memory), "%s.json" % (season_key), "Seasons")
        except Exception as e:
            Log.Debug("Seasons - Couldn't remember season %s's poster (%s)" % (number, e))


def apply_show(show_key):
    LOCK.acquire()
    try:
        seasons = PENDING.pop(show_key, None)
        posters = POSTERS_PENDING.pop(show_key, None)
        show_images = SHOW_IMAGES_PENDING.pop(show_key, None)
        picks = PICKS_PENDING.pop(show_key, None)
        RESETS.pop(show_key, None)
        SCHEDULED.pop(show_key, None)
    finally:
        LOCK.release()
    if picks:
        restore_picks(picks)
    if show_images:
        remember_show_images(show_key, show_images)
    if not seasons and not posters:
        return
    try:
        container = tvdb_v4.parse_json(plex_request("/library/metadata/%s/children" % (show_key))).get("MediaContainer", {})
    except Exception as e:
        Log.Warn("Seasons - Couldn't read the seasons of item %s from Plex (%s); season titles/summaries not applied" % (show_key, e))
        return
    if posters:
        remember_posters(container, posters)
    if not seasons:
        return
    section = container.get("librarySectionID")
    for item in container.get("Metadata", []) or []:
        number = str(item.get("index"))
        if number not in seasons or item.get("type", "season") != "season":
            continue
        try:
            apply_season(section or item.get("librarySectionID"), item, seasons[number])
        except Exception:
            Log.Warn("Seasons - Season %s of item %s failed: %s" % (number, show_key, textutil.exception_text()))


def apply_season(section, item, wanted):
    season_key = str(item.get("ratingKey"))
    number = item.get("index")
    title, summary = wanted[0], wanted[1]
    known = wanted[2] if len(wanted) > 2 else []           # Source summaries: text one of the sources gave is AMSA's
    last = remembered(season_key)
    params = []
    changed = {}
    current_title = item.get("title") or ""
    if not title and last.get("title") and current_title == last.get("title"):
        # AMSA named this season earlier but has no name for it now (e.g. the name became the show's own title, which
        # is trimmed): back to Plex's default name, unlocked
        default = u"Specials" if str(number) == "0" else u"Season %s" % (number)
        params.append("title.value=%s&title.locked=0" % (quote(default)))
        changed["title"] = None                              # Forget it, so it isn't reset again next time
        Log.Info("Seasons - Season %s: AMSA's earlier title '%s' reset to '%s'" % (number, current_title, default))
    for field, new_value, current in (("title", title, item.get("title") or ""), ("summary", summary, item.get("summary") or "")):
        if not new_value or new_value == current:
            if new_value:
                changed[field] = new_value
            continue
        if same_text(new_value, current):
            changed[field] = new_value                     # Plex already shows it (it may tidy spaces and line breaks)
            continue
        is_ours = same_text(current, last.get(field)) or (field == "title" and DEFAULT_TITLE.match(current.strip())) or not current.strip()
        if not is_ours and field == "summary":
            for text in known or []:
                if same_text(current, text):
                    is_ours = True
        if not is_ours:
            Log.Info("Seasons - Season %s %s was edited in Plex; leaving it as it is" % (number, field))
            continue
        params.append("%s.value=%s&%s.locked=1" % (field, quote(new_value), field))
        changed[field] = new_value
    if params:
        plex_request("/library/sections/%s/all?type=3&id=%s&%s" % (section, season_key, "&".join(params)), "PUT")
        Log.Info("Seasons - Season %s (item %s): %s" % (number, season_key, ", ".join(["%s set" % (p.split(".")[0]) for p in params])))
    if changed or params:
        memory = {}
        for field in last:
            memory[field] = last[field]                      # Keep what isn't changed now (e.g. the poster AMSA chose)
        for field in changed:
            memory[field] = changed[field]
        try:
            downloader.save_file(tvdb_v4.dump_json(memory), "%s.json" % (season_key), "Seasons")
        except Exception as e:
            Log.Debug("Seasons - Couldn't remember season %s: %s" % (season_key, e))
