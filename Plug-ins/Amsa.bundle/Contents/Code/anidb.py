
ANIDB_TITLES                 = 'http://anidb.net/api/anime-titles.xml.gz'   
ANIDB_HTTP_API_URL           = 'http://api.anidb.net:9001/httpapi?request=anime&client=amsa&clientver=1&protover=1&aid='          #
ANIDB_PIC_BASE_URL           = 'http://img7.anidb.net/pics/anime/'                                                                # AniDB picture directory
ANIDB_SERIE_URL              = 'http://anidb.net/perl-bin/animedb.pl?show=anime&aid=%s'                                           # AniDB link to the anime

SERIE_LANGUAGE_PRIORITY   = [ Prefs['SerieLanguage1'  ].encode('utf-8'), Prefs['SerieLanguage2'  ].encode('utf-8'), Prefs['SerieLanguage3'].encode('utf-8') ]  #override default language
EPISODE_LANGUAGE_PRIORITY = [ Prefs['EpisodeLanguage1'].encode('utf-8'), Prefs['EpisodeLanguage2'].encode('utf-8') ]                                           #override default language
SERIE_METADATE_PRIORITY   = [ Prefs['AgentPref1'  ].encode('utf-8'), Prefs['AgentPref2'  ].encode('utf-8'), Prefs['AgentPref3'].encode('utf-8') ]              #override default metadata 
