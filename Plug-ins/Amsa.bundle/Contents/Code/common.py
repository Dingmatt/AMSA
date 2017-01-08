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
        id = element.get('aid')
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
        root = etree.tostring(E.Series(), pretty_print=True, xml_declaration=True, encoding='UTF-8')
        root = XML.ElementFromString(root)
        
    if not existing:
        Log.Debug("Common - MapSeries() - Generate Bundle")      
        mapping = SubElement(root, "Mapping")
        for item in mappingData.SeriesList if mappingData.SeriesList else []:
            ScudLee = scudlee.ScudLee()
            ScudLee.Load(item)
            
            AniDB = anidb.AniDB(ScudLee.AnidbId)
            Log.Debug("Common - MapSeries() - AniDB episodecount: '%s', specialCount: '%s', opedCount: '%s'" % (AniDB.EpisodeCount, AniDB.SpecialCount, AniDB.OpedCount))      
                       
            seriesMap = SubElement(mapping, "Series", anidbid = str(ScudLee.AnidbId), tvdbid = str(ScudLee.TvdbId), episodeoffset = str(ScudLee.EpisodeOffset), absolute = str(ScudLee.Absolute))
            
            for season in ScudLee.MappingList:
                Log("Common - MapSeries() - Season - AniDB: '%s', TvDB: '%s'" % (season.AnidbSeason, season.TvdbSeason))
                if season.Offset: 
                    for i in range(season.Start, season.End + 1):
                        SubElement(seriesMap, "Episode", anidb="S%sE%s" % (season.AnidbSeason, str(i).zfill(2)), tvdb="S%sE%s" % (season.TvdbSeason, str(i + int(season.Offset))))
                
                if season.Text != None:
                    for string in filter(None, season.Text.split(';')):
                        for i in range(0, len(string.split('-')[1].split("+"))):
                            SubElement(seriesMap, "Episode", anidb="S%sE%s" % (season.AnidbSeason, string.split('-')[0].zfill(2)), tvdb="S%sE%s" % (season.TvdbSeason, string.split('-')[1].split("+")[i].zfill(2)))
                            
            if not ScudLee.Absolute: 
                for i in range(1, AniDB.EpisodeCount+1):
                    if not seriesMap.xpath("""./Episode[@anidb="S%sE%s"]""" % ("01", str(i).zfill(2))):
                        if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (str(ScudLee.DefaultTvdbSeason).zfill(2), str(i + ScudLee.EpisodeOffset).zfill(2))):
                            SubElement(seriesMap, "Episode", anidb="S%sE%s" % ("01", str(i).zfill(2)), tvdb="S%sE%s" % (str(ScudLee.DefaultTvdbSeason).zfill(2), str(i + ScudLee.EpisodeOffset).zfill(2)))  
                        else:
                            SubElement(seriesMap, "Episode", anidb="S%sE%s" % ("01", str(i).zfill(2)), tvdb="S00E00", missing="scudlee")  
                            Log("Common - MapSeries() - Series: '%s', Episode: '%s' Not Mapped" % (ScudLee.AnidbId, i))
                
                for i in range(1, AniDB.SpecialCount+1):
                    if not seriesMap.xpath("""./Episode[@anidb="S%sE%s"]""" % ("00", str(i).zfill(2))):
                        if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % ("00", str(i + ScudLee.EpisodeOffset).zfill(2))):
                            SubElement(seriesMap, "Episode", anidb="S%sE%s" % ("00", str(i).zfill(2)), tvdb="S%sE%s" % ("00", str(i + ScudLee.EpisodeOffset).zfill(2))) 
                        else:
                            SubElement(seriesMap, "Episode", anidb="S%sE%s" % ("00", str(i).zfill(2)), tvdb="S00E00", missing="scudlee")
                            Log("Common - MapSeries() - Series: '%s', Special: '%s' Not Mapped" % (ScudLee.AnidbId, i))                            
            else:
                TvDB = tvdb.TvDB(ScudLee.TvdbId)
                for episode in TvDB.Episodes if TvDB.Episodes else []:
                    if episode.Absolute: 
                        if episode.Absolute > ScudLee.EpisodeOffset and episode.Absolute <= AniDB.EpisodeCount + ScudLee.EpisodeOffset:
                            #Log("Common - MapSeries() - Ab: %s, Eo: %s, Es: %s, Ee: %s" % (episode.Absolute, ScudLee.EpisodeOffset, episode.Season, episode.Number))
                            SubElement(seriesMap, "Episode", anidb="S%sE%s" % ("01", str(episode.Absolute - ScudLee.EpisodeOffset).zfill(2)), tvdb="S%sE%s" % (episode.Season, episode.Number))        
            
            seriesMap[:] = sorted(seriesMap, key=lambda x: (int(x.get("anidb").split('E')[0].replace("S","")), int(x.get("anidb").split('E')[1])))  
    return root

def MapLocal(self, anidbid, media, root):    
    mapping = etree.Element("Mapping")
    #@parallelize
    #def mapSeasons():
    for media_season in sorted(media.seasons, key=lambda x: int(x),  reverse=False):
        #@task
        #def mapSeason(media_season=media_season, mapping=mapping):
            season = SubElement(root, "Season", num=media_season)
            #@parallelize
            #def mapEpisodes():
            for media_episode in sorted(media.seasons[media_season].episodes, key=lambda x: int(x),  reverse=False):
                #@task
                #def mapEpisode(media_season=media_season, media_episode=media_episode, mapping=mapping):
                    episode = SubElement(season, "Episode", num=media_episode)
                    mapped = SubElement(episode, "Mapped")
                    streams = SubElement(episode, "Streams")
                    
                    
                    for media_item in media.seasons[media_season].episodes[media_episode].items:
                        for item_part in media_item.parts:
                            filename = os.path.splitext(os.path.basename(item_part.file.lower()))[0]
                            type = "episode"
                            if int(media_season) == 0 and int(media_episode) >= 150 and re.match(r'.*\b(?:nced|ed)+\d*\b.*', filename): type = "ending"
                            elif int(media_season) == 0 and int(media_episode) >= 100 and re.match(r'.*\b(?:ncop|op)+\d*\b.*', filename): type = "opening"
                            SubElement(episode, "Type").text = "%s" % (type)
                            SubElement(episode, "Filename").text = "%s" % (filename) 
                            for stream in item_part.streams:
                                SubElement(streams, "Stream", type=str(constants.StreamTypes.get(stream.type, "und")), lang=str(getattr(stream, "language", getattr(stream, "language", "und"))))
                                
                            match = re.search(r'.*\b(?P<season>S\d+)(?P<episode>E\d+)\b.*', filename, re.IGNORECASE)
                            
                            anidbSeriesNumber = ""
                            anidbEpisodeNumber = ""
                            tvdbSeriesNumber = ""
                            tvdbEpisodeNumber = ""
                            if match:
                                Log ("Common - MapLocal() - TVDB Matched: S%sE%s" % (str(media_season).zfill(2), str(media_episode).zfill(2)))
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
    
    