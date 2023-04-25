import constants

from lxml import etree
from unidecode import unidecode
from time import sleep
from datetime import timedelta, datetime as dt

global AniDB_WaitUntil
AniDB_WaitUntil = dt.now() 

ns = etree.FunctionNamespace(None)
ns['upper-case'] = lambda context, s: str.upper(s)
ns['lower-case'] = lambda context, s: str.lower(s)
ns['clean-title'] = lambda context, s: CleanTitle(s)
ns['clean-title-filter'] = lambda context, s: CleanTitle(s, True)
ns['is-match'] = lambda context, x,y: SequenceMatch(x, y)
    
def XMLFromURL (url, filename="", directory="", cache=constants.DefaultCache, timeout=constants.DefaultTimeout):
    global AniDB_WaitUntil  
    result = LoadFile(filename, directory, cache) 
    
    if not result or (result and not len(result) > 1024):
        Log.Debug("Functions - XMLFromURL() - url: '%s', filename: '%s'" % (url, filename))
        try: 
            if url.startswith(constants.ANIDB_HTTP_API_URL) or url.startswith(constants.ANIDB_TITLES) or url.startswith(constants.ANIDB_PIC_BASE_URL):
                runOnce = True
                while AniDB_WaitUntil > dt.now():
                    if runOnce:
                        Log("Functions - XMLFromURL() - AniDB AntiBan Delay: %s" % (AniDB_WaitUntil))
                        runOnce = False
                    sleep(0.1)
                AniDB_WaitUntil = dt.now() + timedelta(seconds=constants.ANIDB_ANTIBAN_WAIT) 

            result = GetFromUrl(url, timeout)
            
            if str(result).startswith("<error>") or str(result).startswith("<Element error at "):
                Log.Debug("Functions - XMLFromURL() - Not an XML file, Possibly Ban, result: '%s'" % result)
                result = None
               
        except Exception as e: 
            result = None 
            Log.Debug("Functions - XMLFromURL() - XML issue loading url: '%s', Exception: '%s'" % (url, e))                                                    
    
        if result and len(result) > 1024 and filename: 
            try: SaveFile(result, os.path.basename(filename), directory)
            except Exception as e: Log.Debug("Functions - XMLFromURL() - url: '%s', filename: '%s' saving failed: %s" % (url, filename, e))
        elif filename and Data.Exists(filename):  # Loading locally if backup exists
            Log.Debug("Functions - XMLFromURL() - Loading locally since banned or empty file (result page <1024 bytes)")
            try: result = Data.Load(filename)
            except Exception as e: Log.Debug("Functions - XMLFromURL() - Loading locally failed but data present - url: '%s', filename: '%s'" % (url, filename))
    
    if url==constants.ANIDB_TVDB_MAPPING and Data.Exists(constants.ANIDB_TVDB_MAPPING_CUSTOM):
        if Data.Exists(constants.ANIDB_TVDB_MAPPING_CORRECTIONS):
            Log.Debug("Functions - XMLFromURL() - Loading remote custom mapping - url: '%s'" % constants.ANIDB_TVDB_MAPPING_CORRECTIONS)
            result_remote_custom = Data.Load(constants.ANIDB_TVDB_MAPPING_CORRECTIONS)     
            result = result_remote_custom[:result_remote_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:]      
        Log.Debug("Functions - XMLFromURL() - Loading local custom mapping - url: '%s'" % constants.ANIDB_TVDB_MAPPING_CUSTOM)
        result_custom = Data.Load(constants.ANIDB_TVDB_MAPPING_CUSTOM)
        result = result_custom[:result_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:] 

    if result:
        result = etree.fromstring(result) 
        return result  
        
    return None
    
def GetFromUrl(url, timeout=constants.DefaultTimeout):
    request = urllib2.Request(url, headers=constants.Default_headers)
    request.add_header('Accept-encoding', 'gzip')
    response = urllib2.urlopen(request, context=ssl.SSLContext(ssl.PROTOCOL_SSLv23), timeout=timeout)
    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO.StringIO(response.read())
        f = gzip.GzipFile(fileobj=buf)
        return f.read()
    else:
        return response.read()
        
def FileFromURL (url, filename="", directory="", cache=constants.DefaultCache, timeout=constants.DefaultTimeout):
    global AniDB_WaitUntil
    result = LoadFile(filename, directory, cache) 
    if not result:
        Log.Debug("Functions - FileFromURL() - url: '%s', filename: '%s'" % (url, filename))
        try: 
            result = GetFromUrl(url, timeout)
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
    return None
    
def LoadFile(filename="", directory="", cache=constants.DefaultCache):  
    filename = os.path.join(str(constants.CacheDirectory), str(directory), str(filename)) 
    result = None
    if filename and Data.Exists(filename):       
        file = os.path.abspath(os.path.join(constants.CachePath, "..", filename))
        if os.path.isfile(file) and os.stat(file).st_mtime > (time.time() - cache):
            Log.Debug("Functions - LoadFile() - Filename: '%s', CacheTime: '%s', Limit: '%s'" % (file, time.ctime(os.stat(file).st_mtime), time.ctime(time.time() - cache)))
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
    Name = Name.lower()
     
    result = [] 
    
    result = Tree.xpath(u"""./anime/title
                [@type='main' or @type='official' or @type='syn' or @type='short']
                [lower-case(string(clean-title(string(text()))))="%s"
                or contains(lower-case(string(clean-title(string(text())))), "%s")]""" % (Name, Name))
    
    if not result:
        result = Tree.xpath(u"""./anime/title
                [@type='main' or @type='official' or @type='syn' or @type='short']
                [is-match("%s", lower-case(string(clean-title(string(text())))))]""" % (Name))           
    return result

def SequenceMatch(word, matcher, cutoff=0.6):
    result = False
    s = difflib.SequenceMatcher()
    s.set_seq2(word)
    s.set_seq1(matcher)
    if s.real_quick_ratio() >= cutoff and \
        s.quick_ratio() >= cutoff and \
        s.ratio() >= cutoff:
            Log("SQ: %s, %s" % (word, s.ratio()))
            result = True
    return result
    
def GetPreferedTitle(titles):    
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
    
def GetByPriority(metaList, priorityList, metaType, secondType=None):
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
            result = sorted(filter(lambda i: i.text != None and i.text != "None", metaList), key=lambda x: priorityList.index(x.tag.lower()),  reverse=False)[0].text
            if secondType == "EpisodeTitle":
                for pattern in constants.ANIDB_BADTITLES:
                    if re.search(r"%s" % (pattern), result, re.IGNORECASE) and priorityList.count > 1:
                        result = sorted(filter(lambda i: i.text != None and i.text != "None", metaList), key=lambda x: priorityList.index(x.tag.lower()),  reverse=False)[1].text
            return result
                                
    except: 
        return ""               
    
def PopulateMetadata(map, metaType, priorityList, metaList=None, secondType=None):
    if map:
        data = GetByPriority(map, priorityList, metaType, secondType)
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
                                #Log("Poster 1: %s, %s, %s" % (image.get("id"), image.get("mainLocalPath"), image.getparent().tag.lower()))
                                if len(image.get("thumbUrl")) > 0:
                                    FileFromURL(image.get("thumbUrl"), os.path.basename(image.get("thumbLocalPath")), os.path.dirname(image.get("thumbLocalPath")), CACHE_1HOUR * 24 * 2)
                                else:
                                    FileFromURL(image.get("mainUrl"), os.path.basename(image.get("mainLocalPath")), os.path.dirname(image.get("mainLocalPath")), CACHE_1HOUR * 24 * 2)
                                #FileFromURL(image.get("mainUrl"), os.path.basename(image.get("mainLocalPath")), os.path.dirname(image.get("mainLocalPath")), CACHE_1HOUR * 24 * 2)
                                if image.getparent().getparent().tag == "Season":
                                    metaList[image.get("season")].posters[image.get("mainUrl")] = Proxy.Preview(Data.Load(image.get("thumbLocalPath")), sort_order=int(image.get("id"))) if len(image.get("thumbLocalPath")) > 0 else Proxy.Media(Data.Load(image.get("mainLocalPath")), sort_order=int(image.get("id")))
                                    #metaList[image.get("season")].posters[image.get("mainUrl")] = Proxy.Media(Data.Load(image.get("mainLocalPath")), sort_order=int(image.get("id")))
                                else:
                                    metaList[image.get("mainUrl")] = Proxy.Preview(Data.Load(image.get("thumbLocalPath")), sort_order=int(image.get("id"))) if len(image.get("thumbLocalPath")) > 0 else Proxy.Media(Data.Load(image.get("mainLocalPath")), sort_order=int(image.get("id")))
                                    #metaList[image.get("mainUrl")] = Proxy.Media(Data.Load(image.get("mainLocalPath")), sort_order=int(image.get("id")))
                elif secondType == "Themes":
                    @parallelize
                    def Theme_Par():
                        for theme in sorted(data, key=lambda x: x.get("id"), reverse=False):
                            @task
                            def Theme_Task(theme=theme, metaList=metaList):
                                FileFromURL(theme.get("url"), os.path.basename(theme.get("localPath")), os.path.dirname(theme.get("localPath")), CACHE_1HOUR * 24 * 2)
                                metaList[theme.get("url")] = Proxy.Media(Data.Load(theme.get("localPath")), sort_order=theme.get("id"))
                return metaList
            else:
                return (metaType)(data)   

def ParseImage(imagePath, baseURL, baseFolder, thumbPath = None):
    #Log("ParseImage: %s, %s, %s, %s" % (imagePath, baseURL, baseFolder, thumbPath))
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
    return mainUrl, thumbUrl, mainLocalPath, thumbLocalPath, mainFilename
  
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

def GetStreamInfo(file, part_id=None):  
    d = {"stream": {}}
    data = d["stream"]

    current_part = None
    current_media = None
    for media in file.items:
        for part in media.parts:
            if not part_id or str(part.id) == part_id:
                current_part = part
                current_media = media
                break
        if current_part:
            break

    if not current_part:
        return d
    
    audio_language = []
    subtitle_language = []
    for stream in current_part.streams:
        if stream.type  == 2: # audio stream
            audio_language.append(stream.language if hasattr(stream, 'language') else "")
            
        if stream.type  == 3: # subtitle stream
            subtitle_language.append(stream.language if hasattr(stream, 'language') else "")
            
    data["audio_language"] = audio_language
    data["subtitle_language"] = subtitle_language
    return d