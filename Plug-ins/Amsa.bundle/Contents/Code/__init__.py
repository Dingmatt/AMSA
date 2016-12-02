from common import CommonStart, XMLFromURL
import re, time, unicodedata, hashlib, types, os, inspect, datetime, common, tvdb, anidb

AniDB_title_tree = None
AniDB_TVDB_mapping_tree = None
AniDB_collection_tree = None

### Pre-Defined Start function #########################################################################################################################################
def Start():
    CommonStart()
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
        orig_title = unicodedata.normalize('NFC', unicode(media.show)).strip()
        if orig_title.startswith("clear-cache"):   HTTP.ClearCache()
        Log.Info("search() - Title: '%s', name: '%s', filename: '%s', manual:'%s'" % (orig_title, media.name, media.filename, str(manual)))
        
        match = re.search("(?P<show>.*?) ?\[(?P<source>(anidb|tvdb|tmdb|imdb))-(tt)?(?P<guid>[0-9]{1,7})\]", orig_title, re.IGNORECASE)
        if match:  ###metadata id provided
            source = match.group('source').lower() 
            guid = match.group('guid')
            show = match.group('show')
            if source=="anidb":  show, mainTitle = Helpers().getAniDBTitle(AniDB_title_tree.xpath("/animetitles/anime[@aid='%s']/*" % guid), SERIE_LANGUAGE_PRIORITY) #global AniDB_title_tree, SERIE_LANGUAGE_PRIORITY;
            Log.Debug( "search - source: '%s', id: '%s', show from id: '%s' provided in foldername: '%s'" % (source, guid, show, orig_title) )
            results.Append(MetadataSearchResult(id="%s-%s" % (source, guid), name=show, year=media.year, lang=Locale.Language.English, score=100))
            return
        
        if media.year is not None: orig_title = orig_title + " (" + str(media.year) + ")"
        parent_element = None
        show = ""
        score = 0
        maxi = 0
        test = 0
        AniDB_title_tree_elements = list(AniDB_title_tree.iterdescendants()) if AniDB_title_tree else []
        for element in AniDB_title_tree_elements:
            if element.get('aid'):
                
                if score: #only when match found and it skipped to next serie in file, then add
                    if score>maxi: maxi=score
                    Log.Debug("search() - AniDB - score: '%3d', id: '%6s', title: '%s' " % (score, aid, show))
                    langTitle, mainTitle = Helpers().getAniDBTitle(parent_element, SERIE_LANGUAGE_PRIORITY)
                    results.Append(MetadataSearchResult(id="%s-%s" % ("anidb", aid), name="%s [%s-%s]" % (langTitle, "anidb", aid), year=media.year, lang=Locale.Language.English, score=score))
                    parent_element, show , score = None, "", 0
                aid = element.get('aid')
            elif element.get('type') in ('main', 'official', 'syn', 'short'):
                Log.Debug("search() - AniDB - score: '%3d', id: '%6s', title: '%s' " % (score, aid, show))
                title = element.text
                if   title.lower()              == orig_title.lower() and 100                            > score:  parent_element, show , score = element.getparent(), title,         100; Log.Debug("search() - AniDB - temp score: '%3d', id: '%6s', title: '%s' " % (100, aid, show))  #match = [element.getparent(), show,         100]
                elif Helpers().cleanse_title (title) == cleansedTitle      and  99                            > score:  parent_element, show , score = element.getparent(), cleansedTitle,  99  #match = [element.getparent(), cleansedTitle, 99]
                elif orig_title in title                              and 100*len(orig_title)/len(title) > score:  parent_element, show , score = element.getparent(), orig_title,    100*len(orig_title)/len(title)  #match = [element.getparent(), show, 100*len(orig_title)/len(element.text)]
                else:  continue #no match 
        if score: #last serie detected, added on next serie OR here
            Log.Debug("search() - AniDB - score: '%3d', id: '%6s', title: '%s' " % (score, aid, show))
            langTitle, mainTitle = Helpers().getAniDBTitle(parent_element, SERIE_LANGUAGE_PRIORITY)
            results.Append(MetadataSearchResult(id="%s-%s" % ("anidb", aid), name="%s [%s-%s]" % (langTitle, "anidb", aid), year=media.year, lang=Locale.Language.English, score=score))
        if len(results)>=1:  return  #results.Sort('score', descending=True)

        
        
        return
        
        try:    orig_title = orig_title.encode('utf-8')  # NEEDS UTF-8
        except: Log("UTF-8 encode issue")  # NEEDS UTF-8
        if not orig_title:  return
        if orig_title.startswith("clear-cache"):   HTTP.ClearCache()  ### Clear Plex http cache manually by searching a serie named "clear-cache" ###
        Log.Info("search() - Title: '%s', name: '%s', filename: '%s', manual:'%s'" % (orig_title, media.name, media.filename, str(manual)))  #if media.filename is not None: filename = String.Unquote(media.filename) #auto match only
        
        ### Check if a guid is specified "Show name [anidb-id]" ###
        global SERIE_LANGUAGE_PRIORITYlist
        match = re.search("(?P<show>.*?) ?\[(?P<source>(anidb|tvdb|tmdb|imdb))-(tt)?(?P<guid>[0-9]{1,7})\]", orig_title, re.IGNORECASE)
        if match:  ###metadata id provided
            source, guid, show = match.group('source').lower(), match.group('guid'), match.group('show')
            if source=="anidb":  show, mainTitle = Helpers().getAniDBTitle(AniDB_title_tree.xpath("/animetitles/anime[@aid='%s']/*" % guid), SERIE_LANGUAGE_PRIORITY) #global AniDB_title_tree, SERIE_LANGUAGE_PRIORITY;
            Log.Debug( "search - source: '%s', id: '%s', show from id: '%s' provided in foldername: '%s'" % (source, guid, show, orig_title) )
            results.Append(MetadataSearchResult(id="%s-%s" % (source, guid), name=show, year=media.year, lang=Locale.Language.English, score=100))
            return
      
        ### AniDB Local exact search ###
        cleansedTitle = Helpers().cleanse_title (orig_title).encode('utf-8')
        if media.year is not None: orig_title = orig_title + " (" + str(media.year) + ")"  ### Year - if present (manual search or from scanner but not mine), include in title ###
        parent_element, show , score, maxi = None, "", 0, 0
        AniDB_title_tree_elements = list(AniDB_title_tree.iterdescendants()) if AniDB_title_tree else []
        for element in AniDB_title_tree_elements:
            if element.get('aid'):
                if score: #only when match found and it skipped to next serie in file, then add
                    if score>maxi: maxi=score
                    Log.Debug("search() - AniDB - score: '%3d', id: '%6s', title: '%s' " % (score, aid, show))
                    langTitle, mainTitle = Helpers().getAniDBTitle(parent_element, SERIE_LANGUAGE_PRIORITY)
                    results.Append(MetadataSearchResult(id="%s-%s" % ("anidb", aid), name="%s [%s-%s]" % (langTitle, "anidb", aid), year=media.year, lang=Locale.Language.English, score=score))
                    parent_element, show , score = None, "", 0
                aid = element.get('aid')
            elif element.get('type') in ('main', 'official', 'syn', 'short'):
                title = element.text
                if   title.lower()              == orig_title.lower() and 100                            > score:  parent_element, show , score = element.getparent(), title,         100; Log.Debug("search() - AniDB - temp score: '%3d', id: '%6s', title: '%s' " % (100, aid, show))  #match = [element.getparent(), show,         100]
                elif Helpers().cleanse_title (title) == cleansedTitle      and  99                            > score:  parent_element, show , score = element.getparent(), cleansedTitle,  99  #match = [element.getparent(), cleansedTitle, 99]
                elif orig_title in title                              and 100*len(orig_title)/len(title) > score:  parent_element, show , score = element.getparent(), orig_title,    100*len(orig_title)/len(title)  #match = [element.getparent(), show, 100*len(orig_title)/len(element.text)]
                else:  continue #no match 
        if score: #last serie detected, added on next serie OR here
            Log.Debug("search() - AniDB - score: '%3d', id: '%6s', title: '%s' " % (score, aid, show))
            langTitle, mainTitle = Helpers().getAniDBTitle(parent_element, SERIE_LANGUAGE_PRIORITY)
            results.Append(MetadataSearchResult(id="%s-%s" % ("anidb", aid), name="%s [%s-%s]" % (langTitle, "anidb", aid), year=media.year, lang=Locale.Language.English, score=score))
        if len(results)>=1:  return  #results.Sort('score', descending=True)

        ### AniDB local keyword search ###
        matchedTitles, matchedWords, words  = [ ], { }, [ ]
        log_string     = "search() - Keyword search - Matching '%s' with: " % orig_title
        for word in Helpers().splitByChars(orig_title, SPLIT_CHARS):
            word = Helpers().cleanse_title (word)
            if word and word not in FILTER_SEARCH_WORDS and len(word) > 1:  words.append (word.encode('utf-8'));  log_string += "'%s', " % word
        Log.Debug(log_string[:-2]) #remove last 2 chars  #if len(words)==0:
        for title in AniDB_title_tree_elements:
            if title.get('aid'): aid = title.get('aid')
            elif title.get('{http://www.w3.org/XML/1998/namespace}lang') in SERIE_LANGUAGE_PRIORITY or title.get('type')=='main':
                sample = Helpers().cleanse_title (title.text).encode('utf-8')
                for word in words:
                    if word in sample:
                        index  = len(matchedTitles)-1
                        if index >=0 and matchedTitles[index][0] == aid:
                            if title.get('type') == 'main':               matchedTitles[index][1] = title.text
                            if not title.text in matchedTitles[index][2]: matchedTitles[index][2].append(title.text)
                        else:
                            matchedTitles.append([aid, title.text, [title.text] ])
                            if word in matchedWords: matchedWords[word].append(sample) ## a[len(a):] = [x]
                            else:                    matchedWords[word]=[sample]       ## 
        Log.Debug(", ".join( key+"(%d)" % len(value) for key, value in matchedWords.iteritems() )) #list comprehention
        log_string = "Search - similarity with '%s': " % orig_title
        for match in matchedTitles: ### calculate scores + Buid results ###
            scores = []
            for title in match[2]: # Calculate distance without space and characters
                a, b = Helpers().cleanse_title(title), cleansedTitle
                scores.append( int(100 - (100*float(Util.LevenshteinDistance(a,b)) / float(max(len(a),len(b))) )) )  #To-Do: LongestCommonSubstring(first, second). use that?
            bestScore  = max(scores)
            log_string = log_string + match[1] + " (%s%%), " % '{:>2}'.format(str(bestScore))
            results.Append(MetadataSearchResult(id="anidb-"+match[0], name=match[1]+" [anidb-%s]"  % match[0], year=media.year, lang=Locale.Language.English, score=bestScore))
        Log.Debug(log_string)    #results.Sort('score', descending=True)
        return

        ### TVDB serie search ###
        Log.Debug("maxi: '%d'" % maxi)
        if maxi<50:
            try:  TVDBsearchXml = XML.ElementFromURL( TVDB_SERIE_SEARCH + orig_title.replace(" ", "%20"), cacheTime=CACHE_1HOUR * 24)
            except:  Log.Debug("search() - TVDB Loading search XML failed: ")
            else:
                for serie in TVDBsearchXml.xpath('Series'):
                    a, b = orig_title, serie.xpath('SeriesName')[0].text.encode('utf-8') #a, b  = cleansedTitle, Helpers().cleanse_title (serie.xpath('SeriesName')[0].text)
                    score = 100 - 100*Util.LevenshteinDistance(a,b) / max(len(a),len(b)) if a!=b else 100
                    Log.Debug( "search() - TVDB  - score: '%3d', id: '%6s', title: '%s'" % (score, serie.xpath('seriesid')[0].text, serie.xpath('SeriesName')[0].text) )
                    results.Append(MetadataSearchResult(id="%s-%s" % ("tvdb", serie.xpath('seriesid')[0].text), name="%s [%s-%s]" % (serie.xpath('SeriesName')[0].text, "tvdb", serie.xpath('seriesid')[0].text), year=None, lang=Locale.Language.English, score=score) )
        if len(results)>=1:  return


    
