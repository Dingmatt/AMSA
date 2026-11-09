"""The bundle: an XML tree holding, per TVDB season/episode, which AniDB/TVDB episode it maps to, the files' stream languages,
and every source's values side by side (e.g. <Title><Anidb>..</Anidb><Tvdb>..</Tvdb></Title>).
It is saved to Cache/Bundles/<anidb id>.bundle.xml after each update, which makes it the best file to debug mappings with.
"""
import re
import copy

from lxml import etree
from lxml.etree import SubElement

import settings
import textutil
import models
import anidb
import tvdb
import anime_lists
import sources
import downloader
import tvdb_v4

# [mapping key, providers using it]: AniList entries are keyed by the AniDB id, Plex themes by the TVDB id
def provider_groups():
    """Read now, not at import, so a settings change (AniList, Plex theme music on/off) applies without a restart."""
    return [["Anidb", "Anilist"] if settings.ANILIST_ENABLED else ["Anidb"], ["Tvdb", "Plex"] if settings.PLEX_THEMES_USED else ["Tvdb"]]
OPENING_START = 101
ENDING_START = 151


def get_season(root, number):
    season = root.find('./Season[@num="%s"]' % (number))
    if season is None:
        season = SubElement(root, "Season", num=str(number))
        for field in settings.SERIES_FIELDS:
            SubElement(season, field)
    return season


def get_episode(season, number):
    episode = season.find('./Episode[@num="%s"]' % (number))
    if episode is None:
        episode = SubElement(season, "Episode", num=str(number))
        for field in settings.EPISODE_FIELDS:
            SubElement(episode, field)
    return episode


def add_mapping(series_map, mapped_anidb, used_tvdb, anidb_number, tvdb_number, status):
    """used_tvdb: TVDB number -> AniDB entry that claimed it first."""
    SubElement(series_map, "Episode", anidb="%s" % (anidb_number), tvdb=tvdb_number, status=status)
    mapped_anidb.add("%s" % (anidb_number))
    if tvdb_number not in used_tvdb:
        used_tvdb[tvdb_number] = series_map.get("anidbid")


def claimed_elsewhere(used_tvdb, tvdb_number, anidb_id, absolute=False):
    """True if another AniDB entry already maps to this TVDB episode. (Within one entry, Anime-Lists may map two AniDB
       episodes to one TVDB episode on purpose: a double-length episode.) absolute: the entry's own TVDB absolute mapping
       counts too, so a rule can't add a second AniDB episode to a TVDB episode map_absolute already filled."""
    return tvdb_number in used_tvdb and (absolute or used_tvdb[tvdb_number] != str(anidb_id))


def map_credits(credits, matched_anidb_id, used_tvdb):
    """Openings -> S00E101+, endings -> S00E151+. The matched AniDB entry is numbered first, so a folder for one season
       (e.g. [anidb-<season 2 id>]) finds its own OP1 at S00E101, as scanners number it; the other entries follow in order."""
    ordered = [x for x in credits if x[2] == matched_anidb_id] + [x for x in credits if x[2] != matched_anidb_id]
    numbers = {"op": OPENING_START, "ed": ENDING_START}
    placed = []
    for series_map, mapped_anidb, anidb_id, openings, endings in ordered:
        for kind, items in (("op", openings), ("ed", endings)):
            for item in items:
                add_mapping(series_map, mapped_anidb, used_tvdb, item, anidb.credit_tvdb_number(numbers[kind]), "")
                numbers[kind] = numbers[kind] + 1
        if openings or endings:
            placed.append("%s %s/%s" % (anidb_id, len(openings), len(endings)))
    if placed:
        Log.Debug("Bundle - Openings/endings placed from S00E%s / S00E%s (AniDB entry OP/ED): %s" % (OPENING_START, ENDING_START, ", ".join(placed)))


def disk_tvdb_seasons(media, mapping_data):
    """TVDB season numbers that have files on disk (Plex season 1 = the matched entry's TVDB season), or None if unknown."""
    if media is None:
        return None
    first = mapping_data.default_tvdb_season if (not mapping_data.absolute and mapping_data.default_tvdb_season >= 1) else 1
    seasons = set()
    try:
        for season in media.seasons:
            number = int(season)
            seasons.add(0 if number == 0 else number + first - 1)
    except Exception:
        return None
    return seasons


def entry_needed(entry, disk_seasons, matched_anidb_id):
    """Download this AniDB entry now? Yes for the matched entry, absolute entries and entries with a TVDB season on disk.
       The others are read from the cache only (and queued for a background download if they aren't cached)."""
    if disk_seasons is None or entry.absolute or str(entry.anidb_id) == str(matched_anidb_id):
        return True
    seasons = [entry.default_tvdb_season] + [int(rule.tvdb_season) for rule in entry.mapping_list if textutil.is_digits(rule.tvdb_season)]
    for season in seasons:
        if season in disk_seasons:
            return True
    return False


# Step 1: episode mapping ##############################################################################################################################################
def map_absolute(entry, record, mapped_anidb, used_tvdb, add):
    """An absolute-order entry (a long-running show numbered absolutely): AniDB episode N is the TVDB episode with absolute
       number N (+ offset). Done before the entry's own rules, which then only place what this leaves (specials, episodes
       TVDB hasn't numbered yet), so an episode is never mapped twice where out-of-date rules disagree with TVDB's numbers."""
    series = sources.get_tvdb(entry.tvdb_id) if entry.tvdb_id else None
    for episode in (series.episodes if series is not None else []):
        if episode.absolute_index and episode.season and episode.number:
            if entry.episode_offset < episode.absolute_index <= record.episode_count + entry.episode_offset:
                anidb_number = anidb.episode_number(1, episode.absolute_index - entry.episode_offset)
                tvdb_number = tvdb.episode_number(int(episode.season), int(episode.number))
                if anidb_number not in mapped_anidb and not claimed_elsewhere(used_tvdb, tvdb_number, entry.anidb_id):
                    add(anidb_number, tvdb_number, "")


def map_series(mapping_data, disk_seasons=None, offline=None):
    """<Series><Mapping> with one <Series> per AniDB entry and one <Episode anidb=".." tvdb="SxxEyy"> per episode.
       disk_seasons: TVDB seasons with files (None = all needed). Entries not needed now are read from the cache only and
       listed in offline as (AniDB id, cached?)."""
    root = etree.Element("Series")
    mapping = SubElement(root, "Mapping")
    used_tvdb = {}             # TVDB number -> AniDB entry that claimed it first
    credits = []               # (series map, mapped set, AniDB id, openings, endings) per entry, numbered after the loop
    summary = []               # "6327: 12 episodes, 6 specials" per entry, logged once after the loop
    entries = []               # (entry, record, series map, mapped set) in the mapping's order

    # Three passes over the entries, so what Anime-Lists states beats what is guessed, whichever entry comes first
    # (an entry's guesses never take a TVDB special that a later entry's own rule maps):
    #   1. every entry's explicit mapping rules (absolute-order entries: TVDB's absolute numbers first, see map_absolute);
    #   2. regular episodes by each entry's default season and offset;  3. specials by the "special N = S00EN (+ offset)"
    #   convention, where still free.
    for item in mapping_data.series_list or []:
        entry = anime_lists.AnimeListEntry()
        entry.load(item)
        network = entry_needed(entry, disk_seasons, mapping_data.anidb_id)
        record = sources.get_anidb(entry.anidb_id, True if network else False)
        if not network and offline is not None:
            offline.append((str(entry.anidb_id), record.valid))
        series_map = SubElement(mapping, "Series", anidbid=str(entry.anidb_id), tvdbid=str(entry.tvdb_id), episodeoffset=str(entry.episode_offset), absolute=str(entry.absolute))
        mapped_anidb = set()
        entries.append((entry, record, series_map, mapped_anidb))

        def add(anidb_number, tvdb_number, status, series_map=series_map, mapped_anidb=mapped_anidb):
            add_mapping(series_map, mapped_anidb, used_tvdb, anidb_number, tvdb_number, status)

        if entry.absolute:
            map_absolute(entry, record, mapped_anidb, used_tvdb, add)
        for rule in entry.mapping_list:
            if rule.offset and rule.start is not None and rule.end is not None:
                for number in range(rule.start, rule.end + 1):
                    if entry.absolute and anidb.episode_number(int(rule.anidb_season), number) in mapped_anidb:
                        continue                                # TVDB's absolute numbers already placed it (map_absolute)
                    status, tvdb_number = "scudlee missing", "S00E00"
                    key = tvdb.episode_number(int(rule.tvdb_season), number + int(rule.offset))
                    if not claimed_elsewhere(used_tvdb, key, entry.anidb_id, entry.absolute):
                        status, tvdb_number = "", key
                    add(anidb.episode_number(int(rule.anidb_season), number), tvdb_number, status)
            if rule.text is not None:
                for pair in filter(None, rule.text.split(";")):
                    halves = pair.split("-")
                    if len(halves) < 2 or not halves[0].strip():
                        Log.Debug("Bundle - Ignoring malformed mapping entry '%s' for AniDB '%s'" % (pair, entry.anidb_id))
                        continue
                    if entry.absolute and anidb.episode_number(int(rule.anidb_season), halves[0].strip()) in mapped_anidb:
                        continue                                # TVDB's absolute numbers already placed it (map_absolute)
                    for target in halves[1].split("+"):
                        if not target.strip().isdigit():
                            continue
                        status, tvdb_number = "scudlee missing", "S00E00"
                        key = tvdb.episode_number(int(rule.tvdb_season), int(target))
                        if key == "S00E00":
                            status = "tvdb missing"
                        elif not claimed_elsewhere(used_tvdb, key, entry.anidb_id, entry.absolute):
                            status, tvdb_number = "", key
                        add(anidb.episode_number(int(rule.anidb_season), halves[0].strip()), tvdb_number, status)

    for entry, record, series_map, mapped_anidb in entries:
        def add(anidb_number, tvdb_number, status, series_map=series_map, mapped_anidb=mapped_anidb):
            add_mapping(series_map, mapped_anidb, used_tvdb, anidb_number, tvdb_number, status)

        if not entry.absolute:
            season = str(entry.default_tvdb_season).zfill(2)
            for number in range(1, record.episode_count + 1):
                if str(number) not in mapped_anidb:
                    key = "S%sE%s" % (season, str(number + entry.episode_offset).zfill(2))
                    if claimed_elsewhere(used_tvdb, key, entry.anidb_id):
                        add(number, "S00E00", "scudlee missing")       # Another entry's rule (or earlier default) has it
                    else:
                        add(number, key, "")

    for entry, record, series_map, mapped_anidb in entries:
        def add(anidb_number, tvdb_number, status, series_map=series_map, mapped_anidb=mapped_anidb):
            add_mapping(series_map, mapped_anidb, used_tvdb, anidb_number, tvdb_number, status)

        if not entry.absolute:
            for number in range(1, record.special_count + 1):
                special = anidb.episode_number_by_type(2, number)
                if special not in mapped_anidb:
                    key = "S00E%s" % (str(number + entry.episode_offset).zfill(2))
                    if key not in used_tvdb:
                        add(special, key, "")
                    else:
                        add(special, "S00E00", "scudlee missing")
            credits.append((series_map, mapped_anidb, str(entry.anidb_id),
                            [x for x in record.op_list if x not in mapped_anidb], [x for x in record.ed_list if x not in mapped_anidb]))

        parts = ["%s ep" % (record.episode_count)]
        if record.special_count:
            parts.append("%s sp" % (record.special_count))
        if record.op_list or record.ed_list:
            parts.append("%s OP/%s ED" % (len(record.op_list), len(record.ed_list)))
        if entry.mapping_list:
            parts.append("%s rules" % (len(entry.mapping_list)))
        summary.append("%s (%s)" % (entry.anidb_id, ", ".join(parts) if record.valid else "no data"))

    if summary:
        Log.Debug("Bundle - %s AniDB %s mapped: %s" % (len(summary), "entry" if len(summary) == 1 else "entries", ", ".join(summary)))
    map_credits(credits, str(mapping_data.anidb_id), used_tvdb)
    for series_map in mapping.xpath("./Series"):
        series_map[:] = sorted(series_map, key=lambda x: (0 if re.sub("[^A-Z]", "", x.get("anidb")) else 1, int(re.sub("[^0-9]", "", x.get("anidb")) or 0)))

    unmapped = sorted(mapping.xpath('./Series/Episode[@tvdb="S00E00" and @status!=""]'), key=lambda x: x.getparent().get("anidbid"))
    if unmapped:
        container = SubElement(mapping, "Unmapped")
        for number, episode in enumerate(unmapped):
            SubElement(container, "Episode", anidbid=episode.getparent().get("anidbid"), anidb=episode.get("anidb"), missing=episode.get("status"), id=str(number + 1))
        per_entry = {}
        for x in unmapped:
            per_entry.setdefault(x.getparent().get("anidbid"), []).append(x.get("anidb"))
        parts = []
        for anidb_id in sorted(per_entry.keys(), key=lambda x: -len(per_entry[x])):
            numbers = per_entry[anidb_id]
            parts.append("%s: %s%s" % (anidb_id, ", ".join(numbers[:8]), (" (+%s more)" % (len(numbers) - 8)) if len(numbers) > 8 else ""))
        Log.Debug("Bundle - %s AniDB episodes have no TVDB equivalent (Anime-Lists has none for them): %s" % (len(unmapped), "; ".join(parts)))
    return root


# Step 2: local files ##################################################################################################################################################
LANGUAGE_CODES = {"en": "eng", "english": "eng", "ja": "jpn", "japanese": "jpn", "jp": "jpn"}


def stream_language(stream):
    """A stream's language as a 3-letter code ("eng", "jpn"); Plex may give "en", "eng" or "English"."""
    value = getattr(stream, "language", None) or getattr(stream, "languageCode", None) or ""
    value = ("%s" % (value,)).strip().lower()
    return LANGUAGE_CODES.get(value, value)


def stream_languages(plex_episode):
    """(audio languages, subtitle languages) of all the episode's files (every version and part, incl. external subtitles)."""
    audio = []
    subtitles = []
    for media_item in plex_episode.items:
        for part in media_item.parts:
            for stream in part.streams:
                kind = int(getattr(stream, "type", 0) or 0)
                language = stream_language(stream)
                if kind == 2 and language not in audio:
                    audio.append(language)
                elif kind == 3 and language not in subtitles:
                    subtitles.append(language)
    return audio, subtitles


def map_local(root, media):
    """Create Season/Episode nodes for every mapped TVDB episode (stream languages are added by metadata_writer.write,
       which handles Plex's media tree using string keys and seasons renumbered from the matched entry)."""
    for item in root.xpath("./Mapping/Series/Episode"):
        match = re.search(r".*\bS(?P<season>\d+)E(?P<episode>\d+)\b.*", item.get("tvdb"), re.IGNORECASE)
        if not match:
            continue
        season_number = int(match.group("season"))
        episode_number = int(match.group("episode"))
        if season_number == 0 and episode_number == 0:
            continue  # S00E00 = not mapped to TVDB
        episode = get_episode(get_season(root, season_number), episode_number)
        mapped = SubElement(episode, "Mapped")
        SubElement(mapped, "tvdb", series=item.getparent().get("tvdbid"), episode=item.get("tvdb"))
        SubElement(mapped, "anidb", series=item.getparent().get("anidbid"), episode=item.get("anidb"))
        SubElement(episode, "Streams")   # Filled by metadata_writer for the episodes on disk (it knows Plex's season numbers)


# Step 3: source values ################################################################################################################################################
def has_value(value):
    """True for non-empty values; an lxml element counts as empty when it has no children."""
    if etree.iselement(value):
        return len(value) > 0
    return bool(value)


def add_value(target, provider, value):
    element = SubElement(target, provider)
    if etree.iselement(value):
        element.extend(copy.deepcopy(value).getchildren())
    else:
        element.text = textutil.safe_unicode(value if isinstance(value, basestring) else u"%s" % (value,))
    return element


def mark_language(element, record):
    """Title language on a <Title> value, so the writer can prefer the title in the user's language across sources."""
    if element is not None and getattr(record, "title_lang", None):
        element.set("lang", record.title_lang)
    if element is not None and getattr(record, "title_main", False):
        element.set("main", "1")


def map_meta(root, offline_ids=None):
    """Copy every provider's series and episode values into the tree. Downloads run in parallel;
       the tree is only modified by this thread (lxml trees are not safe to modify concurrently)."""
    wanted = []
    for providers in provider_groups():
        key = providers[0].lower()
        ids = set([x.get("series") for x in root.xpath("./Season/Episode/Mapped/%s" % (key))])
        for series_id in sorted([i for i in ids if textutil.is_digits(i)]):
            if key == "anidb" and offline_ids and series_id in offline_ids:
                continue                                 # Not cached and not needed now (no files for its seasons)
            for provider in providers:
                wanted.append((provider, series_id))

    loaded = {}

    @parallelize
    def load_providers():
        for provider, series_id in wanted:
            @task
            def load_provider(provider=provider, series_id=series_id, loaded=loaded):
                try:
                    loaded[(provider, series_id)] = sources.get(provider, series_id)
                except Exception:
                    Log.Error("Bundle - Loading %s '%s' failed: %s" % (provider, series_id, textutil.exception_text()))

    for providers in provider_groups():
        key = providers[0].lower()
        for provider in providers:
            episode_index = {}
            for mapped in sorted(root.xpath("./Season/Episode/Mapped/%s" % (key)), key=lambda x: int(x.get("series")) if textutil.is_digits(x.get("series")) else 0):
                series_id = mapped.get("series")
                record = loaded.get((provider, series_id))
                if record is None or not record.valid:
                    continue
                episode_node = mapped.getparent().getparent()
                season_node = episode_node.getparent()
                if not season_node.get(provider + "Id"):
                    season_node.attrib[provider + "Id"] = series_id

                for field in settings.SERIES_FIELDS:
                    value = getattr(record, models.field_attr(field), None)
                    if has_value(value):
                        if not season_node.xpath("./%s/%s" % (field, provider)):
                            target = season_node.find("./%s" % (field))
                            if target is not None:
                                element = add_value(target, provider, value)
                                if field == "Title":
                                    mark_language(element, record)
                                elif field == "Rating" and getattr(record, "rating_votes", None):
                                    element.set("votes", str(record.rating_votes))
                                elif field == "Content_Rating":
                                    if getattr(record, "content_rating_adult", False):
                                        element.set("adult", "1")
                                    elif getattr(record, "content_rating_estimate", False):
                                        element.set("estimate", "1")

                if series_id not in episode_index:      # One lookup table per series instead of scanning every episode per mapping
                    index = {}
                    for episode in record.episodes or []:
                        episode_key = ("%s" % (episode.number)) if key == "anidb" else ("S%sE%s" % (episode.season, episode.number))
                        index.setdefault(episode_key, episode)
                    episode_index[series_id] = index
                episode = episode_index[series_id].get(mapped.get("episode"))
                if episode is None:
                    continue
                for field in settings.EPISODE_FIELDS:
                    value = getattr(episode, models.field_attr(field), None)
                    if has_value(value):
                        target = episode_node.find("./%s" % (field))
                        if target is not None:
                            if etree.iselement(value):
                                SubElement(target, provider).extend(copy.deepcopy(value))
                            else:
                                element = add_value(target, provider, value)
                                if field == "Title":
                                    mark_language(element, episode)


def apply_episode_values(root, provider, series_id, record, nodes=None):
    """Add one AniDB-keyed provider's episode values (MAL, Kitsu, AnimeThemes: see episode_fill.py) to the bundle episodes
       mapped to AniDB entry series_id (only those in nodes, if given). Returns the number of values added."""
    if record is None or not record.valid:
        return 0
    index = {}
    for episode in record.episodes or []:
        index.setdefault("%s" % (episode.number), episode)
    allowed = None
    if nodes is not None:
        allowed = set([id(node) for node in nodes])
    added = 0
    for mapped in root.xpath('./Season/Episode/Mapped/anidb[@series="%s"]' % (series_id)):
        episode = index.get(mapped.get("episode"))
        node = mapped.getparent().getparent()
        if episode is None or (allowed is not None and id(node) not in allowed):
            continue
        for field in settings.EPISODE_FIELDS:
            found = getattr(episode, models.field_attr(field), None)
            target = node.find("./%s" % (field))
            if has_value(found) and target is not None and not target.xpath("./%s" % (provider)):
                element = add_value(target, provider, found)
                if field == "Title":
                    mark_language(element, episode)
                added = added + 1
    return added


# Step 4: TVDB v4 episode crew (episodes on disk only) ##################################################################################################################
def wants_tvdb_crew():
    return "tvdb" in settings.EPISODE_PRIORITY["Writers"] or "tvdb" in settings.EPISODE_PRIORITY["Directors"]


def map_crew(episode_nodes, lazy=None):
    """Add TVDB v4 writers/directors to the given bundle episodes (the ones about to be written, i.e. on disk).
       v4 has these only per episode, so each costs one request the first time; answers are cached on disk.
       lazy (metadata_writer.write): use only cached answers now, and leave the missing or outdated ones to the background
       ("crew|series|episode" in lazy["crew"]); the refresh after their download writes them."""
    if not wants_tvdb_crew():
        return
    jobs = []
    indexes = {}
    for node in episode_nodes:
        if node.xpath("./Writers/Tvdb") or node.xpath("./Directors/Tvdb"):
            continue                                     # Already provided (TVDB v1)
        for mapped in node.xpath("./Mapped/tvdb"):
            series_id = mapped.get("series")
            if not textutil.is_digits(series_id):
                continue
            if series_id not in indexes:
                record = sources.get_tvdb(series_id)
                index = {}
                if record.valid and record.api == "v4":
                    for episode in record.episodes:
                        index["S%sE%s" % (episode.season, episode.number)] = episode.source_id
                indexes[series_id] = index
            episode_id = indexes[series_id].get(mapped.get("episode"))
            if episode_id:
                jobs.append((node, series_id, episode_id))
            break
    if not jobs:
        return
    # Cached answers are used for every episode; only downloads count against TVDB4_CREW_LIMIT, so a long show gets the
    # rest of its episodes over the following refreshes
    results = {}
    missing = []
    for node, series_id, episode_id in jobs:
        crew, fresh = tvdb_v4.cached_crew(series_id, episode_id)
        if crew is not None:
            results[episode_id] = crew
        if not fresh:
            missing.append((node, series_id, episode_id))
    if len(missing) > settings.TVDB4_CREW_LIMIT:
        Log.Info("Bundle - %s episodes need TVDB writers/directors downloaded; %s now, the rest on the next refresh" % (len(missing), settings.TVDB4_CREW_LIMIT))
        missing = missing[:settings.TVDB4_CREW_LIMIT]
    if lazy is not None:
        for node, series_id, episode_id in missing:
            lazy["crew"].append("crew|%s|%s" % (series_id, episode_id))
        jobs_now = []
    else:
        jobs_now = missing

    if jobs_now:
        @parallelize
        def load_crew():
            for node, series_id, episode_id in jobs_now:
                @task
                def load_one(series_id=series_id, episode_id=episode_id, results=results):
                    try:
                        crew = tvdb_v4.episode_crew(series_id, episode_id)
                        if crew is not None:
                            results[episode_id] = crew            # Else keep the outdated copy, if any
                    except Exception:
                        Log.Debug("Bundle - Crew for TVDB episode %s failed: %s" % (episode_id, textutil.exception_text()))

    found = 0
    for node, series_id, episode_id in jobs:
        crew = results.get(episode_id)
        if not crew:
            continue
        for field, key in (("Writers", "writers"), ("Directors", "directors")):
            names = crew.get(key) or []
            target = node.find("./%s" % (field))
            if names and target is not None:
                add_value(target, "Tvdb", names)
                found = found + 1
    Log.Debug("Bundle - TVDB v4 crew: %s episodes checked, %s writer/director lists added" % (len(jobs), found))


def export(root, filename):
    """Copy of the bundle without local file details, for sharing (settings.EXPORT_BUNDLES)."""
    data = copy.deepcopy(root)
    for item in data.xpath("./Season/Episode/Filename") + data.xpath("./Season/Episode/Streams"):
        item.getparent().remove(item)
    downloader.save_file(etree.tostring(data, pretty_print=True, xml_declaration=True, encoding="UTF-8"), filename, "Bundles", True)
