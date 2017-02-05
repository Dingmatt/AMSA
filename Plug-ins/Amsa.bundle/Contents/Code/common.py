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
                    Log.Debug("Common - MapSeries() - AniDB ID: '%s', mappingcount: '%s', episodecount: '%s', specialCount: '%s', opCount: '%s', edCount: '%s'" % (AniDB.ID, len(ScudLee.MappingList), AniDB.EpisodeCount, AniDB.SpecialCount, len(AniDB.OpList), len(AniDB.EdList)))      
                               
                    seriesMap = SubElement(mapping, "Series", anidbid = str(ScudLee.AnidbId), tvdbid = str(ScudLee.TvdbId), episodeoffset = str(ScudLee.EpisodeOffset), absolute = str(ScudLee.Absolute))
                    
                    for season in ScudLee.MappingList:
                        Log("Common - MapSeries() - Season - AniDB: '%s', TvDB: '%s', Text: '%s'" % (season.AnidbSeason, season.TvdbSeason, season.Text))
                        if season.Offset: 
                            for i in range(season.Start, season.End + 1):
                                if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (season.TvdbSeason, str(i + int(season.Offset)))):
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), i)) 
                                                                   , tvdb="%s" % (tvdb.ParseNoFromSeason(int(season.TvdbSeason), i + int(season.Offset), ScudLee.DefaultTvdbSeason)))
                                    #Log("Common - MapSeries() - Offset - Series: '%s', Episode: '%s'" % (ScudLee.AnidbId, str(i + int(season.Offset))))
                                else:
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), i)) 
                                                                   , tvdb="%s" % (tvdb.ParseNoFromSeason(0, 0, ScudLee.DefaultTvdbSeason))
                                                                   , missing="scudlee")
                                    #Log("Common - MapSeries() - Offset - Series: '%s', Episode: '%s'" % (ScudLee.AnidbId, str(i + int(season.Offset))))
                                    
                        if season.Text != None:
                            for string in filter(None, season.Text.split(";")):
                                for i in range(0, len(string.split("-")[1].split("+"))):          
                                    if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (season.TvdbSeason, string.split("-")[1].split("+")[i].zfill(2))) and "S%sE%s" % (season.TvdbSeason, string.split("-")[1].split("+")[i].zfill(2)) != "S00E00":
                                        SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), string.split("-")[0]))
                                                                       , tvdb="%s" % (tvdb.ParseNoFromSeason(int(season.TvdbSeason), int(string.split("-")[1].split("+")[i]), ScudLee.DefaultTvdbSeason)))
                                    elif not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (season.TvdbSeason, string.split("-")[1].split("+")[i].zfill(2))):
                                        SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), string.split("-")[0]))
                                                                       , tvdb="%s" % (tvdb.ParseNoFromSeason(0, 0, ScudLee.DefaultTvdbSeason))
                                                                       , missing="tvdb")
                                    else:
                                        SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), string.split("-")[0]))
                                                                       , tvdb="%s" % (tvdb.ParseNoFromSeason(0, 0, ScudLee.DefaultTvdbSeason))
                                                                       , missing="scudlee")
                                        #Log("Common - MapSeries() - No Offset - Series: '%s', Episode: '%s' Not Mapped" % (ScudLee.AnidbId, string.split("-")[1].split("+")[i]))    
                                    
                    if not ScudLee.Absolute: 
                        for i in range(1, AniDB.EpisodeCount+1):
                            if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (anidb.ParseNoFromSeason(1, i))):
                                if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (str(ScudLee.DefaultTvdbSeason).zfill(2), 'S' + str(i + ScudLee.EpisodeOffset).zfill(2))):
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(1, i))
                                                                   , tvdb="S%sE%s" % (str(ScudLee.DefaultTvdbSeason).zfill(2), str(i + ScudLee.EpisodeOffset).zfill(2)))                                                               
                                    #Log("Common - MapSeries() - Not Abs - Series:'%s', Episode: '%s'" % (ScudLee.AnidbId, i))
                                else:
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(1, i))
                                                                   , tvdb="S00E00" 
                                                                   , missing="scudlee")  
                                    #Log("Common - MapSeries() - Not Abs - Series: '%s', Episode: '%s' Not Mapped" % (ScudLee.AnidbId, i))
                        
                        for i in range(1, AniDB.SpecialCount+1):
                            if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (anidb.ParseNoFromType(2, i))):
                                if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % ("00", str(i + ScudLee.EpisodeOffset).zfill(2))):
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromType(2, i))
                                                                   , tvdb="S%sE%s" % ("00", str(i + ScudLee.EpisodeOffset).zfill(2)))
                                    #Log("Common - MapSeries() - Abs - Series: '%s', Special: '%s'" % (ScudLee.AnidbId, i))                            
                                else:
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromType(2, i))
                                                                   , tvdb="S00E00"
                                                                   , missing="scudlee")
                                    L#og("Common - MapSeries() - Abs - Series: '%s', Special: '%s' Not Mapped" % (ScudLee.AnidbId, i))
                        
                        i = 0
                        for opening in AniDB.OpList:                          
                            if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (opening)):
                                SubElement(seriesMap, "Episode", anidb="%s" % (opening)
                                                               , tvdb="%s" % (anidb.ParseLocalNoFromType(3, i, "op")))
                                i = i + 1
                        
                        i = 0
                        for ending in AniDB.EdList:
                            if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (ending)):
                                SubElement(seriesMap, "Episode", anidb="%s" % (ending)
                                                               , tvdb="%s" % (anidb.ParseLocalNoFromType(3, i, "ed")))  
                                i = i + 1                               
                    else:
                        TvDB = tvdb.TvDB(ScudLee.TvdbId)
                        for episode in TvDB.Episodes if TvDB.Episodes else []:
                            if episode.Absolute: 
                                if episode.Absolute > ScudLee.EpisodeOffset and episode.Absolute <= AniDB.EpisodeCount + ScudLee.EpisodeOffset:
                                    #Log("Common - MapSeries() - Ab: %s, Eo: %s, Es: %s, Ee: %s" % (episode.Absolute, ScudLee.EpisodeOffset, episode.Season, episode.Number))
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(1, episode.Absolute - ScudLee.EpisodeOffset))
                                                                   , tvdb="S%sE%s" % (episode.Season, episode.Number))        
                    
                    seriesMap[:] = sorted(seriesMap, key=lambda x: (0 if re.sub('[^A-Z]','', x.get("anidb")) else 1, int(re.sub('[^0-9]','', x.get("anidb")))))  
        
        
        unmappedlist = sorted(mapping.xpath("""./Series/Episode[@tvdb="S00E00"]"""), key=lambda x: x.getparent().get("anidbid"))  
        if unmappedlist:
            unmapped = SubElement(mapping, "Unmapped")
            i = 1
            for episode in unmappedlist:
                SubElement(unmapped, "Episode", anidbid = episode.getparent().get("anidbid"), anidb = episode.get("anidb"), missing = episode.get("missing"), id = str(i))
                i = i + 1
    return root

def MapLocal(media, root, anidbid):    
    mapping = etree.Element("Mapping")
    guessId = 1
    @parallelize
    def mapSeasons():
        for media_season in sorted(media.seasons, key=lambda x: int(x),  reverse=False):
            @task
            def mapSeason(media_season=media_season, mapping=mapping, guessId=guessId):
                season = SubElement(root, "Season", num=media_season)
                SubElement(season, "Title")
                SubElement(season, "Summary")
                SubElement(season, "Originally_Available_At")
                SubElement(season, "Rating")
                SubElement(season, "Studio")
                SubElement(season, "Countries")
                SubElement(season, "Duration")
                SubElement(season, "Genres")
                SubElement(season, "Tags")
                SubElement(season, "Collections")
                SubElement(season, "Content_Rating")
                SubElement(season, "Writers")
                SubElement(season, "Directors")
                SubElement(season, "Producers")
                SubElement(season, "Roles")
                SubElement(season, "Posters")
                
                @parallelize
                def mapEpisodes():
                    for media_episode in sorted(media.seasons[media_season].episodes, key=lambda x: int(x),  reverse=False):
                        @task
                        def mapEpisode(media_season=media_season, media_episode=media_episode, mapping=mapping, guessId=guessId):
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
                                        
                                    anidbSeriesNumber = ""
                                    anidbEpisodeNumber = ""
                                    tvdbSeriesNumber = ""
                                    tvdbEpisodeNumber = ""
                                    mappedEpisode = None
                                    guessEpisode = None
                                    
                                    if re.search(r".*\b(?P<season>S\d+)(?P<episode>E\d+)\b.*", filename, re.IGNORECASE) or re.search(r".*\b(?P<type>ncop|op|nced|ed)(?P<episode>\d+)\b.*", filename, re.IGNORECASE):
                                        mappedEpisode = root.xpath("""./Mapping/Series/Episode[@tvdb="S%sE%s"]""" % (str(media_season).zfill(2), str(media_episode).zfill(2)))
                                        if mappedEpisode: 
                                            #Log("Mapped: '%s'" % (filename))
                                            anidbSeriesNumber = mappedEpisode[0].getparent().get("anidbid")
                                            anidbEpisodeNumber = mappedEpisode[0].get("anidb")
                                            tvdbSeriesNumber = mappedEpisode[0].getparent().get("tvdbid")
                                            tvdbEpisodeNumber = mappedEpisode[0].get("tvdb")  
                                        else:
                                            #Log("Override: '%s'" % (filename))
                                            match = re.search(r".*\B\[(?P<provider>\D+)(?P<id>\d+)\]\B.*", filename, re.IGNORECASE)
                                            if match:
                                                provider = match.group('provider').lower()
                                                anidbSeriesNumber = match.group('id').lower()
                                                anidbEpisodeNumber = anidb.ParseNoFromSeason(int(media_season), int(media_episode))
                                            else:
                                                guessEpisode = root.xpath("""./Mapping/Unmapped/Episode[@id="%s"]""" % (guessId)) 
                                                if guessEpisode:
                                                    anidbSeriesNumber = guessEpisode[0].get("anidbid")
                                                    anidbEpisodeNumber = guessEpisode[0].get("anidb")
                                                    #Log("mappedEpisode: '%s', '%s', '%s', '%s'" % (guessEpisode, guessId, anidbSeriesNumber, anidbEpisodeNumber))
                                    elif re.search(r".*\b(?P<episode>E\d+)\b.*", filename, re.IGNORECASE):
                                        #Log("Absolute: '%s'" % (filename))
                                        mappedEpisode = root.xpath("""./Mapping/Series[@anidbid="%s"]/Episode[@anidb="%s"]""" % (anidbid, anidb.ParseNoFromSeason(int(media_season), int(media_episode))))
                                        anidbSeriesNumber = mappedEpisode[0].getparent().get("anidbid")
                                        anidbEpisodeNumber = mappedEpisode[0].get("anidb")
                                        tvdbSeriesNumber = mappedEpisode[0].getparent().get("tvdbid")
                                        tvdbEpisodeNumber = mappedEpisode[0].get("tvdb")  

                                    if anidbSeriesNumber != "" and anidbEpisodeNumber != "" and guessEpisode == None:                                    
                                        SubElement(mapped, "Anidb", episode=anidbEpisodeNumber, series=anidbSeriesNumber)
                                    elif anidbSeriesNumber != "" and anidbEpisodeNumber != "":
                                        SubElement(mapped, "Anidb", episode=anidbEpisodeNumber, series=anidbSeriesNumber, guess=str(guessId - 1))
                                    if tvdbSeriesNumber != "" and tvdbEpisodeNumber != "":   
                                        SubElement(mapped, "Tvdb", episode=tvdbEpisodeNumber, series=tvdbSeriesNumber)
                                                                     
                            collection = []            
                            if streams.xpath("""count(./Stream[@type="%s"][@lang="%s"])""" % ("audio", "eng")) > 0: collection.append("English Dubbed")
                            if streams.xpath("""count(./Stream[@type="%s"][@lang="%s"])""" % ("audio", "jpn")) > 0 and streams.xpath("""count(./Stream[@type="%s"][@lang="%s"])""" % ("subtitle", "eng")) > 0: collection.append("English Subbed")
                            SubElement(episode, "Collection").text = ";".join(collection)                            
    return root

def MapMeta(root): 
    data = None
    providers = ["Anidb", "Tvdb"]
    
    for provider in providers:
        data = None
        for map in sorted(root.xpath("""./Season/Episode/Mapped/%s""" % (provider)), key=lambda x: int(x.get("series") if x.get("series") else 0)):
            if map.get("series"):
                for existing in map.getparent().getparent().xpath(""".//%s""" % (provider)):
                    if not existing.getparent().tag == "Mapped":
                        existing.getparent().remove(existing)
                if data == None or data.ID != map.get("series"):
                    if provider == "Anidb":
                        data = anidb.AniDB(map.get("series"))
                    elif provider == "Tvdb":
                        data = tvdb.TvDB(map.get("series"))
                for episode in data.Episodes:     
                    if (provider == "Anidb" and "%s" % (episode.Number) == map.get("episode")) or (provider == "Tvdb" and "S%sE%s" % (episode.Season, episode.Number) == map.get("episode")):
                        if not map.getparent().getparent().getparent().xpath("""./Title/%s""" % (provider)):                           
                            SubElement(map.getparent().getparent().getparent().xpath("""./Title""")[0], provider).text = (u'%s' % (data.Title))
                        if not map.getparent().getparent().getparent().xpath("""./Summary/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Summary""")[0], provider).text = (u'%s' % (data.Summary))
                        if not map.getparent().getparent().getparent().xpath("""./Originally_Available_At/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Originally_Available_At""")[0], provider).text = (u'%s' % (data.Originally_Available_At))                        
                        if not map.getparent().getparent().getparent().xpath("""./Rating/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Rating""")[0], provider).text = (u'%s' % (data.Rating))
                        if not map.getparent().getparent().getparent().xpath("""./Studio/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Studio""")[0], provider).text = (u'%s' % (data.Studio))
                        if not map.getparent().getparent().getparent().xpath("""./Countries/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Countries""")[0], provider).text = (u'%s' % (data.Countries))
                        if not map.getparent().getparent().getparent().xpath("""./Duration/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Duration""")[0], provider).text = (u'%s' % (data.Duration))
                        if not map.getparent().getparent().getparent().xpath("""./Genres/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Genres""")[0], provider).text = (u'%s' % (data.Genres))
                        if not map.getparent().getparent().getparent().xpath("""./Tags/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Tags""")[0], provider).text = (u'%s' % (data.Tags))
                        if not map.getparent().getparent().getparent().xpath("""./Collections/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Collections""")[0], provider).text = (u'%s' % (data.Collections))
                        if not map.getparent().getparent().getparent().xpath("""./Content_Rating/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Content_Rating""")[0], provider).text = (u'%s' % (data.Content_Rating))
                        if not map.getparent().getparent().getparent().xpath("""./Writers/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Writers""")[0], provider).text = (u'%s' % (data.Writers))
                        if not map.getparent().getparent().getparent().xpath("""./Directors/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Directors""")[0], provider).text = (u'%s' % (data.Directors))
                        if not map.getparent().getparent().getparent().xpath("""./Producers/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Producers""")[0], provider).text = (u'%s' % (data.Producers))
                        if not map.getparent().getparent().getparent().xpath("""./Roles/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Roles""")[0], provider).extend(data.Roles)
                        if not map.getparent().getparent().getparent().xpath("""./Posters/%s""" % (provider)):
                            SubElement(map.getparent().getparent().getparent().xpath("""./Posters""")[0], provider).extend(data.Posters)
                        SubElement(map.getparent().getparent().xpath("""./Title""")[0], provider).text =  (u'%s' % (episode.Title))
                        SubElement(map.getparent().getparent().xpath("""./FirstAired""")[0], provider).text = episode.FirstAired
                        SubElement(map.getparent().getparent().xpath("""./Rating""")[0], provider).text = episode.Rating
                        SubElement(map.getparent().getparent().xpath("""./Overview""")[0], provider).text = episode.Overview
                        SubElement(map.getparent().getparent().xpath("""./Poster""")[0], provider).text = episode.Poster                    
    return root 

  