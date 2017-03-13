import re, time, unicodedata, hashlib, types, os, inspect, datetime, xml, string, tvdb, anidb, scudlee, functions, constants, copy, logging

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
        
        langTitle = functions.GetPreferedTitle(element).replace("`", "'")
        matchedTitle = functions.CleanTitle(entry.text)
        
        if matchedTitle.lower() == orig_title.lower():
            score = 100
        else:      
            score = 90 # Start word matches off at a slight defecit compared to guid matches.

            # Remove year suffixes that can mess things up.
            searchTitle = orig_title
            if len(orig_title) > 8:
                searchTitle = re.sub(r'([ ]+\(?[0-9]{4}\)?)', '', searchTitle)

            foundTitle = matchedTitle
            if len(foundTitle) > 8:
                foundTitle = re.sub(r'([ ]+\(?[0-9]{4}\)?)', '', foundTitle)

            # Remove prefixes that can screw things up.
            searchTitle = re.sub('^[Bb][Bb][Cc] ', '', searchTitle)
            foundTitle = re.sub('^[Bb][Bb][Cc] ', '', foundTitle)

            # Score adjustment for title distance.
            score = score - int(30 * (1 - functions.lev_ratio(searchTitle, foundTitle)))
    
        Log("Score: '%s', '%s', '%s', '%s', '%s'" % (score, functions.lev_ratio(orig_title, matchedTitle), orig_title, matchedTitle, entry.text))
        
        self.Entry = entry
        self.Id = id
        self.Title = langTitle
        self.Score = score       

        
def GetAnimeTitleByID(Id):
    return functions.GetAnimeTitleByID(scudlee.TitleTree(), Id)
    
    
def GetAnimeTitleByName(Name, OrignalName): 
    return functions.GetAnimeTitleByName(scudlee.TitleTree(), Name, OrignalName)  
       
       
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

            
def ExportMap(map, filename):
    data = copy.deepcopy(map)
    for item in data.xpath("""./Season/Episode/Filename"""):
        item.getparent().remove(item)
    for item in data.xpath("""./Season/Episode/Streams"""):
        item.getparent().remove(item)    
    functions.SaveFile(etree.tostring(data, pretty_print=True, xml_declaration=True, encoding="UTF-8"), filename, "Bundles\\", constants.ExportBundles)
 
 
def SearchMap(season, episode, filename, root, anidbid=None):
    data = []
    if re.search(r".*\b(?P<season>S\d+)(?P<episode>E\d+)\b.*", filename, re.IGNORECASE) or re.search(r".*\b(?P<type>ncop|op|nced|ed)(?P<episode>\d+)\b.*", filename, re.IGNORECASE):
        mappedEpisode = root.xpath("""./Mapping/Series/Episode[@tvdb="S%sE%s"]""" % (str(season).zfill(2), str(episode).zfill(2)))  
        if mappedEpisode: 
            data.append(["Anidb", mappedEpisode[0].getparent().get("anidbid"), mappedEpisode[0].get("anidb")])
            data.append(["Tvdb", mappedEpisode[0].getparent().get("tvdbid"), mappedEpisode[0].get("tvdb")])
        else:
            match = re.search(r".*\B\[(?P<provider>\D+)(?P<id>\d+)\]\B.*", filename, re.IGNORECASE)
            if match:
                provider = match.group('provider').lower()
                data.append(["Anidb", match.group('id').lower(), anidb.ParseNoFromSeason(int(season), int(episode))])
                
        mappedEpisode = root.xpath("""./Mapping/Series[@anidbid="%s"]/Episode[@anidb="%s"]""" % (anidbid, anidb.ParseNoFromSeason(int(season), int(episode))))
        if mappedEpisode: 
            data.append(["Anidb", mappedEpisode[0].getparent().get("anidbid"), mappedEpisode[0].get("anidb")])
            data.append(["Tvdb", mappedEpisode[0].getparent().get("tvdbid"), mappedEpisode[0].get("tvdb")])
    return data

    
def GenerateSeason(root, media_season):
    season = root.find("""./Season[@num="%s"]""" % (media_season))
    if season == None:
        season = SubElement(root, "Season", num=media_season)
        for attrib in constants.SeriesAttribs:
            SubElement(season, attrib)
    return season

    
def GenerateEpisode(root, season, media_season, media_episode):
    episode = root.find("""./Season[@num="%s"]/Episode[num="%s"]""" % (media_season, media_episode))
    if episode == None:
        episode = SubElement(season, "Episode", num=media_episode)
        for attrib in constants.EpisodeAttribs:
            SubElement(episode, attrib)
    return episode
   
   
def MapSeries(mappingData):
    logging.Log_Milestone("MapSeries")
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
                        status = "scudlee missing"
                        tvdbParse = tvdb.ParseNoFromSeason(0, 0, ScudLee.DefaultTvdbSeason) 
                        if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (season.TvdbSeason, str(i + int(season.Offset)))):
                            status = ""
                            tvdbParse = tvdb.ParseNoFromSeason(int(season.TvdbSeason), i + int(season.Offset), ScudLee.DefaultTvdbSeason)
                        SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), i)), tvdb=tvdbParse, status=status)       
                            
                if season.Text != None:
                    for string in filter(None, season.Text.split(";")):
                        for i in range(0, len(string.split("-")[1].split("+"))):
                            status = "scudlee missing"
                            tvdbParse = tvdb.ParseNoFromSeason(0, 0, ScudLee.DefaultTvdbSeason)
                            if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (season.TvdbSeason, string.split("-")[1].split("+")[i].zfill(2))) and "S%sE%s" % (season.TvdbSeason, string.split("-")[1].split("+")[i].zfill(2)) != "S00E00":
                                status = ""
                                tvdbParse = tvdb.ParseNoFromSeason(int(season.TvdbSeason), int(string.split("-")[1].split("+")[i]), ScudLee.DefaultTvdbSeason)
                            elif not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (season.TvdbSeason, string.split("-")[1].split("+")[i].zfill(2))):
                                status = "tvdb missing"
                            SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(int(season.AnidbSeason), string.split("-")[0])), tvdb=tvdbParse, status=status)
                            
            if not ScudLee.Absolute: 
                for i in range(1, AniDB.EpisodeCount+1):
                    status = "scudlee missing"
                    tvdbParse = "S00E00"
                    if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (anidb.ParseNoFromSeason(1, i))):
                        if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % (str(ScudLee.DefaultTvdbSeason).zfill(2), 'S' + str(i + ScudLee.EpisodeOffset).zfill(2))):
                            status = ""
                            tvdbParse = "S%sE%s" % (str(ScudLee.DefaultTvdbSeason).zfill(2), str(i + ScudLee.EpisodeOffset).zfill(2))
                        SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(1, i)), tvdb=tvdbParse, status=status)                                                               
                
                for i in range(1, AniDB.SpecialCount+1):
                    status = "scudlee missing"
                    tvdbParse = "S00E00"
                    if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (anidb.ParseNoFromType(2, i))):
                        if not mapping.xpath("""./Series/Episode[@tvdb="S%sE%s"]""" % ("00", str(i + ScudLee.EpisodeOffset).zfill(2))):
                            status = ""
                            tvdbParse = "S%sE%s" % ("00", str(i + ScudLee.EpisodeOffset).zfill(2))
                        SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromType(2, i)), tvdb=tvdbParse, status=status)                       
                
                for opening in AniDB.OpList:                          
                    if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (opening)):
                        SubElement(seriesMap, "Episode", anidb="%s" % (opening), tvdb="%s" % (anidb.ParseLocalNoFromType(3, openingEpsNo, "op")), status="")
                        openingEpsNo = openingEpsNo + 1
                
                for ending in AniDB.EdList:
                    if not seriesMap.xpath("""./Episode[@anidb="%s"]""" % (ending)):
                        SubElement(seriesMap, "Episode", anidb="%s" % (ending), tvdb="%s" % (anidb.ParseLocalNoFromType(3, endingEpsNo, "ed")), status="")  
                        endingEpsNo = endingEpsNo + 1                               
            else:
                TvDB = tvdb.TvDB(ScudLee.TvdbId)
                for episode in TvDB.Episodes if TvDB.Episodes else []:
                    if episode.Absolute_Index: 
                        if episode.Absolute_Index > ScudLee.EpisodeOffset and episode.Absolute_Index <= AniDB.EpisodeCount + ScudLee.EpisodeOffset:
                            SubElement(seriesMap, "Episode", anidb="%s" % (anidb.ParseNoFromSeason(1, episode.Absolute_Index - ScudLee.EpisodeOffset))
                                                           , tvdb="S%sE%s" % (episode.Season, episode.Number)
                                                           , status="")        
            
            seriesMap[:] = sorted(seriesMap, key=lambda x: (0 if re.sub('[^A-Z]','', x.get("anidb")) else 1, int(re.sub('[^0-9]','', x.get("anidb")))))  
        
        unmappedlist = sorted(mapping.xpath("""./Series/Episode[@tvdb="S00E00" and @missing!=""]"""), key=lambda x: x.getparent().get("anidbid"))  
        if unmappedlist:
            unmapped = SubElement(mapping, "Unmapped")
            i = 1
            for episode in unmappedlist:
                Log("Unmapped: '%s', '%s' , '%s'" % (episode.getparent().get("anidbid"), episode.get("anidb"), episode.get("missing")))
                SubElement(unmapped, "Episode", anidbid = episode.getparent().get("anidbid"), anidb = episode.get("anidb"), missing = episode.get("missing"), id = str(i))
                i = i + 1
    logging.Log_Milestone("MapSeries")
    return root

    
def MapLocal(media, root, anidbid):
    logging.Log_Milestone("MapLocal")
    @parallelize
    def mapSeasons():
        for media_season in sorted(media.seasons, key=lambda x: int(x),  reverse=False):
            season = GenerateSeason(root, media_season)
            @task
            def mapSeason(media_season=media_season, season=season): #, guessId=guessId):
                @parallelize
                def mapEpisodes():
                    for media_episode in sorted(media.seasons[media_season].episodes, key=lambda x: int(x),  reverse=False):
                        episode = GenerateEpisode(root, season, media_season, media_episode)
                        @task
                        def mapEpisode(media_season=media_season, media_episode=media_episode, season=season, episode=episode): #, guessId=guessId):
                            MapEpisode(media, root, media_season, media_episode, anidbid, season, episode)
    logging.Log_Milestone("MapLocal")                                                     
  
  
def MapEpisode(media, root, media_season, media_episode, anidbid, season = None, episode = None):
    logging.Log_Milestone("MapEpisode_S"+str(media_season)+"E"+(str(media_episode)))
    if season == None:
        season = GenerateSeason(root, media_season)
                    
    if episode == None:
        episode = GenerateEpisode(root, season, media_season, media_episode)
                                
    streams = SubElement(episode, "Streams")
    for media_item in media.seasons[media_season].episodes[media_episode].items:
        for item_part in media_item.parts:
            filename = os.path.splitext(os.path.basename(item_part.file.lower()))[0]
            for stream in item_part.streams:
                SubElement(streams, "Stream", type=str(constants.StreamTypes.get(stream.type, "und")), lang=str(getattr(stream, "language", getattr(stream, "language", "und"))))
    
    mapped = SubElement(episode, "Mapped")    
    for match in SearchMap(media_season, media_episode, filename, root, anidbid):
        SubElement(mapped, match[0], series=match[1], episode=match[2])         
    logging.Log_Milestone("MapEpisode_S"+str(media_season)+"E"+(str(media_episode)))
   
   
def MapMeta(root):
    logging.Log_Milestone("MapMeta")
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
                                
                        if not map.getparent().getparent().getparent().get("%s" % provider + "Id"):    
                            map.getparent().getparent().getparent().attrib["%s" % provider + "Id"] = map.get("series")
                            
                        for episode in data.Episodes: 
                            if (provider == "Anidb" and "%s" % (episode.Number) == map.get("episode")) or (provider == "Tvdb" and "S%sE%s" % (episode.Season, episode.Number) == map.get("episode")):
                                for attrib in constants.SeriesAttribs:
                                    if not map.getparent().getparent().getparent().xpath("""./%s/%s""" % (attrib, provider)):
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
    logging.Log_Milestone("MapMeta")                                            

    
def MapMedia(root, metadata, anidbId, tvdbID):
    logging.Log_Milestone("MapMedia")
    seriesPopulated = []
    streamTag = []
    @parallelize
    def Episode_Par():
        for map in root.xpath("""./Season/Episode"""):
            @task
            def Episode_Task(map=map, metadata=metadata, anidbId=anidbId, tvdbID=tvdbID, seriesPopulated=seriesPopulated):
                season = map.getparent().get('num')
                episode = map.get('num')
               
               
                if (str(anidbId) + str(tvdbID)) not in seriesPopulated and (anidbId == map.getparent().get('AnidbId') or (anidbId == "" and tvdbID == map.getparent().get('TvdbId'))):
                    seriesPopulated.append(str(anidbId) + str(tvdbID))
                    logging.Log_Milestone("MapMedia_Season_" + str(anidbId) + str(tvdbID))
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
                    logging.Log_Milestone("MapMedia_Season_" + str(anidbId) + str(tvdbID))
                
                logging.Log_Milestone("MapMedia_Episode_S" + season + "E" + episode)
                metadata.seasons[season].episodes[episode].title = functions.PopulateMetadata(map.xpath("""./Title/*[node()]"""), str, constants.EPISODE_TITLE_PRIORITY)
                metadata.seasons[season].episodes[episode].summary = functions.PopulateMetadata(map.xpath("""./Summary/*[node()]"""), str, constants.EPISODE_SUMMARY_PRIORITY)
                metadata.seasons[season].episodes[episode].originally_available_at = functions.PopulateMetadata(map.xpath("""./Originally_Available_At/*[node()]"""), datetime.date, constants.EPISODE_ORIGINALLYAVAILABLEAT_PRIORITY)
                metadata.seasons[season].episodes[episode].rating = functions.PopulateMetadata(map.xpath("""./Rating/*[node()]"""), float, constants.EPISODE_RATING_PRIORITY)
                metadata.seasons[season].episodes[episode].absolute_index = functions.PopulateMetadata(map.xpath("""./Absolute_Index/*[node()]"""), int, constants.EPISODE_ABSOLUTE_INDEX_PRIORITY)
                
                functions.PopulateMetadata(map.xpath("""./Writers/*[node()]"""), Framework.modelling.attributes.SetObject, constants.EPISODE_WRITERS_PRIORITY, metadata.seasons[season].episodes[episode].writers) 
                functions.PopulateMetadata(map.xpath("""./Directors/*[node()]"""), Framework.modelling.attributes.SetObject, constants.EPISODE_DIRECTORS_PRIORITY, metadata.seasons[season].episodes[episode].directors) 
                functions.PopulateMetadata(map.xpath("""./Producers/*[node()]"""), Framework.modelling.attributes.SetObject, constants.EPISODE_PRODUCERS_PRIORITY, metadata.seasons[season].episodes[episode].producers) 
                functions.PopulateMetadata(map.xpath("""./Thumbs//Image"""), Framework.modelling.attributes.ProxyContainerObject, constants.EPISODE_THUMBS_PRIORITY, metadata.seasons[season].episodes[episode].thumbs)
                if map.xpath("""count(./Streams/Stream[@type="%s"][@lang="%s"])""" % ("audio", "eng")) > 0 and not "English Dubbed" in metadata.collections:
                    metadata.collections.add("English Dubbed")
                    streamTag.append("English Dubbed")
                if map.xpath("""count(./Streams/Stream[@type="%s"][@lang="%s"])""" % ("audio", "jpn")) > 0 and map.xpath("""count(./Streams/Stream[@type="%s"][@lang="%s"])""" % ("subtitle", "eng")) > 0 and not "English Subbed" in metadata.collections: 
                    metadata.collections.add("English Subbed")
                    streamTag.append("English Subbed")
                logging.Log_Milestone("MapMedia_Episode_S" + season + "E" + episode)
    logging.Log_Milestone("MapMedia")