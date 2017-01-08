import constants, functions
from functions import XMLFromURL, GetElementText

class AniDB(constants.Series):
    Title = None
    Network = None
    Overview = None
    FirstAired = None
    Genre = None
    ContentRating = None
    Rating = None
    Episodes = None
    EpisodeCount = None
    SpecialCount = None
    OpedCount = None
    
    def __init__(self, id):
        data = XMLFromURL(constants.ANIDB_HTTP_API_URL + id, id + ".xml", "AniDB\\" + id, CACHE_1HOUR * 24).xpath("""/anime""")[0]
        if data.xpath("""./titles"""):
            self.Title = functions.GetPreferedTitle(data.xpath("""./titles/title"""))
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
        
        Log("AniDB - __init__() - Populate  Title: '%s', Network: '%s', Overview: '%s', FirstAired: '%s', Genre: '%s', ContentRating: '%s', Rating: '%s', Episodes: '%s', EpisodeCount: '%s', SpecialCount: '%s', OpedCount: '%s'"
        % (self.Title, self.Network, self.Overview, self.FirstAired, self.Genre, self.ContentRating, self.Rating, self.Episodes, self.EpisodeCount, self.SpecialCount, self.OpedCount) )