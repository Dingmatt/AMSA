import string
from string import maketrans 

#-------------------AMSA-------------------#
CacheDirectory = "Cache"
CachePath = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "..", "..", "..", "..", "Plug-in Support\Data\com.plexapp.agents.amsa_test\DataItems", CacheDirectory))
DefaultTimeout = 30
DefaultCache = CACHE_1HOUR * 24
DeleteChars = ":;"
ReplaceChars = maketrans("`", "'")
StreamTypes = {1: "video", 2: "audio", 3: "subtitle"}
#-------------------AMSA-------------------#

#-------------------ANIDB------------------#
ANIDB_TITLES                 = "http://anidb.net/api/anime-titles.xml.gz"   
ANIDB_HTTP_API_URL           = "http://api.anidb.net:9001/httpapi?request=anime&client=amsa&clientver=1&protover=1&aid="          #
ANIDB_PIC_BASE_URL           = "http://img7.anidb.net/pics/anime/"                                                                # AniDB picture directory
ANIDB_SERIE_URL              = "http://anidb.net/perl-bin/animedb.pl?show=anime&aid=%s"                                           # AniDB link to the anime

SERIES_LANGUAGE_PRIORITY     = [Prefs["SerieLanguage1"].encode("utf-8"), Prefs["SerieLanguage2"].encode("utf-8"), Prefs["SerieLanguage3"].encode("utf-8"), "main"]  #override default language
EPISODE_LANGUAGE_PRIORITY    = [Prefs["EpisodeLanguage1"].encode("utf-8"), Prefs["EpisodeLanguage2"].encode("utf-8")]                                               #override default language
SERIES_METADATE_PRIORITY     = [Prefs["AgentPref1"].encode("utf-8"), Prefs["AgentPref2"].encode("utf-8"), Prefs["AgentPref3"].encode("utf-8")]                      #override default metadata 
MINIMUM_WEIGHT               = Prefs["MinimumWeight"]
SERIES_TYPE_PRIORITY         = ["main", "official", "syn", "synonym", "short"]
#-------------------ANIDB------------------#

#-------------------TVDB-------------------#
TVDB_HTTP_API_URL            = "http://thetvdb.com/api/A27AD9BE0DA63333/series/%s/all/en.xml"                                     # TVDB Serie XML for episodes sumaries for now
TVDB_BANNERS_URL             = "http://thetvdb.com/api/A27AD9BE0DA63333/series/%s/banners.xml"                                    # TVDB Serie pictures xml: fanarts, posters, banners
TVDB_SERIE_SEARCH            = "http://thetvdb.com/api/GetSeries.php?seriesname="                                                 #
TVDB_IMAGES_URL              = "http://thetvdb.com/banners/"                                                                      # TVDB picture directory
TVDB_SERIE_URL               = "http://thetvdb.com/?tab=series&id=%s"  
#-------------------TVDB-------------------#

#-------------------SCUDLEE----------------#
ANIDB_TVDB_MAPPING              = "http://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-list-master.xml"                                                                                
ANIDB_COLLECTION                = "http://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-movieset-list.xml"
ANIDB_TVDB_MAPPING_CUSTOM       = os.path.join(CacheDirectory, "anime-list-custom.xml")
ANIDB_TVDB_MAPPING_CORRECTIONS  = "http://raw.githubusercontent.com/Dingmatt/AMSA/master/Plug-in%20Support/Data/com.plexapp.agents.amsa/DataItems/anime-list-corrections.xml"  
#-------------------SCUDLEE----------------#

class Series():
    ID = None
    Title = None
    Summary = None
    Originally_Available_At = None
    Rating = None
    Studio = None
    Countries = None
    Duration = None
    Genres = None
    Tags = None
    Collections = None
    Content_Rating = None
    Writers = None
    Directors = None
    Producers = None
    Roles = None
    EpisodeCount = None
    SpecialCount = None
    OpList = None
    EdList = None
    Episodes = None
    Posters = None
    
class Episode():
    Title = None
    Number = None
    Season = None
    FirstAired = None
    Rating = None
    Overview = None
    Poster = None
    Absolute = None