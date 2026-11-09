"""Update: build the bundle for a matched show and write it to Plex."""
import time

from lxml import etree

import settings
import textutil
import anime_lists
import bundle
import downloader
import metadata_writer
import sources
import anidb_limiter
import anidb_retry
import refresher
import episode_fill
import airing
import forced_refresh
import background_refresh
import tvdb_v4
import health_report
import offline_db
import title_index

ANIDB_SOURCES = ("anidb", "anidb2")
TVDB_SOURCES = ("tvdb", "tvdb2", "tvdb3", "tvdb4", "tvdb5")


def update(metadata, media, force, lang=None):
    started = time.time()
    # No HTTP.ClearCache() here: AMSA downloads into its own cache and asks Plex with cacheTime=0, so Plex's HTTP cache
    # holds nothing of AMSA's, and clearing it during parallel updates (a library refresh) fails while others write to it.
    # A manual search for "clear-cache" still clears it (matcher.py).
    anime_lists.refresh()
    try:
        source, source_id = metadata.id.split("-", 1)
    except ValueError:
        Log.Info("==== Update: %s%s ====" % (header_name(metadata, media), metadata.id))
        Log.Error("Update - Unexpected metadata id '%s'" % (metadata.id))
        return

    mapping = None
    try:
        if source in ANIDB_SOURCES:
            mapping = anime_lists.AnimeListEntry(source_id)
        elif source in TVDB_SOURCES:
            mapping = anime_lists.AnimeListEntry(None, source_id)
    finally:
        Log.Info("==== Update: %s(%s)%s ====" % (header_name(metadata, media), ", ".join(header_ids(metadata.id, mapping)), " (Refresh Metadata)" if force else ""))
    if mapping is None or not mapping.series_list:
        Log.Error("Update - No mapping available for '%s', update skipped" % (metadata.id))
        return
    Log.Debug("Update - AniDB: '%s', TVDB: '%s', related AniDB entries: %s" % (mapping.anidb_id, mapping.tvdb_id, ", ".join([x.get("anidbid") for x in mapping.series_list])))

    rating_key = getattr(media, "id", None)
    own = bool(rating_key) and anidb_retry.own_refresh(rating_key)     # Used up here whether Plex sends it forced or not
    forced = forced_refresh.start(mapping, rating_key, own) if force else None
    # Background mode: an expired TVDB copy (over 2 days) is used as it is and downloaded after the update
    stale_ids = forced_refresh.tvdb_ids(mapping) if (settings.REFRESH_IN_BACKGROUND and rating_key) else []
    tvdb_v4.allow_stale(stale_ids)
    try:
        timings = {}
        disk_seasons = bundle.disk_tvdb_seasons(media, mapping)
        try:
            prefetch_anilist(mapping, disk_seasons)
        except Exception as e:
            Log.Debug("Update - AniList prefetch not started: %s" % (e))     # Only a speed-up: the update loads AniList itself
        root, offline = build(mapping, media, disk_seasons, timings)
        phase = time.time()
        report = metadata_writer.episode_report(root, mapping.anidb_id, mapping.tvdb_id, media)
        rebuild = False
        skipped = [x[0] for x in offline if not x[1]]
        if report["unwritten"] and skipped:
            # Files the seasons-on-disk rule didn't cover (e.g. absolute numbering in one folder): use every entry after all
            Log.Info("Update - %s episodes on disk not mapped; downloading the %s related AniDB entries skipped so far" % (len(report["unwritten"]), len(skipped)))
            disk_seasons = None
            rebuild = True
        if forced is None and refresher.refetch(report, mapping, rating_key, metadata.title):
            rebuild = True
        phase = metadata_writer.add_time(timings, "re-download", phase)
        if rebuild:
            root, offline = build(mapping, media, disk_seasons, timings)
        phase = time.time()
        try:
            episode_fill.fill(root, mapping.anidb_id, mapping.tvdb_id, media)
        except Exception:
            Log.Warn("Update - Filling episode gaps failed: %s" % (textutil.exception_text()))
        metadata_writer.add_time(timings, "fill", phase)
        if offline:
            Log.Debug("Update - Related AniDB entries without files, read from the cache: %s" % (", ".join(["%s (%s)" % (x[0], "cached" if x[1] else "not cached") for x in offline])))
        try:
            downloader.save_file(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8"), mapping.first_series + ".bundle.xml", "Bundles")
            if settings.EXPORT_BUNDLES:
                bundle.export(root, mapping.first_series + ".bundle.xml")
        except Exception as e:
            Log.Warn("Update - Saving bundle failed: %s" % (e))
        # Background mode: episode thumbnails and writers/directors that aren't cached yet are downloaded after the update
        # (background_refresh "Files"), not during it, which made e.g. Magi's update take 16s instead of about 3
        lazy = {"crew": [], "images": []} if (settings.REFRESH_IN_BACKGROUND and rating_key) else None
        metadata_writer.write(root, metadata, mapping.anidb_id, mapping.tvdb_id, media, lang, timings, lazy)
        if lazy is not None:
            background_refresh.add_files(rating_key, metadata.title, lazy)
        expired = tvdb_v4.end_stale(stale_ids)
        if expired:
            background_refresh.add(rating_key, metadata.title, [], expired, [], "TVDB copy older than 2 days, used as it was")
        if forced is not None and forced == forced_refresh.BACKGROUND:
            forced = None
            forced_refresh.queue_background(mapping, rating_key, metadata.title)
        elif forced is not None:
            forced.finish(rating_key)         # After writing: season texts (TVDB v4) are read while writing
            forced = None
        try:
            health_report.record(rating_key, metadata.title, metadata_writer.episode_report(root, mapping.anidb_id, mapping.tvdb_id, media))
        except Exception as e:
            Log.Debug("Update - Health record failed: %s" % (e))
        queue_postponed(mapping, media)
        queue_prefetch(offline)
        if settings.REFRESH_AIRING:
            airing.record(rating_key, metadata.id, metadata.title, mapping)
    except Exception:
        Log.Error("Update - Update failed for '%s': %s" % (metadata.id, textutil.exception_text()))
        tvdb_v4.end_stale(stale_ids)
        if forced is not None and forced != forced_refresh.BACKGROUND:
            forced.finish(rating_key)
        if force:
            forced_refresh.done(mapping, rating_key)
        return
    if force:
        forced_refresh.done(mapping, rating_key)
    Log.Info("==== Update finished: '%s' (%s) in %.1fs: %s ====" % (metadata.title, metadata.id, time.time() - started, timing_text(timings, time.time() - started)))


def header_name(metadata, media):
    """"'Name' " for the update's first log line: the title Plex shows, else the name Plex read from the files; "" if neither."""
    for item in (metadata, media):
        try:
            title = getattr(item, "title", None)
        except Exception:
            title = None
        if title:
            return "'%s' " % (textutil.safe_unicode(title))
    return ""


def header_ids(metadata_id, mapping):
    """["AniDB 16172", "TVDB 400133", "AniList 131681"] for the update's first log line, always in that order whichever
       id Plex matched the show by; ids that aren't known are left out."""
    anidb_id = getattr(mapping, "anidb_id", None) if mapping is not None else None
    tvdb_id = getattr(mapping, "tvdb_id", None) if mapping is not None else None
    source, found = (metadata_id.split("-", 1) + [""])[:2] if metadata_id else ("", "")
    if not anidb_id and source in ANIDB_SOURCES:
        anidb_id = found
    if not tvdb_id and source in TVDB_SOURCES:
        tvdb_id = found
    ids = []
    if anidb_id and textutil.is_digits(anidb_id):
        ids.append("AniDB %s" % (anidb_id))
    if tvdb_id and textutil.is_digits(tvdb_id):
        ids.append("TVDB %s" % (tvdb_id))
    try:
        anilist_id = offline_db.anilist_id(anidb_id) if anidb_id else None
    except Exception:
        anilist_id = None
    if anilist_id:
        ids.append("AniList %s" % (anilist_id))
    return ids or [metadata_id]


def prefetch_anilist(mapping, disk_seasons):
    """Start AniList for the entries this update needs while AniDB is still being mapped (AniDB goes one request at a time,
       4s apart; AniList has its own 2s pace). Only entries whose AniList id the anime dataset knows: they don't need
       AniDB's data first. The update later finds them already loaded (sources.py waits for a load in progress)."""
    if not settings.ANILIST_ENABLED:
        return
    wanted = []
    for item in mapping.series_list or []:
        try:
            entry = anime_lists.AnimeListEntry()
            entry.load(item)
            if entry.anidb_id and offline_db.anilist_id(entry.anidb_id) and bundle.entry_needed(entry, disk_seasons, mapping.anidb_id):
                wanted.append(str(entry.anidb_id))
        except Exception:
            continue
    if len(wanted) < 2:
        return                                    # Nothing to gain for one entry

    def anilist_prefetch():
        for anidb_id in wanted:
            try:
                sources.get("Anilist", anidb_id)
            except Exception:
                pass
    Log.Debug("Update - AniList for %s entries started alongside AniDB" % (len(wanted)))
    title_index.run_later(0.1, anilist_prefetch)


TIMING_ORDER = ["mapping/AniDB", "sources", "re-download", "fill", "images", "crew", "seasons", "episodes"]


def timing_text(timings, total):
    """'mapping/AniDB 4.1s, sources 9.8s, ..., other 0.2s' (phases under 0.05s left out)."""
    parts = []
    counted = 0
    for name in TIMING_ORDER:
        seconds = timings.get(name, 0)
        counted = counted + seconds
        if seconds >= 0.05:
            parts.append("%s %.1fs" % (name, seconds))
    if total - counted >= 0.05:
        parts.append("other %.1fs" % (total - counted))
    return ", ".join(parts) or "nothing to do"


def build(mapping, media, disk_seasons, timings=None):
    """The bundle: mapping (entries without files on disk from the cache only), local files, source values.
       Returns (root, [(AniDB id, cached?) read from the cache only]).
       timings: "mapping/AniDB" = AniDB entries (incl. limiter waits), "sources" = TVDB, AniList, Plex themes and the rest."""
    offline = []
    started = time.time()
    root = bundle.map_series(mapping, disk_seasons, offline)
    bundle.map_local(root, media)
    started = metadata_writer.add_time(timings, "mapping/AniDB", started)
    bundle.map_meta(root, set([x[0] for x in offline if not x[1]]))
    metadata_writer.add_time(timings, "sources", started)
    return root, offline


def queue_prefetch(offline):
    """Related AniDB entries that have no files yet and aren't cached: download them in the background (through the limiter),
       so their data is ready when the files arrive. No Plex refresh is needed for these."""
    for anidb_id, cached in offline:
        if not cached and not sources.get_anidb(anidb_id, False).valid:
            anidb_retry.add(anidb_id, None)


def queue_postponed(mapping, media):
    """AniDB anime this update needed but the limiter refused to download: fetch them later and refresh the show then."""
    for item in mapping.series_list:
        anidb_id = item.get("anidbid")
        if not textutil.is_digits(anidb_id):
            continue
        if anidb_limiter.was_deferred(settings.ANIDB_API_URL + anidb_id) and not sources.get_anidb(anidb_id, False).valid:
            anidb_retry.add(anidb_id, getattr(media, "id", None))
