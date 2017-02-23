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
                            if episode.Absolute_Index: 
                                if episode.Absolute_Index > ScudLee.EpisodeOffset and episode.Absolute_Index <= AniDB.EpisodeCount + ScudLee.EpisodeOffset:
                                    #Log("Common - MapSeries() - Ab: %s, Eo: %s, Es: %s, Ee: %s" % (episode.Absolute, ScudLee.EpisodeOffset, episode.Season, episode.Number))
                                    SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(1, episode.Absolute_Index - ScudLee.EpisodeOffset))
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
                SubElement(season, "Images")
                SubElement(season, "Themes")
                
                @parallelize
                def mapEpisodes():
                    for media_episode in sorted(media.seasons[media_season].episodes, key=lambda x: int(x),  reverse=False):
                        @task
                        def mapEpisode(media_season=media_season, media_episode=media_episode, mapping=mapping, guessId=guessId):
                            episode = SubElement(season, "Episode", num=media_episode)
                            mapped = SubElement(episode, "Mapped")
                            streams = SubElement(episode, "Streams")
                            SubElement(episode, "Title")
                            SubElement(episode, "Summary")
                            SubElement(episode, "Originally_Available_At")
                            SubElement(episode, "Rating")
                            SubElement(episode, "Absolute_Index")
                            SubElement(episode, "Writers")
                            SubElement(episode, "Directors")
                            SubElement(episode, "Producers")
                            SubElement(episode, "Thumbs")

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
                                                                     
                            #SubElement(episode, "Collection").text = ";".join(collection)                            
    return root

def MapMeta(root): 
    providers = ["Anidb", "Tvdb"]
    @parallelize
    def Provider_Par():
        for provider in providers:
            @task
            def Provider_Task(root=root, provider=provider):
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
                                for attrib in constants.SeriesAttribs:
                                    if not map.getparent().getparent().getparent().xpath("""./%s/%s""" % (attrib, provider)):
                                        if getattr(data, attrib):
                                            if not isinstance(getattr(data, attrib), type(Element("None"))):
                                                SubElement(map.getparent().getparent().getparent().xpath("""./%s""" % (attrib))[0], provider).text = (u'%s' % (getattr(data, attrib)))
                                            else:
                                                SubElement(map.getparent().getparent().getparent().xpath("""./%s""" % (attrib))[0], provider).extend(getattr(data, attrib))
                                          
                                for attrib in constants.EpisodeAttribs:
                                    if getattr(episode, attrib):
                                        if not isinstance(getattr(episode, attrib), type(Element("None"))):
                                            SubElement(map.getparent().getparent().xpath("""./%s""" % (attrib))[0], provider).text =  (u'%s' % (getattr(episode, attrib)))
                                        else:
                                            SubElement(map.getparent().getparent().xpath("""./%s""" % (attrib))[0], provider).extend(getattr(episode, attrib))
 
    return root 

def MapMedia(root, metadata):
    for map in root.xpath("""./Season/Episode"""):
        season = map.getparent().get('num')
        episode = map.get('num')
        if map.getparent().xpath("""./Title"""):
            metadata.title = functions.GetByPriority(map.getparent().xpath("""./Title/*[node()]"""), constants.SERIES_TITLE_PRIORITY)
        if map.getparent().xpath("""./Summary"""):
            metadata.summary = functions.GetByPriority(map.getparent().xpath("""./Summary/*[node()]"""), constants.SERIES_SUMMARY_PRIORITY)
        if map.getparent().xpath("""./Originally_Available_At"""):
            metadata.originally_available_at = datetime.datetime.strptime(functions.GetByPriority(map.getparent().xpath("""./Originally_Available_At/*[node()]"""), constants.SERIES_ORIGINALLYAVAILABLEAT_PRIORITY), "%Y-%m-%d").date()
        if map.getparent().xpath("""./Rating"""):
            metadata.rating = float(functions.GetByPriority(map.getparent().xpath("""./Rating/*[node()]"""), constants.SERIES_RATING_PRIORITY))
        if map.getparent().xpath("""./Studio"""):
            metadata.studio = functions.GetByPriority(map.getparent().xpath("""./Studio/*[node()]"""), constants.SERIES_STUDIO_PRIORITY)
        if map.getparent().xpath("""./Countries"""):
            metadata.countries.clear()
            for country in functions.GetByPriorityList(map.getparent().xpath("""./Countries/*[node()]"""), constants.SERIES_PRODUCERS_PRIORITY): 
                metadata.countries.add(country) 
        if map.getparent().xpath("""./Duration"""):
            metadata.duration = int(float(functions.GetByPriority(map.getparent().xpath("""./Duration/*[node()]"""), constants.SERIES_DURATION_PRIORITY)))
        if map.getparent().xpath("""./Genres"""):
            metadata.genres.clear()
            for genre in functions.GetByPriorityList(map.getparent().xpath("""./Genres/*[node()]"""), constants.SERIES_GENRES_PRIORITY): 
                metadata.genres.add(genre)
        if map.getparent().xpath("""./Tags"""):
            metadata.tags.clear()
            for tag in functions.GetByPriorityList(map.getparent().xpath("""./Tags/*[node()]"""), constants.SERIES_TAGS_PRIORITY): 
                metadata.tags.add(tag)   
        if map.getparent().xpath("""./Collections"""):
            metadata.collections.clear()
            for collection in functions.GetByPriorityList(map.getparent().xpath("""./Collections/*[node()]"""), constants.SERIES_COLLECTIONS_PRIORITY): 
                metadata.collections.add(collection)
        if map.getparent().xpath("""./Content_Rating"""):
            metadata.content_rating = functions.GetByPriority(map.getparent().xpath("""./Content_Rating/*[node()]"""), constants.SERIES_CONTENTRATING_PRIORITY)                
        #if map.getparent().xpath("""./Writers"""):
        #    metadata.writers.clear()
        #    for writer in functions.GetByPriorityList(map.getparent().xpath("""./Writers/*"""), constants.SERIES_WRITERS_PRIORITY): 
        #        metadata.writers.add(writer) 
        #if map.getparent().xpath("""./Directors"""):
        #    metadata.directors.clear()
        #    for director in functions.GetByPriorityList(map.getparent().xpath("""./Directors/*"""), constants.SERIES_DIRECTORS_PRIORITY): 
        #        metadata.directors.add(director) 
        #if map.getparent().xpath("""./Producers"""):
        #    metadata.producers.clear()
        #    for producer in functions.GetByPriorityList(map.getparent().xpath("""./Producers/*"""), constants.SERIES_PRODUCERS_PRIORITY): 
        #        metadata.producers.add(producer) 
        if map.getparent().xpath("""./Roles"""):
            functions.AddPeople(map.getparent().xpath("""./Roles/*[node()]"""), constants.SERIES_ROLES_PRIORITY, metadata.roles)
        Log("Season: '%s', Episode: '%s'" % (season, episode))
        if map.xpath("""./Title/Anidb"""):
            metadata.seasons[season].episodes[episode].title = map.xpath("""./Title/Anidb""")[0].text
        if map.xpath("""./Summary/Tvdb"""):
            metadata.seasons[season].episodes[episode].summary = map.xpath("""./Summary/Tvdb""")[0].text