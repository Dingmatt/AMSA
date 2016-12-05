import re, time, unicodedata, hashlib, types, os, inspect, datetime

CacheDirectory = "Cache"
CachePath = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "..", "..", "..", "..", "Plug-in Support\Data\com.plexapp.agents.amsa_test\DataItems", CacheDirectory))                                                
ANIDB_TVDB_MAPPING              = "http://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-list-master.xml"                                                                                
ANIDB_COLLECTION                = "http://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-movieset-list.xml"
ANIDB_TVDB_MAPPING_CUSTOM       = CacheDirectory + "\anime-list-custom.xml"   
ANIDB_TVDB_MAPPING_CORRECTIONS  = "http://raw.githubusercontent.com/Dingmatt/AMSA/master/Plug-in%20Support/Data/com.plexapp.agents.amsa/DataItems/anime-list-corrections.xml"      
AniDB_title_tree = None
AniDB_TVDB_mapping_tree = None
AniDB_collection_tree = None
DefaultSleep = 0
DefaultTimeout = 30
DefaultCache = CACHE_1HOUR * 24
HTTP.CacheTime = CACHE_1HOUR * 24
netLock = Thread.Lock()
                             
def CommonStart():
    CheckData()
    CleanCache()
    XMLFromURL(ANIDB_TVDB_MAPPING_CORRECTIONS, os.path.basename(ANIDB_TVDB_MAPPING_CORRECTIONS), "", CACHE_1HOUR * 24 * 2)

    
def CheckData():
    if not os.path.exists(CachePath):
        os.makedirs(CachePath)
    if not os.path.exists(os.path.join(CachePath, "AniDB")):
        os.makedirs(os.path.join(CachePath, "AniDB"))
    if not os.path.exists(os.path.join(CachePath, "TvDB")):
        os.makedirs(os.path.join(CachePath, "TvDB"))
    
def CleanCache():
    for root, dirs, _  in os.walk(CachePath, topdown=False):
        for directory in dirs:
            directory = os.path.join(root, directory)
            for file in os.listdir(directory):
                file = os.path.join(directory, file)
                if os.path.isfile(file) and os.stat(file).st_mtime < time.time() - 3 * 86400:
                    Log.Debug("CleanCache() - file: '%s'" % (file))
                    os.remove(file)   
            try: 
                if root.strip("\\\\?\\") != CachePath: 
                    Log.Debug("CleanCache() - directory: '%s'" % (directory)) 
                    os.rmdir(directory)    
            except: pass  
            
def XMLFromURL (url, filename="", directory="", cache=DefaultCache, timeout=DefaultTimeout, sleep=DefaultSleep):
    Log.Debug("XMLFromURL() - url: '%s', filename: '%s'" % (url, filename))
    try:
        netLock.acquire()
        absoDirectory = os.path.join(CachePath, directory)
        directory = os.path.join(CacheDirectory, directory)
        filename = os.path.join(directory, filename)  
        if not os.path.exists(absoDirectory):
            Log.Debug("XMLFromURL() - dir: '%s'" % (absoDirectory))
            os.makedirs(absoDirectory)
        result = None
        if filename and Data.Exists(filename):       
            file = os.path.abspath(os.path.join(CachePath, "..", filename))
            Log.Debug("XMLFromURL() - Filename: '%s', CacheTime: '%s', Limit: '%s'" % (file, time.ctime(os.stat(file).st_mtime), time.ctime(time.time() - DefaultCache)))
            if os.path.isfile(file) and os.stat(file).st_mtime > (time.time() - DefaultCache):
                Log.Debug("XMLFromURL() - Load from cache")  
                result = Data.Load(filename)   
        
        if not result:
            try: result = str(HTTP.Request(url, headers={'Accept-Encoding':'gzip', 'content-type':'charset=utf8'}, cacheTime=cache, sleep=sleep, timeout=timeout))
            except Exception as e: 
                result = None 
                Log.Debug("XMLFromURL() - XML issue loading url: '%s', Exception: '%s'" % (url, e))                                                    
        
            if result and len(result) > 1024 and filename: 
                try: Data.Save(filename, result)
                except: Log.Debug("XMLFromURL() - url: '%s', filename: '%s' saving failed, probably missing folder" % (url, filename))
            elif filename and Data.Exists(filename):  # Loading locally if backup exists
                Log.Debug("XMLFromURL() - Loading locally since banned or empty file (result page <1024 bytes)")
                try: result = Data.Load(filename)
                except: Log.Debug("XMLFromURL() - Loading locally failed but data present - url: '%s', filename: '%s'" % (url, filename)); return
        
        if url==ANIDB_TVDB_MAPPING and Data.Exists(ANIDB_TVDB_MAPPING_CUSTOM):
            if Data.Exists(ANIDB_TVDB_MAPPING_CORRECTIONS):
                Log.Debug("xmlElementFromFile() - Loading remote custom mapping - url: '%s'" % ANIDB_TVDB_MAPPING_CORRECTIONS)
                result_remote_custom = Data.Load(ANIDB_TVDB_MAPPING_CORRECTIONS)
                result = result_remote_custom[:result_remote_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:]      
            Log.Debug("xmlElementFromFile() - Loading local custom mapping - url: '%s'" % ANIDB_TVDB_MAPPING_CUSTOM)
            result_custom = Data.Load(ANIDB_TVDB_MAPPING_CUSTOM)
            result = result_custom[:result_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:] 

        if result:
            result = XML.ElementFromString(result)
            if str(result).startswith("<Element error at "):  
                Log.Debug("xmlElementFromFile() - Not an XML file, AniDB banned possibly, result: '%s'" % result)
            else:       
                return result  
    finally:
        netLock.release()
        
    return None