import constants, unicodedata, ast, datetime, re, requests, StringIO, io, shutil, string, lxml, logging, difflib, heapq
from lxml import etree
from unidecode import unidecode
from time import sleep
from datetime import timedelta, datetime as dt
from string import maketrans 
from http.requests.proxy.requestProxy import RequestProxy

global AniDB_WaitUntil, queue, req_proxy, AniDB_RequestCount
req_proxy = RequestProxy(sustain=True)
AniDB_WaitUntil = dt.now() 
AniDB_RequestCount = 0

ns = etree.FunctionNamespace(None)
ns['upper-case'] = lambda context, s: str.upper(s)
ns['lower-case'] = lambda context, s: str.lower(s)
ns['clean-title'] = lambda context, s: CleanTitle(s)
ns['clean-title-filter'] = lambda context, s: CleanTitle(s, True)
ns['is-match'] = lambda context, x,y: SequenceMatch(x, y)
    
def XMLFromURL (url, filename="", directory="", cache=constants.DefaultCache, timeout=constants.DefaultTimeout):
    Log.Debug("Functions - XMLFromURL() - url: '%s', filename: '%s'" % (url, filename))
    global AniDB_WaitUntil, req_proxy, AniDB_RequestCount
    #try:
    #    netLock.acquire()
    result = LoadFile(filename, directory, cache) 
    if not result:
        try: 
            if url.startswith(constants.ANIDB_HTTP_API_URL):
                runOnce = True
                while AniDB_WaitUntil > dt.now():
                    if runOnce:
                        Log("Functions - XMLFromURL() - AniDB AntiBan Delay: %s" % (AniDB_RequestCount)) 
                        AniDB_RequestCount += 1
                        runOnce = False
                    sleep(0.1)
                AniDB_WaitUntil = dt.now() + timedelta(seconds=constants.ANIDB_ANTIBAN_WAIT) 
                if AniDB_RequestCount >= constants.ANIDB_THROTTLE_THRESHOLD:
                    AniDB_RequestCount = 0
                    req_proxy = RequestProxy(sustain=True)
                result = None
                while result is None:
                    request = req_proxy.generate_proxied_request(url, params={}, req_timeout=2)
                    if request is not None and request.status_code == 200:
                        result = request.text
            else:
                result = str(HTTP.Request(url, headers={"Accept-Encoding":"gzip, deflate", "content-type":"charset=utf8"}, cacheTime=cache, timeout=timeout))
            if str(result).startswith("<error>"): 
                result = None
                while result is None:
                    req_proxy = RequestProxy(sustain=True)
                    request = req_proxy.generate_proxied_request(url, params={}, req_timeout=2)  
                    if request is not None and request.status_code == 200:
                        result = request.text
                        
                Log("Functions - XMLFromURL() - AniDB AntiBan Proxy") 
            logging.Log_AniDB(url)
               
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
    #finally:
    #    netLock.release()
        
    return None

def FileFromURL (url, filename="", directory="", cache=constants.DefaultCache, timeout=constants.DefaultTimeout):
    Log.Debug("Functions - FileFromURL() - url: '%s', filename: '%s'" % (url, filename))
    global AniDB_WaitUntil
    #try:
    #    netLock.acquire()
    result = LoadFile(filename, directory, cache) 
    if not result:
        try: 
            result = HTTP.Request(url, headers={"Accept-Encoding":"gzip", "content-type":"charset=utf8"}, cacheTime=cache, timeout=timeout)
            result = result.content
        except Ex.HTTPError, e:
            result = None 
            Log('Functions - FileFromURL() - HTTPError %s: %s' % (e.code, e.message))
            #if (e.code == 401):      
        except Exception as e: 
            result = None 
            Log("Functions - FileFromURL() - Issue loading url: '%s', Exception: '%s'" % (url, e))                                                    
        if result and filename: 
            try: SaveFile(result, os.path.basename(filename), directory)
            except Exception as e: Log.Debug("Functions - FileFromURL() - url: '%s', filename: '%s' saving failed: %s" % (url, filename, e))
        elif filename and Data.Exists(filename):  # Loading locally if backup exists
            Log.Debug("Functions - FileFromURL() - Loading locally since banned or empty file (result page <1024 bytes)")
            try: result = Data.Load(filename)
            except:
                Log.Debug("Functions - FileFromURL() - Loading locally failed but data present - url: '%s', filename: '%s'" % (url, filename))
    if result:     
        return result  
    #finally:
    #    netLock.release()     
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

def SaveFile(file, filename="", directory="", export=False):   
    absoDirectory = os.path.join(constants.CachePath if export == False else constants.BundleExportPath, directory)
    directory = os.path.join(constants.CacheDirectory if export == False else constants.BundleExportDirectory, directory)
    filename = os.path.join(directory, filename) 
    if not os.path.exists(absoDirectory):
        Log.Debug("Functions - SaveFile() - dir: '%s'" % (absoDirectory))
        os.makedirs(absoDirectory)
    Data.Save(filename, file)
    
def GetAnimeTitleByID(Tree, Id):    
    return Tree.xpath("""/animetitles/anime[@aid="%s"]/*""" % Id)
    
def GetAnimeTitleByName(Tree, Name): 
    logging.Log_Milestone("GetAnimeTitleByName_" + Name)
    Name = Name.lower()
     
    #Log("Name: %s" % (Name))
    result = [] 
    
    logging.Log_Milestone("GetAnimeTitleByName_Xpath_" + Name)
    result = Tree.xpath(u"""./anime/title
                [@type='main' or @type='official' or @type='syn' or @type='short']
                [lower-case(string(clean-title(string(text()))))="%s"
                or contains(lower-case(string(clean-title(string(text())))), "%s")]""" % (Name, Name))
    logging.Log_Milestone("GetAnimeTitleByName_Xpath_" + Name)
    
    if not result:
        logging.Log_Milestone("GetAnimeTitleByName_DiffLib_" + Name)
        result = Tree.xpath(u"""./anime/title
                [@type='main' or @type='official' or @type='syn' or @type='short']
                [is-match("%s", lower-case(string(clean-title(string(text())))))]""" % (Name))           
        logging.Log_Milestone("GetAnimeTitleByName_DiffLib_" + Name)   
    logging.Log_Milestone("GetAnimeTitleByName_" + Name)  
    return result

def SequenceMatch(word, matcher, cutoff=0.6):
    result = False
    s = difflib.SequenceMatcher()
    s.set_seq2(word)
    s.set_seq1(matcher)
    if s.real_quick_ratio() >= cutoff and \
        s.quick_ratio() >= cutoff and \
        s.ratio() >= cutoff:
            result = True
    return result
    
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
   
def CleanTitle(title, filter = False):
    if filter: title = re.sub(constants.Filter_Regex, "", title.lower())
    title = re.sub(r'\[(tvdb\d?|anidb\d?).*\]', "", title.lower())
    title = re.sub(r'[^A-Za-z0-9 ]+', ' ', title)
    title = re.sub(r'[ ]+', ' ', title)
    title = title.replace("&", "&amp;")
    title = unidecode(u"%s" % (title))
    return str(unicodedata.normalize('NFKD', safe_unicode(title)).strip())
    
def GetElementText(el, xp, default=None):
    return el.xpath(xp)[0].text if el is not None and el.xpath(xp) and el.xpath(xp)[0].text else ("" if default == None else default)  
    
def GetByPriority(metaList, priorityList, metaType):
    try:
        if metaType is list:
            return ast.literal_eval(sorted(filter(lambda i: i.text != None and i.text != "None", metaList), key=lambda x: priorityList.index(x.tag.lower()),  reverse=False)[0].text)
        if metaType is Framework.modelling.attributes.SetObject:
            return sorted(filter(lambda i: len(i.getchildren()) > 0, metaList), key=lambda x: priorityList.index(x.tag.lower()),  reverse=False)[0]
        elif metaType is Framework.modelling.attributes.ProxyContainerObject:
            
            dataList = sorted(metaList, key=lambda x: priorityList.index(x.getparent().tag.lower()) and x.get("id"),  reverse=False)
            indexArray = []
            for image in dataList:
                indexNum = image.get("season") if image.getparent().getparent().tag == "Season" else 1
                indexArray.append(indexNum)
                image.set('id', str(indexArray.count(indexNum)))
                #Log("Order: %s, %s, %s" % (image.getparent().tag.lower(), image.get("id"), image.get("season")))
                
            return dataList
        else:
            return sorted(filter(lambda i: i.text != None and i.text != "None", metaList), key=lambda x: priorityList.index(x.tag.lower()),  reverse=False)[0].text
    except: 
        return ""               
    
def PopulateMetadata(map, metaType, priorityList, metaList=None, secondType=None):
    if map:
        data = GetByPriority(map, priorityList, metaType)
        if data:
            #Log("Data: %s, %s" % (data, metaList))
            if metaType is datetime.date:
                return dt.strptime(data, "%Y-%m-%d").date()
            if metaType is list:
                metaList.clear()
                for item in data:
                    metaList.add(item) 
                return metaList    
            if metaType is Framework.modelling.attributes.SetObject:
                metaList.clear()
                for person in sorted(data, key=lambda x: x.get('seiyuu_name', ''),  reverse=False):
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
                if secondType == "Images":
                    @parallelize
                    def Image_Par():
                        for image in sorted(data, key=lambda x: int(x.get("id")),  reverse=False):
                            @task
                            def Image_Task(image=image, metaList=metaList):
                                #Log("Poster: %s, %s, %s" % (image.get("id"), image.get("mainLocalPath"), image.getparent().tag.lower()))
                                if len(image.get("thumbUrl")) > 0:
                                    FileFromURL(image.get("thumbUrl"), os.path.basename(image.get("thumbLocalPath")), os.path.dirname(image.get("thumbLocalPath")), CACHE_1HOUR * 24)
                                else:
                                    FileFromURL(image.get("mainUrl"), os.path.basename(image.get("mainLocalPath")), os.path.dirname(image.get("mainLocalPath")), CACHE_1HOUR * 24)
                                if image.getparent().getparent().tag == "Season":
                                    metaList[image.get("season")].posters[image.get("mainUrl")] = Proxy.Preview(Data.Load(image.get("thumbLocalPath")), sort_order=image.get("id")) if len(image.get("thumbLocalPath")) > 0 else Proxy.Media(Data.Load(image.get("mainLocalPath")), sort_order=image.get("id"))
                                else:
                                    metaList[image.get("mainUrl")] = Proxy.Preview(Data.Load(image.get("thumbLocalPath")), sort_order=image.get("id")) if len(image.get("thumbLocalPath")) > 0 else Proxy.Media(Data.Load(image.get("mainLocalPath")), sort_order=image.get("id"))
                elif secondType == "Themes":
                    @parallelize
                    def Theme_Par():
                        for theme in sorted(data, key=lambda x: x.get("id"),  reverse=False):
                            @task
                            def Theme_Task(theme=theme, metaList=metaList):
                                FileFromURL(theme.get("url"), os.path.basename(theme.get("localPath")), os.path.dirname(theme.get("localPath")), CACHE_1HOUR * 24)
                                metaList[theme.get("url")] = Proxy.Media(Data.Load(theme.get("localPath")), sort_order=theme.get("id"))
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

def downloadfile(name,url):
    response=requests.get(url,stream=True)
    absoDirectory = os.path.join(constants.CachePath, name)
    with io.open(absoDirectory, 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response