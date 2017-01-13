import re, time, unicodedata, hashlib, types, os, inspect, datetime, xml, string, tvdb, anidb, scudlee, functions, constants

from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment
from functions import XMLFromURL
from string import maketrans 
from datetime import timedelta  

global CleanCache_WaitUntil
CleanCache_WaitUntil = datetime.datetime.now()
    
class Titles():   
    def __init__(self, entry, orig_title):
        element = entry.getparent()
        id = element.get("aid")
        langTitle = functions.GetPreferedTitle(element)
        if str(langTitle).translate(constants.ReplaceChars, constants.DeleteChars).lower() == orig_title.lower():
            score = 100
        else:   
            score = 100 * len(orig_title) / len(str(langTitle).translate(constants.ReplaceChars, constants.DeleteChars)) 
        
        self.Entry = entry
        self.Id = id
        self.Title = langTitle
        self.Score = score       

def GetAnimeTitleByID(Id):
    return functions.GetAnimeTitleByID(scudlee.TitleTree(), Id)
    
def GetAnimeTitleByName(Name): 
    return functions.GetAnimeTitleByName(scudlee.TitleTree(), Name)  
            
def RefreshData():
    global CleanCache_WaitUntil
    if CleanCache_WaitUntil + timedelta(days=3) < datetime.datetime.now(): 
        CleanCache()
    scudlee.CorrectionsTree()
    scudlee.TitleTree()
    scudlee.MappingTree()
    scudlee.CollectionTree()
    
def CleanCache():
    global CleanCache_WaitUntil
    CleanCache_WaitUntil = datetime.datetime.now()
    for root, dirs, _  in os.walk(constants.CachePath, topdown=False):
        for directory in dirs:
            directory = os.path.join(root, directory)
            for file in os.listdir(directory):
                file = os.path.join(directory, file)
                if os.path.isfile(file) and os.stat(file).st_mtime < time.time() - 3 * 86400:
                    os.remove(file)   
                    Log.Debug("Common - CleanCache() - file: '%s'" % (file))
            try: 
                if root.strip("\\\\?\\") != constants.CachePath: 
                    os.rmdir(directory)   
                    Log.Debug("Common - CleanCache() - directory: '%s'" % (directory)) 
            except: pass  
   
def MapSeries(mappingData):
    root = None
    existing = None
    if not root: 
        #existing = functions.LoadFile(mappingData.FirstSeries + ".bundle.xml", "Bundles\\")
        if existing:
            root = XML.ElementFromString(existing) 
        
    if not root:
        root = etree.tostring(E.Series(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        root = XML.ElementFromString(root)
        
    if not existing:
        Log.Debug("Common - MapSeries() - Generate Bundle %s" % (len(mappingData.SeriesList)))      
        mapping = SubElement(root, "Mapping")
        @parallelize
        def ForEachInSeriesList():
            for item in mappingData.SeriesList if mappingData.SeriesList else []:
                @task
                def MapItem(item=item, mapping=mapping):
                    ScudLee = scudlee.ScudLee()
                    ScudLee.Load(item)
                    AniDB = None
                    AniDB = anidb.AniDB(ScudLee.AnidbId)
                    Log.Debug("Common - MapSeries() - AniDB ID: '%s', mappingcount: '%s', episodecount: '%s', specialCount: '%s', opedCount: '%s'" % (AniDB.ID, len(ScudLee.MappingList), AniDB.EpisodeCount, AniDB.SpecialCount, AniDB.OpedCount))      
                               
                    seriesMap = SubElement(mapping, "Series", anidbid = str(ScudLee.AnidbId), tvdbid = str(ScudLee.TvdbId), episodeoffset = str(ScudLee.EpisodeOffset), absolute = str(ScudLee.Absolute))
                    
                    for season in ScudLee.MappingList:
                        Log("Common - MapSeries() - Season - AniDB: '%s', TvDB: '%s', Text: '%s'" % (season.AnidbSeason, season.TvdbSeason, season.Text))
                        if season.Offset: 
                            for i in range(season.Start, season.End + 1):
                                if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (season.TvdbSeason, str(i + int(season.Offset)))):
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), i)) 
                                                                   , tvdb="S%sE%s" % (season.TvdbSeason, str(i + int(season.Offset))))
                                    Log("Common - MapSeries() - Offset - Series: '%s', Episode: '%s'" % (ScudLee.AnidbId, str(i + int(season.Offset))))
                                else:
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), i)) 
                                                                   , tvdb="S00E00"
                                                                   , missing="scudlee")
                                    Log("Common - MapSeries() - Offset - Series: '%s', Episode: '%s'" % (ScudLee.AnidbId, str(i + int(season.Offset))))
                                    
                        if season.Text != None:
                            for string in filter(None, season.Text.split(";")):
                                for i in range(0, len(string.split("-")[1].split("+"))):          
                                    if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (season.TvdbSeason, string.split("-")[1].split("+")[i].zfill(2))):
                                        SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), string.split("-")[0]))
                                                                       , tvdb="S%sE%s" % (season.TvdbSeason, string.split("-")[1].split("+")[i].zfill(2)))
                                    else:
                                        SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), string.split("-")[0]))
                                                                       , tvdb="S00E00"
                                                                       , missing="scudlee")
                                        Log("Common - MapSeries() - No Offset - Series: '%s', Episode: '%s' Not Mapped" % (ScudLee.AnidbId, string.split("-")[1].split("+")[i]))    
                                    
                    if not ScudLee.Absolute: 
                        for i in range(1, AniDB.EpisodeCount+1):
                            if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (anidb.ParseNoFromSeason(1, i))):
                                if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (str(ScudLee.DefaultTvdbSeason).zfill(2), 'S' + str(i + ScudLee.EpisodeOffset).zfill(2))):
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(1, i))
                                                                   , tvdb="S%sE%s" % (str(ScudLee.DefaultTvdbSeason).zfill(2), str(i + ScudLee.EpisodeOffset).zfill(2)))                                                               
                                    Log("Common - MapSeries() - Not Abs - Series:'%s', Episode: '%s'" % (ScudLee.AnidbId, i))
                                else:
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(1, i))
                                                                   , tvdb="S00E00" 
                                                                   , missing="scudlee")  
                                    Log("Common - MapSeries() - Not Abs - Series: '%s', Episode: '%s' Not Mapped" % (ScudLee.AnidbId, i))
                        
                        for i in range(1, AniDB.SpecialCount+1):
                            if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (anidb.ParseNoFromSeason(0, i))):
                                if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % ("00", str(i + ScudLee.EpisodeOffset).zfill(2))):
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(0, i))
                                                                   , tvdb="S%sE%s" % ("00", str(i + ScudLee.EpisodeOffset).zfill(2)))
                                    Log("Common - MapSeries() - Abs - Series: '%s', Special: '%s'" % (ScudLee.AnidbId, i))                            
                                else:
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(0, i))
                                                                   , tvdb="S00E00"
                                                                   , missing="scudlee")
                                    Log("Common - MapSeries() - Abs - Series: '%s', Special: '%s' Not Mapped" % (ScudLee.AnidbId, i))                            
                    else:
                        TvDB = tvdb.TvDB(ScudLee.TvdbId)
                        for episode in TvDB.Episodes if TvDB.Episodes else []:
                            if episode.Absolute: 
                                if episode.Absolute > ScudLee.EpisodeOffset and episode.Absolute <= AniDB.EpisodeCount + ScudLee.EpisodeOffset:
                                    #Log("Common - MapSeries() - Ab: %s, Eo: %s, Es: %s, Ee: %s" % (episode.Absolute, ScudLee.EpisodeOffset, episode.Season, episode.Number))
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(1, str(episode.Absolute - ScudLee.EpisodeOffset)))
                                                                   , tvdb="S%sE%s" % (episode.Season, episode.Number))        
                    
                    seriesMap[:] = sorted(seriesMap, key=lambda x: (int(re.sub('[^0-9]','', x.get("anidb"))), x.get("anidb")))  
        return root

def MapLocal(media, root):    
    mapping = etree.Element("Mapping")
    @parallelize
    def mapSeasons():
        for media_season in sorted(media.seasons, key=lambda x: int(x),  reverse=False):
            @task
            def mapSeason(media_season=media_season, mapping=mapping):
                season = SubElement(root, "Season", num=media_season)
                SubElement(season, "Title")
                @parallelize
                def mapEpisodes():
                    for media_episode in sorted(media.seasons[media_season].episodes, key=lambda x: int(x),  reverse=False):
                        @task
                        def mapEpisode(media_season=media_season, media_episode=media_episode, mapping=mapping):
                            episode = SubElement(season, "Episode", num=media_episode)
                            mapped = SubElement(episode, "Mapped")
                            streams = SubElement(episode, "Streams")
                            SubElement(episode, "Title")
                            SubElement(episode, "FirstAired")
                            SubElement(episode, "Rating")
                            SubElement(episode, "Overview")
                            SubElement(episode, "Poster")
                                              
                            for media_item in media.seasons[media_season].episodes[media_episode].items:
                                for item_part in media_item.parts:
                                    filename = os.path.splitext(os.path.basename(item_part.file.lower()))[0]
                                    type = "episode"
                                    if int(media_season) == 0 and int(media_episode) >= 150 and re.match(r".*\b(?:nced|ed)+\d*\b.*", filename): type = "ending"
                                    elif int(media_season) == 0 and int(media_episode) >= 100 and re.match(r".*\b(?:ncop|op)+\d*\b.*", filename): type = "opening"
                                    SubElement(episode, "Type").text = "%s" % (type)
                                    SubElement(episode, "Filename").text = "%s" % (filename) 
                                    for stream in item_part.streams:
                                        SubElement(streams, "Stream", type=str(constants.StreamTypes.get(stream.type, "und")), lang=str(getattr(stream, "language", getattr(stream, "language", "und"))))
                                        
                                    match = re.search(r".*\b(?P<season>S\d+)(?P<episode>E\d+)\b.*", filename, re.IGNORECASE)
                                    
                                    anidbSeriesNumber = ""
                                    anidbEpisodeNumber = ""
                                    tvdbSeriesNumber = ""
                                    tvdbEpisodeNumber = ""
                                    if match:
                                        #Log ("Common - MapLocal() - TVDB Matched: S%sE%s" % (str(media_season).zfill(2), str(media_episode).zfill(2)))
                                        mappedEpisode = root.xpath("""./Mapping/Series/Episode[@tvdb="S%sE%s"]""" % (str(media_season).zfill(2), str(media_episode).zfill(2)))
                                        if mappedEpisode:
                                            #if mappedEpisode[0].getparent().get("absolute") == "False": 
                                            anidbSeriesNumber = mappedEpisode[0].getparent().get("anidbid")
                                            anidbEpisodeNumber = mappedEpisode[0].get("anidb")
                                            tvdbSeriesNumber = mappedEpisode[0].getparent().get("tvdbid")
                                            tvdbEpisodeNumber = mappedEpisode[0].get("tvdb")
                                         
                                        SubElement(mapped, "Anidb", episode=anidbEpisodeNumber, series=anidbSeriesNumber)
                                        SubElement(mapped, "Tvdb", episode=tvdbEpisodeNumber, series=tvdbSeriesNumber)
                                                                     
                            collection = []            
                            if streams.xpath("""count(./Stream[@type="%s"][@lang="%s"])""" % ("audio", "eng")) > 0: collection.append("English Dubbed")
                            if streams.xpath("""count(./Stream[@type="%s"][@lang="%s"])""" % ("audio", "jpn")) > 0 and streams.xpath("""count(./Stream[@type="%s"][@lang="%s"])""" % ("subtitle", "eng")) > 0: collection.append("English Subbed")
                            SubElement(episode, "Collection").text = ";".join(collection)
                             
    return root

def MapMeta(root):
    AniDB = None
    for map in sorted(root.xpath("""./Season/Episode/Mapped/Anidb"""), key=lambda x: int(x.get("series") if x.get("series") else 0)):
        if map.get("series"):
            if AniDB == None or AniDB.ID != map.get("series"):    
                AniDB = anidb.AniDB(map.get("series"))           
            for episode in AniDB.Episodes:     
                #Log("Episode: S%sE%s" % (episode.Season, episode.Number))
                if "S%sE%s" % (episode.Season, episode.Number) == map.get("episode"):
                    #Log("Found")
                    if not map.getparent().getparent().getparent().xpath("""./Title/Anidb"""):
                        SubElement(map.getparent().getparent().getparent().xpath("""./Title""")[0], "Anidb").text = (u'%s' % (AniDB.Title))
                    SubElement(map.getparent().getparent().xpath("""./Title""")[0], "Anidb").text =  (u'%s' % (episode.Title))
                    SubElement(map.getparent().getparent().xpath("""./FirstAired""")[0], "Anidb").text = episode.FirstAired
                    SubElement(map.getparent().getparent().xpath("""./Rating""")[0], "Anidb").text = episode.Rating
                    SubElement(map.getparent().getparent().xpath("""./Overview""")[0], "Anidb").text = episode.Overview
                    SubElement(map.getparent().getparent().xpath("""./Poster""")[0], "Anidb").text = episode.Poster
        
    TvDB = None    
    for map in sorted(root.xpath("""./Season/Episode/Mapped/Tvdb"""), key=lambda x: int(x.get("series") if x.get("series") else 0)):
        if map.get("series"):
            if TvDB == None or TvDB.ID != map.get("series"):
                TvDB = tvdb.TvDB(map.get("series"))
            for episode in TvDB.Episodes:
                if "S%sE%s" % (episode.Season, episode.Number) == map.get("episode"):  
                    if not map.getparent().getparent().getparent().xpath("""./Title/Tvdb"""):
                        SubElement(map.getparent().getparent().getparent().xpath("""./Title""")[0], "Tvdb").text = (u'%s' % (TvDB.Title))
                    SubElement(map.getparent().getparent().xpath("""./Title""")[0], "Tvdb").text = (u'%s' % (episode.Title))
                    SubElement(map.getparent().getparent().xpath("""./FirstAired""")[0], "Tvdb").text = episode.FirstAired  
                    SubElement(map.getparent().getparent().xpath("""./Rating""")[0], "Tvdb").text = episode.Rating                    
                    SubElement(map.getparent().getparent().xpath("""./Overview""")[0], "Tvdb").text = episode.Overview
                    SubElement(map.getparent().getparent().xpath("""./Poster""")[0], "Tvdb").text = episode.Poster
    return root        