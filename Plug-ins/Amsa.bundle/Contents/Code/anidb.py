"""AniDB source: one anime from AniDB's HTTP API (requests go through anidb_limiter via downloader)."""
import os
import re
import copy
import time

from lxml import etree

import settings
import textutil
import models
import downloader
import anime_lists
from textutil import element_text

RESTRICTED_TAGS = {"18 restricted": "X", "pornography": "X", "borderline porn": "TV-MA", "tv censoring": "TV-MA"}   # AniDB tag -> content rating (from HAMA)
ADULT_TAGS = ("18 restricted", "pornography")          # AniDB's own adult flags: X is a fact, not an estimate


def episode_number(season, episode):
    """AniDB episode number for a (season, number) pair: regular episodes are plain numbers, specials are 'S<n>'."""
    if season >= 1:
        return str(episode)
    if season == 0:
        return "S" + str(episode)


EPISODE_PREFIXES = {1: "", 2: "S", 3: "C", 4: "T", 5: "P", 6: "O"}   # AniDB epno types: regular, special, credit, trailer, parody, other


def episode_number_by_type(episode_type, episode):
    if episode_type in EPISODE_PREFIXES:
        return EPISODE_PREFIXES[episode_type] + str(episode)


def credit_tvdb_number(episode):
    """Where opening/ending credits are placed in Plex: season 0, episode 101+ (OP) / 151+ (ED)."""
    return "S00E" + str(episode)


def clean_description(text):
    """AniDB description markup -> plain text (see textutil.clean_summary)."""
    return textutil.clean_summary(text)


def cache_age(anidb_id):
    """How long a cached AniDB entry stays fresh, from the end date in the cached copy (idea from HAMA): 2 days while airing
       or within 30 days of ending, then one day per 5 days since it ended, up to a year for shows that ended 5+ years ago."""
    try:
        cached = Data.Load(downloader.cache_path(anidb_id + ".xml", os.path.join("AniDB", anidb_id))) if Data.Exists(downloader.cache_path(anidb_id + ".xml", os.path.join("AniDB", anidb_id))) else None
    except Exception:
        cached = None
    if cached is not None and not isinstance(cached, basestring):
        cached = cached.decode("utf-8", "replace")
    found = re.search(r"<enddate>([0-9]{4})(?:-([0-9]{2}))?(?:-([0-9]{2}))?</enddate>", cached or "")
    if not found:
        return settings.DEFAULT_CACHE
    try:
        ended = time.mktime((int(found.group(1)), int(found.group(2) or 12), int(found.group(3) or 28), 0, 0, 0, 0, 0, -1))
    except Exception:
        return settings.DEFAULT_CACHE
    days_ago = (time.time() - ended) / 86400
    if days_ago <= 30:
        return settings.DEFAULT_CACHE
    age = days_ago / 5 * 86400
    if age > settings.ANIDB_CACHE_ENDED_MAX:
        age = settings.ANIDB_CACHE_ENDED_MAX
    return int(max(settings.DEFAULT_CACHE, age))


def original_title(titles, language):
    """Title in the chosen original-title language: the main title for romaji (x-jat), otherwise the official title."""
    if not language or language == "off":
        return None
    for title in titles:
        if title.get(textutil.XML_LANG) == language and title.get("type") in ("main", "official") and title.text:
            return textutil.clean_text(title.text)
    return None


def mapping_studio(anidb_id):
    try:
        for entry in anime_lists.mapping_entries("anidb", anidb_id):
            studio = entry.find("./supplemental-info/studio")
            if studio is not None and studio.text and studio.text.strip():
                return studio.text.strip()
    except Exception:
        pass
    return None


class AniDBSeries(models.Series):
    def __init__(self, anidb_id, network=True):
        models.Series.__init__(self, anidb_id, "Anidb")
        anidb_id = self.id
        max_age = cache_age(anidb_id)
        xml = downloader.xml_from_url(settings.ANIDB_API_URL + anidb_id, anidb_id + ".xml", os.path.join("AniDB", anidb_id), max_age, network=network)
        found = xml.xpath("/anime") if xml is not None else []
        if not found:
            if network:
                Log.Error("AniDB - No data for AniDB id '%s'" % (anidb_id))
            else:
                Log.Debug("AniDB - AniDB '%s' not cached yet (cache-only lookup)" % (anidb_id))
            return
        data = found[0]
        self.valid = True
        self.type = element_text(data, "type")

        if data.xpath("./titles"):
            title, self.title_lang, self.title_main = textutil.preferred_title_info(data.xpath("./titles/title"))
            self.title = textutil.clean_text(title)
            self.original_title = original_title(data.xpath("./titles/title"), settings.ORIGINAL_TITLE_LANGUAGE)

        if element_text(data, "description"):
            self.summary = clean_description(element_text(data, "description"))

        if element_text(data, "startdate"):
            self.originally_available_at = element_text(data, "startdate")
        self.end_date = element_text(data, "enddate")
        mal = data.xpath('./resources/resource[@type="2"]/externalentity/identifier')
        if mal and mal[0].text and mal[0].text.strip().isdigit():
            self.mal_id = mal[0].text.strip()

        ratings = []
        votes = []
        for path in ("ratings/permanent", "ratings/temporary"):
            try:
                ratings.append(float(element_text(data, path)))
            except ValueError:
                continue
            node = data.find(path)
            count = node.get("count") if node is not None else None
            if count and count.isdigit():
                votes.append(int(count))
        if votes:
            self.rating_votes = max(votes)                 # Permanent and temporary votes overlap; the larger count
        if ratings:
            self.rating = (ratings[0] + ratings[-1]) / 2   # Average of permanent/temporary (sum() is not available in Plex's sandbox)

        for creator in data.xpath('./creators/name[@type="Animation Work"]'):
            self.studio = creator.text
        if not self.studio:
            for creator in data.xpath('./creators/name[@type="Work"]'):
                self.studio = creator.text
        if not self.studio:
            self.studio = mapping_studio(anidb_id)          # The Anime-Lists file names studios AniDB doesn't have

        self.parse_countries(data)

        lengths = [int(element_text(episode, "length")) for episode in data.xpath('./episodes/episode/epno[@type="1"]/..') if (element_text(episode, "length") or "").isdigit()]
        if lengths:
            total = 0
            for length in lengths:
                total = total + length
            self.duration = int(total * 60000 / len(lengths))   # Plex: one episode's length in milliseconds

        for element in data.xpath('./tags/tag/name[text()="elements"]/..'):
            for genre in data.xpath('./tags/tag[@parentid="%s" and @weight>="%s"]/name' % (element.get("id"), settings.ANIDB_MINIMUM_WEIGHT)):
                self.genres = (self.genres or []) + [textutil.safe_unicode(genre.text).title()]

        for tag in data.xpath('./tags/tag[@infobox="true"]/name'):
            self.tags = (self.tags or []) + [textutil.safe_unicode(tag.text).title()]

        for related in data.xpath('./relatedanime/anime[(@type="Prequel") or (@type="Sequel")]'):
            self.collections = (self.collections or []) + [related.text]

        self.parse_content_rating(data)

        for writer in data.xpath('./creators/name[(@type="Original Work") or (@type="Script") or (@type="Screenplay")]'):
            self.writers = (self.writers or []) + [writer.text]
        for director in data.xpath('./creators/name[@type="Direction"]'):
            self.directors = (self.directors or []) + [director.text]
        for producer in data.xpath('./creators/name[@type="Series Composition"]'):
            self.producers = (self.producers or []) + [producer.text]

        self.parse_roles(data)

        if element_text(data, "picture"):
            picture = element_text(data, "picture")
            season = models.new_images()
            models.add_image(season, settings.ANIDB_PIC_BASE_URL + picture, settings.ANIDB_IMAGE_DOMAIN, os.path.join("AniDB", anidb_id, "season"),
                             settings.ANIDB_PIC_THUMB_URL % os.path.splitext(picture)[0], {"id": "1", "season": "1"})
            self.season = season
            self.posters = copy.deepcopy(season)

        if element_text(data, "resources"):
            self.links = self.parse_links(data)

        try:
            self.episode_count = int(element_text(data, "episodecount", "0"))
        except ValueError:
            self.episode_count = 0
        self.special_count = len(data.xpath('./episodes/episode/epno[@type="2"]'))

        for credit in data.xpath('./episodes/episode/epno[@type="3"]/..'):
            # AniDB names credits "Opening 1" / "Ending 1" (English titles); check every title so the language settings don't matter
            credit_titles = [textutil.clean_title(title.text) for title in credit.xpath("./title") if title.text]
            if [t for t in credit_titles if t.startswith("opening")]:
                self.op_list.append(str(element_text(credit, "epno")))
            elif [t for t in credit_titles if t.startswith("ending")]:
                self.ed_list.append(str(element_text(credit, "epno")))

        for item in data.xpath("./episodes/episode"):
            try:
                self.episodes.append(AniDBEpisode(item))
            except Exception as e:
                Log.Debug("AniDB - Skipping malformed episode in '%s': %s" % (anidb_id, e))

        # AniDB lists staff per anime, not per episode: offer them for its episodes and specials (a fallback for TVDB's per-episode crew)
        for episode in self.episodes:
            if episode.kind in ("1", "2"):
                episode.writers = self.writers
                episode.directors = self.directors
                episode.producers = self.producers

    def parse_countries(self, data):
        # AniDB tag tree: setting > place > planet > continent > country
        for setting_tag in data.xpath('./tags/tag/name[text()="setting"]/..'):
            for place in data.xpath('./tags/tag[@parentid="%s"]' % (setting_tag.get("id"))):
                for planet in data.xpath('./tags/tag[@parentid="%s"]' % (place.get("id"))):
                    for continent in data.xpath('./tags/tag[@parentid="%s"]' % (planet.get("id"))):
                        for country in data.xpath('./tags/tag[@parentid="%s" and @weight>="%s"]/name' % (continent.get("id"), settings.ANIDB_MINIMUM_WEIGHT)):
                            self.countries = (self.countries or []) + [country.text]

    def parse_content_rating(self, data):
        """AniDB has no age ratings, so this is an estimate from its content tags (marked as such for metadata_writer):
           no indicator -> TV-PG, nudity -> TV-14, sex or violence -> TV-MA; "borderline porn" / "tv censoring" -> TV-MA.
           AniDB's adult tags ("18 restricted", "pornography") give X, which counts as a fact, not an estimate."""
        self.content_rating_estimate = True
        self.content_rating_adult = False
        for indicators in data.xpath('./tags/tag/name[text()="content indicators"]/..'):
            level = 0
            for tag in data.xpath('./tags/tag[(@parentid="%s") and (@weight>="%s")]/name' % (indicators.get("id"), settings.ANIDB_MINIMUM_WEIGHT)):
                if tag.text == "nudity":
                    level = max(level, 1)
                elif tag.text in ("sex", "violence"):
                    level = max(level, 2)
            self.content_rating = ["TV-PG", "TV-14", "TV-MA"][level]
        self.content_rating_reason = "content indicators" if self.content_rating else None
        for tag in data.xpath("./tags/tag/name"):
            name = (tag.text or "").strip().lower()
            rating = RESTRICTED_TAGS.get(name)
            if not rating:
                continue
            weight = tag.getparent().get("weight") or "0"
            # "18 restricted" is AniDB's unweighted adult flag; content tags only count at the minimum weight, so a show that
            # merely touches on a theme (weight 100-300) isn't rated as pornography
            if name != "18 restricted" and name != "tv censoring" and not (weight.isdigit() and int(weight) >= int(settings.ANIDB_MINIMUM_WEIGHT)):
                continue
            if rating == "X" or self.content_rating != "X":
                self.content_rating = rating
                self.content_rating_reason = "tag '%s'%s" % (name, (" (weight %s)" % weight) if weight != "0" else "")
            if name in ADULT_TAGS:
                self.content_rating_adult = True
                self.content_rating_estimate = False

    def parse_roles(self, data):
        roles = etree.Element("Roles")
        for role in data.xpath('./characters/character/charactertype[text()="Character"]/..'):
            character_name = textutil.clean_text(element_text(role, "name")) if element_text(role, "name") else ""
            seiyuu_name = ""
            seiyuu_pic = ""
            if element_text(role, "seiyuu"):
                seiyuu_name = textutil.clean_text(element_text(role, "seiyuu"))
                if role.find("seiyuu").get("picture"):
                    seiyuu_pic = settings.ANIDB_IMAGE_DOMAIN + settings.ANIDB_PIC_BASE_URL + role.find("seiyuu").get("picture")
            character_pic = ""
            if element_text(role, "picture"):
                character_pic = settings.ANIDB_IMAGE_DOMAIN + settings.ANIDB_PIC_BASE_URL + element_text(role, "picture")
            etree.SubElement(roles, "Role", character_name=character_name, seiyuu_name=seiyuu_name, seiyuu_pic=seiyuu_pic,
                             character_pic=character_pic, lang="ja")
        self.roles = roles

    def parse_links(self, data):
        links = etree.Element("Links")
        animenfo = []
        for entity in data.xpath("./resources/resource/*"):
            resource_type = entity.getparent().get("type")
            for identifier in entity.xpath("./identifier"):
                if resource_type == "3":
                    animenfo.append(identifier.text)
                elif resource_type in settings.ANIDB_RESOURCES:
                    link_type, template = settings.ANIDB_RESOURCES[resource_type]
                    if template:
                        etree.SubElement(links, "Link", type=link_type, url=template % (identifier.text), value=identifier.text)
                    else:
                        etree.SubElement(links, "Link", type=link_type, url=identifier.text)
            if resource_type == "3" and len(animenfo) >= 2:
                etree.SubElement(links, "Link", type="AnimeNfo", url=settings.ANIDB_RESOURCE_ANIMENFO % (u"%s" % animenfo[0], u"%s" % animenfo[1]), value=u"%s" % animenfo)
        return links


class AniDBEpisode(models.Episode):
    def __init__(self, data):
        models.Episode.__init__(self)
        if data.xpath("./title"):
            title, self.title_lang = textutil.preferred_title_any_type_info(data.xpath("./title"))
            self.title = textutil.clean_text(title)
        if element_text(data, "airdate"):
            self.originally_available_at = element_text(data, "airdate")
        if element_text(data, "rating"):
            self.rating = element_text(data, "rating")
        epno = element_text(data, "epno")
        if epno and epno.isdigit():
            self.absolute_index = epno
        if epno:
            self.number = str(epno)
        epno_node = data.find("epno")
        if epno_node is not None and epno_node.get("type"):
            self.season = "01" if epno_node.get("type") == "1" else "00"
            self.kind = epno_node.get("type")             # 1 episode, 2 special, 3 credit (OP/ED), ...
        summary = clean_description(element_text(data, "summary"))
        if summary:
            self.summary = summary
