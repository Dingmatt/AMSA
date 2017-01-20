import constants, functions, lxml 
from functions import XMLFromURL, GetElementText
from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment


def ParseNoFromSeason(season, episode):
    if season >= 1:
        return str(episode)
    elif season == 0:
        return "S" + str(episode)
        
def ParseNoFromType(type, episode):
    if type == 1:
        return str(episode)
    elif type == 2:
        return "S" + str(episode)
    elif type == 3:
        return "C" + str(episode)    
    elif type == 4:
        return "T" + str(episode) 
    elif type == 5:
        return "P" + str(episode) 
    elif type == 6:
        return "O" + str(episode) 
 
def ParseLocalNoFromType(type, episode, prefix = ""):
    if type == 1:
        return "S01" + str(episode).zfill(2)
    elif type == 2:
        return "S00" + str(episode).zfill(2) 
    elif type == 3 and prefix.lower() == "op":
        return "S00" + str(101 + episode)
    elif type == 3 and prefix.lower() == "ed":
        return "S00" + str(151 + episode) 
    elif type == 4:
        return "S00" + str(201 + episode) 
    elif type == 5:
        return "S00" + str(301 + episode) 
    elif type == 6:
        return "S00" + str(401 + episode) 

        
class AniDB(constants.Series):
    
    def __init__(self, id):
        data = XMLFromURL(constants.ANIDB_HTTP_API_URL + id, id + ".xml", "AniDB\\" + id, CACHE_1HOUR * 24).xpath("""/anime""")[0]
        self.ID = id
        if data.xpath("""./titles"""):
            self.Title = functions.GetPreferedTitle(data.xpath("""./titles/title""")).encode('utf-8').strip().translate(constants.ReplaceChars)
        for creator in data.xpath("""./creators/name[@type="Animation Work"]"""):
            self.Network = creator.text
        if GetElementText(data, "description"):    
            self.Overview = re.sub(r"http://anidb\.net/[a-z]{2}[0-9]+ \[(.+?)\]", r"\1", GetElementText(data, "description")).replace("`", "'")
        if GetElementText(data, "startdate"):
            self.FirstAired = GetElementText(data, "startdate")
        for primetag in data.xpath("""./tags/tag/name[text()="elements"]"""):
            self.Genre = []
            for tag in data.xpath("""./tags/tag[@parentid="%s"]""" % (primetag.getparent().get("id"))):
                if tag.get("weight") >= constants.MINIMUM_WEIGHT:
                    self.Genre.append(GetElementText(tag, "name"))
        for primetag in data.xpath("""./tags/tag/name[text()="content indicators"]"""):
            for tag in data.xpath("""./tags/tag[@parentid="%s"]""" % (primetag.getparent().get("id"))):
                if tag.get("weight") >= constants.MINIMUM_WEIGHT:
                    self.ContentRating = "NC-17"
        if GetElementText(data, "ratings/permanent") != "" and GetElementText(data, "ratings/temporary") != "": 
            self.Rating = (float(GetElementText(data, "ratings/permanent")) + float(GetElementText(data, "ratings/temporary"))) / 2   
        elif GetElementText(data, "ratings/permanent") != "": 
            self.Rating = float(GetElementText(data, "ratings/permanent"))   
        elif GetElementText(data, "ratings/temporary") != "": 
            self.Rating = float(GetElementText(data, "ratings/temporary"))        
        self.EpisodeCount = int(GetElementText(data, "episodecount")) 
        self.SpecialCount = len(data.xpath("""./episodes/episode/epno[@type="2"]"""))
        self.OpedCount = len(data.xpath("""./episodes/episode/epno[@type="3"]"""))
        if len(data.xpath("""./episodes/episode""")) > 0:
            self.Episodes = []
            for item in data.xpath("""./episodes/episode"""):
                self.Episodes.append(self.Episode(item))
        if GetElementText(data, "picture"): 
            root = etree.tostring(E.Banners(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
            root = XML.ElementFromString(root)
            SubElement(root, "Banner", bannerType = "season", url = os.path.join(constants.ANIDB_PIC_BASE_URL, GetElementText(data, "picture")), thumb = "")
            self.Posters = root
            
        Log("AniDB - __init__() - Populate  Title: '%s', Network: '%s', Overview: '%s', FirstAired: '%s', Genre: '%s', ContentRating: '%s', Rating: '%s', Episodes: '%s', EpisodeCount: '%s', SpecialCount: '%s', OpedCount: '%s', Posters: '%s'"
        % (self.Title, self.Network, self.Overview, self.FirstAired, self.Genre, self.ContentRating, self.Rating, self.Episodes, self.EpisodeCount, self.SpecialCount, self.OpedCount, self.Posters) )
           
    class Episode(constants.Episode):
        def __init__(self, data):
            if data.xpath("""./title"""):
                self.Title = functions.GetPreferedTitleNoType(data.xpath("""./title""")).encode('utf-8').strip().translate(constants.ReplaceChars)
            if GetElementText(data, "epno"):
                self.Number = str(GetElementText(data, "epno"))             
            if data.xpath("""./epno""")[0].get("type"):
                if data.xpath("""./epno""")[0].get("type") == "1":
                    self.Season = "01"
                else:
                    self.Season = "00"
            if GetElementText(data, "airdate"):
                self.FirstAired = GetElementText(data, "airdate")
            if GetElementText(data, "rating"):
                self.Rating = GetElementText(data, "rating")
            self.Overview = None
            self.Poster = None
            if  GetElementText(data, "epno"):
                self.Absolute = str(GetElementText(data, "epno")).zfill(2)