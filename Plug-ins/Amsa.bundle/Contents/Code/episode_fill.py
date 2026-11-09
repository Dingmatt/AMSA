"""Fill gaps in the episodes on disk from MyAnimeList, Kitsu and AnimeThemes (settings EpisodeFallback / CreditTitles).

Runs after the bundle is built and before it is written, and only asks the extra sources about AniDB entries that have
a gap among the episodes on disk, so complete shows cost nothing:
  * a regular episode gap: no real title in the first episode language (e.g. only romaji or "Episode 7" when English is
    first), or no summary -> MyAnimeList (titles, air dates) and Kitsu (titles, summaries, air dates) for its AniDB entry;
  * a credit gap: an opening/ending special (S00E101+ / S00E151+) whose only title is generic ("Opening 2")
    -> AnimeThemes (song title and artists).
The extra values are added to the bundle as their own sources ("Mal", "Kitsu", "Animethemes"), which settings.py appends
after the user's chosen sources, so they only show where the chosen sources have nothing better.
If a gap remains although the cached answer was used (e.g. a new episode), the answer is downloaded again when it is
older than 6 hours (at most once per 6 hours per entry).
"""
import os

import settings
import textutil
import downloader
import sources
import bundle
import metadata_writer
import refresher

FILL_AGAIN_AFTER = 6 * 3600
PROVIDER_DIRECTORIES = {"Mal": "MAL", "Kitsu": "Kitsu", "Animethemes": "AnimeThemes"}


def real_titles(node):
    return [t for t in node.xpath("./Title/*[node()]") if t.text and not metadata_writer.is_bad_episode_title(t.text)]


def title_gap(node):
    """No real title in the first episode language."""
    first = settings.EPISODE_LANGUAGE_PRIORITY[0] if settings.EPISODE_LANGUAGE_PRIORITY else None
    titles = real_titles(node)
    return not (len([t for t in titles if t.get("lang") == first]) > 0 if first else len(titles) > 0)


def regular_gap(node):
    """No real title in the first episode language, or no summary."""
    return title_gap(node) or len(node.xpath("./Summary/*[node()]")) == 0


def open_for(provider, node):
    """Is there still something this provider could fill? (MAL has no summaries; AnimeThemes only names credits.)"""
    if provider == "Animethemes":
        return credit_gap(node)
    if provider == "Mal":
        return title_gap(node)
    return regular_gap(node)


def credit_gap(node):
    if not node.xpath("./Mapped/anidb[starts-with(@episode, 'C')]"):
        return False
    return len(real_titles(node)) == 0


def anidb_ids(nodes, credits):
    found = []
    for node in nodes:
        for mapped in node.xpath("./Mapped/anidb"):
            series = mapped.get("series")
            is_credit = (mapped.get("episode") or "").startswith("C")
            if textutil.is_digits(series) and is_credit == credits and series not in found:
                found.append(series)
    return found


def gaps(root, anidb_id, tvdb_id, media):
    """(regular gap nodes, credit gap nodes) among the episodes on disk."""
    main = metadata_writer.main_season(root, anidb_id, tvdb_id)
    if main is None or media is None:
        return [], []
    episodes = metadata_writer.select_episodes(root, int(main.get("num")), media, True)
    regular = []
    credits = []
    for node, season, episode in episodes:
        if season == "0":
            if settings.CREDIT_TITLES and credit_gap(node):
                credits.append(node)
        elif settings.EPISODE_FILL and regular_gap(node):
            regular.append(node)
    return regular, credits


def load(provider, series_id, nodes, root):
    """Add one provider's values for one AniDB entry. If the cached answer left a gap open and the entry is still airing
       (a new episode may be missing from it), download it again, at most once per 6 hours."""
    nodes = [n for n in nodes if open_for(provider, n)]
    if not nodes:
        return 0
    record = sources.get(provider, series_id)
    added = bundle.apply_episode_values(root, provider, series_id, record, nodes)
    still_open = [n for n in nodes if open_for(provider, n)]
    if not still_open or not refresher.is_airing(series_id):
        return added
    directory = os.path.join(PROVIDER_DIRECTORIES[provider], str(series_id))
    newest = None
    try:
        for name in os.listdir(os.path.join(settings.CACHE_PATH, directory)):
            age = downloader.cache_age_of(name, directory)
            if age is not None and (newest is None or age < newest):
                newest = age
    except Exception:
        newest = None
    if newest is None or newest < FILL_AGAIN_AFTER or not refresher.may_try("%s-%s" % (provider.lower(), series_id), FILL_AGAIN_AFTER):
        return added
    downloader.force_refresh(directory)
    try:
        sources.forget(provider, series_id)
        record = sources.get(provider, series_id)
    finally:
        downloader.end_refresh(directory)
    return added + bundle.apply_episode_values(root, provider, series_id, record, still_open)


def fill(root, anidb_id, tvdb_id, media):
    """Fill the gaps; returns a short summary for the log, or None if there was nothing to do."""
    if not settings.EPISODE_FILL and not settings.CREDIT_TITLES:
        return None
    regular, credits = gaps(root, anidb_id, tvdb_id, media)
    if not regular and not credits:
        return None
    counts = {}
    jobs = []
    for series_id in anidb_ids(regular, False):
        nodes = [n for n in regular if n.xpath('./Mapped/anidb[@series="%s"]' % (series_id))]
        for source in settings.FALLBACK_ORDER:              # Setting EpisodeFallback: which, in which order
            jobs.append(({"mal": "Mal", "kitsu": "Kitsu"}[source], series_id, nodes))
    for series_id in anidb_ids(credits, True):
        nodes = [n for n in credits if n.xpath('./Mapped/anidb[@series="%s"]' % (series_id))]
        jobs.append(("Animethemes", series_id, nodes))
    for provider, series_id, nodes in jobs:
        try:
            counts[provider] = counts.get(provider, 0) + load(provider, series_id, nodes, root)
        except Exception:
            Log.Warn("EpisodeFill - %s for AniDB '%s' failed: %s" % (provider, series_id, textutil.exception_text()))
    left = len([n for n in regular if regular_gap(n)]) + len([n for n in credits if credit_gap(n)])
    summary = "%s episodes and %s openings/endings had gaps; values added: MyAnimeList %s, Kitsu %s, AnimeThemes %s; %s still without" % (
        len(regular), len(credits), counts.get("Mal", 0), counts.get("Kitsu", 0), counts.get("Animethemes", 0), left)
    Log.Info("EpisodeFill - " + summary)
    return summary
