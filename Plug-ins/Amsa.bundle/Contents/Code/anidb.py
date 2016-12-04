
ANIDB_TITLES                 = 'http://anidb.net/api/anime-titles.xml.gz'   
ANIDB_HTTP_API_URL           = 'http://api.anidb.net:9001/httpapi?request=anime&client=amsa&clientver=1&protover=1&aid='          #
ANIDB_PIC_BASE_URL           = 'http://img7.anidb.net/pics/anime/'                                                                # AniDB picture directory
ANIDB_SERIE_URL              = 'http://anidb.net/perl-bin/animedb.pl?show=anime&aid=%s'                                           # AniDB link to the anime

SERIE_LANGUAGE_PRIORITY   = [ Prefs['SerieLanguage1'  ].encode('utf-8'), Prefs['SerieLanguage2'  ].encode('utf-8'), Prefs['SerieLanguage3'].encode('utf-8') ]  #override default language
EPISODE_LANGUAGE_PRIORITY = [ Prefs['EpisodeLanguage1'].encode('utf-8'), Prefs['EpisodeLanguage2'].encode('utf-8') ]                                           #override default language
SERIE_METADATE_PRIORITY   = [ Prefs['AgentPref1'  ].encode('utf-8'), Prefs['AgentPref2'  ].encode('utf-8'), Prefs['AgentPref3'].encode('utf-8') ]              #override default metadata 

def getAniDBTitle(titles, languages):
    if not 'main' in languages:  
        languages.append('main')                                                                                        # Add main to the selection if not present
    langTitles = ["" for index in range(len(languages)+1)]                                                              # languages: title order including main title, then choosen title
    for title in titles:                                                                                                # Loop through all languages listed in the anime XML
        type = title.get('type')
        lang = title.get('{http://www.w3.org/XML/1998/namespace}lang')                                                  # If Serie: Main, official, Synonym, short. If episode: None # Get the language, 'xml:lang' attribute need hack to read properly
        if type == 'main' or type == None and langTitles[languages.index('main')] == "":  
            langTitles [languages.index('main')] = title.text                                                           # type==none is for mapping episode language
        if lang in languages and type in ['main', 'official', None]:      
            langTitles [languages.index(lang)] = title.text                                                             # 'Applede' Korean synonym fix 
        if lang in languages and langTitles[languages.index(lang)] == "": 
            langTitles.pop(languages.index(lang)) 
            if lang in languages and type in ['syn', 'synonym', None]:    
                langTitles.insert(languages.index(lang) + 1, title.text)
            else:
                langTitles.append('')
                       
    for index in range(len(languages)):                                                                                 # Loop through title result array
        if langTitles[index]:  
            langTitles[len(languages)] = langTitles[index]  
            break                                                                                                       # If title present we're done
    else: 
        langTitles[len(languages)] = langTitles[languages.index('main')]                                                # Fallback on main title
    return langTitles[len(languages)].replace("`", "'").encode("utf-8"), langTitles[languages.index('main')].replace("`", "'").encode("utf-8") #    