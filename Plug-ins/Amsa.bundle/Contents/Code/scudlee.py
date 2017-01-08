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
        pMappingTree = XMLFromURL(constants.ANIDB_TVDB_MAPPING, os.path.splitext(os.path.basename(constants.ANIDB_TVDB_MAPPING))[0], "", CACHE_1HOUR * 24 * 2, 60)
    return pMappingTree
    
def CollectionTree():
    global pCollectionTree
    if pCollectionTree == None:
        pCollectionTree = XMLFromURL(constants.ANIDB_COLLECTION, os.path.splitext(os.path.basename(constants.ANIDB_COLLECTION))[0], "", CACHE_1HOUR * 24 * 2, 60)
    return pCollectionTree

def CorrectionsTree():
    global pCorrectionsTree
    if pCorrectionsTree == None:
        pCorrectionsTree = XMLFromURL(constants.ANIDB_TVDB_MAPPING_CORRECTIONS, os.path.splitext(os.path.basename(constants.ANIDB_TVDB_MAPPING_CORRECTIONS))[0], "", CACHE_1HOUR * 24 * 2, 60)
    return pCorrectionsTree

class ScudLee():
    def __init__(self, anidbid = None, tvdbid = None):
        if anidbid != None or tvdbid != None:
            if anidbid != None: 
                data = MappingTree().xpath("""./anime[@anidbid="%s"]""" % (anidbid))[0]
            elif tvdbid != None: 
                data = MappingTree().xpath("""./anime[@tvdbid="%s"]""" % (tvdbid))[0]
            self.Load(data)
            self.SeriesList = MappingTree().xpath("""./anime[@tvdbid="%s"]""" % (self.TvdbId))
            for series in self.SeriesList:
                if series.get("defaulttvdbseason") == "1" or (series.get("defaulttvdbseason") == "a" and series.get("episodeoffset") == ""):
                    self.FirstSeries = series.get("anidbid")
    
    def Load(self, data):  
        self.AnidbId = data.get("anidbid")
        self.TvdbId = data.get("tvdbid")
        self.EpisodeOffset = int(data.get("episodeoffset")) if data.get("episodeoffset") else 0
        self.Absolute = "True" if data.get("defaulttvdbseason") == "a" else "False"
        self.DefaultTvdbSeason = int(data.get("defaulttvdbseason")) if self.Absolute == False else 1
        self.MappingList = []
        for item in data.xpath("""./mapping-list/mapping"""):
            self.MappingList.append(self.Mapping(item))
            
    class Mapping(): 
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
        
        