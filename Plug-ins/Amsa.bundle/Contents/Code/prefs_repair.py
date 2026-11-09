"""Settings Plex can't read, converted to their new option (or, failing that, the default its settings page shows).

A setting saved when AMSA's settings were text boxes (e.g. "AniDB,TVDB,Plex") isn't one of its dropdown's options. Plex's
settings page then shows the setting's default, and AMSA uses that default too (settings.page_default). Plex only saves the
settings you change, so such a value would stay in Plex's preferences file for good.

A minute after the agent starts, AMSA asks Plex for its settings (the same request Plex's settings page makes). For each
saved value Plex can't read, it reads the old text (from Plex's preferences file, read-only, else from Plex's answer) and
finds the matching new option (a blank one gets the default): "AniDB,TVDB,Plex" -> "AniDB > TVDB" (sources a setting doesn't offer are dropped, in
order), "400" -> "400 (recommended)", "en" -> "en - English", "yes" -> on. A value saved blank, or with no match, gets the
default the page shows instead. Values are stored through Plex, so Plex's memory and its file agree, then read back; anything that
didn't take is logged as a warning with how to fix it by hand. Settings never saved are left alone: Plex already
gives AMSA their default.
"""
import json
import os
import re

import settings
import textutil

IDENTIFIER = "com.plexapp.agents.amsa"
DELAY = 60
STATE = {"done": False}
SOURCES = {"anidb": "AniDB", "tvdb": "TVDB", "thetvdb": "TVDB", "tvdb3": "TVDB", "tvdb4": "TVDB", "anilist": "AniList", "plex": "Plex"}
OFF_WORDS = ["off", "none", "no", "disabled", "false", "0"]
ON_WORDS = ["on", "yes", "enabled", "true", "1"]


def unescape(text):
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&#39;", "'").replace("&amp;", "&")


def parse_settings(text):
    """{setting id: value} from Plex's answer to its settings request: JSON (MediaContainer.Setting[]) or, as plug-in
       settings are usually answered, XML (<Setting id=".." value=".." .../>). None if it's neither."""
    text = text or ""
    if not isinstance(text, str):
        try:
            text = text.decode("utf-8", "replace")
        except Exception:
            text = "%s" % (text)
    values = {}
    try:
        data = json.loads(text)
        for item in (data.get("MediaContainer") or {}).get("Setting") or []:
            if item.get("id"):
                values[item.get("id")] = "" if item.get("value") is None else "%s" % (item.get("value"))
        return values
    except Exception:
        pass
    for match in re.finditer(r"<Setting\b([^>]*)>", text):
        attributes = {}
        for pair in re.finditer(r'([A-Za-z_]+)="([^"]*)"', match.group(1)):
            attributes[pair.group(1)] = unescape(pair.group(2))
        if attributes.get("id"):
            values[attributes["id"]] = attributes.get("value", "")
    if values or "<MediaContainer" in text:
        return values
    return None


def current():
    """{setting id: raw value} as Plex has it saved, from Plex's own settings request; None if Plex can't be asked."""
    import season_editor
    path = "/:/plugins/%s/prefs" % (IDENTIFIER)
    try:
        text = season_editor.plex_request(path)
    except Exception as e:
        Log.Info("Settings - Couldn't ask Plex for the settings (%s, request %s)" % (e, path))
        return None
    values = parse_settings(text)
    if values is None:
        Log.Info("Settings - Plex's answer to %s wasn't JSON or XML settings: %r" % (path, ("%s" % (text or ""))[:300]))
        return None
    Log.Debug("Settings - Plex reported %s settings" % (len(values)))
    return values


def saved_file():
    """{setting id: text} exactly as Plex's preferences file holds it (read only, never written); {} if it can't be read."""
    values = {}
    try:
        descriptor = os.open(settings.PREFS_FILE, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            content = os.read(descriptor, os.fstat(descriptor).st_size + 1)
        finally:
            os.close(descriptor)
        if not isinstance(content, str):
            content = content.decode("utf-8", "replace")
        for match in re.finditer(r"<([A-Za-z0-9_]+)\s*/>", content):  # <Setting/>: saved blank
            values[match.group(1)] = ""
        for match in re.finditer(r"<([A-Za-z0-9_]+)>([^<]*)</\1>", content):
            text = unescape(match.group(2))
            values[match.group(1)] = text
    except Exception as e:
        if os.path.exists(settings.PREFS_FILE):
            import environment
            Log.Info("Settings - Couldn't read Plex's preferences file %s; using Plex's settings request instead" % (environment.describe(settings.PREFS_FILE, e)))
        else:
            Log.Debug("Settings - No preferences file at '%s'" % (settings.PREFS_FILE))
    return values


def readable(key):
    """True if Plex gives the agent a value for this setting (Prefs is None when the saved value isn't a valid option)."""
    try:
        return Prefs[key] is not None
    except Exception:
        return True                                       # Not a setting Plex knows: leave it alone


def stored(key, label):
    """True if Plex now gives AMSA exactly the option that was stored."""
    try:
        value = Prefs[key]
    except Exception:
        return False
    if isinstance(value, bool):
        return ("true" if value else "false") == label
    return value is not None and "%s" % (value) == label


def plain(label):
    """An option's label without its "(recommended)"-style note, lower case."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", label or "").strip().lower()


def label_sources(label):
    """["AniDB", "TVDB"] for "AniDB > TVDB"; [] for "Off"; None if the label isn't a list of sources."""
    text = plain(label)
    if text == "off":
        return []
    if text.endswith(" only"):
        text = text[:-5]
    found = []
    for part in re.split(r"\s*>\s*|, then ", text):         # "AniDB > TVDB"; also the older "AniDB, then TVDB"
        if part.strip() == "fallback":                    # Episode lists end with the second tier (setting EpisodeFallback)
            continue
        name = SOURCES.get(part.strip())
        if not name:
            return None
        found.append(name)
    return found


def convert_sources(options, raw):
    """Position of the option matching an old source list ("AniDB,TVDB,Plex"); None if the options aren't source lists or
       nothing matches. Sources the setting doesn't offer are dropped, keeping the order; if no option has exactly the rest,
       the one sharing the longest start with it is used (fewest extra sources on a tie)."""
    lists = []
    for option in options:
        sources = label_sources(option)
        if sources is None:
            return None
        lists.append(sources)
    offered = []
    for sources in lists:
        for name in sources:
            if name not in offered:
                offered.append(name)
    wanted = []
    words = [part.strip().lower() for part in re.split(r"[,;|]", raw) if part.strip()]
    if len(words) == 1 and words[0] in OFF_WORDS:
        return lists.index([]) if [] in lists else None
    for word in words:
        name = SOURCES.get(word)
        if name and name in offered and name not in wanted:
            wanted.append(name)
    if not wanted:
        return None
    if wanted in lists:
        return lists.index(wanted)
    best = None
    for index in range(len(lists)):
        shared = 0
        while shared < len(lists[index]) and shared < len(wanted) and lists[index][shared] == wanted[shared]:
            shared += 1
        if shared:
            score = (shared, -len(lists[index]))
            if best is None or score > best[0]:
                best = (score, index)
    return best[1] if best else None


def number(text):
    try:
        return float(text)
    except Exception:
        return None


def convert_value(options, raw):
    """Position of the option an old value names: the whole label ("All"), or its first word ("400" for "400 (recommended)",
       "en" for "en - English", "4" for "4 seconds"); else, for numeric options, the nearest number. None if nothing fits."""
    text = raw.strip().lower()
    for index in range(len(options)):
        if plain(options[index]) == text:
            return index
    for index in range(len(options)):
        first = re.split(r"\s+-\s+|\s+", plain(options[index]))[0]
        if first == text:
            return index
    value = number(text)
    if value is None:
        return None
    numbers = []
    for index in range(len(options)):
        option_value = number(re.split(r"\s+", plain(options[index]))[0])
        if option_value is not None:
            numbers.append((abs(option_value - value), index))
    if len(numbers) * 2 < len(options) or not numbers:
        return None
    numbers.sort()
    return numbers[0][1]


def target(entry, raw):
    """(value to store, its label, why), or None. why: "converted from the old value", or the reason the default is used."""
    kind = entry.get("type")
    if kind == "enum":
        options = entry.get("values") or []
        if raw.strip():
            index = convert_sources(options, raw)
            if index is None:
                index = convert_value(options, raw)
            if index is not None:
                return (str(index), options[index], "converted from the old value")
        default = entry.get("default")
        if default in options:
            return (str(options.index(default)), default, "blank, so the default" if not raw.strip() else "no matching option, so the default")
    elif kind == "bool":
        text = raw.strip().lower()
        if text in ON_WORDS or text in OFF_WORDS:
            value = text in ON_WORDS
            return ("true" if value else "false", "true" if value else "false", "converted from the old value")
        value = str(entry.get("default")).lower() == "true"
        return ("true" if value else "false", "true" if value else "false", "blank, so the default" if not text else "no matching option, so the default")
    return None


def invalid(entries, values, texts=None):
    """{setting id: (old text, value to store, its label, why, where the old text was read)}: settings Plex can't read
       (Prefs[key] is None), and settings saved blank in Plex's file (Plex reads those as the default, but the file keeps
       the blank for good). Plex's own answer decides, not a guess at how
       its settings request reports values; a setting Plex can read (including one never saved, which Plex gives its
       default) is left alone. The old text comes from Plex's file when it has it (Plex's settings request may report
       something else for a value it can't read)."""
    found = {}
    for entry in entries:
        key = entry.get("id")
        blank_in_file = bool(texts) and key in texts and not (texts.get(key) or "").strip()
        if not key or entry.get("type") not in ["enum", "bool"] or (readable(key) and not blank_in_file):
            continue
        if texts and key in texts:                       # The file holds exactly what's saved, blank included
            old = (texts.get(key) or "").strip()
            origin = "Plex's preferences file"
        else:
            old = (values.get(key) or "").strip()
            origin = "Plex's settings request"
        result = target(entry, old)
        if result:
            found[key] = (old, result[0], result[1], result[2], origin)
    return found


def describe(bad, keys):
    return ", ".join(["%s ('%s' -> '%s')" % (key, bad[key][0], bad[key][2]) for key in keys])


def run():
    if STATE["done"]:
        return
    STATE["done"] = True
    try:
        entries = settings.page_entries()
        texts = saved_file()
        values = current()
        if values is None:
            bad = invalid(entries, texts, texts) if texts else {}
            if bad:
                Log.Warn("Settings - Couldn't store fixes through Plex; these settings are saved blank or with an older AMSA's value that isn't one of their options, "
                         "so their default is used. Set each on the settings page and save: %s"
                         % (", ".join(["%s (choose '%s')" % (key, bad[key][2]) for key in sorted(bad.keys())])))
            else:
                unset = sorted(settings.PAGE["unset"].keys())
                if unset and not texts:
                    Log.Warn("Settings - Couldn't check the saved settings through Plex; these use their default because no valid value is saved: %s. "
                             "To store one, change it on the settings page, save, then change it back and save again" % (", ".join(unset)))
            return
        bad = invalid(entries, values, texts)
        if not bad:
            return
        import season_editor
        for key in sorted(bad.keys()):
            old, value, label, why, origin = bad[key]
            path = "/:/plugins/%s/prefs/set?%s=%s" % (IDENTIFIER, key, season_editor.quote(value))
            Log.Info("Settings - Changing %s: saved '%s' (from %s); storing '%s' (%s) as %s, request %s"
                     % (key, old, origin, label, why, value, path))
            try:
                answer = season_editor.plex_request(path)
                Log.Debug("Settings - %s: Plex answered %r" % (key, (answer or "")[:200]))
            except Exception as e:
                Log.Warn("Settings - %s: the request to Plex failed: %s" % (key, e))
        converted = []
        defaulted = []
        failed = []
        for key in sorted(bad.keys()):
            try:
                now = Prefs[key]
            except Exception as e:
                now = "unreadable (%s)" % (e)
            Log.Info("Settings - %s: Plex now gives AMSA %r (wanted '%s')" % (key, now, bad[key][2]))
            if not stored(key, bad[key][2]):
                failed.append(key)
            elif bad[key][3] == "converted from the old value":
                converted.append(key)
            else:
                defaulted.append(key)
        if converted:
            Log.Info("Settings - %s settings saved by an older AMSA were converted to their new option: %s" % (len(converted), describe(bad, converted)))
        if defaulted:
            Log.Info("Settings - %s settings saved blank or with no matching option were set to the default the settings page shows: %s"
                     % (len(defaulted), describe(bad, defaulted)))
        if failed:
            Log.Warn("Settings - %s settings are saved blank or with a value that isn't one of their options and couldn't be fixed automatically, so their default is used. "
                     "Set each on the settings page and save (if it already shows that choice, change it, save, change it back and save again): %s"
                     % (len(failed), ", ".join(["%s (choose '%s')" % (key, bad[key][2]) for key in failed])))
    except Exception:
        Log.Warn("Settings - Checking the saved settings failed: %s" % (textutil.exception_text()))


def prefs_repair():
    """Named for Plex's log ("Scheduled a timed thread named 'prefs_repair'")."""
    run()


def start():
    """Called from Start(): once, a minute later (Plex must be answering requests to the agent by then)."""
    try:
        Thread.CreateTimer(DELAY, prefs_repair)
    except Exception:
        import threading
        timer = threading.Timer(DELAY, prefs_repair)
        timer.daemon = True
        timer.start()
