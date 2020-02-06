import constants, lxml
from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment

class MyAnimeList(constants.Series):
    def __init__(self, id):
        logging.Log_Milestone("MyAnimeList" + "_" + id)
        data = XMLFromURL(constants.MAL_HTTP_API_URL + id, id + ".xml", os.path.join("MyAnimeList", id), CACHE_1HOUR * 24).xpath("""/anime""")[0]
        
        self.ID = id
        
        self.MetaType = "Myanimelist"
        
        ##--------------------------------Themes-------------------------------##
        art = etree.tostring(E.Images(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        art = XML.ElementFromString(art)
        artCount = 2
        posters = etree.tostring(E.Images(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        posters = XML.ElementFromString(posters)
        postersCount = 2
        banners = etree.tostring(E.Images(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        banners = XML.ElementFromString(banners)
        bannersCount = 2
        
        for banner in bannersXml.xpath("./Banner"):
            bannerType = GetElementText(banner, "BannerType")
            bannerType2 = GetElementText(banner, "BannerType2")
            bannerPath = GetElementText(banner, "BannerPath")
            bannerThumb = GetElementText(banner, "ThumbnailPath")
            metatype = ("art"       if bannerType == "fanart" else \
                        "posters"   if bannerType == "poster" else \
                        "banners"   if bannerType == "series" or bannerType2=="seasonwide" else \
                        "season"    if bannerType == "season" and bannerType2=="season" else None)  
            
            mainUrl, thumbUrl, mainLocalPath, thumbLocalPath = functions.ParseImage(bannerPath, constants.TVDB_IMAGES_URL, os.path.join("TvDB", id, metatype), bannerThumb)               
            if metatype == "art":
                SubElement(art, "Image", id = str(1 if bannerPath == GetElementText(data, "Series/fanart") else artCount), mainUrl = mainUrl, thumbUrl = thumbUrl, mainLocalPath = mainLocalPath, thumbLocalPath = thumbLocalPath)
                artCount = artCount + 1
            if metatype == "posters":
                SubElement(posters, "Image", id = str(1 if bannerPath == GetElementText(data, "Series/poster") else postersCount), mainUrl = mainUrl, thumbUrl = thumbUrl, mainLocalPath = mainLocalPath, thumbLocalPath = thumbLocalPath)
                postersCount = postersCount + 1
            if metatype == "banners":
                SubElement(banners, "Image", id = str(1 if bannerPath == GetElementText(data, "Series/banner") else bannersCount), mainUrl = mainUrl, thumbUrl = thumbUrl, mainLocalPath = mainLocalPath, thumbLocalPath = thumbLocalPath)
                bannersCount = bannersCount + 1
                
        self.Art = art
        self.Posters = posters 
        self.Banners = banners 
        
        self.Episodes = []
        logging.Log_Milestone("MyAnimeList" + "_" + id)