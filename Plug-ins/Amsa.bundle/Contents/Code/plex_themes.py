"""Plex source: TV theme music from tvthemes.plexapp.com (keyed by TVDB id)."""
import os

from lxml import etree

import settings
import models


class PlexThemes(models.Series):
    def __init__(self, tvdb_id):
        models.Series.__init__(self, tvdb_id, "Plex")
        self.valid = True
        url = settings.THEME_URL % self.id
        filename = os.path.join(settings.CACHE_DIR, os.path.join("Plex", self.id, "theme"), os.path.basename(url))
        themes = etree.Element("Themes")
        etree.SubElement(themes, "Theme", type="Main", url=url, id="1", localPath=os.path.abspath(os.path.join(settings.CACHE_PATH, "..", filename)))
        self.themes = themes
