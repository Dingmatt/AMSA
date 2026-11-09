"""Reference lists: the AniDB titles dump and the Anime-Lists (ScudLee) AniDB<->TVDB mapping.

Lists are held in memory and re-read after settings.REFERENCE_RELOAD (from the disk cache, or the network once the
cached copy is older than settings.DEFAULT_CACHE), so a long-running Plex picks up new mappings without a restart.
"""
import os
import copy
import time

from lxml import etree

import settings
import downloader
import cache_cleaner

try:
    import threading
    new_lock = threading.Lock
except ImportError:
    new_lock = lambda: Thread.Lock()

LOCK = new_lock()
TREES = {}                   # name -> (loaded_at, tree)
MAPPING_INDEX = {}           # "anidb" / "tvdb" -> {id: [entries in document order]}, rebuilt with the mapping tree


def load_tree(name, loader):
    """Cached in-memory tree, reloaded after REFERENCE_RELOAD."""
    LOCK.acquire()
    try:
        entry = TREES.get(name)
        if entry and entry[1] is not None and entry[0] > time.time() - settings.REFERENCE_RELOAD:
            return entry[1]
        started = time.time()
        tree = loader()
        TREES[name] = (time.time(), tree)
        if tree is not None:
            Log.Debug("AnimeLists - Loaded %s in %.1fs" % (name, time.time() - started))
            if name == "mapping":
                build_mapping_index(tree)
        return tree
    finally:
        LOCK.release()


def refresh():
    """Called at the start of every search/update: make sure the lists are loaded; every 3 days the cache clean-up (cache_cleaner.py) runs in the background."""
    titles_tree()
    mapping_tree()
    collection_tree()
    if cache_cleaner.due():
        cache_cleaner.start_later(60)


# The lists ############################################################################################################################################################
def titles_tree():
    return load_tree("titles", lambda: downloader.xml_from_url(settings.ANIDB_TITLES_URL, "anime-titles", "", settings.DEFAULT_CACHE, 60))


def collection_tree():
    return load_tree("collection", lambda: downloader.xml_from_url(settings.COLLECTION_URL, os.path.basename(settings.COLLECTION_URL), "", settings.DEFAULT_CACHE, 60))


def mapping_tree():
    return load_tree("mapping", load_mapping)


def load_mapping():
    """anime-list-master.xml with entries from the optional local anime-list-custom.xml placed first, so they take precedence."""
    master = downloader.xml_from_url(settings.MAPPING_URL, os.path.basename(settings.MAPPING_URL), "", settings.DEFAULT_CACHE, 60)
    if master is None:
        return None
    overrides = []
    custom = load_custom_mapping()
    if custom is not None:
        overrides.extend(custom.xpath("./anime"))
    if settings.APPLY_CORRECTIONS:
        corrections = downloader.xml_from_url(settings.MAPPING_CORRECTIONS_URL, os.path.basename(settings.MAPPING_CORRECTIONS_URL), "", settings.DEFAULT_CACHE, 60)
        if corrections is not None:
            overrides.extend(corrections.xpath("./anime"))
    for index, entry in enumerate(overrides):
        master.insert(index, copy.deepcopy(entry))
    if overrides:
        Log.Info("AnimeLists - Using %s entries from anime-list-custom.xml; they replace the official entries for AniDB %s"
                 % (len(overrides), ", ".join([x.get("anidbid") or "?" for x in overrides][:20]) + (", ..." if len(overrides) > 20 else "")))
    return master


def load_custom_mapping():
    """Optional user file: DataItems/Cache/anime-list-custom.xml (same format as anime-list-master.xml)."""
    try:
        if Data.Exists(settings.MAPPING_CUSTOM_FILE):
            return etree.fromstring(Data.Load(settings.MAPPING_CUSTOM_FILE))
    except Exception as e:
        Log.Error("AnimeLists - '%s' is invalid and was ignored: %s" % (settings.MAPPING_CUSTOM_FILE, e))
    return None


def build_mapping_index(tree):
    by_anidb = {}
    by_tvdb = {}
    for entry in tree.xpath("./anime"):
        by_anidb.setdefault(entry.get("anidbid"), []).append(entry)
        by_tvdb.setdefault(entry.get("tvdbid"), []).append(entry)
    MAPPING_INDEX["anidb"] = by_anidb
    MAPPING_INDEX["tvdb"] = by_tvdb


def mapping_entries(key, value):
    """All mapping entries with anidbid/tvdbid == value, in file order (custom entries first)."""
    if mapping_tree() is None:
        return []
    return list(MAPPING_INDEX.get(key, {}).get(str(value), []))


def titles_for_anime(anidb_id):
    """All <title> elements of one anime from the titles dump."""
    tree = titles_tree()
    if tree is None:
        return []
    return tree.xpath('/animetitles/anime[@aid="%s"]/*' % anidb_id)


# Mapping entries ######################################################################################################################################################
def is_valid_id(value):
    return value is not None and (u"%s" % (value)).isnumeric()


class MappingRule():
    """One <mapping> element: either an episode range with an offset, or explicit ';anidb-tvdb;' pairs."""
    def __init__(self, data):
        self.text = data.text if data.text else None
        self.offset = data.get("offset").zfill(2) if data.get("offset") else None
        self.start = None
        self.end = None
        try:
            if data.get("start"):
                self.start = int(data.get("start"))
            if data.get("end"):
                self.end = int(data.get("end"))
        except ValueError:
            pass
        self.anidb_season = (data.get("anidbseason") or "1").zfill(2)
        self.tvdb_season = (data.get("tvdbseason") or "1").zfill(2)


class AnimeListEntry():
    """Mapping for one AniDB entry, plus (when looked up by id) every AniDB entry that shares its TVDB series."""
    def __init__(self, anidb_id=None, tvdb_id=None):
        self.anidb_id = None
        self.tvdb_id = None
        self.episode_offset = 0
        self.absolute = False
        self.default_tvdb_season = 1
        self.mapping_list = []
        self.series_list = []
        self.first_series = None
        self.found = False

        if anidb_id is None and tvdb_id is None:
            return

        data = mapping_entries("anidb", anidb_id) if anidb_id is not None else mapping_entries("tvdb", tvdb_id)
        if data:
            self.found = True
            self.load(data[0])
            if self.tvdb_id:
                self.series_list = mapping_entries("tvdb", self.tvdb_id)
            else:
                self.series_list = mapping_entries("anidb", self.anidb_id)
        elif anidb_id is not None and is_valid_id(anidb_id):
            # Not in the mapping list yet (common for new shows): continue AniDB-only, numbering episodes as S01Exx / specials as S00Exx
            Log.Warn("AnimeLists - AniDB '%s' not found in mapping list, using AniDB data only" % (anidb_id))
            entry = etree.Element("anime", anidbid=str(anidb_id), tvdbid="", defaulttvdbseason="1", episodeoffset="")
            self.load(entry)
            self.series_list = [entry]
        else:
            Log.Error("AnimeLists - No mapping found for anidb: '%s', tvdb: '%s'" % (anidb_id, tvdb_id))
            return

        # Remove duplicate AniDB entries (custom entries override the master entry that follows them)
        visited = set()
        unique = []
        for series in self.series_list:
            current = series.get("anidbid")
            if current not in visited and is_valid_id(current):
                visited.add(current)
                unique.append(series)
        self.series_list = sorted(unique, key=lambda x: int(x.get("anidbid")))

        for series in self.series_list:
            if series.get("defaulttvdbseason") == "1" or (series.get("defaulttvdbseason") == "a" and series.get("episodeoffset") in (None, "", "0")):
                self.first_series = series.get("anidbid")
        if not self.first_series:
            self.first_series = self.anidb_id or anidb_id or (self.series_list[0].get("anidbid") if self.series_list else None)
        if anidb_id is None and self.first_series and self.first_series != self.anidb_id:
            # Looked up by TVDB id: describe the entry that starts the show (TVDB season 1), not whichever entry came first in the file
            for series in self.series_list:
                if series.get("anidbid") == self.first_series:
                    self.load(series)

    def load(self, data):
        if data.get("anidbid"):
            self.anidb_id = data.get("anidbid") if is_valid_id(data.get("anidbid")) else None
        if data.get("tvdbid"):
            self.tvdb_id = data.get("tvdbid") if is_valid_id(data.get("tvdbid")) else None   # "movie", "hentai", "unknown" -> None
        try:
            self.episode_offset = int(data.get("episodeoffset") or 0)
        except ValueError:
            self.episode_offset = 0
        if data.get("defaulttvdbseason") == "a":
            self.absolute = True
        elif data.get("defaulttvdbseason"):
            try:
                self.default_tvdb_season = int(data.get("defaulttvdbseason"))
            except ValueError:
                pass
        # Anime-Lists also has TMDB rules now (tmdbseason, no tvdbseason). They were read as TVDB season 1 rules (the old
        # default), which put AniDB episodes on the wrong TVDB episodes or blocked the real TVDB rules. Only TVDB rules count.
        self.mapping_list = [MappingRule(item) for item in data.xpath("./mapping-list/mapping")
                             if item.get("tvdbseason") is not None or item.get("tmdbseason") is None]
