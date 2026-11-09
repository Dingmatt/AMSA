"""In-memory index of cleaned AniDB titles for search.

Previously every search ran clean-title (regex + transliteration) over every title in the AniDB dump inside XPath, twice,
which took 6-18s per search. The cleaned titles are now computed once per titles-dump load and searched in memory.
Matching rules are unchanged: a title matches if its cleaned form contains the cleaned search text; if nothing does,
a difflib ratio >= 0.6 is used instead.
"""
import time
import difflib

import settings
import textutil
import anime_lists
import offline_db

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

LOCK = new_lock()
WARM_UP_DELAY = 1                         # Seconds after agent start before the background warm-up begins
INDEX = {"tree": None, "entries": [], "offline": None}   # entries: [(cleaned title, <title> element or Synonym)] in document order


class Synonym():
    """A title from anime-offline-database, shaped like an AniDB <title> element for matcher.TitleMatch (.text, .getparent())."""
    def __init__(self, text, anime):
        self.text = text
        self.anime = anime

    def getparent(self):
        return self.anime

    def get(self, key, default=None):
        return "syn" if key == "type" else default


def entries():
    tree = anime_lists.titles_tree()
    if tree is None:
        return []
    LOCK.acquire()
    try:
        if INDEX["tree"] is not tree or INDEX["offline"] != offline_db.version():
            started = time.time()
            built = []
            known = {}                                   # AniDB id -> cleaned titles already indexed
            anime_by_id = {}
            for title in tree.xpath("./anime/title"):
                if title.get("type") in settings.SEARCH_TITLE_TYPES and title.text:
                    cleaned = textutil.clean_title(title.text).lower()
                    built.append((cleaned, title))
                    anime = title.getparent()
                    known.setdefault(anime.get("aid"), set()).add(cleaned)
                    anime_by_id[anime.get("aid")] = anime
            extra = 0
            try:
                offline_titles = offline_db.titles()
                for anidb_id in offline_titles:
                    anime = anime_by_id.get(anidb_id)
                    if anime is None:
                        continue                         # Not in the AniDB titles dump: AMSA couldn't update it anyway
                    seen = known.get(anidb_id) or set()
                    for text in offline_titles[anidb_id]:
                        cleaned = textutil.clean_title(text).lower()
                        if cleaned and cleaned not in seen:
                            seen.add(cleaned)
                            built.append((cleaned, Synonym(text, anime)))
                            extra = extra + 1
            except Exception:
                Log.Warn("TitleIndex - anime-offline-database titles skipped: %s" % (textutil.exception_text()))
            INDEX["entries"] = built
            INDEX["tree"] = tree
            INDEX["offline"] = offline_db.version()
            Log.Info("TitleIndex - Indexed %s titles (%s from anime-offline-database) in %.1fs" % (len(built), extra, time.time() - started))
        return INDEX["entries"]
    finally:
        LOCK.release()


def find(name, fuzzy=True):
    """<title> elements whose cleaned form contains the cleaned search text, in titles-dump order.
       If none do and fuzzy is True, titles with a difflib ratio >= 0.6 instead (slower: compares every title)."""
    if not name:
        return []
    name = name.lower().replace('"', '')
    indexed = entries()
    result = [title for cleaned, title in indexed if name in cleaned]
    if not result and fuzzy:
        # difflib quick-ratio test; it analyses the search text once instead of once per title
        matcher = difflib.SequenceMatcher()
        matcher.set_seq2(name)
        for cleaned, title in indexed:
            matcher.set_seq1(cleaned)
            if matcher.real_quick_ratio() >= 0.6 and matcher.quick_ratio() >= 0.6 and matcher.ratio() >= 0.6:
                result.append(title)
    return result


# Background warm-up #####################################################################################################################################################
def run_later(delay, function):
    """Run function in a background thread after delay seconds (Plex's timer API, else a plain thread)."""
    try:
        Thread.CreateTimer(delay, function)
    except Exception:
        timer = threading.Timer(delay, function)
        timer.daemon = True
        timer.start()


def warm_up():
    """Load the reference lists and build the title index in the background, so the first search after a start
       (or after the daily reload) doesn't pay for it. A search arriving meanwhile waits for this instead of duplicating it."""
    started = time.time()
    try:
        anime_lists.refresh()
        offline_db.refresh()                 # Weekly dataset download (background only; searches never download it)
        count = len(entries())
        Log.Info("Warm-up - Reference lists and title index (%s titles) ready in %.1fs" % (count, time.time() - started))
    except Exception:
        Log.Error("Warm-up - Failed (searches will load on demand): %s" % (textutil.exception_text()))
    run_later(settings.REFERENCE_RELOAD + 60, warm_up)     # Re-warm just after the lists expire, ahead of the next search


def start_warm_up():
    try:
        run_later(WARM_UP_DELAY, warm_up)
    except Exception as e:
        Log.Warn("Warm-up - Could not start background thread (lists will load on the first search): %s" % (e))
