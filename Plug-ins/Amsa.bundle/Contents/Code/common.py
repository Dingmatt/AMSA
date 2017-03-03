import re, time, unicodedata, hashlib, types, os, inspect, datetime, xml, string, tvdb, anidb, scudlee, functions, constants, copy

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
        cleanTitle = functions.CleanTitle(langTitle)

        if cleanTitle.lower() == orig_title.lower():
            score = 100
        else:      
            score = 90 # Start word matches off at a slight defecit compared to guid matches.

            # Remove year suffixes that can mess things up.
            searchTitle = orig_title
            if len(orig_title) > 8:
                searchTitle = re.sub(r'([ ]+\(?[0-9]{4}\)?)', '', searchTitle)

            foundTitle = cleanTitle
            if len(foundTitle) > 8:
                foundTitle = re.sub(r'([ ]+\(?[0-9]{4}\)?)', '', foundTitle)

            # Remove prefixes that can screw things up.
            searchTitle = re.sub('^[Bb][Bb][Cc] ', '', searchTitle)
            foundTitle = re.sub('^[Bb][Bb][Cc] ', '', foundTitle)

            # Adjust if both have 'the' prefix by adding a prefix that won't be stripped.
            distTitle = searchTitle
            distFoundTitle = foundTitle
            if searchTitle.lower()[0:4] == 'the ' and foundTitle.lower()[0:4] == 'the ':
                distTitle = 'xxx' + searchTitle
                distFoundTitle = 'xxx' + foundTitle

            # Score adjustment for title distance.
            score = score - int(30 * (1 - functions.lev_ratio(searchTitle, foundTitle)))
    
        Log("Score: '%s', '%s', '%s', '%s'" % (score, functions.lev_ratio(orig_title, cleanTitle), orig_title, cleanTitle))
        
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
        openingEpsNo = 101
        endingEpsNo = 151        
        for item in mappingData.SeriesList if mappingData.SeriesList else []:
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
                
                for opening in AniDB.OpList:                          
                    if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (opening)):
                        SubElement(seriesMap, "Episode", anidb="%s" % (opening)
                                                       , tvdb="%s" % (anidb.ParseLocalNoFromType(3, openingEpsNo, "op")))
                        openingEpsNo = openingEpsNo + 1
                
                
                for ending in AniDB.EdList:
                    if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (ending)):
                        SubElement(seriesMap, "Episode", anidb="%s" % (ending)
                                                       , tvdb="%s" % (anidb.ParseLocalNoFromType(3, endingEpsNo, "ed")))  
                        endingEpsNo = endingEpsNo + 1                               
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
    @parallelize
    def mapSeasons():
        for media_season in sorted(media.seasons, key=lambda x: int(x),  reverse=False):
            season = root.find("""./Season[@num="%s"]""" % (media_season))
            if season == None:
                Log("MapEpisode - Season Missing")
                season = SubElement(root, "Season", num=media_season)
                for attrib in constants.SeriesAttribs:
                    SubElement(season, attrib)
            @task
            def mapSeason(media_season=media_season, season=season): #, guessId=guessId):
                @parallelize
                def mapEpisodes():
                    for media_episode in sorted(media.seasons[media_season].episodes, key=lambda x: int(x),  reverse=False):
                        episode = root.find("""./Season[@num="%s"]/Episode[num="%s"]""" % (media_season, media_episode))
                        if episode == None:
                            Log("MapEpisode - Episode Missing")
                            episode = SubElement(season, "Episode", num=media_episode)
                            for attrib in constants.EpisodeAttribs:
                                SubElement(episode, attrib)
                        @task
                        def mapEpisode(media_season=media_season, media_episode=media_episode, season=season, episode=episode): #, guessId=guessId):
                            MapEpisode(media, root, media_season, media_episode, anidbid, season, episode)
                                                         

def MapEpisode(media, root, media_season, media_episode, anidbid, season = None, episode = None):
    if season == None:
        season = root.find("""./Season[@num="%s"]""" % (media_season))
        if season == None:
            Log("MapEpisode - Season Missing")
            season = SubElement(root, "Season", num=media_season)
            for attrib in constants.SeriesAttribs:
                SubElement(season, attrib)
                    
    if episode == None:
        episode = root.find("""./Season[@num="%s"]/Episode[num="%s"]""" % (media_season, media_episode))
        if episode == None:
            Log("MapEpisode - Episode Missing")
            episode = SubElement(season, "Episode", num=media_episode)
            for attrib in constants.EpisodeAttribs:
                SubElement(episode, attrib)
                                
    Log("MapEpisode - Season: '%s', Episode: '%s'" %(media_season, media_episode))
    mapped = SubElement(episode, "Mapped")
    streams = SubElement(episode, "Streams")
    
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
            #guessEpisode = None
            if re.search(r".*\b(?P<season>S\d+)(?P<episode>E\d+)\b.*", filename, re.IGNORECASE) or re.search(r".*\b(?P<type>ncop|op|nced|ed)(?P<episode>\d+)\b.*", filename, re.IGNORECASE):
                mappedEpisode = root.xpath("""./Mapping/Series/Episode[@tvdb="S%sE%s"]""" % (str(media_season).zfill(2), str(media_episode).zfill(2)))
                if mappedEpisode: 
                    Log("Mapped: '%s', 'S%sE%s'" % (filename, media_season, media_episode))
                    anidbSeriesNumber = mappedEpisode[0].getparent().get("anidbid")
                    anidbEpisodeNumber = mappedEpisode[0].get("anidb")
                    tvdbSeriesNumber = mappedEpisode[0].getparent().get("tvdbid")
                    tvdbEpisodeNumber = mappedEpisode[0].get("tvdb")  
                else:
                    Log("Override: '%s'" % (filename))
                    match = re.search(r".*\B\[(?P<provider>\D+)(?P<id>\d+)\]\B.*", filename, re.IGNORECASE)
                    if match:
                        provider = match.group('provider').lower()
                        anidbSeriesNumber = match.group('id').lower()
                        Log("Season: '%s', Episode: '%s'" %(media_season, media_episode))
                        anidbEpisodeNumber = anidb.ParseNoFromSeason(int(media_season), int(media_episode))
                    #else:
                    #    guessEpisode = root.xpath("""./Mapping/Unmapped/Episode[@id="%s"]""" % (guessId)) 
                    #    if guessEpisode:
                    #        anidbSeriesNumber = guessEpisode[0].get("anidbid")
                    #        anidbEpisodeNumber = guessEpisode[0].get("anidb")
                    #        #Log("mappedEpisode: '%s', '%s', '%s', '%s'" % (guessEpisode, guessId, anidbSeriesNumber, anidbEpisodeNumber))
            elif re.search(r".*\b(?P<episode>E\d+)\b.*", filename, re.IGNORECASE):
                Log("Absolute: '%s'" % (filename))
                mappedEpisode = root.xpath("""./Mapping/Series[@anidbid="%s"]/Episode[@anidb="%s"]""" % (anidbid, anidb.ParseNoFromSeason(int(media_season), int(media_episode))))
                anidbSeriesNumber = mappedEpisode[0].getparent().get("anidbid")
                anidbEpisodeNumber = mappedEpisode[0].get("anidb")
                tvdbSeriesNumber = mappedEpisode[0].getparent().get("tvdbid")
                tvdbEpisodeNumber = mappedEpisode[0].get("tvdb")  
            
            if anidbSeriesNumber != "" and anidbEpisodeNumber != "": #and guessEpisode == None:                                    
                SubElement(mapped, "Anidb", episode=anidbEpisodeNumber, series=anidbSeriesNumber)
            #elif anidbSeriesNumber != "" and anidbEpisodeNumber != "":
            #    SubElement(mapped, "Anidb", episode=anidbEpisodeNumber, series=anidbSeriesNumber, guess=str(guessId - 1))
            if tvdbSeriesNumber != "" and tvdbEpisodeNumber != "":   
                SubElement(mapped, "Tvdb", episode=tvdbEpisodeNumber, series=tvdbSeriesNumber)
                                             
    #SubElement(episode, "Collection").text = ";".join(collection)    
    
def MapMeta(root): 
    providers = ["Anidb", "Tvdb"]
    @parallelize
    def Provider_Par():
        for provider in providers:
            @task
            def Provider_Task(root=root, provider=provider):
                data = None
                for map in sorted(root.xpath("""./Season/Episode/Mapped/%s""" % (provider)), key=lambda x: int(x.get("series") if x.get("series") else 0)):
                    Log("Season: %s, Episode: %s" % (map.getparent().getparent().getparent().get("num"), map.getparent().getparent().get("num")))
                    if map.get("series"):
                        for existing in map.getparent().getparent().xpath(""".//%s""" % (provider)):
                            if not existing.getparent().tag == "Mapped":
                                existing.getparent().remove(existing)
                        if data == None or data.ID != map.get("series"):
                            if provider == "Anidb":
                                data = anidb.AniDB(map.get("series"))
                                map.getparent().getparent().getparent().attrib["AnidbId"] = data.ID
                            elif provider == "Tvdb":
                                data = tvdb.TvDB(map.get("series")) 
                                map.getparent().getparent().getparent().attrib["TvdbId"] = data.ID
                        for episode in data.Episodes: 
                            
                            if (provider == "Anidb" and "%s" % (episode.Number) == map.get("episode")) or (provider == "Tvdb" and "S%sE%s" % (episode.Season, episode.Number) == map.get("episode")):
                                for attrib in constants.SeriesAttribs:
                                    if not map.getparent().getparent().getparent().xpath("""./%s/%s""" % (attrib, provider)):
                                        #Log("Attrib: %s, %s, %s, %s" % (attrib, getattr(data, attrib), type(getattr(data, attrib)), type(getattr(data, attrib)) is type(Element("None"))))
                                        if getattr(data, attrib):
                                            if type(getattr(data, attrib)) is type(Element("None")):
                                                elementList = copy.deepcopy(getattr(data, attrib))
                                                SubElement(map.getparent().getparent().getparent().find("""./%s""" % (attrib)), provider).extend(elementList.getchildren())
                                            else:
                                                elementItem = copy.copy(getattr(data, attrib))
                                                SubElement(map.getparent().getparent().getparent().find("""./%s""" % (attrib)), provider).text = (u'%s' % (elementItem))
                                                
                                         
                                for attrib in constants.EpisodeAttribs:
                                    if getattr(episode, attrib):
                                        if type(getattr(episode, attrib)) is type(Element("None")):
                                            elementList = copy.deepcopy(getattr(episode, attrib))
                                            SubElement(map.getparent().getparent().find("""./%s""" % (attrib)), provider).extend(elementList)
                                        else:
                                            elementItem = copy.copy(getattr(episode, attrib))
                                            SubElement(map.getparent().getparent().find("""./%s""" % (attrib)), provider).text =  (u'%s' % (elementItem))
                                            

def MapMedia(root, metadata, anidbId, tvdbID):
    seriesPopulate = True
    for map in root.xpath("""./Season/Episode"""):
        season = map.getparent().get('num')
        episode = map.get('num')
        
        Log("This: '%s' , '%s', '%s', '%s'" %(map.getparent().get('AnidbId'), map.getparent().get('TvdbId'), anidbId, tvdbID))
        if seriesPopulate and (anidbId == map.getparent().get('AnidbId') or (anidbId == "" and tvdbID == map.getparent().get('TvdbId'))):
            metadata.title = functions.PopulateMetadata(map.getparent().xpath("""./Title/*[node()]"""), str, constants.SERIES_TITLE_PRIORITY)
            metadata.summary = functions.PopulateMetadata(map.getparent().xpath("""./Summary/*[node()]"""), str, constants.SERIES_SUMMARY_PRIORITY)
            metadata.originally_available_at = functions.PopulateMetadata(map.getparent().xpath("""./Originally_Available_At/*[node()]"""), datetime.date, constants.SERIES_ORIGINALLYAVAILABLEAT_PRIORITY)
            metadata.rating = functions.PopulateMetadata(map.getparent().xpath("""./Rating/*[node()]"""), float, constants.SERIES_RATING_PRIORITY)
            metadata.studio = functions.PopulateMetadata(map.getparent().xpath("""./Studio/*[node()]"""), str, constants.SERIES_STUDIO_PRIORITY)
            functions.PopulateMetadata(map.getparent().xpath("""./Countries/*[node()]"""), list, constants.SERIES_COUNTRIES_PRIORITY, metadata.countries)
            metadata.duration = functions.PopulateMetadata(map.getparent().xpath("""./Duration/*[node()]"""), int, constants.SERIES_DURATION_PRIORITY)
            functions.PopulateMetadata(map.getparent().xpath("""./Genres/*[node()]"""), list, constants.SERIES_GENRES_PRIORITY, metadata.genres)
            functions.PopulateMetadata(map.getparent().xpath("""./Tags/*[node()]"""), list, constants.SERIES_TAGS_PRIORITY, metadata.tags)
            functions.PopulateMetadata(map.getparent().xpath("""./Collections/*[node()]"""), list, constants.SERIES_COLLECTIONS_PRIORITY, metadata.collections)
            metadata.content_rating = functions.PopulateMetadata(map.getparent().xpath("""./Content_Rating/*[node()]"""), str, constants.SERIES_CONTENTRATING_PRIORITY)
            functions.PopulateMetadata(map.getparent().xpath("""./Roles/*[node()]"""), Framework.modelling.attributes.SetObject, constants.SERIES_ROLES_PRIORITY, metadata.roles)   
            functions.PopulateMetadata(map.getparent().xpath("""./Posters//Image"""), Framework.modelling.attributes.ProxyContainerObject, constants.SERIES_IMAGES_PRIORITY, metadata.posters)
            functions.PopulateMetadata(map.getparent().xpath("""./Art//Image"""), Framework.modelling.attributes.ProxyContainerObject, constants.SERIES_IMAGES_PRIORITY, metadata.art)
            functions.PopulateMetadata(map.getparent().xpath("""./Banners//Image"""), Framework.modelling.attributes.ProxyContainerObject, constants.SERIES_IMAGES_PRIORITY, metadata.banners)
            functions.PopulateMetadata(map.getparent().xpath("""./Season//Image"""), Framework.modelling.attributes.ProxyContainerObject, constants.SERIES_IMAGES_PRIORITY, metadata.seasons)
            seriesPopulate = False
            
        if map.xpath("""./Title/Anidb"""):
            metadata.seasons[season].episodes[episode].title = map.xpath("""./Title/Anidb""")[0].text
        if map.xpath("""./Summary/Tvdb"""):
            metadata.seasons[season].episodes[episode].summary = map.xpath("""./Summary/Tvdb""")[0].text