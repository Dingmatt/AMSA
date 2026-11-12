"""Common data model for every metadata source (AniDB, TVDB, Plex themes).

Each source fills the attributes it knows. Attribute names are the lower-case form of the bundle field
names in settings.SERIES_FIELDS / EPISODE_FIELDS, e.g. "Originally_Available_At" -> originally_available_at.
Plain values (text, numbers, lists) are stored as text in the bundle; lxml elements (images, roles, links) are copied as-is.
"""
import os

from lxml import etree

import settings


def field_attr(field):
    """Bundle field name -> source attribute name."""
    return field.lower()


class Series():
    def __init__(self, source_id, meta_type):
        self.id = str(source_id)
        self.meta_type = meta_type          # Tag used in the bundle: "Anidb", "Tvdb" or "Plex"
        self.api = None                     # TVDB only: "v4" or "v1"
        self.valid = False                  # False when no data could be loaded (callers must not crash on it)
        self.type = None
        self.title = None
        self.original_title = None
        self.title_lang = None              # Language of the title (AniDB code, e.g. "en", "x-jat", "ja"); None = unknown
        self.title_main = False             # AniDB/AniList: the title is the main (romaji) title, which ranks as "main" in the language settings
        self.mal_id = None                  # AniDB only: MyAnimeList id, used to find the AniList entry
        self.site_id = None                 # The source's own id where it isn't the lookup id (AniList: looked up by AniDB id)
        self.end_date = None                # AniDB only: "YYYY[-MM[-DD]]" end date (cache age)
        self.season_ids = {}                # TVDB v4 only: official season number -> v4 season id
        self.aliases = []                   # TVDB v4 only: the series' other names (aliases, untranslated name)
        self.content_ratings = {}           # TVDB v4 only: country ("gbr") -> official content rating there
        self.summary = None
        self.originally_available_at = None
        self.rating = None
        self.rating_votes = None            # How many votes the rating is from, where the source says
        self.studio = None
        self.countries = None
        self.duration = None
        self.genres = None
        self.tags = None
        self.collections = None
        self.content_rating = None
        self.writers = None
        self.directors = None
        self.producers = None
        self.roles = None
        self.art = None
        self.posters = None
        self.banners = None
        self.season = None
        self.themes = None
        self.links = None
        self.episode_count = 0
        self.special_count = 0
        self.op_list = []
        self.ed_list = []
        self.episodes = []


class Episode():
    def __init__(self):
        self.title = None
        self.summary = None
        self.originally_available_at = None
        self.rating = None
        self.absolute_index = 0
        self.writers = None
        self.directors = None
        self.producers = None
        self.thumbs = None
        self.number = None
        self.season = None
        self.title_lang = None              # Language of the episode title (AniDB code); None = unknown
        self.kind = None                    # AniDB episode type ("1" episode, "2" special, "3" credit)
        self.source_id = None               # The source's own episode id (TVDB v4: used to fetch writers/directors)


def new_images():
    """Empty <Images> container for image entries."""
    return etree.Element("Images")


SHARED_NAME_FOLDERS = ("blank", "text")     # TVDB's legacy banners: banners/blank/74796.jpg and banners/text/74796.jpg


def cache_name(url):
    """File name an image is cached under: the URL's own, with the folder in front where TVDB uses the same name in two
       folders (a series' textless and text banners have the same file name, so one would replace the other)."""
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2 and parts[-2].lower() in SHARED_NAME_FOLDERS:
        return parts[-2].lower() + "-" + parts[-1]
    return parts[-1]


def add_image(images, image_path, base_url, base_folder, thumb_path=None, extra=None):
    """Append an <Image> describing where to download an image and where to cache it."""
    main_url = os.path.join(base_url, image_path).replace("\\", "/")
    main_filename = os.path.join(settings.CACHE_DIR, base_folder, cache_name(main_url))
    main_local_path = os.path.abspath(os.path.join(settings.CACHE_PATH, "..", main_filename))
    if thumb_path:
        thumb_url = os.path.join(base_url, thumb_path).replace("\\", "/")
        thumb_filename = os.path.join(settings.CACHE_DIR, base_folder, "thumb_" + cache_name(thumb_url))
        thumb_local_path = os.path.abspath(os.path.join(settings.CACHE_PATH, "..", thumb_filename))
    else:
        thumb_url = ""
        thumb_local_path = ""
    attributes = {"mainUrl": main_url, "thumbUrl": thumb_url, "mainLocalPath": main_local_path, "thumbLocalPath": thumb_local_path, "mainFilename": main_filename}
    for key in (extra or {}):
        attributes[key] = str(extra[key])
    return etree.SubElement(images, "Image", attributes)
