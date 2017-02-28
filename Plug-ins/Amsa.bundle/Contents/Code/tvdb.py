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
        
        ##--------------------------------Images-------------------------------##
        banners = []
        bannersXml = XMLFromURL(constants.TVDB_BANNERS_URL % id, id + "_banners.xml", "TvDB\\" + id, CACHE_1HOUR * 24)
        root = etree.tostring(E.Banners(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        root = XML.ElementFromString(root)
        order = 1
        for banner in sorted(bannersXml.xpath("./Banner"), key=lambda x: (GetElementText(x, "BannerType"), GetElementText(x, "id")),  reverse=False):
            bannerType = GetElementText(banner, "BannerType")
            bannerType2 = GetElementText(banner, "BannerType2")
            bannerPath = GetElementText(banner, "BannerPath")
            bannerThumb = GetElementText(banner, "ThumbnailPath")
            metatype = ("art"       if bannerType == "fanart" else \
                        "posters"   if bannerType == "poster" else \
                        "banners"   if bannerType == "series" or bannerType2=="seasonwide" else \
                        "season"    if bannerType == "season" and bannerType2=="season" else None)  
            remoteUrl = os.path.join(constants.TVDB_IMAGES_URL, bannerPath)
            directory = "TvDB\\" + id
            functions.FileFromURL(os.path.join(constants.TVDB_IMAGES_URL, bannerPath), os.path.basename(remoteUrl), directory, CACHE_1HOUR * 24)
            filename = os.path.join(constants.CacheDirectory, directory, os.path.basename(remoteUrl)) 
            localPath = os.path.abspath(os.path.join(constants.CachePath, "..", filename))
            
            SubElement(root, "Banner", id = str(order), bannerType = metatype, url = remoteUrl, thumb = os.path.join(constants.TVDB_IMAGES_URL, bannerThumb) if len(bannerThumb) > 0 else "", local = localPath)
            order = order + 1
        self.Images = root 
            

        ##--------------------------------Themes-------------------------------##
        self.Themes = []
         
        ##--------------------------------EpisodeCount-------------------------##
        self.EpisodeCount = len(data.xpath("""./Episode/SeasonNumber[text()>0]"""))
        
        ##--------------------------------SpecialCount-------------------------##
        self.SpecialCount = len(data.xpath("""./Episode/SeasonNumber[text()=0]"""))
        
        ##--------------------------------Duration-----------------------------##
        if GetElementText(data, "Series/Runtime"):
            self.Duration = int(int(self.EpisodeCount) * int(GetElementText(data, "Series/Runtime")))
        
        ##--------------------------------OP/ED_List---------------------------##
        self.OpList = []
        self.EdList = []
        
        ##--------------------------------Episodes-----------------------------## 
        if len(data.xpath("""./Episode""")) > 0:
            self.Episodes = []
            for item in data.xpath("""./Episode"""):
                self.Episodes.append(self.Episode(item))               

             
        #Log("AniDB - __init__() - Populate  Title: '%s', Network: '%s', Overview: '%s', FirstAired: '%s', Genre: '%s', ContentRating: '%s', Rating: '%s', Episodes: '%s', EpisodeCount: '%s', SpecialCount: '%s', OpedCount: '%s', Posters: '%s'"
        #% (self.Title, self.Network, self.Overview, self.FirstAired, self.Genre, self.ContentRating, self.Rating, self.Episodes, self.EpisodeCount, self.SpecialCount, self.OpedCount, self.Posters) )
        
    class Episode(constants.Episode):
        def __init__(self, data):
            ##--------------------------------Title--------------------------------##
            if GetElementText(data, "EpisodeName"):
                self.Title = str(GetElementText(data, "EpisodeName")).encode('utf-8').strip().translate(constants.ReplaceChars)
            
            ##--------------------------------Summary------------------------------##
            if GetElementText(data, "Overview"):
                self.Summary = GetElementText(data, "Overview")
            
            ##--------------------------------Originally_Available_At--------------##
            if GetElementText(data, "FirstAired" ):
                self.Originally_Available_At = GetElementText(data, "FirstAired")
            
            ##--------------------------------Rating-------------------------------##
            if GetElementText(data, "Rating"):
                self.Rating = GetElementText(data, "Rating")
            
            ##--------------------------------Absolute_Index-----------------------## 
            if GetElementText(data, "absolute_number"):
                self.Absolute_Index = int(GetElementText(data, "absolute_number"))

            ##--------------------------------Writers------------------------------##
            if GetElementText(data, "Writer"):
                if self.Writers is None: self.Writers = [] 
                self.Writers.append(GetElementText(data, "Writer"))
        
            ##--------------------------------Directors----------------------------##
            if GetElementText(data, "Director"):
                if self.Directors is None: self.Directors = [] 
                self.Directors.append(GetElementText(data, "Director"))

            ##--------------------------------Producers----------------------------##
            
        
            ##--------------------------------Thumbs-------------------------------##
            if GetElementText(data, "filename"):
                self.Thumbs = os.path.join(constants.TVDB_IMAGES_URL, GetElementText(data, "filename"))
            
            ##--------------------------------Number-------------------------------##            
            if GetElementText(data, "EpisodeNumber"):
                self.Number = str(GetElementText(data, "EpisodeNumber")).zfill(2)
            
            ##--------------------------------Season-------------------------------##
            if GetElementText(data, "SeasonNumber"):
                self.Season = str(GetElementText(data, "SeasonNumber")).zfill(2)
            
            
            
            
            
