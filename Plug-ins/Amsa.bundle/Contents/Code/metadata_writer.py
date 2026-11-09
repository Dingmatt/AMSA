"""Write the bundle to Plex: for each field pick the value from the highest-priority source that has one (user preferences)."""
import os
import re
import ast
import datetime
import time
import copy

from lxml import etree
from lxml.etree import SubElement

import settings
import textutil
import downloader
import bundle
import sources
import tvdb_v4
import season_editor


def set_object_type():
    return Framework.modelling.attributes.SetObject                   # Plex people lists (roles, writers, ...)


def proxy_container_type():
    return Framework.modelling.attributes.ProxyContainerObject        # Plex image/theme containers


# Choosing a value #####################################################################################################################################################
def provider_rank(priority, provider):
    """Position of a provider in the user's priority list; providers not listed sort last."""
    provider = (provider or "").lower()
    return priority.index(provider) if provider in priority else len(priority)


def is_bad_episode_title(title):
    for pattern in settings.ANIDB_BAD_TITLES:
        if re.search(pattern, title, re.IGNORECASE):
            return True
    return False


def language_rank(image, language):
    """With 'Prefer artwork based on section language': the library's language first, then images without text, then others."""
    if not settings.PREFER_LOCAL_ART or not language:
        return 0
    image_language = image.get("lang") or ""
    if image_language == language:
        return 0
    return 2 if image_language else 1


def by_priority(candidates, priority, kind, episode_title=False, language=None):
    """The winning value among a field's provider elements (<Anidb>, <Tvdb>, <Plex>) in the bundle.
       Only providers in the field's priority list are used, so "AniDB only" and "Off" really exclude the others."""
    try:
        if kind is proxy_container_type():
            candidates = [i for i in candidates if i.getparent().tag.lower() in priority]
        else:
            candidates = [i for i in candidates if i.tag.lower() in priority]
        if kind is list:
            values = sorted([i for i in candidates if i.text and i.text != "None"], key=lambda x: provider_rank(priority, x.tag))
            return ast.literal_eval(values[0].text) if values else None
        if kind is set_object_type():
            values = sorted([i for i in candidates if len(i) > 0], key=lambda x: provider_rank(priority, x.tag))
            if values:
                return values[0]                                  # Element with children, e.g. <Anidb><Role .../></Anidb>
            values = sorted([i for i in candidates if i.text and i.text.startswith("[")], key=lambda x: provider_rank(priority, x.tag))
            return ast.literal_eval(values[0].text) if values else None   # Plain name list, e.g. episode writers
        if kind is proxy_container_type():
            def image_key(image):
                try:
                    image_id = int(image.get("id") or 0)
                except ValueError:
                    image_id = 0
                if image.get("set_size"):
                    # Season posters with "prefer matching sets" (mark_poster_sets): the set covering most seasons first,
                    # within the library-language groups when that setting is on
                    return (language_rank(image, language) if (settings.PREFER_LOCAL_ART and language) else 0, -int(image.get("set_size")),
                            int(image.get("set_order") or 0), provider_rank(priority, image.getparent().tag), image_id)
                if settings.PREFER_LOCAL_ART and language:
                    # As the setting says: the library's language first, then images without (known) text, then the rest;
                    # source order only decides within those.
                    return (language_rank(image, language), provider_rank(priority, image.getparent().tag), image_id)
                return (provider_rank(priority, image.getparent().tag), language_rank(image, language), image_id)
            images = sorted(candidates, key=image_key)
            seen = []
            for image in images:                                  # Renumber 1..n (per season for season posters) in priority order
                group = image.get("season") if image.getparent().getparent().tag == "Season" else 1
                seen.append(group)
                image.set("id", str(seen.count(group)))
            return images
        values = sorted([i for i in candidates if i.text and i.text != "None"], key=lambda x: provider_rank(priority, x.tag))
        if not values:
            return None
        result = values[0].text
        if episode_title and is_bad_episode_title(result):
            # Prefer the next source's title over generic ones like "Episode 5"; keep the generic title if nothing better exists
            for value in values[1:]:
                if not is_bad_episode_title(value.text):
                    return value.text
        return result
    except Exception:
        Log.Debug("MetadataWriter - by_priority() failed: %s" % (textutil.exception_text()))
        return None


# Converting for Plex ##################################################################################################################################################
def title_text(candidates, priority, languages, episode_title=False):
    """Title in the best-ranked language among the allowed sources (idea from HAMA): e.g. TVDB's English episode title beats
       AniDB's romaji one when English is listed first. Source order breaks ties, and decides alone if "TitleLanguageFirst" is off.
       For episodes, generic titles like "Episode 5" lose to real ones."""
    if not settings.TITLE_LANGUAGE_FIRST:
        return text(candidates, priority, episode_title)
    allowed = [i for i in candidates if i.text and i.text != "None" and i.tag.lower() in priority]
    if episode_title:
        allowed = [i for i in allowed if not is_bad_episode_title(i.text)] or allowed
    if not allowed:
        return None
    best = sorted(allowed, key=lambda i: (textutil.title_rank(i.get("lang"), i.get("main") == "1", languages), provider_rank(priority, i.tag)))[0]
    return textutil.safe_unicode(best.text)


def text(candidates, priority, episode_title=False):
    value = by_priority(candidates, priority, str, episode_title)
    return textutil.safe_unicode(value) if value else None    # Plex accepts unicode; str() would fail on non-ASCII text


def number(candidates, priority, kind):
    value = by_priority(candidates, priority, kind)
    try:
        return kind(value) if value else None
    except (TypeError, ValueError):
        return None


RATING_FULL_WEIGHT = 100      # Votes at which a source counts half as much as one whose vote count isn't known


def combined_rating(candidates, priority, mode):
    """(rating, how) for the show from the sources in priority (setting "Rating from"); mode (setting "RatingCombine"):
       "first": the first source that has one;
       "average": the plain average of those sources;
       "weighted": an average where a source counts by its votes, votes / (votes + 100): one with 15 votes counts 0.13,
       one with 100 counts 0.5, one with thousands about 1. So an obscure show's handful of AniDB votes doesn't outweigh
       AniList, while big sites don't drown each other out by size. A source without a count (TVDB v4) counts 1."""
    if mode == "first":
        return number(candidates, priority, float), "first source"
    total = 0.0
    weights = 0.0
    parts = []
    for candidate in candidates or []:
        if candidate.tag.lower() not in priority:
            continue
        try:
            value = float(candidate.text)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        weight = 1.0
        votes = candidate.get("votes")
        if mode == "weighted" and votes and votes.isdigit():
            weight = float(votes) / (float(votes) + RATING_FULL_WEIGHT)
        total = total + value * weight
        weights = weights + weight
        parts.append("%s %s%s" % (candidate.tag, value, (" x %.2f" % (weight)) if mode == "weighted" else ""))
    if not weights:
        return None, "no source"
    return round(total / weights, 2), ("%s of %s" % ("weighted average" if mode == "weighted" else "average", ", ".join(parts)))


def date(candidates, priority):
    value = by_priority(candidates, priority, datetime.date)
    return textutil.parse_date(value) if value else None


def fill_set(candidates, priority, target):
    """Plex list attribute (genres, tags, collections, countries)."""
    values = by_priority(candidates, priority, list) if candidates else None
    if values:
        target.clear()
        for value in values:
            if value:
                target.add(value)


def fill_people(candidates, priority, target):
    """Plex people list: roles (seiyuu + character) or plain names (writers, directors, producers)."""
    people = by_priority(candidates, priority, set_object_type()) if candidates else None
    if not people:
        return
    target.clear()
    for person in sorted(people, key=lambda x: x if isinstance(x, basestring) else x.get("seiyuu_name", "")):
        if isinstance(person, basestring):
            if person.strip():
                entry = target.new()
                entry.name = person.strip()
        else:
            entry = target.new()
            entry.name = person.get("seiyuu_name", "")
            entry.role = person.get("character_name", "")
            entry.photo = person.get("seiyuu_pic", "")


def role_lists(candidates, priority):
    """(Japanese roles, English roles) as lists of <Role> elements, in their source's order (main characters first).
       Japanese: the first source by "Series: Roles" order that has any (AniDB, TVDB, AniList; TVDB's cast counts as
       Japanese, as before). English: AniList's (the only source listing English voice actors), whatever that order says."""
    japanese = []
    for provider in sorted([c for c in candidates if c.tag.lower() in priority], key=lambda c: provider_rank(priority, c.tag)):
        found = [r for r in provider if r.get("lang") != "en" and r.get("seiyuu_name")]
        if found:
            japanese = found
            break
    english = []
    if settings.ANILIST_ENABLED:
        for provider in candidates:
            if provider.tag == "Anilist":
                english = [r for r in provider if r.get("lang") == "en" and r.get("seiyuu_name")]
    return unique_roles(japanese), unique_roles(english)


def unique_roles(roles):
    """Without repeats of the same actor as the same character: AniDB lists a character once per form or appearance under
       one name (the same character up to 5 times), which Plex would show as identical cast entries. The first one is kept."""
    seen = {}
    found = []
    for role in roles:
        key = (role.get("seiyuu_name"), role.get("character_name"))
        if key in seen:
            continue
        seen[key] = True
        found.append(role)
    return found


def fill_roles(candidates, priority, target):
    """Plex cast by settings.CAST_LANGUAGE (ja / en / both) and settings.CAST_PHOTOS (actor / character)."""
    japanese, english = role_lists(candidates or [], priority)
    mode = settings.CAST_LANGUAGE
    if mode == "en":
        chosen = [(r, None) for r in english] or [(r, None) for r in japanese]
        if not english and japanese:
            Log.Debug("MetadataWriter - Cast: no English voice actors listed; Japanese cast used")
    elif mode == "both":
        chosen = [(r, u"Japanese") for r in japanese] + [(r, u"English") for r in english]
    else:
        chosen = [(r, None) for r in japanese]
    if not chosen:
        return
    target.clear()
    pictures = 0
    for role, label in chosen:
        entry = target.new()
        entry.name = role.get("seiyuu_name", "")
        character = role.get("character_name", "")
        entry.role = (u"%s (%s)" % (character, label) if character else label) if label else character
        photo = role.get("seiyuu_pic", "")
        if settings.CAST_PHOTOS == "character" and role.get("character_pic"):
            photo = role.get("character_pic")
            pictures = pictures + 1
        entry.photo = photo
    Log.Debug("MetadataWriter - Cast: %s Japanese, %s English listed; %s written (%s)%s" % (
        len(japanese), len(english), len(chosen), {"ja": "Japanese", "en": "English", "both": "both"}.get(mode, mode),
        (", %s character pictures" % (pictures)) if settings.CAST_PHOTOS == "character" else ""))


def cached_file(url, local_path):
    """A cached copy of an image (any age: images don't change under the same URL), or None; never downloads."""
    if not url or not local_path:
        return None
    name, directory = os.path.basename(local_path), os.path.dirname(local_path)
    return downloader.load_cached(name, directory) or downloader.load_stale(name, directory, True)


def image_task(image):
    """The background download of one image: "image|thumb url|thumb path|main url|main path" (background_refresh)."""
    return "|".join(["image", image.get("thumbUrl") or "", image.get("thumbLocalPath") or "", image.get("mainUrl") or "", image.get("mainLocalPath") or ""])


def download_image(image, target, lazy=None):
    """Download (or load from cache) one image and add it to a Plex image container. Never raises.
       lazy: a dict collecting what's left to the background (see write()); an image that isn't cached yet is added there
       instead of downloaded, and written by the refresh that follows its download."""
    try:
        use_thumb = len(image.get("thumbUrl") or "") > 0
        content = None
        if lazy is not None:
            content = cached_file(image.get("thumbUrl"), image.get("thumbLocalPath")) if use_thumb else None
            if not content:
                use_thumb = False
                content = cached_file(image.get("mainUrl"), image.get("mainLocalPath"))
            if not content:
                lazy["images"].append(image_task(image))
                return
        if use_thumb and not content:
            content = downloader.file_from_url(image.get("thumbUrl"), os.path.basename(image.get("thumbLocalPath")), os.path.dirname(image.get("thumbLocalPath")))
            if not content:
                use_thumb = False             # No thumbnail (not every image has one): use the full-size image instead
        if not content:
            content = downloader.file_from_url(image.get("mainUrl"), os.path.basename(image.get("mainLocalPath")), os.path.dirname(image.get("mainLocalPath")))
        if not content:
            return  # Download failed and nothing cached: skip this image
        sort_order = int(image.get("id"))
        proxy = Proxy.Preview(content, sort_order=sort_order) if use_thumb else Proxy.Media(content, sort_order=sort_order)
        if image.getparent().getparent().tag == "Season":
            target[image.get("season")].posters[image.get("mainUrl")] = proxy
        else:
            target[image.get("mainUrl")] = proxy
    except Exception:
        Log.Debug("MetadataWriter - Image '%s' failed: %s" % (image.get("mainUrl"), textutil.exception_text()))


def drop_stale(target, keys, label):
    """Remove images/themes this agent added on earlier refreshes but no longer provides (other sources or settings), so
       Plex's list follows the current priority. Only called when there is something to keep, so a refresh that found no
       images at all (e.g. sources offline) never empties the list. User-chosen uploads are not affected."""
    try:
        target.validate_keys(keys)
    except Exception:
        Log.Debug("MetadataWriter - Could not tidy %s: %s" % (label, textutil.exception_text()))


def already_in_plex(image, target):
    """True if Plex already holds this image (as HAMA checks: `url in container`); never raises."""
    try:
        return image.get("mainUrl") in target
    except Exception:
        return False


def season_has(target, image):
    """True if this season's poster list in Plex already holds the image; never raises."""
    try:
        return image.get("mainUrl") in target[image.get("season")].posters
    except Exception:
        return False


def unique_urls(images):
    """Best-first images without repeats of the same URL (two sources can list one file, e.g. TVDB v4 and v1 thumbnails;
       downloading both at once made Plex's Data.Save fail). Season posters count per season."""
    seen = {}
    found = []
    for image in images:
        key = (image.get("season"), image.get("mainUrl"))
        if key in seen:
            continue
        seen[key] = True
        found.append(image)
    return found


def fill_images(candidates, priority, target, language=None, label="images", limit=0, skip_existing=False, keep=None, lazy=None):
    """limit: most images kept (per season for season posters), best first; 0 = all. Dropped ones are removed from Plex too.
       skip_existing: images Plex already has aren't downloaded and set again (episode thumbnails: thousands for a long show).
       keep: True, or the season numbers (season posters), where you picked an image and Plex locked it: only images Plex
       doesn't have yet are added, and nothing is removed, so your pick is untouched."""
    images = by_priority(candidates, priority, proxy_container_type(), False, language) if candidates else None
    if not images:
        return
    images = unique_urls(sorted(images, key=lambda x: int(x.get("id"))))
    keys = None
    if skip_existing:
        keys = [image.get("mainUrl") for image in images if not limit or int(image.get("id")) <= limit]
        images = [image for image in images if not already_in_plex(image, target)]
        if not images:
            if keep is not True:
                drop_stale(target, keys, label)    # Locked (your pick): nothing removed, so the pick (uploaded, or from
            return                                 # a source) stays
    if limit:
        kept = [image for image in images if int(image.get("id")) <= limit]
        if len(kept) < len(images) and kept:
            Log.Debug("MetadataWriter - %s: best %s of %s kept (setting Images: maximum per type)" % (label, len(kept), len(images)))
        images = kept
        if not images:
            # With skip_existing: the best ones are all in Plex already and the rest are over the limit.
            Log.Debug("MetadataWriter - %s: the best %s are already in Plex; nothing to add" % (label, limit))
            if keep is not True and keys is not None:
                drop_stale(target, keys, label)
            return
    if keep and images[0].getparent().getparent().tag == "Season":
        images = [image for image in images if image.get("season") not in keep or not season_has(target, image)]
        if not images:
            return
    if images[0].getparent().getparent().tag == "Season":
        for season in sorted(set([image.get("season") for image in images])):
            try:
                target[season].posters                # Create each season's record here, not from several threads at once
            except Exception:
                pass
    if len(images) == 1 or lazy is not None:
        for image in images:                     # No thread pool for one image (most episode thumbnails) or the cache
            download_image(image, target, lazy)
    else:
        @parallelize
        def download_images():
            for image in images:
                @task
                def download_one(image=image, target=target):
                    download_image(image, target)

    if images[0].getparent().getparent().tag == "Season":
        per_season = {}
        for image in images:
            per_season.setdefault(image.get("season"), []).append(image.get("mainUrl"))
        for season in per_season:
            if keep and season in keep:
                continue                                       # Locked: nothing removed
            try:
                container = target[season].posters
            except Exception:
                continue
            drop_stale(container, per_season[season], "season %s posters" % (season))
    elif keep is not True:
        drop_stale(target, keys if keys is not None else [image.get("mainUrl") for image in images], label)   # Kept ones count too


def fill_themes(candidates, priority, target):
    themes = by_priority(candidates, priority, proxy_container_type()) if candidates else None
    for theme in sorted(themes or [], key=lambda x: x.get("id")):
        try:
            content = downloader.file_from_url(theme.get("url"), os.path.basename(theme.get("localPath")), os.path.dirname(theme.get("localPath")))
            if content:
                target[theme.get("url")] = Proxy.Media(content, sort_order=int(theme.get("id") or 1))
        except Exception:
            Log.Debug("MetadataWriter - Theme '%s' failed: %s" % (theme.get("url"), textutil.exception_text()))
    if themes:
        drop_stale(target, [theme.get("url") for theme in themes], "themes")


# Writing ##############################################################################################################################################################
def local_episode(media, season, episode):
    """Plex's on-disk episode object, or None."""
    for season_key, episode_key in ((int(season), int(episode)), (str(season), str(episode))):
        try:
            return media.seasons[season_key].episodes[episode_key]
        except Exception:
            pass
    return None


def has_local_episode(media, season, episode):
    """True if Plex has this season/episode on disk. Writing to seasons/episodes that don't exist crashes Plex's model objects."""
    if media is None:
        return True
    return local_episode(media, season, episode) is not None


def copy_streams(node, plex_episode):
    """Stream languages of an episode found by absolute number (bundle.map_local only looks up SxxEyy), for the dub/sub collections."""
    streams = node.find("./Streams")
    if streams is None:
        streams = SubElement(node, "Streams")
    if len(streams):
        return
    try:
        audio, subtitles = bundle.stream_languages(plex_episode)
        for language in audio:
            SubElement(streams, "Stream", type="audio", lang=language)
        for language in subtitles:
            SubElement(streams, "Stream", type="subtitle", lang=language)
    except Exception as e:
        Log.Debug("MetadataWriter - Stream info for S%sE%s failed: %s" % (node.getparent().get("num"), node.get("num"), e))


def episode_key(node):
    return "%s-%s" % (node.getparent().get("num"), node.get("num"))


def absolute_numbers(nodes, first_season):
    """{episode key: absolute number counted from the show's first season} for the regular episodes.
       TVDB's absolute numbers are used when at least half of the episodes have one (rebased so the first season starts at 1),
       otherwise the episodes' order (season, then episode)."""
    regular = [node for node in nodes if int(node.getparent().get("num")) >= max(first_season, 1) and textutil.is_digits(node.get("num"))]
    regular = sorted(regular, key=lambda x: (int(x.getparent().get("num")), int(x.get("num"))))
    tvdb_numbers = {}
    for node in regular:
        values = node.xpath("./Absolute_Index/Tvdb/text()")
        if values and textutil.is_digits(values[0].strip()) and int(values[0].strip()) > 0:
            tvdb_numbers[episode_key(node)] = int(values[0].strip())
    numbers = {}
    if regular and len(tvdb_numbers) * 2 >= len(regular):
        base = sorted(tvdb_numbers.values())[0]
        for key in tvdb_numbers:
            numbers[key] = tvdb_numbers[key] - base + 1
    else:
        for index, node in enumerate(regular):
            numbers[episode_key(node)] = index + 1
    return numbers


def absolute_matches(missing, nodes, first_season, media, found, quiet=False):
    """Absolutely numbered files (Show - 105.mkv, which scanners report as S01E105): a mapped regular episode that isn't on disk
       as SxxEyy is written to season 1, episode <absolute number> when that file exists and no other episode is written there."""
    if media is None or not missing:
        return []
    numbers = None
    taken = set(["%s-%s" % (season, episode) for node, season, episode in found])
    matches = []
    for node in missing:
        if node.getparent().get("num") == "0":
            continue
        if numbers is None:
            numbers = absolute_numbers(nodes, first_season)
        number = numbers.get(episode_key(node))
        if not number or ("1-%s" % (number)) in taken:
            continue
        plex_episode = local_episode(media, "1", str(number))
        if plex_episode is not None:
            taken.add("1-%s" % (number))
            matches.append((node, "1", str(number)))
            copy_streams(node, plex_episode)
    if matches and not quiet:
        Log.Info("MetadataWriter - %s episodes matched by absolute number (e.g. TVDB S%sE%s -> S01E%s)"
                 % (len(matches), matches[0][0].getparent().get("num"), matches[0][0].get("num"), matches[0][2]))
    return matches


def series_values(season_node, field):
    return season_node.xpath("./%s/*[node()]" % (field))


# Seasons ##############################################################################################################################################################
GENERIC_SEASON_NAME = re.compile(r"^(season|series|specials?)( [0-9]+)?$", re.IGNORECASE)
# Words that only number or describe a season ("2nd Season", "Season 2 Part 2", "Final Season", "II", "(2017)"):
# a name made only of these says nothing the season number doesn't already say.
SEASON_WORDS = set("season seasons series part parts cour cours the final last specials special arc first second third fourth fifth "
                   "sixth seventh eighth ninth tenth st nd rd th tv".split())
SEASON_NUMBER_WORD = re.compile(r"^([0-9]+(st|nd|rd|th)?|[ivx]+)$")
SEASON_NAME_SEPARATORS = u" :-\u2013\u2014~,./|"


def generic_season_name(name):
    words = textutil.clean_title(name).split()
    for word in words:
        if word not in SEASON_WORDS and not SEASON_NUMBER_WORD.match(word):
            return False
    return True


def trim_show_title(name, show_titles):
    """Remove the show's title from the start of a season name: 'Show Name 2nd Season' -> '2nd Season',
       'Show Name: Name of Season' -> 'Name of Season'. Punctuation and case don't matter; whole words only
       ('Prefixshow' isn't trimmed by 'Show'). A leftover leading 'Series' goes too ('Show Series: Name of Season' ->
       'Name of Season'). Unchanged if it doesn't start with a show title."""
    best = name
    for show in show_titles or []:
        target = textutil.clean_title(show)
        if not target:
            continue
        for word in re.finditer(r"\S+", name, re.UNICODE):
            cleaned = textutil.clean_title(name[:word.end()])
            if cleaned == target:
                rest = name[word.end():].lstrip(SEASON_NAME_SEPARATORS)
                rest = LEADING_SERIES_WORD.sub(u"", rest).lstrip(SEASON_NAME_SEPARATORS) or rest
                if len(rest) < len(best):
                    best = rest
                break
            if len(cleaned) > len(target):
                break
    return best


LEADING_SERIES_WORD = re.compile(r"^series(?=\W|$)", re.IGNORECASE | re.UNICODE)


def starts_with_show(name, titles):
    return trim_show_title(name, titles) != name


def shared_by_others(title, others):
    for name in others:
        if starts_with_show(name, [title]):
            return True
    return False


def show_titles(root, first_season, series_title, names=None):
    """The show's own titles, for trimming and for dropping season names that only repeat the show's name:
       * TVDB's title for the show;
       * titles of the entry behind season 1 (AniDB, AniList) only if another season's name starts with them
         ('Show Name' when season 2 is 'Show Name Season 2'). Otherwise they name only that season (a franchise whose
         first entry has a name of its own);
       * the title Plex shows: by the same rule when it comes from season 1's entry, else always. A show without other named
         seasons always counts it.
       names: {TVDB season: name} (season_names)."""
    main = root.find('./Season[@num="%s"]' % (first_season))
    if main is None:
        return [series_title] if series_title else []
    tvdb = [x.text for x in main.xpath("./Title/Tvdb[node()]") + main.xpath("./Original_Title/Tvdb[node()]") if x.text]
    entry = [x.text for x in main.xpath("./Title/*[node()]") + main.xpath("./Original_Title/*[node()]") if x.text and x.tag != "Tvdb"]
    others = [names[n] for n in sorted((names or {}).keys()) if n != first_season]
    titles = []
    if series_title:
        from_entry = textutil.clean_title(series_title) in [textutil.clean_title(x) for x in entry]
        in_tvdb = textutil.clean_title(series_title) in [textutil.clean_title(x) for x in tvdb]
        if in_tvdb or not from_entry or not others or shared_by_others(series_title, others):
            titles.append(series_title)
    for title in tvdb:
        if title not in titles:
            titles.append(title)
    for title in entry:
        if title not in titles and shared_by_others(title, others):
            titles.append(title)
    return titles


def season_entries(season_node):
    """[(AniDB id, first episode, last episode)] of the entries making up this season's regular episodes, in episode order
       (a TVDB season can hold several: a split cour, or a long season released in parts)."""
    ranges = {}
    for episode in season_node.xpath("./Episode"):
        number = episode.get("num")
        if not textutil.is_digits(number):
            continue
        for mapped in episode.xpath("./Mapped/anidb"):
            series_id = mapped.get("series")
            if textutil.is_digits(series_id) and textutil.is_digits(mapped.get("episode")):
                low, high = ranges.get(series_id, (int(number), int(number)))
                ranges[series_id] = (min(low, int(number)), max(high, int(number)))
    return [(k, ranges[k][0], ranges[k][1]) for k in sorted(ranges.keys(), key=lambda k: (ranges[k][0], int(k)))]


def entry_record(provider, anidb_id):
    record = sources.get_anidb(anidb_id, False) if provider == "anidb" else (sources.get("Anilist", anidb_id) if settings.ANILIST_ENABLED else None)
    return record if record is not None and record.valid else None


def part_heading(title, first_title, low, high):
    """'The Separation (episodes 27-40)': a later part's own title without the season's title in front."""
    rest = trim_show_title(title, [first_title]) if title and first_title else title
    rest = (rest or "").strip(SEASON_NAME_SEPARATORS + u" ") or title or u"Part"
    return u"%s (episodes %s\u2013%s)" % (textutil.safe_unicode(rest), low, high)


def combined_summary(provider, entries, first_record):
    """The first entry's summary, then each later part's under its own heading; parts without a summary are left out."""
    parts = []
    lead = first_record.summary if first_record is not None else None
    if lead:
        parts.append(textutil.safe_unicode(lead))
    first_title = first_record.title if first_record is not None else None
    for anidb_id, low, high in entries[1:]:
        record = entry_record(provider, anidb_id)
        if record is None or not record.summary or same_summary(record.summary, lead):
            continue
        parts.append(u"%s\n%s" % (part_heading(record.title, first_title, low, high), textutil.safe_unicode(record.summary)))
    return u"\n\n".join(parts) if parts else None


def season_provider_text(provider, season_node, tvdb_number):
    """(name, summary) from one provider: AniDB/AniList = the season's entries (name from the first; summaries combined in
       episode order when several make up the season, setting SeasonParts), TVDB = v4 season text (one cached request)."""
    if provider in ("anidb", "anilist") and tvdb_number != 0:
        entries = season_entries(season_node)
        if entries:
            record = entry_record(provider, entries[0][0])
            summary = record.summary if record is not None else None
            if len(entries) > 1 and settings.SEASON_PARTS_COMBINED:
                summary = combined_summary(provider, entries, record)
            if record is not None or summary:
                return (record.title if record is not None else None), summary
    if provider == "tvdb":
        tvdb_ids = sorted(set([x.get("series") for x in season_node.xpath("./Episode/Mapped/tvdb") if textutil.is_digits(x.get("series"))]))
        if tvdb_ids:
            record = sources.get_tvdb(tvdb_ids[0])
            season_id = record.season_ids.get(str(tvdb_number)) if record.valid and record.api == "v4" else None
            text_values = tvdb_v4.season_text(tvdb_ids[0], season_id) if season_id else None
            if text_values:
                return text_values.get("name"), text_values.get("overview")
    return None, None


def useful_season_name(name):
    return bool(name) and not GENERIC_SEASON_NAME.match(name) and not generic_season_name(name)


class SeasonTexts:
    """Provider (name, summary) per bundle season, asked once each and only when needed."""
    def __init__(self):
        self.found = {}

    def get(self, provider, season_node, tvdb_number):
        key = (tvdb_number, provider)
        if key not in self.found:
            try:
                self.found[key] = season_provider_text(provider, season_node, tvdb_number)
            except Exception:
                Log.Debug("MetadataWriter - Season %s text from %s failed: %s" % (tvdb_number, provider, textutil.exception_text()))
                self.found[key] = (None, None)
        return self.found[key]


def season_names(root, first_season, plex_seasons, texts):
    """{TVDB season: the first provider name that says more than its number} for the show's seasons. Seasons without files
       count too (AniDB's cached name only, no downloads), so decisions based on them don't change as files arrive."""
    names = {}
    on_disk = set([int(x) + first_season - 1 for x in plex_seasons if x != "0"])
    for node in root.xpath('./Season[@num!="0"]'):
        tvdb_number = int(node.get("num"))
        if tvdb_number < first_season:
            continue
        providers = settings.SEASON_PRIORITY if tvdb_number in on_disk else [x for x in settings.SEASON_PRIORITY if x == "anidb"]
        for provider in providers:
            name = texts.get(provider, node, tvdb_number)[0]
            name = name.strip() if name else name
            if useful_season_name(name):
                names[tvdb_number] = name
                break
    return names


def trim_mode(names, titles):
    """(trim?, named, prefixed): season names lose the show's title only when most named seasons start with it
       ('Show Name: Name of Season', 'Show Name Season 2'), so a show's seasons read alike. Kept whole when most have
       names of their own (a franchise whose entries are each named differently)."""
    named = len(names)
    prefixed = len([n for n in names if starts_with_show(names[n], titles)])
    return prefixed * 2 > named, named, prefixed


def same_summary(one, two):
    """Equal apart from spacing, line breaks and case (one source's summary copied by another)."""
    flat = lambda x: re.sub(r"\s+", " ", textutil.safe_unicode(x or "")).strip().lower()
    return bool(one) and bool(two) and flat(one) == flat(two)


def starts_with_summary(summary, show_summary):
    """A combined season summary whose first part is the show's summary (season 1 of a show matched to its first entry)."""
    flat = lambda x: re.sub(r"\s+", " ", textutil.safe_unicode(x or "")).strip().lower()
    return bool(summary) and bool(show_summary) and flat(summary).startswith(flat(show_summary) + " ")


def repeated_summary(metadata, main, season, summary, node, tvdb_number, texts):
    """Setting "SummaryRepeat": when a season's summary is the show's summary again (a show matched to its first AniDB
       entry: that entry describes both the show and season 1, or one entry spans several TVDB seasons). Returns the season's summary to use.
         "show" (recommended): the show takes TVDB's series overview instead (TVDB has one for nearly every show), and the
                 season keeps its own entry's summary, which is about that season;
         "season": the season takes TVDB's season overview instead, if TVDB has one (often not, for anime);
         "both": left as they are."""
    if season == "0" or not (same_summary(summary, metadata.summary) or starts_with_summary(summary, metadata.summary)) or settings.SUMMARY_REPEAT == "both":
        return summary
    if settings.SUMMARY_REPEAT == "show":
        tvdb = [x.text for x in series_values(main, "Summary") if x.tag == "Tvdb" and x.text] if main is not None else []
        if tvdb and not same_summary(tvdb[0], summary):
            metadata.summary = tvdb[0]
            Log.Info("MetadataWriter - Season %s's summary is the show's: the show now uses TVDB's summary (%s characters)" % (season, len(tvdb[0])))
        else:
            Log.Debug("MetadataWriter - Season %s's summary is the show's, but TVDB has no other show summary" % (season))
        return summary
    tvdb = texts.get("tvdb", node, tvdb_number)[1] if texts is not None else None
    if tvdb and not same_summary(tvdb, summary):
        Log.Info("MetadataWriter - Season %s's summary is the show's: the season uses TVDB's season summary instead" % (season))
        return tvdb
    Log.Debug("MetadataWriter - Season %s's summary is the show's, but TVDB has no season summary for it" % (season))
    return summary


def season_text(season_node, tvdb_number, titles=None, trim=True, texts=None, order=None):
    """(name, summary) for one TVDB season by settings.SEASON_PRIORITY; later providers are only asked for what's still missing.
       trim: the show's title is removed from a name's start (titles); a name that is then empty or only numbers the season
       ("2nd Season") is skipped, so the next source can offer a real name. Not trimming, only names that say nothing
       ("Season 2") or are the show's title are skipped."""
    texts = texts or SeasonTexts()
    shows = [textutil.clean_title(x) for x in titles or []]
    name = None
    summary = None
    for provider in settings.SEASON_PRIORITY:
        provider_name = texts.get(provider, season_node, tvdb_number)[0]
        if provider_name:
            candidate = provider_name.strip()
            if trim:
                candidate = trim_show_title(candidate, titles)
            elif textutil.clean_title(candidate) in shows:
                candidate = None
            if useful_season_name(candidate):
                name = candidate
                break
    for provider in order or settings.SEASON_PRIORITY:
        summary = texts.get(provider, season_node, tvdb_number)[1]
        if summary:
            break
    return name, summary


def write_seasons(root, metadata, first_season, plex_seasons, series_title, show_key=None, main=None):
    """Season titles and summaries for seasons with episodes on disk. Plex ignores these when an agent writes them, so they are
       also queued for season_editor, which applies them through Plex's own edit API once this update has been applied."""
    if not settings.SEASON_PRIORITY:
        return
    texts = SeasonTexts()
    try:
        names = season_names(root, first_season, plex_seasons, texts)
        titles = show_titles(root, first_season, series_title, names)
        trim, named, prefixed = trim_mode(names, titles)
    except Exception:
        Log.Debug("MetadataWriter - Season naming check failed: %s" % (textutil.exception_text()))
        titles = show_titles(root, first_season, series_title)
        trim, named, prefixed = True, 0, 0
    shows = [textutil.clean_title(x).lower() for x in titles]
    if named:
        Log.Debug("MetadataWriter - Season names: %s of %s start with the show's title (%s), so they are %s"
                  % (prefixed, named, " / ".join(titles), "trimmed" if trim else "kept whole"))
    queued = {}
    for season in sorted(plex_seasons, key=lambda x: int(x)):
        tvdb_number = 0 if season == "0" else int(season) + first_season - 1
        node = root.find('./Season[@num="%s"]' % (tvdb_number))
        if node is None:
            continue
        try:
            name, summary = season_text(node, tvdb_number, titles, trim, texts)
        except Exception:
            Log.Debug("MetadataWriter - Season %s text failed: %s" % (season, textutil.exception_text()))
            name, summary = None, None
        try:
            summary = repeated_summary(metadata, main, season, summary, node, tvdb_number, texts)
        except Exception:
            Log.Debug("MetadataWriter - Season %s summary check failed: %s" % (season, textutil.exception_text()))
        if name and (season == "0" or textutil.clean_title(name).lower() in shows):
            name = None                                             # A season named after the show adds nothing
        name = textutil.safe_unicode(name) if name else None
        summary = textutil.safe_unicode(summary) if summary else None
        title = None
        if name and settings.SEASON_NAME_MODE == "number-name":
            title = u"Season %s: %s" % (season, name)
        elif name and settings.SEASON_NAME_MODE == "name":
            title = name
        if name and settings.SEASON_NAME_IN_SUMMARY:                 # Separate setting: works with any title choice
            summary = (u"%s\n\n%s" % (name, summary)) if summary else name
        if summary:
            try:
                metadata.seasons[season].summary = summary
            except Exception:
                Log.Debug("MetadataWriter - Season %s summary failed: %s" % (season, textutil.exception_text()))
        known = []                                  # Every source's summary: one of these in Plex was written by AMSA, not typed by you
        for provider in settings.SEASON_PRIORITY:
            try:
                provider_summary = texts.get(provider, node, tvdb_number)[1]
            except Exception:
                provider_summary = None
            if provider_summary:
                known.append(textutil.safe_unicode(provider_summary))
        queued[season] = (title, summary, known)    # Also without a title: season_editor then resets a title AMSA set earlier
        if title or summary:
            Log.Debug("MetadataWriter - Season %s: title %r, summary %s" % (season, title, ("%s characters" % len(summary)) if summary else "none"))
    if show_key:
        season_editor.queue(show_key, queued)


def main_season(root, anidb_id, tvdb_id):
    """The bundle season holding the matched entry; its TVDB number becomes Plex season 1."""
    season_nodes = root.xpath('./Season[@AnidbId="%s" and @num!="0"]' % (anidb_id))
    if not season_nodes:
        season_nodes = root.xpath('./Season[@TvdbId="%s" and @num!="0"]' % (tvdb_id))
    if not season_nodes:
        # No provider data matched the requested ids (e.g. AniDB unreachable): use the first regular season, then specials
        season_nodes = sorted(root.xpath('./Season[@num!="0"]'), key=lambda x: int(x.get("num"))) or root.xpath('./Season[@num="0"]')
    return season_nodes[0] if season_nodes else None


def select_episodes(root, first_season, media, quiet=False):
    """[(bundle episode, Plex season, Plex episode)] for every mapped episode on disk (by SxxEyy, else by absolute number)."""
    episodes = []
    missing = []
    nodes = sorted(root.xpath("./Season[@num>=%s or @num=0]/Episode" % (max(first_season, 1))), key=lambda x: int(x.getparent().get("num")))
    for node in nodes:
        number_in_tvdb = int(node.getparent().get("num"))
        season = "0" if number_in_tvdb == 0 else str(number_in_tvdb - first_season + 1)   # Renumber so the show's first season is 1; specials stay 0
        episode = node.get("num")
        if has_local_episode(media, season, episode):
            episodes.append((node, season, episode))
        else:
            missing.append(node)
    absolute = absolute_matches(missing, nodes, first_season, media, episodes, quiet)
    episodes.extend(absolute)
    if not quiet:
        Log.Debug("MetadataWriter - Writing %s episodes found on disk (%s by absolute number; %s mapped episodes not on disk skipped)"
                  % (len(episodes), len(absolute), len(missing) - len(absolute)))
    return episodes


def local_keys(media):
    """[(season, episode)] of every episode Plex has on disk (as strings), or None if the media tree can't be read."""
    keys = []
    try:
        for season in media.seasons:
            for episode in media.seasons[season].episodes:
                keys.append((str(season), str(episode)))
    except Exception:
        return None
    return keys


def has_episode_data(node):
    """True if a bundle episode has a real title (not "Episode 7") or a summary from any source."""
    for title in node.xpath("./Title/*[node()]"):
        if title.text and not is_bad_episode_title(title.text):
            return True
    return len(node.xpath("./Summary/*[node()]")) > 0


def episode_report(root, anidb_id, tvdb_id, media):
    """What a write would leave without data, for refresher.py: {"unwritten": [(season, episode)] on disk but not mapped,
       "empty": [bundle episodes] on disk with no title or summary}. Specials (season 0) are not counted."""
    report = {"unwritten": [], "empty": [], "empty_keys": []}
    main = main_season(root, anidb_id, tvdb_id)
    keys = local_keys(media) if media is not None else None
    if main is None or keys is None:
        return report
    episodes = select_episodes(root, int(main.get("num")), media, True)
    written = set(["%s-%s" % (season, episode) for node, season, episode in episodes])
    report["unwritten"] = [key for key in keys if key[0] != "0" and ("%s-%s" % (key[0], key[1])) not in written]
    report["empty"] = [node for node, season, episode in episodes if season != "0" and not has_episode_data(node)]
    report["empty_keys"] = [(season, episode) for node, season, episode in episodes if season != "0" and not has_episode_data(node)]
    return report


def add_time(timings, name, started):
    """Add the seconds since started to timings[name] (timings may be None)."""
    if timings is not None:
        timings[name] = timings.get(name, 0) + time.time() - started
    return time.time()


def tvdb_title_for_alias(root, main, tvdb_id, title):
    """Setting SeriesTitleAlias: if the chosen show title is one of the TVDB series' aliases (e.g. AniDB's title for the
       first entry of a franchise TVDB lists as one series), the TVDB series is the show as a whole, so its own title is used.
       "several" (default) only does this for shows spanning more than one AniDB entry; single-entry shows keep their title."""
    if not settings.TITLE_FROM_TVDB_ALIAS or not title:
        return title
    series_id = main.get("TvdbId") or tvdb_id
    if not textutil.is_digits(series_id):
        return title
    entries = set([x.get("series") for x in root.xpath("./Season/Episode/Mapped/anidb") if textutil.is_digits(x.get("series"))])
    if settings.TITLE_FROM_TVDB_ALIAS == "several" and len(entries) < 2:
        return title
    record = sources.get_tvdb(series_id)
    if not record.valid or not record.title:
        return title
    chosen = textutil.clean_title(title)
    if chosen == textutil.clean_title(record.title):
        return title
    aliases = [textutil.clean_title(x) for x in getattr(record, "aliases", None) or []]
    if chosen in aliases:
        Log.Info("MetadataWriter - Show title: TVDB's '%s' instead of '%s' (one of TVDB %s's aliases; setting: %s)"
                 % (record.title, title, series_id, settings.TITLE_FROM_TVDB_ALIAS))
        return record.title
    Log.Debug("MetadataWriter - Show title '%s' kept: not one of TVDB %s's aliases (%s)" % (title, series_id, ", ".join(getattr(record, "aliases", None) or []) or "none"))
    return title


SET_TIME_GAP = 3 * 86400       # Season posters uploaded within 3 days of each other...
SET_ID_GAP = 500                 # ...or within 500 TVDB artwork ids count as one upload batch


def number_or_zero(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def mark_poster_sets(images):
    """Setting SeasonPosterSets: guess which season posters belong to one designed set and mark each with the set's size
       (seasons it covers) and rank, for by_priority. TVDB doesn't say who uploaded an image, so a set is guessed as posters
       with the same language and text flag uploaded in one batch (within SET_TIME_GAP or SET_ID_GAP of the previous one).
       TVDB's own season-record images form one group, and each other source (AniDB, AniList entry posters) one group.
       Returns the groups as [(size, label)], biggest first, for the log."""
    groups = []
    batches = {}
    tvdb = sorted([i for i in images if i.getparent().tag == "Tvdb" and i.get("artwork_id")],
                  key=lambda i: (number_or_zero(i.get("updated")), number_or_zero(i.get("artwork_id"))))
    for image in tvdb:
        key = (image.get("lang") or "", image.get("text") or "")
        updated = number_or_zero(image.get("updated"))
        artwork_id = number_or_zero(image.get("artwork_id"))
        group = batches.get(key)
        if group is not None and ((updated and group["updated"] and updated - group["updated"] <= SET_TIME_GAP) or abs(artwork_id - group["artwork_id"]) <= SET_ID_GAP):
            group["members"].append(image)
        else:
            group = {"label": "TVDB %s%s batch from artwork %s" % (key[0] or "no-language", ", text" if key[1] == "1" else "", artwork_id), "members": [image]}
            groups.append(group)
            batches[key] = group
        group["updated"] = updated
        group["artwork_id"] = artwork_id
    others = {}
    for image in images:
        if image.getparent().tag == "Tvdb" and image.get("artwork_id"):
            continue
        name = image.getparent().tag + (" season records" if image.getparent().tag == "Tvdb" else " entry posters")
        if name not in others:
            others[name] = {"label": name, "members": []}
            groups.append(others[name])
        others[name]["members"].append(image)
    for group in groups:
        group["size"] = len(set([i.get("season") for i in group["members"]]))
    ordered = sorted(groups, key=lambda g: (-g["size"], groups.index(g)))
    for rank, group in enumerate(ordered):
        for image in group["members"]:
            image.set("set_size", str(group["size"]))
            image.set("set_order", str(rank))
    return [(g["size"], g["label"]) for g in ordered]


def season_poster_candidates(root, first_season):
    """Season posters for Plex, numbered like Plex's seasons (the show's first season is 1, specials 0):
       * TVDB's season posters (on the matched season's bundle node: TVDB numbers, renumbered here);
       * each season's own AniDB / AniList entry poster (its bundle node), like season names.
       Copies are returned under a <Season><Provider> holder, so the bundle isn't changed and by_priority sees the provider."""
    holder = etree.Element("Season")
    groups = {}
    tvdb_node = root.find('./Season[@num="%s"]' % (first_season))
    if tvdb_node is None or not tvdb_node.xpath("./Season/Tvdb"):
        found = root.xpath("./Season[Season/Tvdb]")
        tvdb_node = found[0] if found else None
    entry_posters = []                                     # An entry spanning several seasons names only its first
    for node in sorted(root.xpath("./Season"), key=lambda x: int(x.get("num"))):
        tvdb_number = int(node.get("num"))
        if tvdb_number != 0 and tvdb_number < first_season:
            continue
        plex_number = "0" if tvdb_number == 0 else str(tvdb_number - first_season + 1)
        for provider_node in node.xpath("./Season/*"):
            tag = provider_node.tag
            for image in provider_node.xpath(".//Image"):
                if tag == "Tvdb":
                    if node is not tvdb_node:
                        continue                             # Every node carries the same TVDB list: use one (the matched season's)
                    number = image.get("season")
                    if not textutil.is_digits(number):
                        continue
                    number = int(number)
                    if number != 0 and number < first_season:
                        continue
                    target = "0" if number == 0 else str(number - first_season + 1)
                else:
                    if tvdb_number == 0:
                        continue                             # Specials: no entry poster of their own
                    if image.get("mainUrl") in entry_posters:
                        continue                             # Already the poster of an earlier season of the same entry
                    entry_posters.append(image.get("mainUrl"))
                    target = plex_number                     # The entry's own poster names this season
                if tag not in groups:
                    groups[tag] = SubElement(holder, tag)
                item = copy.deepcopy(image)
                item.set("season", target)
                groups[tag].append(item)
    return holder.xpath(".//Image")


def write(root, metadata, anidb_id, tvdb_id, media=None, lang=None, timings=None, lazy=None):
    """Populate Plex's metadata object from the bundle. lang: the library's language (Plex code, e.g. "en"), for image order.
       timings: optional dict that receives seconds per phase (images, crew, seasons, episodes).
       lazy: {"crew": [], "images": []} to leave episode writers/directors and thumbnails that aren't cached yet to the
       background (background refresh mode): they're collected there instead of downloaded during the update, and the
       caller queues them (background_refresh.add_files). None: download them now."""
    language = textutil.short_language(lang)
    main = main_season(root, anidb_id, tvdb_id)
    if main is None:
        Log.Error("MetadataWriter - Nothing to write for anidb: '%s', tvdb: '%s'" % (anidb_id, tvdb_id))
        return
    first_season = int(main.get("num"))
    priority = settings.SERIES_PRIORITY

    metadata.title = title_text(series_values(main, "Title"), priority["Title"], settings.SERIES_LANGUAGE_PRIORITY)
    try:
        metadata.title = tvdb_title_for_alias(root, main, tvdb_id, metadata.title)
    except Exception:
        Log.Debug("MetadataWriter - TVDB alias check failed: %s" % (textutil.exception_text()))
    try:
        metadata.original_title = text(series_values(main, "Original_Title"), [p for p in priority["Title"] if p in ("anidb", "anilist")] or ["anidb", "anilist"])
    except Exception:
        Log.Debug("MetadataWriter - Original title not set: %s" % (textutil.exception_text()))
    metadata.summary = text(series_values(main, "Summary"), priority["Summary"])
    metadata.originally_available_at = date(series_values(main, "Originally_Available_At"), priority["Originally_Available_At"])
    metadata.rating, how = combined_rating(series_values(main, "Rating"), priority["Rating"], settings.RATING_COMBINE)
    Log.Info("MetadataWriter - Series rating: %s (%s; sources with a rating: %s; setting: %s)" % (
        metadata.rating, how, ", ".join(["%s %s%s" % (x.tag, x.text, (" (%s votes)" % x.get("votes")) if x.get("votes") else "") for x in series_values(main, "Rating")]) or "none",
        ",".join(priority["Rating"]) or "off"))
    metadata.studio = text(series_values(main, "Studio"), priority["Studio"])
    fill_set(series_values(main, "Countries"), priority["Countries"], metadata.countries)
    metadata.duration = number(series_values(main, "Duration"), priority["Duration"], int)
    fill_set(series_values(main, "Genres"), priority["Genres"], metadata.genres)
    fill_set(series_values(main, "Tags"), priority["Tags"], metadata.tags)
    metadata.content_rating = regional_rating(choose_content_rating(series_values(main, "Content_Rating"), priority["Content_Rating"]),
                                              main.get("TvdbId") or tvdb_id, series_values(main, "Content_Rating"))
    fill_roles(series_values(main, "Roles"), priority["Roles"], metadata.roles)
    Log.Debug("MetadataWriter - Image priority: %s; prefer library language: %s" % (",".join(settings.SERIES_IMAGES_PRIORITY), settings.PREFER_LOCAL_ART))
    started = time.time()
    show_key = getattr(media, "id", None)
    leave_show = season_editor.chosen_show_images(show_key, ["posters", "art", "banners"]) if show_key else {}
    written = []
    for kind, field, target, label in (("posters", "Posters", metadata.posters, "posters"), ("art", "Art", metadata.art, "backgrounds"),
                                       ("banners", "Banners", metadata.banners, "banners")):
        if leave_show.get(kind) == "locked in Plex":
            # Plex locks an image you pick: new ones are only added (your pick and the rest untouched)
            Log.Info("MetadataWriter - Show %s: your pick is kept; only new ones added" % (label))
            try:
                fill_images(main.xpath("./%s//Image" % (field)), settings.SERIES_IMAGES_PRIORITY, target, language, label, settings.IMAGES_MAX, True, True)
            except Exception:
                Log.Warn("MetadataWriter - Show %s skipped: %s" % (label, textutil.exception_text()))
            continue
        if kind in leave_show:
            Log.Info("MetadataWriter - Show %s left as they are: %s" % (label, leave_show[kind]))
            continue
        try:
            fill_images(main.xpath("./%s//Image" % (field)), settings.SERIES_IMAGES_PRIORITY, target, language, label, settings.IMAGES_MAX)
            written.append(kind)
        except Exception:
            Log.Warn("MetadataWriter - Show %s skipped: %s" % (label, textutil.exception_text()))
    if show_key:
        season_editor.queue_show_images(show_key, written)
    season_images = season_poster_candidates(root, first_season)
    if season_images and settings.PREFER_POSTER_SETS:
        found = mark_poster_sets(season_images)
        Log.Info("MetadataWriter - Season poster sets (best first): %s" % ("; ".join(["%s: %s seasons" % (label, size) for size, label in found[:4]]) or "none"))
    if season_images and getattr(media, "id", None):
        numbers = []
        for image in season_images:
            if image.get("season") not in numbers:
                numbers.append(image.get("season"))
        leave = season_editor.chosen_posters(getattr(media, "id", None), numbers)
        locked = [x for x in leave if leave[x] == "poster locked in Plex"]
        if locked:
            Log.Info("MetadataWriter - Season %s posters: your picks are kept; only new ones added" % (", ".join(sorted(locked, key=lambda x: int(x)))))
        for season in sorted([x for x in leave if x not in locked], key=lambda x: int(x)):
            Log.Info("MetadataWriter - Season %s posters left as they are: %s" % (season, leave[season]))
        season_images = [image for image in season_images if image.get("season") not in leave or image.get("season") in locked]
        season_editor.queue_posters(getattr(media, "id", None), [x for x in numbers if x not in leave])
        keep_seasons = locked
    else:
        keep_seasons = None
    # Each image step on its own, so a failure here doesn't lose the whole update (seasons and episodes included)
    try:
        fill_images(season_images, settings.SERIES_IMAGES_PRIORITY, metadata.seasons, language, "season posters", settings.IMAGES_MAX, False, keep_seasons)
    except Exception:
        Log.Warn("MetadataWriter - Season posters skipped: %s" % (textutil.exception_text()))
    try:
        fill_themes(main.xpath("./Themes//Theme"), settings.SERIES_THEMES_PRIORITY, metadata.themes)
    except Exception:
        Log.Warn("MetadataWriter - Themes skipped: %s" % (textutil.exception_text()))
    started = add_time(timings, "images", started)

    episodes = select_episodes(root, first_season, media)
    for node, season, episode in episodes:
        plex_episode = local_episode(media, season, episode) if media is not None else None
        if plex_episode is not None:
            streams = node.find("./Streams")
            if streams is not None:
                node.remove(streams)                                    # Re-read with Plex's own season/episode numbers
            copy_streams(node, plex_episode)
    write_collections(main, metadata, episodes, priority["Collections"])
    rated = [node for node, season, episode in episodes if [x for x in node.xpath("./Rating/*[node()]") if x.tag.lower() in settings.EPISODE_PRIORITY["Rating"]]]
    Log.Info("MetadataWriter - Episode ratings: %s of %s episodes on disk have one (setting: %s)" % (
        len(rated), len(episodes), ",".join(settings.EPISODE_PRIORITY["Rating"]) or "off"))
    try:
        bundle.map_crew([node for node, season, episode in episodes], lazy)
    except Exception:
        Log.Warn("MetadataWriter - Episode writers/directors skipped: %s" % (textutil.exception_text()))
    started = add_time(timings, "crew", started)
    try:
        write_seasons(root, metadata, first_season, set([season for node, season, episode in episodes]), metadata.title, getattr(media, "id", None), main)
    except Exception:
        Log.Warn("MetadataWriter - Season titles/summaries skipped: %s" % (textutil.exception_text()))
    started = add_time(timings, "seasons", started)

    # Plex creates a season's / episode's record the first time it's asked for. On a show matched for the first time (Fix
    # Match) none exist yet, and creating them from several threads at once crashed Plex's model ("'NoneType' object has
    # no attribute '_core'"), losing those episodes. So they're created here, one at a time, before the parallel writes.
    targets = []
    for node, season, episode in episodes:
        try:
            targets.append((node, metadata.seasons[season].episodes[episode]))
        except Exception:
            Log.Warn("MetadataWriter - Episode S%sE%s skipped: Plex couldn't create its record (%s)" % (season, episode, textutil.exception_text()))

    @parallelize
    def write_episodes():
        for node, target in targets:
            @task
            def write_one(node=node, target=target, metadata=metadata):
                write_episode(node, target, metadata, lazy)
    add_time(timings, "episodes", started)


# Episode title clean-up ###############################################################################################################################################
EPISODE_PREFIX_RX = re.compile(u"^\\s*(?:episode|ep\\.?|#|\u7b2c)\\s*([0-9]+(?:\\.[0-9])?)\\s*\u8a71?\\s*[-:.)|\u2013\u2014\uff1a]+\\s*(.+)$", re.IGNORECASE | re.UNICODE)
NUMBER_PREFIX_RX = re.compile(u"^\\s*([0-9]{1,4})\\s*[-:.)|\u2013\u2014\uff1a]+\\s+(.+)$", re.UNICODE)
ROMAN_WORD = re.compile(r"^[IVX]+[,.:!?]?$")


def capitalise_word(word):
    """'BOY'S' -> 'Boy's', '"HELLO' -> '"Hello'; roman numerals ('II') stay as they are."""
    if ROMAN_WORD.match(word):
        return word
    for index in range(len(word)):
        if word[index].isalpha():
            return word[:index] + word[index].upper() + word[index + 1:].lower()
    return word


def clean_episode_title(title, numbers):
    """'Episode 5 - The Vow' / 'Ep. 5: The Vow' / '05 - The Vow' (when 5 is this episode's number) -> 'The Vow';
       an ALL-CAPS title -> Capitalised Words. Anything else is left as it is."""
    if not title:
        return title
    found = EPISODE_PREFIX_RX.match(title)
    if found and found.group(2).strip() and not is_bad_episode_title(found.group(2).strip()):
        title = found.group(2).strip()
    else:
        found = NUMBER_PREFIX_RX.match(title)
        if found and (found.group(1).lstrip("0") or "0") in numbers and found.group(2).strip():
            title = found.group(2).strip()
    letters = re.findall(r"[^\W\d_]", title, re.UNICODE)     # Not "for c in title": Plex's sandbox can't iterate over strings
    if len(letters) >= 4 and title.upper() == title and title.lower() != title:
        title = u" ".join([capitalise_word(word) for word in title.split(u" ")])
    return title


def episode_numbers(node):
    """This episode's numbers as written in titles: TVDB number, absolute numbers, AniDB number (no leading zeros)."""
    numbers = set([(node.get("num") or "").lstrip("0") or "0"])
    for found in node.xpath("./Absolute_Index/*[node()]") + node.xpath("./Mapped/anidb"):
        number = found.text if found.text else found.get("episode")
        if textutil.is_digits(number):
            numbers.add(str(number).lstrip("0") or "0")
    return numbers


def special_title(node, current, show_title):
    """A special (season 0) with no real title gets the title of the AniDB entry it comes from, in the preferred language:
       'Kizumonogatari Part 1: Tekketsu' for a one-episode entry, 'Entry - Episode 2' / 'Entry - Special 2' otherwise.
       Not for openings/endings, and not when the entry is the show itself (its own specials stay "Special 3")."""
    if node.getparent().get("num") != "0" or (current and not is_bad_episode_title(current)):
        return current
    mapped = node.find("./Mapped/anidb")
    if mapped is None or not textutil.is_digits(mapped.get("series")) or (mapped.get("episode") or "").upper().startswith("C"):
        return current
    record = sources.get_anidb(mapped.get("series"), False)
    if not record.valid or not record.title or textutil.clean_title(record.title) == textutil.clean_title(show_title or ""):
        return current
    siblings = node.getparent().xpath('./Episode/Mapped/anidb[@series="%s"][not(starts-with(@episode, "C"))]' % (mapped.get("series")))
    if len(siblings) <= 1:
        return textutil.safe_unicode(record.title)
    number = mapped.get("episode") or ""
    if number.upper().startswith("S"):
        return u"%s - Special %s" % (textutil.safe_unicode(record.title), number[1:])
    return u"%s - Episode %s" % (textutil.safe_unicode(record.title), number)


# Collections #################################################################################################################################################
LANGUAGE_COLLECTIONS = ("English Dubbed", "English Subbed")


def adult_level(main, metadata):
    """2 = explicit: an adult flag (AniDB "18 restricted" / "pornography", AniList isAdult) or an *official* adults-only
           rating (X, AO, R18+, 18+, NC-17 from TVDB);
       1 = mature: any source rates it 17+ (TV-MA, R, or AniDB's estimate from sex/violence tags);
       0 = neither. Every source counts, not only the rating shown, so TVDB's TV-MA can't hide AniDB's adult flag."""
    level = 0
    for element in series_values(main, "Content_Rating"):
        age = rating_age(element.text)
        if element.get("adult") == "1" or (age is not None and age >= 18 and element.get("estimate") != "1"):
            return 2
        if age is not None and age >= 17:
            level = 1
    age = rating_age(metadata.content_rating)
    if age is not None and age >= 17:
        level = max(level, 1)
    return level


# Content rating #############################################################################################################################################
# One age scale for US TV, US film and common other ratings, to compare sources ("strictest") and decide "mature"/"explicit"
RATING_AGES = {"tv-y": 0, "tv-g": 0, "g": 0, "all": 0, "0": 0, "0+": 0, "tv-y7": 7, "tv-y7-fv": 7, "7": 7, "7+": 7, "tv-pg": 10, "pg": 10,
               "6": 6, "6+": 6, "10": 10, "11": 11, "12": 12, "12+": 12, "pg-12": 12, "pg-13": 13, "13": 13, "13+": 13, "tv-14": 14, "14": 14,
               "14+": 14, "15": 15, "15+": 15, "r15+": 15, "m": 15, "16": 16, "16+": 16, "ma15+": 15, "tv-ma": 17, "r": 17, "17": 17, "17+": 17,
               "nc-17": 18, "18": 18, "18+": 18, "r18": 18, "r18+": 18, "r-18": 18, "ao": 18, "x": 18, "xxx": 18, "adults only": 18,
               "u": 0, "tous publics": 0, "12a": 12, "pg12": 12, "-10": 10, "-12": 12, "-16": 16, "-18": 18,
               "c": 0, "c8": 8, "8": 8, "8+": 8, "l": 0, "tp": 0, "t": 0, "9": 9, "9+": 9, "19": 18, "19+": 18}


# Plex country code -> (TVDB's country code, [(highest age covered, rating)], rating above those). A category covers the ages
# up to its limit, so an age-restricted rating is never converted to a less strict one ("TV-14" -> UK "15", Germany "16").
# Guidance ratings map to the country's usual equivalent: TV-PG -> Germany "6", TV-Y7 -> Germany "6" / Japan "G".
REGIONS = {
    "gb": ("gbr", [(0, "U"), (10, "PG"), (12, "12"), (15, "15")], "18"),
    "de": ("deu", [(0, "0"), (10, "6"), (12, "12"), (16, "16")], "18"),
    "fr": ("fra", [(0, "U"), (10, "10"), (12, "12"), (16, "16")], "18"),
    "jp": ("jpn", [(7, "G"), (12, "PG12"), (15, "R15+")], "R18+"),
    "ca": ("can", [(0, "G"), (8, "C8"), (10, "PG"), (14, "14+")], "18+"),
    "au": ("aus", [(0, "G"), (10, "PG"), (14, "M"), (15, "MA15+")], "R18+"),
    "br": ("bra", [(0, "L"), (10, "10"), (12, "12"), (14, "14"), (16, "16")], "18"),
    "es": ("esp", [(0, "TP"), (7, "7"), (12, "12"), (16, "16")], "18"),
    "it": ("ita", [(0, "T"), (6, "6+"), (14, "14+")], "18+"),
}


def rating_age(rating):
    """Minimum age of a content rating, or None if unknown. Plex's country prefix ("gb/15") is ignored."""
    return RATING_AGES.get(re.sub(r"^[a-z]{2}/", "", (rating or "").strip().lower()))


def strong_content(candidates):
    """For the TV-MA tie-breaker: True / False if AniDB's tags say the show has strong content (sex or violence at the
       minimum weight, a restricted tag, an adult flag: its estimate is TV-MA or X), None if AniDB has no estimate."""
    for candidate in candidates or []:
        if candidate.tag == "Anidb" and candidate.text and candidate.text != "None":
            if candidate.get("adult") == "1":
                return True
            age = rating_age(candidate.text)
            return age is not None and age >= 17
    return None


def tie_break(age, scale, top, record, candidates):
    """A 15-17 rating (TV-MA is 17+) where the country goes from a 14-16 category straight to 18: (lower or top, reason).
       1. TVDB's Japanese rating, if it has one (Japan also jumps from R15+ to R18+): R15+ or milder -> lower, R18+ -> top;
       2. else AniDB's tags (strong_content): no strong content -> lower, strong -> top;
       3. else top (cautious)."""
    lower = scale[-1][1]
    japanese = (getattr(record, "content_ratings", None) or {}).get("jpn") if record is not None else None
    japanese_age = rating_age(japanese) if japanese else None
    if japanese_age is not None:
        return (lower, "TVDB's Japanese rating %s" % (japanese)) if japanese_age < 18 else (top, "TVDB's Japanese rating %s" % (japanese))
    strong = strong_content(candidates)
    if strong is False:
        return lower, "AniDB's tags show no strong content"
    if strong:
        return top, "AniDB's tags show strong content"
    return top, "no Japanese rating or AniDB tags to go by"


US_RATINGS = ("tv-y", "tv-y7", "tv-y7-fv", "tv-g", "tv-pg", "tv-14", "tv-ma", "g", "pg", "pg-13", "r", "nc-17")
US_SCALE = [(0, "TV-G"), (7, "TV-Y7"), (10, "TV-PG"), (14, "TV-14")]


def us_rating(rating):
    """US (the default): US TV and film ratings unchanged. Another country's rating is converted by age: TVDB gives its
       first country's rating when it has no US one, which would otherwise show as e.g. Australia's "MA15+" or a bare "16"."""
    if rating.strip().lower() in US_RATINGS:
        return rating
    age = rating_age(rating)
    if age is None:
        return rating
    result = "TV-MA"
    for limit, name in US_SCALE:
        if age <= limit:
            result = name
            break
    Log.Info("MetadataWriter - Content rating for US: %s (converted from %s, age %s)" % (result, rating, age))
    return result


def regional_rating(rating, series_id=None, candidates=None):
    """The content rating for settings.CONTENT_RATING_COUNTRY, in Plex's form ("gb/15"):
       the official rating there if TVDB has one (not for adult shows: those stay at the top rating), else the chosen
       rating converted by age. "us": US ratings unchanged, others converted (us_rating). candidates: the sources' Content_Rating
       values, for the TV-MA tie-breaker (tie_break)."""
    country = settings.CONTENT_RATING_COUNTRY
    if country == "us" and rating:
        return us_rating(rating)
    if country not in REGIONS or not rating:
        return rating
    tvdb_country, scale, top = REGIONS[country]
    age = rating_age(rating)
    official = None
    record = None
    if textutil.is_digits(series_id) and (age is None or age < 18):
        try:
            record = sources.get_tvdb(series_id)
            record = record if record.valid else None
            official = (getattr(record, "content_ratings", None) or {}).get(tvdb_country) if record is not None else None
        except Exception:
            official = None
    if official:
        result = u"%s/%s" % (country, official.lstrip("-").strip())
        Log.Info("MetadataWriter - Content rating for %s: %s (TVDB's official rating there; chosen rating %s)" % (country.upper(), result, rating))
        return result
    if age is None:
        Log.Info("MetadataWriter - Content rating for %s: '%s' kept (unknown age, can't convert)" % (country.upper(), rating))
        return rating
    result = None
    for limit, name in scale:
        if age <= limit:
            result = name
            break
    if result is None and 15 <= age < 18 and scale[-1][0] >= 14:
        result, reason = tie_break(age, scale, top, record, candidates)
        result = u"%s/%s" % (country, result)
        Log.Info("MetadataWriter - Content rating for %s: %s (converted from %s, age %s; %s)" % (country.upper(), result, rating, age, reason))
        return result
    result = u"%s/%s" % (country, result or top)
    Log.Info("MetadataWriter - Content rating for %s: %s (converted from %s, age %s)" % (country.upper(), result, rating, age))
    return result


def choose_content_rating(candidates, priority):
    """Content rating when sources disagree (setting ContentRatingRule). Only sources allowed by "Series: Content rating" take part.
       An adult flag (AniDB's "18 restricted" / "pornography" tags, AniList's isAdult) always wins: X.
       official (default): the first official rating in source order (TVDB's broadcast rating; AniDB's is only an estimate from
                 its tags and is used when there's no official one);
       strictest: the highest age of all sources (source order breaks ties);
       order:     the first source in order."""
    allowed = sorted([c for c in candidates if c.text and c.text != "None" and c.tag.lower() in priority], key=lambda c: provider_rank(priority, c.tag))
    chosen = None
    adult = [c for c in allowed if c.get("adult") == "1"]
    if adult:
        chosen = adult[0]
    elif allowed and settings.CONTENT_RATING_RULE == "strictest":
        known = [c for c in allowed if rating_age(c.text) is not None]
        chosen = sorted(known, key=lambda c: -rating_age(c.text))[0] if known else allowed[0]
    elif allowed and settings.CONTENT_RATING_RULE == "official":
        official = [c for c in allowed if c.get("estimate") != "1"]
        chosen = official[0] if official else allowed[0]
    elif allowed:
        chosen = allowed[0]
    Log.Info("MetadataWriter - Content rating: %s (%s; rule: %s)" % (
        chosen.text if chosen is not None else None,
        ", ".join(["%s %s%s" % (c.tag, c.text, " [adult flag]" if c.get("adult") == "1" else " [estimate]" if c.get("estimate") == "1" else "")
                   for c in candidates if c.text]) or "no source has one", settings.CONTENT_RATING_RULE))
    return textutil.safe_unicode(chosen.text) if chosen is not None else None


def write_collections(main, metadata, episodes, priority):
    """Collections from the sources, plus "English Dubbed" (an episode on disk has English audio) and "English Subbed"
       (Japanese audio with English subtitles). Rebuilt on every update, so a show that no longer qualifies leaves them.
       Setting CollectionsExclude can leave adult shows out of the two language collections."""
    values = by_priority(series_values(main, "Collections"), priority, list) or []
    dubbed = 0
    subbed = 0
    audio_seen = []
    subtitles_seen = []
    for node, season, episode in episodes:
        audio = [s.get("lang") for s in node.xpath('./Streams/Stream[@type="audio"]')]
        subtitles = [s.get("lang") for s in node.xpath('./Streams/Stream[@type="subtitle"]')]
        for language in audio:
            if language not in audio_seen:
                audio_seen.append(language)
        for language in subtitles:
            if language not in subtitles_seen:
                subtitles_seen.append(language)
        if "eng" in audio:
            dubbed = dubbed + 1
        if "jpn" in audio and "eng" in subtitles:
            subbed = subbed + 1
    level = adult_level(main, metadata)
    excluded = (settings.COLLECTIONS_EXCLUDE == "explicit" and level == 2) or (settings.COLLECTIONS_EXCLUDE == "mature" and level >= 1)
    wanted = [v for v in values if v and v not in LANGUAGE_COLLECTIONS]
    if dubbed and not excluded:
        wanted.append("English Dubbed")
    if subbed and not excluded:
        wanted.append("English Subbed")
    metadata.collections.clear()
    for value in wanted:
        metadata.collections.add(value)
    Log.Info("MetadataWriter - Language collections: English Dubbed %s (%s episodes), English Subbed %s (%s episodes)%s; audio seen: %s; subtitles seen: %s"
             % ("yes" if dubbed and not excluded else "no", dubbed, "yes" if subbed and not excluded else "no", subbed,
                " - left out: %s show (setting)" % ("explicit" if level == 2 else "mature") if excluded and (dubbed or subbed) else "",
                ", ".join([a or "unknown" for a in audio_seen]) or "none", ", ".join([s or "unknown" for s in subtitles_seen]) or "none"))


def write_episode(node, target, metadata, lazy=None):
    priority = settings.EPISODE_PRIORITY
    title = title_text(node.xpath("./Title/*[node()]"), priority["Title"], settings.EPISODE_LANGUAGE_PRIORITY, True)
    try:
        title = special_title(node, title, metadata.title)
    except Exception:
        Log.Debug("MetadataWriter - Special title failed: %s" % (textutil.exception_text()))
    target.title = clean_episode_title(title, episode_numbers(node))
    target.summary = text(node.xpath("./Summary/*[node()]"), priority["Summary"])
    target.originally_available_at = date(node.xpath("./Originally_Available_At/*[node()]"), priority["Originally_Available_At"])
    target.rating = number(node.xpath("./Rating/*[node()]"), priority["Rating"], float)
    target.absolute_index = number(node.xpath("./Absolute_Index/*[node()]"), priority["Absolute_Index"], int)
    fill_people(node.xpath("./Writers/*[node()]"), priority["Writers"], target.writers)
    fill_people(node.xpath("./Directors/*[node()]"), priority["Directors"], target.directors)
    fill_people(node.xpath("./Producers/*[node()]"), priority["Producers"], target.producers)
    fill_images(node.xpath("./Thumbs//Image"), priority["Thumbs"], target.thumbs, None, "thumbs", 0, True, None, lazy)
