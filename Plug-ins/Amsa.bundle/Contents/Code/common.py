import re, time, unicodedata, hashlib, types, os, inspect, datetime, xml, string, tvdb, anidb
from time import sleep
from datetime import timedelta  
from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment

class Common():
    global AniDB_WaitUntil
    CacheDirectory = "Cache"
    CachePath = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "..", "..", "..", "..", "Plug-in Support\Data\com.plexapp.agents.amsa_test\DataItems", CacheDirectory))                                                
    ANIDB_TVDB_MAPPING              = "http://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-list-master.xml"                                                                                
    ANIDB_COLLECTION                = "http://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-movieset-list.xml"
    ANIDB_TVDB_MAPPING_CUSTOM       = CacheDirectory + "\anime-list-custom.xml"   
    ANIDB_TVDB_MAPPING_CORRECTIONS  = "http://raw.githubusercontent.com/Dingmatt/AMSA/master/Plug-in%20Support/Data/com.plexapp.agents.amsa/DataItems/anime-list-corrections.xml"      
    AniDB_title_tree = None
    AniDB_TVDB_mapping_tree = None
    AniDB_collection_tree = None
    AniDB_WaitUntil = datetime.datetime.now()
    DefaultTimeout = 30
    DefaultCache = CACHE_1HOUR * 24
    HTTP.CacheTime = CACHE_1HOUR * 24
    netLock = Thread.Lock()
    
    Stream_Types = {1: "video", 2: "audio", 3: "subtitle"}

    def __init__(self):
        self.CleanCache()
        self.XMLFromURL(self.ANIDB_TVDB_MAPPING_CORRECTIONS, os.path.basename(self.ANIDB_TVDB_MAPPING_CORRECTIONS), "", CACHE_1HOUR * 24 * 2) 
        self.AniDB_title_tree        = self.XMLFromURL(anidb.ANIDB_TITLES, os.path.splitext(os.path.basename(anidb.ANIDB_TITLES))[0], "", CACHE_1HOUR * 24 * 2, 60)
        self.AniDB_TVDB_mapping_tree = self.XMLFromURL(self.ANIDB_TVDB_MAPPING, os.path.basename(self.ANIDB_TVDB_MAPPING), "", CACHE_1HOUR * 24 * 2)
        self.AniDB_collection_tree   = self.XMLFromURL(self.ANIDB_COLLECTION, os.path.basename(self.ANIDB_COLLECTION), "", CACHE_1HOUR * 24 * 2)                        
    #def CommonStart(self):
             

    def CleanCache(self):
        for root, dirs, _  in os.walk(self.CachePath, topdown=False):
            for directory in dirs:
                directory = os.path.join(root, directory)
                for file in os.listdir(directory):
                    file = os.path.join(directory, file)
                    if os.path.isfile(file) and os.stat(file).st_mtime < time.time() - 3 * 86400:
                        os.remove(file)   
                        Log.Debug("Common - CleanCache() - file: '%s'" % (file))
                try: 
                    if root.strip("\\\\?\\") != self.CachePath: 
                        os.rmdir(directory)   
                        Log.Debug("Common - CleanCache() - directory: '%s'" % (directory)) 
                except: pass  
        
    def XMLFromURL (self, url, filename="", directory="", cache=DefaultCache, timeout=DefaultTimeout):
        Log.Debug("Common - XMLFromURL() - url: '%s', filename: '%s'" % (url, filename))
        global AniDB_WaitUntil
        try:
            self.netLock.acquire()
            filename = os.path.join(self.CacheDirectory, directory, filename) 
            result = None
            if filename and Data.Exists(filename):       
                file = os.path.abspath(os.path.join(self.CachePath, "..", filename))
                Log.Debug("Common - XMLFromURL() - Filename: '%s', CacheTime: '%s', Limit: '%s'" % (file, time.ctime(os.stat(file).st_mtime), time.ctime(time.time() - cache)))
                if os.path.isfile(file) and os.stat(file).st_mtime > (time.time() - cache):
                    Log.Debug("Common - XMLFromURL() - Load from cache")  
                    result = Data.Load(filename)   
            
            if not result:
                try: 
                    if url.startswith(anidb.ANIDB_HTTP_API_URL):
                        while AniDB_WaitUntil > datetime.datetime.now(): 
                            sleep(1)
                        Log("Common - XMLFromURL() - AniDB AntiBan Delay")    
                        AniDB_WaitUntil = datetime.datetime.now() + timedelta(seconds=3) 
                    result = str(HTTP.Request(url, headers={'Accept-Encoding':'gzip', 'content-type':'charset=utf8'}, cacheTime=cache, timeout=timeout))
                except Exception as e: 
                    result = None 
                    Log.Debug("Common - XMLFromURL() - XML issue loading url: '%s', Exception: '%s'" % (url, e))                                                    
            
                if result and len(result) > 1024 and filename: 
                    try: self.SaveFile(result, os.path.basename(filename), directory)
                    except Exception as e: Log.Debug("Common - XMLFromURL() - url: '%s', filename: '%s' saving failed: %s" % (url, filename, e))
                elif filename and Data.Exists(filename):  # Loading locally if backup exists
                    Log.Debug("Common - XMLFromURL() - Loading locally since banned or empty file (result page <1024 bytes)")
                    try: result = Data.Load(filename)
                    except: Log.Debug("Common - XMLFromURL() - Loading locally failed but data present - url: '%s', filename: '%s'" % (url, filename)); return
            
            if url==self.ANIDB_TVDB_MAPPING and Data.Exists(self.ANIDB_TVDB_MAPPING_CUSTOM):
                if Data.Exists(self.ANIDB_TVDB_MAPPING_CORRECTIONS):
                    Log.Debug("Common - XMLFromURL() - Loading remote custom mapping - url: '%s'" % self.ANIDB_TVDB_MAPPING_CORRECTIONS)
                    result_remote_custom = Data.Load(self.ANIDB_TVDB_MAPPING_CORRECTIONS)
                    result = result_remote_custom[:result_remote_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:]      
                Log.Debug("Common - XMLFromURL() - Loading local custom mapping - url: '%s'" % self.ANIDB_TVDB_MAPPING_CUSTOM)
                result_custom = Data.Load(self.ANIDB_TVDB_MAPPING_CUSTOM)
                result = result_custom[:result_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:] 

            if result:
                result = XML.ElementFromString(result)
                if str(result).startswith("<Element error at "):  
                    Log.Debug("Common - XMLFromURL() - Not an XML file, AniDB banned possibly, result: '%s'" % result)
                else:       
                    return result  
        finally:
            self.netLock.release()
            
        return None

    def SaveFile(self, file, filename="", directory=""):   
        absoDirectory = os.path.join(self.CachePath, directory)
        directory = os.path.join(self.CacheDirectory, directory)
        filename = os.path.join(directory, filename) 
        if not os.path.exists(absoDirectory):
            Log.Debug("Common - SaveFile() - dir: '%s'" % (absoDirectory))
            os.makedirs(absoDirectory)
        Data.Save(filename, file)

    def GetElementText(self, el, xp):
        return el.xpath(xp)[0].text if el is not None and el.xpath(xp) and el.xpath(xp)[0].text else "" 
        
    def MapSeries(self, media, mappingXml):
        root = etree.tostring(E.Series(), pretty_print=True, xml_declaration=True, encoding='UTF-8')
        root = XML.ElementFromString(root)
        
        mapping = SubElement(root, "Mapping")
        for series in mappingXml if mappingXml else []:
            anidbid = series.get("anidbid")
            tvdbid = series.get("tvdbid")
            episodeoffset = int(series.get("episodeoffset")) if series.get("episodeoffset") else 0
            absolute = True if series.get("defaulttvdbseason") == "a" else False 
            data = None
            
            try: data = self.XMLFromURL(anidb.ANIDB_HTTP_API_URL + anidbid, anidbid+".xml", "AniDB\\" + anidbid, CACHE_1HOUR * 24).xpath('/anime')[0]
            except Exception as e: Log.Error("Init - Search() - AniDB Series XML: Exception raised: %s" % (e)) 
            if data: 
                episodecount = self.GetElementText(data, "episodecount") 
                Log.Debug("Common - MapSeries() - episodecount: '%s'" % episodecount)
                  
            seriesMap = SubElement(mapping, "Series", anidbid=anidbid, tvdbid=tvdbid, episodeoffset=str(episodeoffset), absolute=str(absolute))
            
            for season in series.xpath("""./mapping-list/mapping""") if mappingXml else []:
                if season.get("offset"): 
                    i = int(season.get("start"))
                    for i in range(int(season.get("start")), int(season.get("end"))+1):
                        SubElement(seriesMap, "Episode", anidb="S%sE%s" % (season.get("anidbseason").zfill(2), str(i).zfill(2)), tvdb="S%sE%s" % (season.get("tvdbseason").zfill(2),str(i + int(season.get("offset"))).zfill(2)))
                
                if season.text != None:
                    for string in filter(None, season.text.split(';')): 
                        SubElement(seriesMap, "Episode", anidb="S%sE%s" % (season.get("anidbseason").zfill(2), string.split('-')[0].zfill(2)), tvdb="S%sE%s" % (season.get("tvdbseason").zfill(2),string.split('-')[1].split("+")[0].zfill(2)))
            
            if not absolute:
                for i in range(1, int(episodecount)+1):
                    if not seriesMap.xpath("""./Episode[@anidb="S%sE%s"]""" % ("01", str(i).zfill(2))):
                        SubElement(seriesMap, "Episode", anidb="S%sE%s" % ("01", str(i).zfill(2)), tvdb="S%sE%s" % (series.get("defaulttvdbseason").zfill(2),str(i + episodeoffset).zfill(2)))               
            seriesMap[:] = sorted(seriesMap, key=lambda x: (int(x.get("anidb").split('E')[0].replace("S","")), int(x.get("anidb").split('E')[1])))
            
        @parallelize
        def mapSeasons():
            for media_season in sorted(media.seasons, key=lambda x: int(x),  reverse=False):
                @task
                def mapSeason(media_season=media_season):
                    season = SubElement(root, "Season", num=media_season)
                    @parallelize
                    def mapEpisodes():
                        for media_episode in sorted(media.seasons[media_season].episodes, key=lambda x: int(x),  reverse=False):
                            @task
                            def mapEpisode(media_season=media_season, media_episode=media_episode):
                                episode = SubElement(season, "Episode", num=media_episode)
                                SubElement(episode, "Series")
                                SubElement(episode, "Number") #.text = "S%sE%s" % (str(media_season).zfill(2), str(media_episode).zfill(2))           
                                streams = SubElement(episode, "Streams")
                                
                                #for map in mapping.xpath("""./Series[@anidbid="%s"]""" %()):
                                #    for map.xpath("""./Episode[@anidb="%s"]"""):
                                
                               
                                
                                for media_item in media.seasons[media_season].episodes[media_episode].items:
                                    for item_part in media_item.parts:
                                        filename = os.path.splitext(os.path.basename(item_part.file.lower()))[0]
                                        type = "episode"
                                        if int(media_season) == 0 and int(media_episode) >= 150 and re.match(r'.*\b(?:nced|ed)+\d*\b.*', filename): type = "ending"
                                        elif int(media_season) == 0 and int(media_episode) >= 100 and re.match(r'.*\b(?:ncop|op)+\d*\b.*', filename): type = "opening"
                                        SubElement(episode, "Type").text = "%s" % (type)
                                        SubElement(episode, "Filename").text = "%s" % (filename) 
                                        for stream in item_part.streams:
                                            SubElement(streams, "Stream", type=str(self.Stream_Types.get(stream.type, "und")), lang=str(getattr(stream, "language", getattr(stream, "language", "und"))))
                                collection = []            
                                if streams.xpath("""count(./Stream[@type="%s"][@lang="%s"])""" % ("audio", "eng")) > 0: collection.append("English Dubbed")
                                if streams.xpath("""count(./Stream[@type="%s"][@lang="%s"])""" % ("audio", "jpn")) > 0 and streams.xpath("""count(./Stream[@type="%s"][@lang="%s"])""" % ("subtitle", "eng")) > 0: collection.append("English Subbed")
                                SubElement(episode, "Collection").text = ";".join(collection)
           
                                
        return root
        
        