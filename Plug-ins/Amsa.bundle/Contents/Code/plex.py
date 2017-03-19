import constants, lxml
from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment

class Plex(constants.Series):
    def __init__(self, id):
    
        self.ID = id
        
        self.MetaType = "Plex"
        
        ##--------------------------------Themes-------------------------------##
        themes = etree.tostring(E.Themes(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        themes = XML.ElementFromString(themes)
        SubElement(themes, "Theme", type = "Main", url = constants.THEME_URL % id)       
        self.Themes = themes
        
        self.Episodes = []