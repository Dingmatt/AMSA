"""Library health report: what AMSA couldn't fill in, in one place in the log.

Every update records its show's leftovers (episodes on disk AMSA has no mapping for, episodes with neither title nor
summary). Once a day, and 5 minutes after Plex starts the agent, AMSA logs a report:
  * shows in libraries using AMSA that aren't matched to anything (asked from Plex, local requests only);
  * shows with episodes on disk without data, worst first;
  * AniDB downloads still waiting in the retry queue, and shows in the background refresh queue.
The records are kept in Cache/health.json (never removed by the cache clean-up). A show that's no longer in Plex drops out
of the report the next time it runs.
"""
import time

import settings
import textutil
import downloader
import tvdb_v4

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

STATE_FILE = "health.json"
FIRST_RUN = 300
RUN_EVERY = 86400
MAX_LINES = 15                    # Per section; the rest is counted
LOCK = new_lock()
SHOWS = {}                        # rating key -> {"title", "unwritten": ["S06E14", ...], "empty": [...], "updated": t}
STATE = {"loaded": False, "started": False}


def label(key):
    """('6', '14') -> 'S06E14'."""
    try:
        return "S%02dE%02d" % (int(key[0]), int(key[1]))
    except Exception:
        return "%s" % (key,)


def load():
    LOCK.acquire()
    try:
        if STATE["loaded"]:
            return
        STATE["loaded"] = True
        try:
            path = downloader.cache_path(STATE_FILE)
            if Data.Exists(path):
                data = tvdb_v4.parse_json(Data.Load(path)) or {}
                for key in data.get("shows") or {}:
                    SHOWS[key] = data["shows"][key]
        except Exception as e:
            Log.Debug("Health - Reading %s failed: %s" % (STATE_FILE, e))
    finally:
        LOCK.release()


def save():
    """Call with LOCK held."""
    try:
        downloader.save_file(tvdb_v4.dump_json({"shows": SHOWS}), STATE_FILE)
    except Exception as e:
        Log.Debug("Health - Saving %s failed: %s" % (STATE_FILE, e))


def record(rating_key, title, report):
    """After an update: remember what this show was left without (report: metadata_writer.episode_report)."""
    if not rating_key:
        return
    load()
    unwritten = [label(x) for x in report.get("unwritten") or []]
    empty = [label(x) for x in report.get("empty_keys") or []]
    LOCK.acquire()
    try:
        old = SHOWS.get(str(rating_key))
        if not unwritten and not empty:
            if old is not None:
                del SHOWS[str(rating_key)]
                save()
            return
        SHOWS[str(rating_key)] = {"title": textutil.safe_unicode(title or ""), "unwritten": unwritten, "empty": empty, "updated": int(time.time())}
        save()
    finally:
        LOCK.release()


def library_shows():
    """{rating key: (title, matched)} for every show in libraries using AMSA, or None if Plex couldn't be asked."""
    import season_editor
    shows = {}
    try:
        sections = tvdb_v4.parse_json(season_editor.plex_request("/library/sections")).get("MediaContainer", {}).get("Directory") or []
        for section in sections:
            if section.get("type") != "show" or section.get("agent") != "com.plexapp.agents.amsa":
                continue
            items = tvdb_v4.parse_json(season_editor.plex_request("/library/sections/%s/all?type=2" % (section.get("key")))).get("MediaContainer", {}).get("Metadata") or []
            for item in items:
                guid = item.get("guid") or ""
                shows[str(item.get("ratingKey"))] = (u"%s (%s)" % (textutil.safe_unicode(item.get("title") or "?"), textutil.safe_unicode(section.get("title") or "?")),
                                                     guid.startswith("com.plexapp.agents.amsa://"))
    except Exception as e:
        Log.Debug("Health - Couldn't read the libraries from Plex (%s)" % (e))
        return None
    return shows


def section(lines, header, items):
    """Append a report section: header, up to MAX_LINES items, and a count of the rest."""
    lines.append(header)
    for item in items[:MAX_LINES]:
        lines.append(u"    " + item)
    if len(items) > MAX_LINES:
        lines.append(u"    ... and %s more" % (len(items) - MAX_LINES))


def build():
    """The report as a list of lines."""
    load()
    shows = library_shows()
    LOCK.acquire()
    try:
        if shows is not None:
            for key in [k for k in SHOWS]:
                if key not in shows:
                    del SHOWS[key]                          # No longer in Plex
            save()
        recorded = [(key, SHOWS[key]) for key in SHOWS]
    finally:
        LOCK.release()
    lines = []
    if shows is None:
        lines.append(u"Libraries: couldn't be read from Plex this time")
    else:
        unmatched = sorted([shows[k][0] for k in shows if not shows[k][1]])
        lines.append(u"Libraries using AMSA: %s shows, %s matched" % (len(shows), len(shows) - len(unmatched)))
        if unmatched:
            section(lines, u"Not matched (%s) - use Fix Match in Plex:" % (len(unmatched)), unmatched)
    gaps = sorted(recorded, key=lambda x: -(len(x[1].get("unwritten") or []) + len(x[1].get("empty") or [])))
    if gaps:
        items = []
        for key, show in gaps:
            parts = []
            if show.get("unwritten"):
                parts.append(u"%s not mapped (%s)" % (len(show["unwritten"]), ", ".join(show["unwritten"][:6]) + (", ..." if len(show["unwritten"]) > 6 else "")))
            if show.get("empty"):
                parts.append(u"%s without title or summary (%s)" % (len(show["empty"]), ", ".join(show["empty"][:6]) + (", ..." if len(show["empty"]) > 6 else "")))
            items.append(u"%s: %s" % (show.get("title") or key, "; ".join(parts)))
        section(lines, u"Episodes on disk without data (%s shows):" % (len(gaps)), items)
    else:
        lines.append(u"Episodes on disk without data: none")
    try:
        import anidb_retry
        import background_refresh
        lines.append(u"Waiting: %s AniDB downloads in the retry queue, %s shows in the background refresh queue"
                     % (anidb_retry.pending_count(), background_refresh.queue_length()))
    except Exception:
        pass
    return lines


def run():
    try:
        lines = build()
        Log.Info(u"Health - ==== AMSA %s library health report ====" % (settings.VERSION))
        for line in lines:
            Log.Info(u"Health - " + line)
        Log.Info(u"Health - ==== end of report (next in 24h) ====")
    except Exception:
        Log.Warn("Health - Report failed: %s" % (textutil.exception_text()))
    finally:
        schedule(RUN_EVERY)


def health_report():
    """Named for Plex's log ("Scheduled a timed thread named 'health_report'")."""
    run()


def schedule(delay):
    try:
        Thread.CreateTimer(delay, health_report)
    except Exception:
        import threading
        timer = threading.Timer(delay, health_report)
        timer.daemon = True
        timer.start()


def start():
    """Called from Start(): first report 5 minutes after the agent starts, then daily."""
    if STATE["started"]:
        return
    STATE["started"] = True
    schedule(FIRST_RUN)
