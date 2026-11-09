"""TVDB source: one series from TheTVDB's v1 XML API (series + banners)."""
import os

import settings
import textutil
import models
import downloader
from textutil import element_text


def episode_number(season, episode):
    """TVDB-style 'SxxEyy'."""
    return "S" + str(season).zfill(2) + "E" + str(episode).zfill(2)


def banner_kind(banner_type, banner_type2):
    """Which image list a TVDB banner belongs to, or None to ignore it."""
    if banner_type == "fanart":
        return "art"
    if banner_type == "poster":
        return "posters"
    if banner_type == "series" or banner_type2 == "seasonwide":
        return "banners"
    if banner_type == "season" and banner_type2 in ("680x1000", "season"):
        return "season"
    return None


class TvDBSeries(models.Series):
    def __init__(self, tvdb_id):
        models.Series.__init__(self, tvdb_id, "Tvdb")
        tvdb_id = self.id
        if not textutil.is_digits(tvdb_id):
            Log.Debug("TvDB - Ignoring invalid TVDB id '%s'" % (tvdb_id))
            return
        xml = downloader.xml_from_url(settings.TVDB_SERIES_URL % tvdb_id, tvdb_id + ".xml", os.path.join("TvDB", tvdb_id), settings.DEFAULT_CACHE)
        found = xml.xpath("/Data") if xml is not None else []
        if not found:
            Log.Error("TvDB - No data for TVDB id '%s'" % (tvdb_id))
            return
        data = found[0]
        self.valid = True

        if element_text(data, "Series/SeriesName"):
            self.title = textutil.clean_text(element_text(data, "Series/SeriesName"))
            self.title_lang = "en"
        if element_text(data, "Series/Overview"):
            self.summary = element_text(data, "Series/Overview")
        if element_text(data, "Series/FirstAired"):
            self.originally_available_at = element_text(data, "Series/FirstAired")
        if element_text(data, "Series/Rating"):
            self.rating = element_text(data, "Series/Rating")
            if (element_text(data, "Series/RatingCount") or "").isdigit():
                self.rating_votes = int(element_text(data, "Series/RatingCount"))
        if element_text(data, "Series/Network"):
            self.studio = element_text(data, "Series/Network")
        if element_text(data, "Series/Genre"):
            self.genres = [genre.strip() for genre in element_text(data, "Series/Genre").split("|") if genre.strip()]
        if element_text(data, "Series/ContentRating"):
            self.content_rating = element_text(data, "Series/ContentRating")

        self.parse_banners(data)

        self.episode_count = len(data.xpath("./Episode/SeasonNumber[text()>0]"))
        self.special_count = len(data.xpath("./Episode/SeasonNumber[text()=0]"))
        if element_text(data, "Series/Runtime").isdigit():
            self.duration = int(element_text(data, "Series/Runtime")) * 60000      # Plex: one episode's length in milliseconds

        for item in data.xpath("./Episode"):
            try:
                self.episodes.append(TvDBEpisode(item, tvdb_id))
            except Exception as e:
                Log.Debug("TvDB - Skipping malformed episode in '%s': %s" % (tvdb_id, e))

    def parse_banners(self, data):
        tvdb_id = self.id
        banners_xml = downloader.xml_from_url(settings.TVDB_BANNERS_URL % tvdb_id, tvdb_id + "_banners.xml", os.path.join("TvDB", tvdb_id), settings.DEFAULT_CACHE)
        if banners_xml is None or not len(banners_xml):
            return
        images = {"art": models.new_images(), "posters": models.new_images(), "banners": models.new_images(), "season": models.new_images()}
        counters = {"art": 2, "posters": 2, "banners": 2}           # id 1 is reserved for the series' own fanart/poster/banner
        preferred = {"art": element_text(data, "Series/fanart"), "posters": element_text(data, "Series/poster"), "banners": element_text(data, "Series/banner")}
        season_seen = []
        for banner in sorted(banners_xml.xpath("./Banner"), key=lambda x: textutil.safe_float(element_text(x, "Rating", "0")), reverse=True):
            kind = banner_kind(element_text(banner, "BannerType"), element_text(banner, "BannerType2"))
            path = element_text(banner, "BannerPath")
            if kind is None or not path:
                continue  # Unknown banner type (e.g. clearlogo)
            thumb = element_text(banner, "ThumbnailPath") or (os.path.splitext(path)[0] + "_t" + os.path.splitext(path)[1])
            if kind == "season":
                season_number = element_text(banner, "Season")
                season_seen.append(season_number)
                extra = {"id": season_seen.count(season_number), "season": season_number}
            else:
                extra = {"id": 1 if path == preferred[kind] else counters[kind]}
                counters[kind] = counters[kind] + 1
            extra["lang"] = textutil.short_language(element_text(banner, "Language", ""))
            models.add_image(images[kind], path, settings.TVDB_IMAGES_URL, os.path.join(settings.TVDB_IMAGES_FOLDER, tvdb_id, kind), thumb, extra)
        self.art = images["art"]
        self.posters = images["posters"]
        self.banners = images["banners"]
        self.season = images["season"]


class TvDBEpisode(models.Episode):
    def __init__(self, data, tvdb_id):
        models.Episode.__init__(self)
        if element_text(data, "EpisodeName"):
            self.title = textutil.clean_text(element_text(data, "EpisodeName"))
            self.title_lang = "en"
        if element_text(data, "Overview"):
            self.summary = element_text(data, "Overview")
        if element_text(data, "FirstAired"):
            self.originally_available_at = element_text(data, "FirstAired")
        if element_text(data, "Rating"):
            self.rating = element_text(data, "Rating")
        if element_text(data, "absolute_number").isdigit():
            self.absolute_index = int(element_text(data, "absolute_number"))
        if element_text(data, "Writer"):
            self.writers = [name.strip() for name in element_text(data, "Writer").split("|") if name.strip()] or None   # TVDB uses "|A|B|"
        if element_text(data, "Director"):
            self.directors = [name.strip() for name in element_text(data, "Director").split("|") if name.strip()] or None
        if element_text(data, "filename"):
            path = element_text(data, "filename")
            thumbs = models.new_images()
            models.add_image(thumbs, path, settings.TVDB_IMAGES_URL, os.path.join(settings.TVDB_IMAGES_FOLDER, tvdb_id, "thumbs"), os.path.splitext(path)[0] + "_t" + os.path.splitext(path)[1], {"id": "1"})
            self.thumbs = thumbs
        if element_text(data, "EpisodeNumber"):
            self.number = str(element_text(data, "EpisodeNumber")).zfill(2)
        if element_text(data, "SeasonNumber"):
            self.season = str(element_text(data, "SeasonNumber")).zfill(2)
