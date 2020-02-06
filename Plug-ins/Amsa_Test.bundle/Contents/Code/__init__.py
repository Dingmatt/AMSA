import sys, re, time, unicodedata, hashlib, types, os, inspect, datetime, string, urllib
import common, tvdb, anidb, scudlee, logging, functions, constants

from functions import XMLFromURL
#from Common import CommonStart, XMLFromURL, SaveFile, MapSeries, GetElementText
from dateutil.parser import parse as dateParse
from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment
from string import maketrans 
from common import Titles 
 
### Pre-Defined Start function #########################################################################################################################################
def Start():
    Log.Debug("--- AmsaTVAgent Start -------------------------------------------------------------------------------------------")


### Pre-Defined ValidatePrefs function Values in "DefaultPrefs.json", accessible in Settings>Tab:Plex Media Server>Sidebar:Agents>Tab:Movies/TV Shows>Tab:AmsaTV #######
def ValidatePrefs(): #     a = sum(getattr(t, name, 0) for name in "xyz")
    DefaultPrefs = ("GetTvdbFanart", "GetTvdbPosters", "GetTvdbBanners", "GetAnidbPoster", "localart", "adult", 
                  "GetPlexThemes", "MinimumWeight", "SerieLanguage1", "SerieLanguage2", "SerieLanguage3", 
                  "AgentPref1", "AgentPref2", "AgentPref3", "EpisodeLanguage1", "EpisodeLanguage2")
    try: [Prefs[key] for key in DefaultPrefs]
    except: Log.Error("Init - ValidatePrefs() - DefaultPrefs.json invalid" );  return MessageContainer ("Error", "Value '%s' missing from 'DefaultPrefs.json', update it" % key)
    else: Log.Info ("Init - ValidatePrefs() - DefaultPrefs.json is valid");  return MessageContainer ("Success", "AMSA - Provided preference values are ok")
  
  
### Agent declaration ###############################################################################################################################################
class AmsaTVAgent(Agent.TV_Shows):    
    name = "Anime Multi Source Agent"
    primary_provider = True
    fallback_agent = False
    contributes_to = None
    languages = [Locale.Language.English]
    accepts_from = ["com.plexapp.agents.localmedia"] 
    
    def search(self, results, media, lang, manual=False):
        Log.Debug("--- Search Begin -------------------------------------------------------------------------------------------")
        logging.New_Milestones()
        logging.Log_Milestone("WholeSearch")
        common.RefreshData()
        orig_title = media.show
        if orig_title.startswith("clear-cache"):   HTTP.ClearCache()
        Log.Info("Init - Search() - Show: '%s', Title: '%s', name: '%s', filename: '%s', manual:'%s'" % (media.show, orig_title, media.name, urllib.unquote(media.filename) if media.filename else "", str(manual)))
               
        match = re.search("(?P<show>.*?) ?\[(?P<source>(.*))-(tt)?(?P<id>[0-9]{1,7})\]", orig_title, re.IGNORECASE)
        if match:
            title = match.group("show")
            source = match.group("source").lower() 
            if source in ["anidb", "anidb2", "tvdb", "tvdb2", "tvdb3", "tvdb4", "tvdb5"]:
                id = match.group("id")
                startdate = None
                if source in ["anidb", "anidb2"]:  
                    title = functions.GetPreferedTitle(common.GetAnimeTitleByID(id))
                Log.Debug("Init - Search() - force - id: '%s-%s', title from id: '%s' provided in foldername: '%s'" % (source, id, title, orig_title) )
                results.Append(MetadataSearchResult(id="%s-%s" % (source, id), name=title, year=startdate, lang=Locale.Language.English, score=100))
                return
            else: orig_title = functions.CleanTitle(title)
       
       
        maxi = {}
        elite = []
        perfectScore = []
        orig_title = functions.CleanTitle(orig_title)
        @parallelize
        def searchTitles():
            for anime in common.GetAnimeTitleByName(orig_title):
                @task
                def scoreTitle(anime=anime, maxi=maxi, anidb=anidb, perfectScore=perfectScore): 
                    logging.Log_Milestone("Title")
                    anime = Titles(anime, orig_title)
                    logging.Log_Milestone("Title")
                    isValid = True
                    if (anime.Id in maxi and maxi[anime.Id] <= anime.Score) or (not anime.Id in maxi):
                        maxi[anime.Id] = anime.Score
                    else: 
                        isValid = False
                    if isValid: 
                        startdate = None
                        if(media.year and anime.Score >= 90):
                            show = anidb.AniDB(anime.Id) 
                            if show: 
                                try: 
                                    startdate = dateParse(show.Originally_Available_At).year
                                except: pass
                                if str(startdate) != str(media.year):
                                    isValid = False 
                                Log.Debug("Init - Search() - date: '%s', aired: '%s'" % (media.year, startdate)) 
                            elite.append(isValid)
                        elif anime.Score >= 90:
                            elite.append(isValid)
                        if isValid:
                            if anime.Score == 100: perfectScore.append(anime.Id)
                            Log.Debug("Init - Search() - find - id: '%s-%s', title: '%s', score: '%s'" % ("anidb", anime.Id, anime.Title, anime.Score))
                            results.Append(MetadataSearchResult(id="%s-%s" % ("anidb", anime.Id), name="%s [%s-%s]" % (anime.Title, "anidb", anime.Id), year=startdate, lang=Locale.Language.English, score=anime.Score))
        
        
        if len(list(set(perfectScore))) > 1:
            for result in results:
                if result.score == 100:    
                    show = anidb.AniDB(result.id.split("-")[1])
                    if show.Type != "TV Series": 
                        result.score = result.score - 1
                         
        if len(elite) > 0 and not True in elite: del results[:]
        results.Sort("score", descending=True)
        logging.Log_Milestone("WholeSearch")
        return
        
    ### Parse the AniDB anime title XML ##################################################################################################################################
    def update(self, metadata, media, lang, force=False):       
        Log.Debug("--- Update Begin -------------------------------------------------------------------------------------------")
        if force:
            HTTP.ClearCache()
        logging.New_Milestones()
        logging.New_AniDB()
        logging.Log_Milestone("WholeUpdate")
        common.RefreshData()
        source, id = metadata.id.split("-")     
        Log("Source: %s, ID: %s" % (source, id))
        #filename = ""
        #for sea_item in media.seasons:
        #    Log("FileName1: %s" % (sea_item))
        #    for eps_item in media.seasons[sea_item].episodes:
        #        Log("FileName2: %s" % (eps_item))
        #        for media_item in media.seasons[sea_item].episodes[eps_item].items:
        #            for item_part in media_item.parts:
        #                filename = item_part.file.lower()
        #                Log("FileName: %s" % (filename))
        #functions.downloadfile("test.webm", "https://my.mixtape.moe/sovrtq.webm")
        
        mappingData = None
        if source in  ["anidb", "anidb2"]: 
            mappingData = scudlee.ScudLee(id)
        if source in  ["tvdb", "tvdb2", "tvdb3", "tvdb4", "tvdb5"]: 
            mappingData = scudlee.ScudLee(None, id)
        Log.Debug("Init - Update() - source: '%s', anidbid: '%s', tvdbid: '%s'" % (source, mappingData.AnidbId, mappingData.TvdbId))
        
        if mappingData != None:
            map = common.MapSeries(mappingData)
            #functions.SaveFile(etree.tostring(map, pretty_print=True, xml_declaration=True, encoding="UTF-8"), mappingData.FirstSeries + ".bundle.xml", "Bundles")
            #common.MapLocal(media, map, mappingData.AnidbId)
            common.MapLocal(map, media)
            common.MapMeta(map)
            functions.SaveFile(etree.tostring(map, pretty_print=True, xml_declaration=True, encoding="UTF-8"), mappingData.FirstSeries + ".bundle.xml", "Bundles")
            if constants.ExportBundles:
                common.ExportMap(map, mappingData.FirstSeries + ".bundle.xml")
            common.MapMedia(map, metadata, mappingData.AnidbId, mappingData.TvdbId)
        logging.Log_Milestone("WholeUpdate")    
        logging.Log_AniDB(None, True)

    
