from common import CommonStart, XMLFromURL
from dateutil.parser import parse as dateParse
import re, time, unicodedata, hashlib, types, os, inspect, datetime, common, tvdb, anidb
          
AniDB_title_tree = None
AniDB_TVDB_mapping_tree = None
AniDB_collection_tree = None


### Pre-Defined Start function #########################################################################################################################################
def Start():
    Log.Debug("search() - Start:")
    CommonStart()
    global AniDB_title_tree, AniDB_TVDB_mapping_tree, AniDB_collection_tree, getElementText
    AniDB_title_tree        = XMLFromURL(anidb.ANIDB_TITLES, os.path.splitext(os.path.basename(anidb.ANIDB_TITLES))[0], "", CACHE_1HOUR * 24 * 2, 60)
    AniDB_TVDB_mapping_tree = XMLFromURL(common.ANIDB_TVDB_MAPPING, os.path.basename(common.ANIDB_TVDB_MAPPING), "", CACHE_1HOUR * 24 * 2)
    AniDB_collection_tree   = XMLFromURL(common.ANIDB_COLLECTION, os.path.basename(common.ANIDB_COLLECTION), "", CACHE_1HOUR * 24 * 2)
    getElementText = lambda el, xp: el.xpath(xp)[0].text if el is not None and el.xpath(xp) and el.xpath(xp)[0].text else ""  # helper for getting text from XML element


### Pre-Defined ValidatePrefs function Values in "DefaultPrefs.json", accessible in Settings>Tab:Plex Media Server>Sidebar:Agents>Tab:Movies/TV Shows>Tab:AmsaTV #######
def ValidatePrefs(): #     a = sum(getattr(t, name, 0) for name in "xyz")
    DefaultPrefs = ("GetTvdbFanart", "GetTvdbPosters", "GetTvdbBanners", "GetAnidbPoster", "localart", "adult", 
                  "GetPlexThemes", "MinimumWeight", "SerieLanguage1", "SerieLanguage2", "SerieLanguage3", 
                  "AgentPref1", "AgentPref2", "AgentPref3", "EpisodeLanguage1", "EpisodeLanguage2")
    try:  [Prefs[key] for key in DefaultPrefs]
    except:  Log.Error("DefaultPrefs.json invalid" );  return MessageContainer ('Error', "Value '%s' missing from 'DefaultPrefs.json', update it" % key)
    else:    Log.Info ("DefaultPrefs.json is valid");  return MessageContainer ('Success', 'AMSA - Provided preference values are ok')
  
  
### Agent declaration ###############################################################################################################################################
class AmsaTVAgentTest(Agent.TV_Shows):
    name = 'Anime Multi Source Agent (Test)'
    primary_provider = True
    fallback_agent = False
    contributes_to = None
    languages = [Locale.Language.English]
    accepts_from = ['com.plexapp.agents.localmedia'] 
    
    def search(self, results, media, lang, manual=False):
        Log.Debug("=== Search - Begin - ================================================================================================")
        orig_title = unicodedata.normalize('NFC', unicode(media.show)).strip().replace("`", "'")
        if orig_title.startswith("clear-cache"):   HTTP.ClearCache()
        Log.Info("search() - Title: '%s', name: '%s', filename: '%s', manual:'%s'" % (orig_title, media.name, media.filename, str(manual)))
        
        match = re.search("(?P<show>.*?) ?\[(?P<source>(.*))-(tt)?(?P<id>[0-9]{1,7})\]", orig_title, re.IGNORECASE)
        if match:
            show = match.group('show')
            source = match.group('source').lower() 
            if source in ["anidb", "tvdb"]:
                id = match.group('id')
                startdate = None
                if source=="anidb":  
                    show, mainTitle = anidb.getAniDBTitle(AniDB_title_tree.xpath("/animetitles/anime[@aid='%s']/*" % id), anidb.SERIE_LANGUAGE_PRIORITY)
                Log.Debug( "search - source: '%s', id: '%s', show from id: '%s' provided in foldername: '%s'" % (source, id, show, orig_title) )
                results.Append(MetadataSearchResult(id="%s-%s" % (source, id), name=show, year=startdate, lang=Locale.Language.English, score=100))
                return
            else: orig_title = show
        
        maxi = {}
        @parallelize
        def searchTitles():
            for anime in AniDB_title_tree.xpath("""./anime/title
                [type='main' or @type='official' or @type='syn' or @type='short']
                [translate(text(),"ABCDEFGHJIKLMNOPQRSTUVWXYZ 0123456789.`", "abcdefghjiklmnopqrstuvwxyz 0123456789.'")="%s"
                or contains(translate(text(),"ABCDEFGHJIKLMNOPQRSTUVWXYZ 0123456789.`", "abcdefghjiklmnopqrstuvwxyz 0123456789.'"),"%s")]""" % (orig_title.lower().replace("'", "\'"), orig_title.lower().replace("'", "\'"))):
                @task
                def scoreTitle(anime=anime, maxi=maxi):
                    element = anime.getparent()
                    id = element.get('aid')
                    title = anime.text
                    langTitle, mainTitle = anidb.getAniDBTitle(element, anidb.SERIE_LANGUAGE_PRIORITY)
                    if title == orig_title.lower():
                        score = 100
                    elif langTitle == orig_title.lower():
                        score = 100
                    else:   
                        score = 100 * len(orig_title) / len(langTitle)
                    
                    isValid = True
                    if id in maxi and maxi[id] <= score:
                        isValid = False
                    else: 
                        maxi[id] = score 
                    startdate = None
                    if(media.year and score >= 90 and isValid):
                        try: data = XMLFromURL(anidb.ANIDB_HTTP_API_URL + id, id+".xml", "AniDB\\" + id, CACHE_1HOUR * 24, 10, 2).xpath('/anime')[0]
                        except: Log.Error("Update() - AniDB Series XML: Exception raised, probably no return in xmlElementFromFile") 
                        if data: 
                            try: startdate = dateParse(getElementText(data, 'startdate')).year
                            except: pass
                            if str(startdate) != str(media.year):
                                isValid = False 
                            Log.Debug("search() - date: '%s', aired: '%s'" % (media.year, startdate)) 
                    if isValid: 
                        Log.Debug("search() - find - id: '%s', title: '%s', score: '%s'" % (id, langTitle, score))
                        results.Append(MetadataSearchResult(id="%s-%s" % ("anidb", id), name="%s [%s-%s]" % (langTitle, "anidb", id), year=startdate, lang=Locale.Language.English, score=score))

        results.Sort('score', descending=True)
        return
        
   
    
