import constants, lxml
from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment

class Plex(constants.Series):
    def __init__(self, id):
        """
        Initialize an element.

        Args:
            self: (todo): write your description
            id: (str): write your description
        """
    
        self.ID = id
        
        self.MetaType = "Plex"
        
        ##--------------------------------Themes-------------------------------##
        themes = etree.tostring(E.Themes(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        themes = XML.ElementFromString(themes)
        
        mainUrl = constants.THEME_URL % id
        mainFilename = os.path.join(constants.CacheDirectory, os.path.join("Plex", id, "theme"), os.path.basename(mainUrl))
        mainLocalPath = os.path.abspath(os.path.join(constants.CachePath, "..", mainFilename))
        SubElement(themes, "Theme", type = "Main", url = mainUrl, id = "1", localPath = mainLocalPath)       
        self.Themes = themes
        
        self.Episodes = []