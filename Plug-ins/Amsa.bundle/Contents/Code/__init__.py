from common import CommonStart, XMLFromURL
import re, time, unicodedata, hashlib, types, os, inspect, datetime, common, tvdb, anidb
          
AniDB_title_tree = None
AniDB_TVDB_mapping_tree = None
AniDB_collection_tree = None

### Pre-Defined Start function #########################################################################################################################################
def Start():
    Log.Debug("search() - Start:")
    CommonStart()
    global AniDB_title_tree, AniDB_TVDB_mapping_tree, AniDB_collection_tree
    AniDB_title_tree        = XMLFromURL(anidb.ANIDB_TITLES, os.path.splitext(os.path.basename(anidb.ANIDB_TITLES))[0], CACHE_1HOUR * 24 * 2, 60)
    AniDB_TVDB_mapping_tree = XMLFromURL(common.ANIDB_TVDB_MAPPING, os.path.basename(common.ANIDB_TVDB_MAPPING), CACHE_1HOUR * 24 * 2)
    AniDB_collection_tree   = XMLFromURL(common.ANIDB_COLLECTION, os.path.basename(common.ANIDB_COLLECTION), CACHE_1HOUR * 24 * 2)

       
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
        #if orig_title.startswith("clear-cache"):   HTTP.ClearCache()
        
        Log.Info("search() - Title: '%s', name: '%s', filename: '%s', manual:'%s'" % (orig_title, media.name, media.filename, str(manual)))
        
        match = re.search("(?P<show>.*?) ?\[(?P<source>(anidb|tvdb|tmdb|imdb))-(tt)?(?P<guid>[0-9]{1,7})\]", orig_title, re.IGNORECASE)
        if match:  ###metadata id provided
            source = match.group('source').lower() 
            guid = match.group('guid')
            show = match.group('show')
            if source=="anidb":  
                show, mainTitle = Helpers().getAniDBTitle(AniDB_title_tree.xpath("/animetitles/anime[@aid='%s']/*" % guid), SERIE_LANGUAGE_PRIORITY)
            Log.Debug( "search - source: '%s', id: '%s', show from id: '%s' provided in foldername: '%s'" % (source, guid, show, orig_title) )
            results.Append(MetadataSearchResult(id="%s-%s" % (source, guid), name=show, year=media.year, lang=Locale.Language.English, score=100))
            return
        
        #if media.year is not None: orig_title = orig_title + " (" + str(media.year) + ")"
        parent_element = None
        show = ""
        score = 0
        maxi = 0
        test = 0

        for anime in AniDB_title_tree.xpath("""./anime/title
            [type='main' or @type='official' or @type='syn' or @type='short']
            [translate(text(),"ABCDEFGHJIKLMNOPQRSTUVWXYZ 0123456789.`", "abcdefghjiklmnopqrstuvwxyz 0123456789.'")="%s"
            or contains(translate(text(),"ABCDEFGHJIKLMNOPQRSTUVWXYZ 0123456789.`", "abcdefghjiklmnopqrstuvwxyz 0123456789.'"),"%s")]""" % (orig_title.lower().replace("'", "\'"), orig_title.lower().replace("'", "\'"))):
            element = anime.getparent()
            aid = element.get('aid')
            title = anime.text
            if title == orig_title.lower():
                score = 100
            else:
                score = 100 * len(orig_title) / len(title)
            langTitle, mainTitle = self.getAniDBTitle(element, anidb.SERIE_LANGUAGE_PRIORITY)
            Log.Debug("search() - find - aid: '%s', title: '%s', score: '%s'" % (aid, title, score))
            results.Append(MetadataSearchResult(id="%s-%s" % ("anidb", aid), name="%s [%s-%s]" % (langTitle, "anidb", aid), year=media.year, lang=Locale.Language.English, score=score))

            
        results.Sort('score', descending=True)
        if len(results)>=1:  
            return  

        
        
        return
        
    def getAniDBTitle(self, titles, languages):
        if not 'main' in languages:  languages.append('main')                                                                                      # Add main to the selection if not present
        langTitles = ["" for index in range(len(languages)+1)]                                                                                     # languages: title order including main title, then choosen title
        for title in titles:                                                                                                                       # Loop through all languages listed in the anime XML
            type, lang = title.get('type'), title.get('{http://www.w3.org/XML/1998/namespace}lang')                                                  # If Serie: Main, official, Synonym, short. If episode: None # Get the language, 'xml:lang' attribute need hack to read properly
            if type == 'main' or type == None and langTitles[ languages.index('main') ] == "":  langTitles [ languages.index('main') ] = title.text  # type==none is for mapping episode language
            if lang in languages and type in ['main', 'official', None]:      langTitles [ languages.index( lang ) ] = title.text  # 'Applede' Korean synonym fix 
            if lang in languages and langTitles[languages.index( lang )] == "": 
                #Log.Debug("AniDB Title : %s " % (lang))  
                langTitles.pop(languages.index( lang )) 
                if lang in languages and type in ['syn', 'synonym', None]:    
                    langTitles.insert(languages.index( lang ) + 1, title.text)
                else:
                    langTitles.append('')
                           
            #if type == 'main' or type == None and langTitles[ languages.index('main') ] == "":  langTitles [ languages.index('main') ] = title.text  # type==none is for mapping episode language
            #if lang in languages and type in ['main', 'official', 'syn', 'synonym', None]:      langTitles [ languages.index( lang ) ] = title.text  # 'Applede' Korean synonym fix
        for index in range( len(languages) ):                                                                                                      # Loop through title result array
            if langTitles[index]:  langTitles[len(languages)] = langTitles[index];  break                                               # If title present we're done
        else: langTitles[len(languages)] = langTitles[languages.index('main')]                                     # Fallback on main title
        #Log.Debug("AniDB Title : %s | %s | %s" % (langTitles, languages, langTitles[len(languages)]))    
        return langTitles[len(languages)].replace("`", "'").encode("utf-8"), langTitles[languages.index('main')].replace("`", "'").encode("utf-8") #    
    
