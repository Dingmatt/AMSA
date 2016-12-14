from common import XMLFromURL

ANIDB_TITLES                 = 'http://anidb.net/api/anime-titles.xml.gz'   
ANIDB_HTTP_API_URL           = 'http://api.anidb.net:9001/httpapi?request=anime&client=amsa&clientver=1&protover=1&aid='          #
ANIDB_PIC_BASE_URL           = 'http://img7.anidb.net/pics/anime/'                                                                # AniDB picture directory
ANIDB_SERIE_URL              = 'http://anidb.net/perl-bin/animedb.pl?show=anime&aid=%s'                                           # AniDB link to the anime

SERIES_LANGUAGE_PRIORITY     = [Prefs['SerieLanguage1'].encode('utf-8'), Prefs['SerieLanguage2'].encode('utf-8'), Prefs['SerieLanguage3'].encode('utf-8'), 'main']  #override default language
EPISODE_LANGUAGE_PRIORITY    = [Prefs['EpisodeLanguage1'].encode('utf-8'), Prefs['EpisodeLanguage2'].encode('utf-8')]                                               #override default language
SERIES_METADATE_PRIORITY     = [Prefs['AgentPref1'].encode('utf-8'), Prefs['AgentPref2'].encode('utf-8'), Prefs['AgentPref3'].encode('utf-8')]                      #override default metadata 
SERIES_TYPE_PRIORITY         = ['main', 'official', 'syn', 'short']
  
def getAniDBTitle(titles):    
    #for title in sorted([[x.text, SERIES_LANGUAGE_PRIORITY.index(x.get('{http://www.w3.org/XML/1998/namespace}lang')) + SERIES_TYPE_PRIORITY.index(x.get('type')), SERIES_TYPE_PRIORITY.index(x.get('type')) ] 
    #    for x in titles if x.get('{http://www.w3.org/XML/1998/namespace}lang') in SERIES_LANGUAGE_PRIORITY], key=lambda x: (x[1], x[2])):
    #    Log.Debug("AniDBTitle() - type: '%s', pri: '%s', sec: '%s'" % (title[0], title[1], title[2]))
    title = None
    try:
        title = sorted([[x.text, SERIES_LANGUAGE_PRIORITY.index(x.get('{http://www.w3.org/XML/1998/namespace}lang')) + SERIES_TYPE_PRIORITY.index(x.get('type')), SERIES_TYPE_PRIORITY.index(x.get('type'))] 
            for x in titles if x.get('{http://www.w3.org/XML/1998/namespace}lang') in SERIES_LANGUAGE_PRIORITY], key=lambda x: (x[1], x[2]))[0][0]
    except: pass
    
    if title == None:
        title = [x.text for x in titles if x.get('type') == 'main'][0]
    
    return title
    
def populateMetadata(id, mappingData):
    try: data = XMLFromURL(ANIDB_HTTP_API_URL + id, id+".xml", "AniDB\\" + id, CACHE_1HOUR * 24).xpath('/anime')[0]
    except: Log.Error("Anidb - PopulateMetadata() - AniDB Series XML: Exception raised, probably no return in xmlElementFromFile") 
    if data:
        langTitle = getAniDBTitle(data.xpath('/anime/titles')[0])
    
    return None