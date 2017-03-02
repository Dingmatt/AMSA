import constants, unicodedata, ast, datetime
from time import sleep
from datetime import timedelta  

global netLock, AniDB_WaitUntil
AniDB_WaitUntil = datetime.datetime.now() 
netLock = Thread.Lock()

def XMLFromURL (url, filename="", directory="", cache=constants.DefaultCache, timeout=constants.DefaultTimeout):
    Log.Debug("Functions - XMLFromURL() - url: '%s', filename: '%s'" % (url, filename))
    global AniDB_WaitUntil
    try:
        netLock.acquire()
        result = LoadFile(filename, directory, cache) 
        if not result:
            try: 
                if url.startswith(constants.ANIDB_HTTP_API_URL):
                    while AniDB_WaitUntil > datetime.datetime.now(): 
                        sleep(1)
                    Log("Functions - XMLFromURL() - AniDB AntiBan Delay")    
                    AniDB_WaitUntil = datetime.datetime.now() + timedelta(seconds=2) 
                result = str(HTTP.Request(url, headers={"Accept-Encoding":"gzip", "content-type":"charset=utf8"}, cacheTime=cache, timeout=timeout))
            except Exception as e: 
                result = None 
                Log.Debug("Functions - XMLFromURL() - XML issue loading url: '%s', Exception: '%s'" % (url, e))                                                    
        
            if result and len(result) > 1024 and filename: 
                try: SaveFile(result, os.path.basename(filename), directory)
                except Exception as e: Log.Debug("Functions - XMLFromURL() - url: '%s', filename: '%s' saving failed: %s" % (url, filename, e))
            elif filename and Data.Exists(filename):  # Loading locally if backup exists
                Log.Debug("Functions - XMLFromURL() - Loading locally since banned or empty file (result page <1024 bytes)")
                try: result = Data.Load(filename)
                except: Log.Debug("Functions - XMLFromURL() - Loading locally failed but data present - url: '%s', filename: '%s'" % (url, filename)); return
        
        if url==constants.ANIDB_TVDB_MAPPING and Data.Exists(constants.ANIDB_TVDB_MAPPING_CUSTOM):
            if Data.Exists(constants.ANIDB_TVDB_MAPPING_CORRECTIONS):
                Log.Debug("Functions - XMLFromURL() - Loading remote custom mapping - url: '%s'" % constants.ANIDB_TVDB_MAPPING_CORRECTIONS)
                result_remote_custom = Data.Load(constants.ANIDB_TVDB_MAPPING_CORRECTIONS)     
                result = result_remote_custom[:result_remote_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:]      
            Log.Debug("Functions - XMLFromURL() - Loading local custom mapping - url: '%s'" % constants.ANIDB_TVDB_MAPPING_CUSTOM)
            result_custom = Data.Load(constants.ANIDB_TVDB_MAPPING_CUSTOM)
            result = result_custom[:result_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:] 
            
            #SaveFile(result, "Test.xml")

        if result:
            result = XML.ElementFromString(result)
            if str(result).startswith("<Element error at "):  
                Log.Debug("Functions - XMLFromURL() - Not an XML file, AniDB banned possibly, result: '%s'" % result)
            else:       
                return result  
    finally:
        netLock.release()
        
    return None

def FileFromURL (url, filename="", directory="", cache=constants.DefaultCache, timeout=constants.DefaultTimeout):
    Log.Debug("Functions - FileFromURL() - url: '%s', filename: '%s'" % (url, filename))
    global AniDB_WaitUntil
    try:
        netLock.acquire()
        result = LoadFile(filename, directory, cache) 
        if not result:
            try: 
                if url.startswith(constants.ANIDB_HTTP_API_URL):
                    while AniDB_WaitUntil > datetime.datetime.now(): 
                        sleep(1)
                    Log("Functions - FileFromURL() - AniDB AntiBan Delay")    
                    AniDB_WaitUntil = datetime.datetime.now() + timedelta(seconds=3) 
                result = HTTP.Request(url, headers={"Accept-Encoding":"gzip", "content-type":"charset=utf8"}, cacheTime=cache, timeout=timeout)
            except Exception as e: 
                result = None 
                Log.Debug("Functions - FileFromURL() - Issue loading url: '%s', Exception: '%s'" % (url, e))                                                    
        
            if result and filename: 
                try: SaveFile(result, os.path.basename(filename), directory)
                except Exception as e: Log.Debug("Functions - FileFromURL() - url: '%s', filename: '%s' saving failed: %s" % (url, filename, e))
            elif filename and Data.Exists(filename):  # Loading locally if backup exists
                Log.Debug("Functions - FileFromURL() - Loading locally since banned or empty file (result page <1024 bytes)")
                try: result = Data.Load(filename)
                except: Log.Debug("Functions - FileFromURL() - Loading locally failed but data present - url: '%s', filename: '%s'" % (url, filename)); return
        
        if result:     
            return result  
    finally:
        netLock.release()
        
    return None
def LoadFile(filename="", directory="", cache=constants.DefaultCache):  
    filename = os.path.join(str(constants.CacheDirectory), str(directory), str(filename)) 
    result = None
    if filename and Data.Exists(filename):       
        file = os.path.abspath(os.path.join(constants.CachePath, "..", filename))
        Log.Debug("Functions - LoadFile() - Filename: '%s', CacheTime: '%s', Limit: '%s'" % (file, time.ctime(os.stat(file).st_mtime), time.ctime(time.time() - cache)))
        if os.path.isfile(file) and os.stat(file).st_mtime > (time.time() - cache):
            Log.Debug("Functions - LoadFile() - Load from cache")  
            result = Data.Load(filename) 
    return result                

def SaveFile(file, filename="", directory=""):   
    absoDirectory = os.path.join(constants.CachePath, directory)
    directory = os.path.join(constants.CacheDirectory, directory)
    filename = os.path.join(directory, filename) 
    if not os.path.exists(absoDirectory):
        Log.Debug("Functions - SaveFile() - dir: '%s'" % (absoDirectory))
        os.makedirs(absoDirectory)
    Data.Save(filename, file)
    
def GetAnimeTitleByID(Tree, Id):    
    return Tree.xpath("""/animetitles/anime[@aid="s"]/*""" % Id)
    
def GetAnimeTitleByName(Tree, Name):    
    return Tree.xpath("""./anime/title
                [@type='main' or @type='official' or @type='syn' or @type='short']
                [translate(text(),"ABCDEFGHJIKLMNOPQRSTUVWXYZ 0123456789 .` :;", "abcdefghjiklmnopqrstuvwxyz 0123456789 .' ")="%s"
                or contains(translate(text(),"ABCDEFGHJIKLMNOPQRSTUVWXYZ 0123456789 .` :;", "abcdefghjiklmnopqrstuvwxyz 0123456789 .' "),"%s")]""" % (Name.lower().replace("'", "\'"), Name.lower().replace("'", "\'")))
    
def GetPreferedTitle(titles):    
    #for title in sorted([[x.text, constants.SERIES_LANGUAGE_PRIORITY.index(x.get('{http://www.w3.org/XML/1998/namespace}lang')) + constants.SERIES_TYPE_PRIORITY.index(x.get('type')), constants.SERIES_TYPE_PRIORITY.index(x.get('type')) ] 
    #    for x in titles if x.get('{http://www.w3.org/XML/1998/namespace}lang') in constants.SERIES_LANGUAGE_PRIORITY], key=lambda x: (x[1], x[2])):
    #    Log.Debug("AniDBTitle() - type: '%s', pri: '%s', sec: '%s'" % (title[0], title[1], title[2]))
    title = None
    try:
        title = sorted([[x.text, constants.SERIES_LANGUAGE_PRIORITY.index(x.get("{http://www.w3.org/XML/1998/namespace}lang")) + constants.SERIES_TYPE_PRIORITY.index(x.get("type")), constants.SERIES_TYPE_PRIORITY.index(x.get("type"))] 
            for x in titles if x.get("{http://www.w3.org/XML/1998/namespace}lang") in constants.SERIES_LANGUAGE_PRIORITY], key=lambda x: (x[1], x[2]))[0][0]
    except: pass

    if title == None:
        title = [x.text for x in titles if x.get("type") == "main"][0]

    return title
   
def GetPreferedTitleNoType(titles):    
    title = None
    
    #for i in sorted([[x.text, constants.SERIES_LANGUAGE_PRIORITY.index(x.get("{http://www.w3.org/XML/1998/namespace}lang"))] for x in titles if x.get("{http://www.w3.org/XML/1998/namespace}lang") in constants.SERIES_LANGUAGE_PRIORITY], key=lambda x: (x[1])):
    #    Log("GetPreferedTitleNoType - %s" % (i))
    try:
        title = sorted([[x.text, constants.SERIES_LANGUAGE_PRIORITY.index(x.get("{http://www.w3.org/XML/1998/namespace}lang"))] 
            for x in titles if x.get("{http://www.w3.org/XML/1998/namespace}lang") in constants.SERIES_LANGUAGE_PRIORITY], key=lambda x: (x[1]))[0][0]
    except: pass

    if title == None:
        title = titles[0].text

    return title
   
def CleanTitle(title):
    return str(unicodedata.normalize('NFC', unicode(title)).strip()).translate(constants.ReplaceChars, constants.DeleteChars)
    
def GetElementText(el, xp):
    return el.xpath(xp)[0].text if el is not None and el.xpath(xp) and el.xpath(xp)[0].text else "" 
    
def GetByPriority(metaList, priorityList, metaType):
    try:
        if metaType is list:
            return ast.literal_eval(sorted(filter(lambda i: i.text != None and i.text != "None", metaList), key=lambda x: priorityList.index(x.tag.lower()),  reverse=False)[0].text)
        if metaType is Framework.modelling.attributes.SetObject:
            return sorted(filter(lambda i: len(i.getchildren()) > 0, metaList), key=lambda x: priorityList.index(x.tag.lower()),  reverse=False)[0]
        elif metaType is Framework.modelling.attributes.ProxyContainerObject:
            dataList = sorted(metaList, key=lambda x: priorityList.index(x.getparent().tag.lower()),  reverse=False)
            dataList[0].set('id', '0')
            return dataList
        else:
            return sorted(filter(lambda i: i.text != None and i.text != "None", metaList), key=lambda x: priorityList.index(x.tag.lower()),  reverse=False)[0].text
    except: 
        return ""               
    
def PopulateMetadata(map, metaType, priorityList, metaList=None):
    if map:
        data = GetByPriority(map, priorityList, metaType)
        if data:
            #Log("Data: %s" % (data))
            if metaType is datetime.date:
                return datetime.datetime.strptime(data, "%Y-%m-%d").date()
            if metaType is list:
                metaList.clear()
                for item in data:
                    metaList.add(item) 
                return metaList    
            if metaType is Framework.modelling.attributes.SetObject:
                metaList.clear()
                for person in data:
                    if isinstance(person, basestring):
                        if not len(person):
                            continue
                        else:
                            new_person_obj = metaList.new()
                            new_person_obj.name = person
                    else:
                        new_person_obj = metaList.new()
                        new_person_obj.name = person.get('seiyuu_name', '')
                        new_person_obj.role = person.get('character_name', '')
                        new_person_obj.photo = person.get('seiyuu_pic', '')
                    #Log("Person: %s, %s, %s, %s," %(new_person_obj.name,  person.get('seiyuu_name', ''), person.get('character_name', ''), person.get('seiyuu_pic', '')))
                return metaList
            if metaType is Framework.modelling.attributes.ProxyContainerObject:
                @parallelize
                def Image_Par():
                    for image in sorted(data, key=lambda x: x.get("id"),  reverse=False):
                        @task
                        def Image_Task(image=image, metaList=metaList):
                            #Log("Poster: %s, %s" % (image.get("id"), image.get("local")))
                            if len(image.get("thumbUrl")) > 0:
                                FileFromURL(image.get("thumbUrl"), os.path.basename(image.get("thumbLocalPath")), os.path.dirname(image.get("thumbLocalPath")), CACHE_1HOUR * 24)
                            else:
                                FileFromURL(image.get("mainUrl"), os.path.basename(image.get("mainLocalPath")), os.path.dirname(image.get("mainLocalPath")), CACHE_1HOUR * 24)
                            if image.getparent().getparent().tag == "Season":
                                metaList[image.get("id")].posters[image.get("mainUrl")] = Proxy.Preview(Data.Load(image.get("thumbLocalPath")), sort_order=image.get("id")) if len(image.get("thumbLocalPath")) > 0 else Proxy.Media(Data.Load(image.get("mainLocalPath")), sort_order=image.get("id"))
                            else:
                                metaList[image.get("mainUrl")] = Proxy.Preview(Data.Load(image.get("thumbLocalPath")), sort_order=image.get("id")) if len(image.get("thumbLocalPath")) > 0 else Proxy.Media(Data.Load(image.get("mainLocalPath")), sort_order=image.get("id"))
                return metaList
            else:
                return (metaType)(data)   

def ParseImage(imagePath, baseURL, baseFolder, thumbPath = None):
    mainUrl = os.path.join(baseURL, imagePath)
    mainFilename = os.path.join(constants.CacheDirectory, baseFolder, os.path.basename(mainUrl))
    mainLocalPath = os.path.abspath(os.path.join(constants.CachePath, "..", mainFilename))
    if thumbPath:
        thumbUrl = os.path.join(baseURL, thumbPath)
        thumbFilename = os.path.join(constants.CacheDirectory, baseFolder, "thumb_" + os.path.basename(thumbUrl))
        thumbLocalPath = os.path.abspath(os.path.join(constants.CachePath, "..", thumbFilename))
    else:
        thumbUrl = ""
        thumbLocalPath = ""       
    return mainUrl, thumbUrl, mainLocalPath, thumbLocalPath
  
def lev_ratio(s1, s2):
    distance = Util.LevenshteinDistance(safe_unicode(s1), safe_unicode(s2))
    max_len = float(max([ len(s1), len(s2) ]))

    ratio = 0.0
    try:
        ratio = float(1 - (distance/max_len))
    except:
        pass

    return ratio  
    
def safe_unicode(s, encoding='utf-8'):
    if s is None:
        return None
    if isinstance(s, basestring):
        if isinstance(s, types.UnicodeType):
            return s
        else:
            return s.decode(encoding)
    else:
        return str(s).decode(encoding)