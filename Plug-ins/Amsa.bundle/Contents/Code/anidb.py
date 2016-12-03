
ANIDB_TITLES                    = 'http://anidb.net/api/anime-titles.xml.gz'   
SERIE_LANGUAGE_PRIORITY   = [ Prefs['SerieLanguage1'  ].encode('utf-8'), Prefs['SerieLanguage2'  ].encode('utf-8'), Prefs['SerieLanguage3'].encode('utf-8') ]  #override default language
EPISODE_LANGUAGE_PRIORITY = [ Prefs['EpisodeLanguage1'].encode('utf-8'), Prefs['EpisodeLanguage2'].encode('utf-8') ]                                           #override default language
SERIE_METADATE_PRIORITY   = [ Prefs['AgentPref1'  ].encode('utf-8'), Prefs['AgentPref2'  ].encode('utf-8'), Prefs['AgentPref3'].encode('utf-8') ]              #override default metadata 