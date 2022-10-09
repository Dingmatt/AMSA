import constants, functions

from functions import XMLFromURL, GetElementText
 
global pTitleTree, pMappingTree, pCollectionTree, pCorrectionsTree
pTitleTree = None
pMappingTree = None
pCollectionTree = None
pCorrectionsTree = None
    
def TitleTree():
    global pTitleTree
    if pTitleTree == None:
        pTitleTree = XMLFromURL(constants.ANIDB_TITLES, os.path.splitext(os.path.basename(constants.ANIDB_TITLES))[0], "", CACHE_1HOUR * 24 * 2, 60)
    return pTitleTree
    
def MappingTree():
    global pMappingTree
    if pMappingTree == None:
        pMappingTree = XMLFromURL(constants.ANIDB_TVDB_MAPPING, os.path.basename(constants.ANIDB_TVDB_MAPPING), "", CACHE_1HOUR * 24 * 2, 60)
    return pMappingTree
    
def CollectionTree():
    global pCollectionTree
    if pCollectionTree == None:
        pCollectionTree = XMLFromURL(constants.ANIDB_COLLECTION, os.path.basename(constants.ANIDB_COLLECTION), "", CACHE_1HOUR * 24 * 2, 60)
    return pCollectionTree

def CorrectionsTree():
    global pCorrectionsTree
    if pCorrectionsTree == None:
        pCorrectionsTree = XMLFromURL(constants.ANIDB_TVDB_MAPPING_CORRECTIONS, os.path.basename(constants.ANIDB_TVDB_MAPPING_CORRECTIONS), "", CACHE_1HOUR * 24 * 2, 60)
    return pCorrectionsTree

class ScudLee():
    AnidbId = None
    TvdbId = None
    EpisodeOffset = 0
    Absolute = False
    DefaultTvdbSeason = 1
    MappingList = []
    FirstSeries = None
    
    def __init__(self, anidbid = None, tvdbid = None):
        if anidbid != None or tvdbid != None:
            if anidbid != None: 
                data = MappingTree().xpath("""./anime[@anidbid="%s"]""" % (anidbid))
            elif tvdbid != None: 
                data = MappingTree().xpath("""./anime[@tvdbid="%s"]""" % (tvdbid))
				
            if data != None:
                self.Load(data[0])
                self.SeriesList = []
                if self.TvdbId:
                    self.SeriesList = MappingTree().xpath("""./anime[@tvdbid="%s"]""" % (self.TvdbId))
                else:
                    self.SeriesList = MappingTree().xpath("""./anime[@anidbid="%s"]""" % (self.AnidbId))
                visited = []
                remove = []

                for series in self.SeriesList:
                    current = series.get("anidbid")
                    if current in visited:
                        remove.append(series)
                    else:
                        visited.append(current)
                    
                for item in remove:
                    self.SeriesList.remove(item)
            
                #Log("SeriesList: %s %s %s" % (self.SeriesList, self.TvdbId, self.AnidbId))
                self.SeriesList = sorted(self.SeriesList, key=lambda x: int(x.get("anidbid")))   
                for series in self.SeriesList:            
                    if series.get("defaulttvdbseason") == "1" or (series.get("defaulttvdbseason") == "a" and series.get("episodeoffset") == ""):
                        self.FirstSeries = series.get("anidbid")
                if not self.FirstSeries:
                    self.FirstSeries = anidbid
    
    def Load(self, data):
        if data.get("anidbid"):
            self.AnidbId = data.get("anidbid")
            if not (u"%s" % (self.AnidbId)).isnumeric(): 
                #Log("Anidb: %s" %(self.AnidbId))
                self.AnidbId = None   
                
        if data.get("tvdbid"): 
            self.TvdbId = data.get("tvdbid")
            if not (u"%s" % (self.TvdbId)).isnumeric(): 
                #Log("TvdbId: %s" %(self.TvdbId))
                self.TvdbId = None   
        if data.get("episodeoffset"):
            self.EpisodeOffset = int(data.get("episodeoffset"))
        if data.get("defaulttvdbseason") and data.get("defaulttvdbseason") == "a":
            self.Absolute = True 
        if data.get("defaulttvdbseason") and not self.Absolute:
            self.DefaultTvdbSeason = int(data.get("defaulttvdbseason"))
        if data.xpath("""./mapping-list/mapping"""):  
            self.MappingList = []
            for item in data.xpath("""./mapping-list/mapping"""):
                self.MappingList.append(self.Mapping(item))
            
    class Mapping(): 
        Text = None
        Offset = None
        Start = None
        End = None
        AnidbSeason = None
        TvdbSeason = None
        
        def __init__(self, data):
            if data.text:
                self.Text = data.text
            if data.get("offset"):
                self.Offset = data.get("offset").zfill(2)
            if data.get("start"):    
                self.Start = int(data.get("start"))
            if data.get("end"):
                self.End = int(data.get("end"))
            if data.get("anidbseason"):
                self.AnidbSeason = data.get("anidbseason").zfill(2)
            if data.get("tvdbseason"):
                self.TvdbSeason = data.get("tvdbseason").zfill(2)
        
        