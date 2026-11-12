"""Choosing among one list of images (show posters, backgrounds, banners; season posters per season; an episode's
thumbnails) with what image_match learns from looking at them. Called by metadata_writer.fill_images after the images
are in priority order. Each step logs what it did, so it can be checked before relying on it.

  * Blank images (setting "Duplicate artwork"): nearly one shade all over (an all-black episode image, a grey
    placeholder) - left out ("Remove duplicates"). An episode thumbnail is only checked when
    another site has one for that episode.
  * Duplicates (same setting): the same picture from several sites. The largest copy is kept (sizes: TVDB lists them),
    in the place of the best-ranked one. Language and text flag pass between the copies, so an AniList or AniDB copy of
    a TVDB image counts as what TVDB says it is.
  * Text (setting "Language and text", textless first): where two versions of one artwork differ in text, the one with
    less text moves up. An image found to have more text than a TVDB textless copy is marked as having text.
  * Languages (same setting, "... only" options): images in other languages left out, keeping at least one.
  The image checks run when duplicates, an "... only" option or poster sets are on (each image is looked at once).
"""
import image_match
import settings
import textutil

KINDS = {"library": "your library's language", "textless": "textless", "other": "another language",
         "text": "text in an unknown language", "unknown": "language unknown"}


def wanted():
    """Whether images are looked at at all (each look is a request to Plex the first time)."""
    return (getattr(settings, "IMAGE_DUPLICATES", "off") != "off" or getattr(settings, "IMAGE_LANGUAGES", "all") != "all"
            or getattr(settings, "PREFER_POSTER_SETS", False))


def group_of(image):
    return image.get("season") if image.getparent().getparent().tag == "Season" else ""


def area(image):
    """Pixels, where the site says (TVDB); 0 when unknown."""
    try:
        return int(image.get("width") or 0) * int(image.get("height") or 0)
    except ValueError:
        return 0


def text_state(image):
    """"0" textless, "1" has text, "" unknown. TVDB: its includesText flag; a TVDB image with no flag and no language
       counts as textless (TVDB's convention for textless artwork)."""
    text = image.get("text") or ""
    if text in ("0", "1"):
        return text
    if image.getparent().tag == "Tvdb" and not image.get("lang"):
        return "0"
    return ""


def language_class(image, library):
    language = image.get("lang") or ""
    if library and language == library:
        return "library"
    if text_state(image) == "0":
        return "textless"
    if language:
        return "other"
    if text_state(image) == "1":
        return "text"
    return "unknown"


LEARNED = {}                       # Image address -> {"lang": .., "text": ..} learned from a copy or a comparison, so an image
                                   # in another list of the same show (season posters after show posters) knows it too
LEARNED_MOST = 20000


def share(target, source):
    """Copies of one picture: whatever one knows about language and text, the other gets."""
    for name in ("lang", "text"):
        if source.get(name) and not target.get(name):
            target.set(name, source.get(name))
            target.set("learned", "1")
            remember_learned(target, name)


def remember_learned(image, name):
    url = image.get("mainUrl")
    if not url:
        return
    if len(LEARNED) > LEARNED_MOST:
        LEARNED.clear()
    facts = LEARNED.get(url) or {}
    facts[name] = image.get(name)
    LEARNED[url] = facts


def recall_learned(images):
    """Language and text flags learned for these images in an earlier list (or update); True if any were applied."""
    applied = False
    for image in images:
        facts = LEARNED.get(image.get("mainUrl") or "")
        if not facts:
            continue
        for name in ("lang", "text"):
            if facts.get(name) and not image.get(name):
                image.set(name, facts[name])
                image.set("learned", "1")
                applied = True
    return applied


def name_of(image):
    """Short name for the log: site and file ("Tvdb 6344b8cb0bd14.jpg")."""
    return "%s %s" % (image.getparent().tag, (image.get("mainUrl") or image.get("thumbUrl") or "?").split("/")[-1])


def fingerprints(images, tasks, limit):
    """{id(image): value} for the images that have one; the rest are worked out now (tasks None) or queued.
       limit: only the best this many per group are looked at, unless images can be left out by language (then all)."""
    values = {}
    shown = {}
    for image in images:
        group = group_of(image)
        if limit and getattr(settings, "IMAGE_LANGUAGES", "all") == "all" and shown.get(group, 0) >= limit:
            continue
        shown[group] = shown.get(group, 0) + 1
        url = image.get("thumbUrl") or image.get("mainUrl")
        value, known = image_match.cached(url)
        if not known:
            if tasks is not None:
                task = "print|%s" % (url)
                if task not in tasks:
                    tasks.append(task)
            else:
                value = image_match.work_out(url) or value
        if value is not None:
            values[id(image)] = value
    return values


def choose(images, label, tasks=None, limit=0, language=None, resort=None):
    """images: one list in priority order. Returns the list to use, renumbered. resort(images): the writer's ordering
       again (after language and text flags were learned). Never raises: on a failure the list is returned unchanged."""
    if not images or not wanted():
        return images
    try:
        return choose_now(images, label, tasks, limit, language, resort)
    except Exception:
        Log.Warn("Images - %s: checking the images failed, so they were used as they are: %s" % (label, textutil.exception_text()))
        return images


def choose_now(images, label, tasks, limit, language, resort):
    mode = getattr(settings, "IMAGE_DUPLICATES", "off")
    thumbs = label == "thumbs"
    if thumbs and (mode == "off" or len(images) < 2):
        return images
    if not thumbs:
        recall_learned(images)
    values = fingerprints(images[:1] if thumbs else images, tasks, limit)
    library = textutil.short_language(language) if language else ""
    groups = {}
    order = []
    for image in images:
        group = group_of(image)
        if group not in groups:
            groups[group] = []
            order.append(group)
        groups[group].append(image)
    blanks = []
    copies = []
    alike = []
    result = []
    for group in order:
        members = groups[group]
        if thumbs:
            first = values.get(id(members[0]))
            if first is not None and image_match.is_blank(first[2]):
                blanks.append(members[0])
                members = members[1:]
            result.extend(members)
            continue
        kept = []
        for image in members:
            value = values.get(id(image))
            if value is not None and mode != "off" and image_match.is_blank(value[2]):
                blanks.append(image)
                continue
            match = None
            if value is not None:
                for position in range(len(kept)):
                    other_value, other = kept[position]
                    how = image_match.same_artwork(value, other_value)
                    if how == "duplicate" and match is None:
                        match = position
                    elif how == "alike":
                        side = image_match.text_side(value, other_value)
                        if side:
                            alike.append((image, other, side))
            if match is not None:
                other_value, other = kept[match]
                share(image, other)                       # Known either way: used by the language and text settings too
                share(other, image)
            if match is not None and mode != "off":
                bigger = area(image) > area(other)
                copies.append((image, other, bigger))
                if bigger:                                # The larger copy takes the better-ranked one's place
                    result[result.index(other)] = image
                    kept[match] = (value, image)
                continue
            if value is not None:
                kept.append((value, image))
            result.append(image)
    learned_text = []
    for image, other, side in alike:
        textful, clean = (image, other) if side == 1 else (other, image)
        if text_state(clean) == "0" and not text_state(textful):
            textful.set("text", "1")
            remember_learned(textful, "text")
            learned_text.append((textful, clean))
    summary = []
    log_checks(label, blanks, copies, learned_text, summary)
    if resort is not None and [image for image in result if image.get("learned") or image in [x[0] for x in learned_text]]:
        result = resort(result)
    result = by_language(result, label, library, summary)
    result = by_text(result, label, alike, summary)
    if summary:
        Log.Info("Images - %s: %s" % (label, "; ".join(summary)))
    numbers = {}
    for image in result:
        group = group_of(image)
        numbers[group] = numbers.get(group, 0) + 1
        image.set("id", str(numbers[group]))
    return result


def log_checks(label, blanks, copies, learned_text, summary):
    """What was found: a short summary (one Info line per list, see choose_now) and the details at Debug."""
    if blanks:
        summary.append("%s blank left out" % (len(blanks)))
        Log.Debug("Images - %s, blank: %s" % (label, ", ".join([name_of(image) for image in blanks])))
    if copies:
        summary.append("%s duplicate%s left out" % (len(copies), "" if len(copies) == 1 else "s"))
        Log.Debug("Images - %s, duplicates: %s" % (label, "; ".join(["%s = %s%s" % (name_of(image), name_of(other), " (larger, kept in its place)" if bigger else "")
                                                                     for image, other, bigger in copies])))
    if learned_text:
        summary.append("%s found to have text" % (len(learned_text)))
        Log.Debug("Images - %s, more text than TVDB's textless copy: %s" % (label, "; ".join(["%s (vs %s)" % (name_of(textful), name_of(clean)) for textful, clean in learned_text])))


def by_language(images, label, library, summary=None):
    """Setting "Language and text", its "... only" options. Per group (season posters: per season); never left empty."""
    rule = getattr(settings, "IMAGE_LANGUAGES", "all")
    if rule == "all" or not images:
        return images
    groups = {}
    order = []
    for image in images:
        group = group_of(image)
        if group not in groups:
            groups[group] = []
            order.append(group)
        groups[group].append(image)
    result = []
    dropped = {}
    fallbacks = []
    for group in order:
        members = groups[group]
        kinds = [language_class(image, library) for image in members]
        if rule == "library_textless":
            keep = [image for image, kind in zip_lists(members, kinds) if kind != "other"]
        else:
            keep = [image for image, kind in zip_lists(members, kinds) if kind == "textless"]
        if not keep:
            keep = members[:1]                            # Never nothing: the best one by the usual order
            fallbacks.append((group, members[0], kinds[0]))
        for image, kind in zip_lists(members, kinds):
            if image not in keep:
                dropped[kind] = dropped.get(kind, 0) + 1
        result.extend(keep)
    notes = summary if summary is not None else []
    if dropped:
        notes.append("%s left out by language (%s)" % (len(images) - len(result), ", ".join(["%s: %s" % (KINDS[kind], dropped[kind]) for kind in sorted(dropped)])))
    if fallbacks:
        notes.append("no %s image%s, so the best kept%s" % ("textless" if rule == "textless" else "suitable", "" if len(fallbacks) == 1 else "s",
                     (" in season %s" % (", ".join([group for group, image, kind in fallbacks]))) if fallbacks[0][0] else ""))
        Log.Debug("Images - %s, kept with nothing suitable: %s" % (label, "; ".join(["%s (%s)" % (name_of(image), KINDS[kind]) for group, image, kind in fallbacks])))
    if summary is None and notes:
        Log.Info("Images - %s: %s" % (label, "; ".join(notes)))
    return result


def zip_lists(one, two):
    return [(one[index], two[index]) for index in range(min(len(one), len(two)))]


def by_text(images, label, alike, summary=None):
    """Setting "Language and text", textless first: within each artwork found in several versions, the one with less text
       moves up; other images keep their places. ("titled" is still understood: more text first.)"""
    rule = getattr(settings, "IMAGE_TEXT_ORDER", "keep")
    if rule == "keep" or not alike:
        return images
    present = [image for image, other, side in alike if image in images and other in images]
    if not present:
        return images
    leader = {}
    def find(image):
        key = id(image)
        while leader.get(key, key) != key:
            key = leader[key]
        return key
    score = {}
    for image, other, side in alike:
        if image not in images or other not in images:
            continue
        textful, clean = (image, other) if side == 1 else (other, image)
        score[id(textful)] = score.get(id(textful), 0) + 1
        score[id(clean)] = score.get(id(clean), 0) - 1
        leader[find(textful)] = find(clean)
    clusters = {}
    for image in images:
        if id(image) in score:
            clusters.setdefault(find(image), []).append(image)
    result = list(images)
    moved = []
    for members in clusters.values():
        if len(members) < 2 or len(set([group_of(image) for image in members])) > 1:
            continue
        places = sorted([result.index(image) for image in members])
        ranked = sorted(members, key=lambda image: (score[id(image)] if rule == "textless" else -score[id(image)], result.index(image)))
        if ranked != [result[place] for place in places]:
            moved.append(ranked[0])
        for place, image in zip_lists(places, ranked):
            result[place] = image
    if moved:
        note = "%s %s version%s moved first" % (len(moved), "textless" if rule == "textless" else "titled", "" if len(moved) == 1 else "s")
        if summary is not None:
            summary.append(note)
        else:
            Log.Info("Images - %s: %s" % (label, note))
        Log.Debug("Images - %s, moved first: %s" % (label, ", ".join([name_of(image) for image in moved])))
    return result
