import constants, functions, lxml
from functions import XMLFromURL, GetElementText
from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment

def ParseNoFromSeason(season, episode, default):
    #if season == 0 and episode == 0:
    #    return "S" + str(default).zfill(2) + "E00"
    #else:
    return "S" + str(season).zfill(2) + "E"  + str(episode).zfill(2)
        
class TvDB(constants.Series):
    def __init__(self, id):
        self.ID = id
        data = XMLFromURL(constants.TVDB_HTTP_API_URL % id, id + ".xml", "TvDB\\" + id, CACHE_1HOUR * 24).xpath("""/Data""")[0]
        
        ##--------------------------------Title--------------------------------##
        if GetElementText(data, "Series/SeriesName"):
            self.Title = str(GetElementText(data, "Series/SeriesName")).encode('utf-8').strip().translate(constants.ReplaceChars)
            
        ##--------------------------------Summary------------------------------##
        if GetElementText(data, "Series/Overview"): 
            self.Summary = GetElementText(data, "Series/Overview")
            
        ##--------------------------------Originally_Available_At--------------##     
        if GetElementText(data, "Series/FirstAired"):
            self.Originally_Available_At = GetElementText(data, "Series/FirstAired")
            
        ##--------------------------------Rating-------------------------------##     
        if GetElementText(data, "Series/Rating"):    
            self.Rating = GetElementText(data, "Series/Rating")

        ##--------------------------------Studio-------------------------------##    
        if GetElementText(data, "Series/Network"):
            self.Studio = GetElementText(data, "Series/Network")

        ##--------------------------------Countries----------------------------##
        
        ##--------------------------------Duration-----------------------------##
        
        ##--------------------------------Genres-------------------------------##
        if GetElementText(data, "Series/Genre"):
            self.Genres = filter(None, GetElementText(data, "Series/Genre").split("|"))
            
        ##--------------------------------Tags---------------------------------##
        
        ##--------------------------------Collections--------------------------## 
        
        ##--------------------------------Content_Rating-----------------------##
        if GetElementText(data, "Series/ContentRating"):
            self.Content_Rating = GetElementText(data, "Series/ContentRating")

            
        ##--------------------------------Writers------------------------------##

        ##--------------------------------Directors----------------------------##

        ##--------------------------------Producers----------------------------##
        
        ##--------------------------------Roles--------------------------------##
        self.Roles = []
        
        self.EpisodeCount = len(data.xpath("""./Episode/SeasonNumber[text()>0]"""))
        self.SpecialCount = len(data.xpath("""./Episode/SeasonNumber[text()=0]"""))
        self.OpList = []
        self.EdList = []
        if len(data.xpath("""./Episode""")) > 0:
            self.Episodes = []
            for item in data.xpath("""./Episode"""):
                self.Episodes.append(self.Episode(item))               
        banners = []
        bannersXml = XMLFromURL(constants.TVDB_BANNERS_URL % id, id + "_banners.xml", "AniDB\\" + id, CACHE_1HOUR * 24)
        root = etree.tostring(E.Banners(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        root = XML.ElementFromString(root)
        for banner in bannersXml.xpath("./Banner"):
            bannerType = GetElementText(banner, "BannerType")
            bannerType2 = GetElementText(banner, "BannerType2")
            bannerPath = GetElementText(banner, "BannerPath")
            bannerThumb = GetElementText(banner, "ThumbnailPath")
            metatype = ("art"       if bannerType == "fanart" else \
                        "posters"   if bannerType == "poster" else \
                        "banners"   if bannerType == "series" or bannerType2=="seasonwide" else \
                        "season"    if bannerType == "season" and bannerType2=="season" else None)            
            SubElement(root, "Banner", bannerType = metatype, url = os.path.join(constants.TVDB_IMAGES_URL, bannerPath), thumb = os.path.join(constants.TVDB_IMAGES_URL, bannerThumb))
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
                self.Poster = os.path.join(constants.TVDB_IMAGES_URL, GetElementText(data, "filename"))
            if GetElementText(data, "absolute_number"):
                self.Absolute = int(GetElementText(data, "absolute_number"))
