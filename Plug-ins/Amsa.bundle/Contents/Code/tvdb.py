import constants, functions, lxml
from functions import XMLFromURL, GetElementText
from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment

class TvDB(constants.Series):
    def __init__(self, id):
        self.ID = id
        data = XMLFromURL(constants.TVDB_HTTP_API_URL % id, id + ".xml", "TvDB\\" + id, CACHE_1HOUR * 24).xpath("""/Data""")[0]
        if GetElementText(data, "Series/SeriesName"):
            self.Title = str(GetElementText(data, "Series/SeriesName")).encode('utf-8').strip().translate(constants.ReplaceChars)
        if GetElementText(data, "Series/Network"):
            self.Network = GetElementText(data, "Series/Network")
        if GetElementText(data, "Series/Overview"): 
            self.Overview = GetElementText(data, "Series/Overview")
        if GetElementText(data, "Series/FirstAired"):
            self.FirstAired = GetElementText(data, "Series/FirstAired")
        if GetElementText(data, "Series/Genre"):
            self.Genre = filter(None, GetElementText(data, "Series/Genre").split("|"))
        if GetElementText(data, "Series/ContentRating"):
            self.ContentRating = GetElementText(data, "Series/ContentRating")
        if GetElementText(data, "Series/Rating"):    
            self.Rating = GetElementText(data, "Series/Rating")
        self.EpisodeCount = len(data.xpath("""./Episode/SeasonNumber[text()>0]"""))
        self.SpecialCount = len(data.xpath("""./Episode/SeasonNumber[text()=0]"""))
        self.OpedCount = 0
        if len(data.xpath("""./Episode""")) > 0:
            self.Episodes = []
            for item in data.xpath("""./Episode"""):
                self.Episodes.append(self.Episode(item))               
        banners = []
        bannersXml = XMLFromURL(constants.TVDB_BANNERS_URL % id, id + "_banners.xml", "AniDB\\" + id, CACHE_1HOUR * 24)
        for banner in bannersXml.xpath("./Banner"):
            root = etree.tostring(E.Banners(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
            root = XML.ElementFromString(root)
            bannerType = GetElementText(banner, "BannerType")
            bannerType2 = GetElementText(banner, "BannerType2")
            bannerPath = GetElementText(banner, "BannerPath")
            bannerThumb = GetElementText(banner, "ThumbnailPath")
            metatype = ("art"       if bannerType == "fanart" else \
                        "posters"   if bannerType == "poster" else \
                        "banners"   if bannerType == "series" or bannerType2=="seasonwide" else \
                        "season"    if bannerType == "season" and bannerType2=="season" else None)            
            SubElement(root, "Banner", bannerType = metatype, url = bannerPath, thumb = bannerThumb)
            self.Posters = root 
             
        #Log("AniDB - __init__() - Populate  Title: '%s', Network: '%s', Overview: '%s', FirstAired: '%s', Genre: '%s', ContentRating: '%s', Rating: '%s', Episodes: '%s', EpisodeCount: '%s', SpecialCount: '%s', OpedCount: '%s', Posters: '%s'"
        #% (self.Title, self.Network, self.Overview, self.FirstAired, self.Genre, self.ContentRating, self.Rating, self.Episodes, self.EpisodeCount, self.SpecialCount, self.OpedCount, self.Posters) )
        
    class Episode(constants.Episode):
        def __init__(self, data):
            if GetElementText(data, "EpisodeName"):
                self.Title = str(GetElementText(data, "EpisodeName")).encode('utf-8').strip().translate(constants.ReplaceChars)
            if GetElementText(data, "EpisodeNumber"):
                self.Number = str(GetElementText(data, "EpisodeNumber")).zfill(2)
            if GetElementText(data, "SeasonNumber"):
                self.Season = str(GetElementText(data, "SeasonNumber")).zfill(2)
            if GetElementText(data, "FirstAired" ):
                self.FirstAired = GetElementText(data, "FirstAired" )
            if GetElementText(data, "Rating"):
                self.Rating = GetElementText(data, "Rating")
            if GetElementText(data, "Overview"):
                self.Overview = GetElementText(data, "Overview")
            if GetElementText(data, "filename"):
                self.Poster = GetElementText(data, "filename")
            if GetElementText(data, "absolute_number"):
                self.Absolute = int(GetElementText(data, "absolute_number"))
