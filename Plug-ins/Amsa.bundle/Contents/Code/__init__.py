# -*- coding: utf-8 -*-
ANIDB_TITLES                 = 'http://anidb.net/api/anime-titles.xml.gz'                                                         # AniDB title database file contain all ids, all languages  #http://bakabt.info/anidb/animetitles.xml
ANIDB_TVDB_MAPPING           = 'https://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-list-master.xml'               # ScudLee mapping file url
ANIDB_TVDB_MAPPING_CUSTOM    = 'anime-list-custom.xml'                                                                            # Custom local correction for ScudLee mapping file url
ANIDB_COLLECTION             = 'https://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-movieset-list.xml'             # ScudLee collection mapping file
ANIDB_HTTP_API_URL           = 'http://api.anidb.net:9001/httpapi?request=anime&client=hama&clientver=1&protover=1&aid='          #
ANIDB_PIC_BASE_URL           = 'http://img7.anidb.net/pics/anime/'                                                                # AniDB picture directory
ANIDB_SERIE_URL              = 'http://anidb.net/perl-bin/animedb.pl?show=anime&aid=%s'                                           # AniDB link to the anime
ANIDB_TVDB_MAPPING_FEEDBACK  = 'http://github.com/ScudLee/anime-lists/issues/new?title=%s&body=%s'                                # ScudLee mapping file git feedback url
TVDB_HTTP_API_URL            = 'http://thetvdb.com/api/A27AD9BE0DA63333/series/%s/all/en.xml'                                     # TVDB Serie XML for episodes sumaries for now
TVDB_BANNERS_URL             = 'http://thetvdb.com/api/A27AD9BE0DA63333/series/%s/banners.xml'                                    # TVDB Serie pictures xml: fanarts, posters, banners
TVDB_SERIE_SEARCH            = 'http://thetvdb.com/api/GetSeries.php?seriesname='                                                 #
TVDB_IMAGES_URL              = 'http://thetvdb.com/banners/'                                                                      # TVDB picture directory
TVDB_SERIE_URL               = 'http://thetvdb.com/?tab=series&id=%s'                                                             #
TMDB_MOVIE_SEARCH            = 'http://api.tmdb.org/3/search/movie?api_key=7f4a0bd0bd3315bb832e17feda70b5cd&query=%s&year=&language=en&include_adult=true'
TMDB_MOVIE_SEARCH_BY_TMDBID  = 'http://api.tmdb.org/3/movie/%s?api_key=7f4a0bd0bd3315bb832e17feda70b5cd&append_to_response=releases,credits&language=en'
TMDB_SEARCH_URL_BY_IMDBID    = 'https://api.tmdb.org/3/find/%s?api_key=7f4a0bd0bd3315bb832e17feda70b5cd&external_source=imdb_id'  #
TMDB_CONFIG_URL              = 'https://api.tmdb.org/3/configuration?api_key=7f4a0bd0bd3315bb832e17feda70b5cd'                    #
TMDB_IMAGES_URL              = 'https://api.tmdb.org/3/movie/%s/images?api_key=7f4a0bd0bd3315bb832e17feda70b5cd'                  #
OMDB_HTTP_API_URL            = "http://www.omdbapi.com/?i="                                                                       #
THEME_URL                    = 'http://tvthemes.plexapp.com/%s.mp3'                                                               # Plex TV Theme url
AMSA_CORRECTIONS_URL         = 'https://raw.githubusercontent.com/Dingmatt/AMSA/master/Plug-in%20Support/Data/com.plexapp.agents.amsa/DataItems/anime-list-corrections.xml'               # Custom remote correction for ScudLee mapping file url
RESTRICTED_CONTENT_RATING    = "NC-17"
RESTRICTED_GENRE_NAMES       = [ '18 Restricted', 'Pornography' ]
FILTER_CHARS                 = "\\/:*?<>|~-; "
SPLIT_CHARS                  = [';', ':', '*', '?', ',', '.', '~', '-', '\\', '/' ] #Space is implied, characters forbidden by os filename limitations
WEB_LINK                     = "<a href='%s' target='_blank'>%s</a>"
GENRE_NAMES                  = [  ### List of AniDB category names useful as genre. 1st variable mark 18+ categories. The 2nd variable will actually cause a flag to appear in Plex ####################
    ### Audience categories - all useful but not used often ############################################################################################################
    'Josei', 'Kodomo', 'Mina', 'Seinen', 'Shoujo', 'Shounen',
    ### Elements - many useful #########################################################################################################################################
    'Action', 'Martial Arts', 'Swordplay', 'Adventure', 'Angst', 'Anthropomorphism', 'Comedy', 'Parody', 'Slapstick', 'Super Deformed', 'Detective', 'Ecchi', 'Fantasy',
    'Contemporary Fantasy', 'Dark Fantasy', 'Ghost', 'High Fantasy', 'Magic', 'Vampire', 'Zombie', 'Harem', 'Reverse Harem', 'Henshin', 'Horror', 'Incest',
    'Mahou Shoujo', 'Pornography', 'Yaoi', 'Yuri', 'Romance', 'Love Polygon', 'Shoujo Ai', 'Shounen Ai', 'Sci-Fi', 'Alien', 'Mecha', 'Space Travel', 'Time Travel',
    'Thriller', 'Western', 
    ### Fetishes. Leaving out most porn genres #########################################################################################################################
    'Futanari', 'Lolicon', 'Shotacon', 'Tentacle', 'Trap', 'Reverse Trap',
    ### Original Work - mainly useful ##################################################################################################################################
    'Game', 'Action Game', 'Dating Sim - Visual Novel', 'Erotic Game', 'RPG', 'Manga', '4-koma', 'Movie', 'Novel',
    ### Setting - most of the places aren't genres, some Time stuff is useful ##########################################################################################
    'Fantasy World', 'Parallel Universe', 'Virtual Reality', 'Hell', 'Space', 'Mars', 'Space Colony', 'Shipboard', 'Alternative Universe', 'Past', 'Present', 'Future',
    'Historical', '1920s', 'Bakumatsu - Meiji Period', 'Edo Period', 'Heian Period', 'Sengoku Period', 'Victorian Period', 'World War I', 'World War II', 'Alternative Present',
    ### Themes - many useful ###########################################################################################################################################
    'Anti-War', 'Art', 'Music', 'Band', 'Idol', 'Photography', 'Christmas', 'Coming of Age', 'Conspiracy', 'Cooking', 'Cosplay', 'Cyberpunk', 'Daily Life', 'Earthquake',
    'Post-War', 'Post-apocalypse', 'War', 'Dystopia', 'Friendship', 'Law and Order', 'Cops', 'Special Squads', 'Military', 'Airforce', 'Feudal Warfare', 'Navy',
    'Politics', 'Proxy Battles', 'Racism', 'Religion', 'School Life', 'All-boys School', 'All-girls School', 'Art School', 'Clubs', 'College', 'Delinquents',
    'Elementary School', 'High School', 'School Dormitory', 'Student Council', 'Transfer Student', 'Sports', 'Acrobatics', 'Archery', 'Badminton', 'Baseball',
    'Basketball', 'Board Games', 'Chess', 'Go', 'Mahjong', 'Shougi', 'Combat', 'Boxing', 'Judo', 'Kendo', 'Muay Thai', 'Wrestling', 'Cycling', 'Dodgeball', 'Fishing',
    'Football', 'Golf', 'Gymnastics', 'Horse Riding', 'Ice Skating', 'Inline Skating', 'Motorsport', 'Formula Racing', 'Street Racing', 'Rugby', 'Swimming', 'Tennis',
    'Track and Field', 'Volleyball', 'Steampunk', 'Summer Festival', 'Tragedy', 'Underworld', 'Assassin', 'Bounty Hunter', 'Mafia', 'Yakuza', 'Pirate', 'Terrorist',
    'Thief']
FILTER_SEARCH_WORDS = [ ### These are words which cause extra noise due to being uninteresting for doing searches on, Lowercase only #############################################################
    'to', 'wa', 'ga', 'no', 'age', 'da', 'chou', 'super', 'yo', 'de', 'chan', 'hime', 'ni', 'sekai',                                             # Jp
    'a',  'of', 'an', 'the', 'motion', 'picture', 'special', 'oav', 'ova', 'tv', 'special', 'eternal', 'final', 'last', 'one', 'movie', 'me',  'princess', 'theater',  # En Continued
    'le', 'la', 'un', 'les', 'nos', 'vos', 'des', 'ses',                                                                                                               # Fr
    'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi']                                                              # Roman digits
  
import os, re, time, datetime, string, thread, threading, urllib # Functions used per module: os (read), re (sub, match), time (sleep), datetim (datetime).
AniDB_title_tree, AniDB_collection_tree, AniDB_TVDB_mapping_tree = None, None, None  #ValueError if in Start()
SERIE_LANGUAGE_PRIORITY   = [ Prefs['SerieLanguage1'  ].encode('utf-8'), Prefs['SerieLanguage2'  ].encode('utf-8'), Prefs['SerieLanguage3'].encode('utf-8') ]  #override default language
EPISODE_LANGUAGE_PRIORITY = [ Prefs['EpisodeLanguage1'].encode('utf-8'), Prefs['EpisodeLanguage2'].encode('utf-8') ]                                           #override default language
SERIE_METADATE_PRIORITY   = [ Prefs['AgentPref1'  ].encode('utf-8'), Prefs['AgentPref2'  ].encode('utf-8'), Prefs['AgentPref3'].encode('utf-8') ]              #override default metadata 

### Pre-Defined ValidatePrefs function Values in "DefaultPrefs.json", accessible in Settings>Tab:Plex Media Server>Sidebar:Agents>Tab:Movies/TV Shows>Tab:AmsaTV #######
def ValidatePrefs(): #     a = sum(getattr(t, name, 0) for name in "xyz")
    DefaultPrefs = ("GetTvdbFanart", "GetTvdbPosters", "GetTvdbBanners", "GetAnidbPoster", "localart", "adult", 
                  "GetPlexThemes", "MinimumWeight", "SerieLanguage1", "SerieLanguage2", "SerieLanguage3", "EpisodeLanguage1", "EpisodeLanguage2")
    try:  [Prefs[key] for key in DefaultPrefs]
    except:  Log.Error("DefaultPrefs.json invalid" );  return MessageContainer ('Error', "Value '%s' missing from 'DefaultPrefs.json', update it" % key)
    else:    Log.Info ("DefaultPrefs.json is valid");  return MessageContainer ('Success', 'AMSA - Provided preference values are ok')
  
### Pre-Defined Start function #########################################################################################################################################
def Start():
    msgContainer = ValidatePrefs();
    if msgContainer.header == 'Error': return
    Log.Debug('### Anime Multi Source Agent (AMSA) Started ##############################################################################################################')
    global AniDB_title_tree, AniDB_TVDB_mapping_tree, AniDB_collection_tree  # only this one to make search after start faster
    AniDB_title_tree        = Helpers().xmlElementFromFile(ANIDB_TITLES, os.path.splitext(os.path.basename(ANIDB_TITLES))[0]  , True,  CACHE_1HOUR * 24 * 2)
    AniDB_TVDB_mapping_tree = Helpers().xmlElementFromFile(ANIDB_TVDB_MAPPING,            os.path.basename(ANIDB_TVDB_MAPPING), False, CACHE_1HOUR * 24 * 2)
    AniDB_collection_tree   = Helpers().xmlElementFromFile(ANIDB_COLLECTION,              os.path.basename(ANIDB_COLLECTION  ), False, CACHE_1HOUR * 24 * 2)
    Helpers().xmlElementFromFile(AMSA_CORRECTIONS_URL,            os.path.basename(AMSA_CORRECTIONS_URL), False, CACHE_1HOUR * 24 * 2)
    HTTP.CacheTime          = CACHE_1HOUR * 24
   
class Providers():
    AniDB = 1
    TVDB = 2
    Plex = 3
    
class Series:
    def __init__(self):
        self.ID = []
        self.title = []
        self.rating = []	
        self.overview = []
        self.network = []
        self.contentRating = []
        self.firstAired = []
        self.genres = []
        self.rating = []
        self.episodes = []
        self.collections = []
        self.seasons = []
        self.tvdbSeasonLayout = []
        self.tvdbAltSeasonLayout = []
        
class Season:
    def __init__(self, name, number, overview, show, network = None, altNumber = None):
        self.name = name
        self.number = number
        if altNumber: self.altNumber = str(int(float(altNumber)))
        else: self.altNumber = altNumber
        self.overview = overview
        self.show = show
        self.network = network
                   
class Episode:
    def __init__(self, name, number, season, firstAired, rating, overview, filename, absolute, altNumber = None, altSeason = None, derivedNumber = None, derivedSeason = None, derivedAltNumber = None, derivedAltSeason = None, mappedNumber = None, mappedSeason = None):
        self.name = name
        self.number = number
        self.season = season
        if altNumber: self.altNumber = str(int(float(altNumber)))
        else: self.altNumber = None
        if altSeason: self.altSeason = str(int(float(altSeason)))
        else: self.altSeason = None
        self.firstAired = firstAired
        self.rating = rating
        self.overview = overview
        self.filename = filename
        self.absolute = absolute
        if derivedNumber: self.derivedNumber = str(int(derivedNumber))
        else: self.derivedNumber = None
        if derivedSeason: self.derivedSeason = str(int(derivedSeason))
        else: self.derivedSeason = None
        if derivedAltNumber: self.derivedAltNumber = str(int(derivedAltNumber))
        else: self.derivedAltNumber = None
        if derivedAltSeason: self.derivedAltSeason = str(int(derivedAltSeason))
        else: self.derivedAltSeason = None 
        if mappedNumber: self.mappedNumber = str(int(mappedNumber))
        else: self.mappedNumber = None         
        if mappedSeason and mappedSeason.isdigit(): self.mappedSeason = str(int(mappedSeason))
        elif str(mappedSeason).lower() == "a": self.mappedSeason = "1"
        else: self.mappedSeason = None 
    
class WeightedEntry:
    def __init__(self, value, provider):
        self.value = value
        self.provider = provider

class Provider:
    def __init__(self, metadata, media, lang, force, movie):
        self.metadata = metadata
        self.media = media
        self.lang = lang
        self.force = force
        self.movie = movie
        self.imdb = None
        self.error_log = {  'anime-list anidbid missing': [], 'anime-list tvdbid missing': [], 'anime-list studio logos': [], 'Missing episodes'    : [], 'Plex themes missing': [],
                            'AniDB summaries missing'   : [], 'AniDB posters missing'    : [], 'TVDB summaries missing' : [], 'TVDB posters missing': []}

class Plex(Provider): 
    def populate(self, series, ID):
        ##series.ID = self.metadata.id [len("tvdb-"):]
        series.ID.append(WeightedEntry(ID, SERIE_METADATE_PRIORITY.index('Plex')))
        Log.Debug("Update() - Plex Priority: %s" % (SERIE_METADATE_PRIORITY.index('Plex')))
        if THEME_URL % series.ID in self.metadata.themes:  Log.Debug("Update() - Theme song - already added")
        else: Helpers().metadata_download (self.metadata.themes, THEME_URL % ID, 1, "Plex/"+ID+".mp3")  #if local, load it ?
    
class TVDB(Provider):
    def populate(self, series, ID):
        ##series.ID = self.metadata.id [len("tvdb-"):]
        series.ID.append(WeightedEntry(ID, SERIE_METADATE_PRIORITY.index('TVDB')))
        Log.Debug("Update() - TVDB Priority: %s" % (SERIE_METADATE_PRIORITY.index('TVDB')))
        
        Log.Debug("Update() - TVDB mode - TVDB Series XML: %s" % (TVDB_HTTP_API_URL % ID))
        data = None
        try: data = Helpers().xmlElementFromFile ( TVDB_HTTP_API_URL % ID, "TVDB/"+ID+".xml", False, CACHE_1HOUR * 24).xpath('/Data')[0] 
        except: Log.Error("Update() - TVDB Series XML: Exception raised, probably no return in xmlElementFromFile") 
        if data:
            getElementText = lambda el, xp: el.xpath(xp)[0].text if el is not None and el.xpath(xp) and el.xpath(xp)[0].text else ""  # helper for getting text from XML element

            if getElementText(data, 'Series/SeriesName') != "": 
                series.title.append(WeightedEntry(getElementText(data, 'Series/SeriesName'), Providers.TVDB))
                Log.Debug("Update() - TVDB Title : %s" % (getElementText(data, 'Series/SeriesName')))
            if getElementText(data, 'Series/Network') != "": 
                series.network.append(WeightedEntry(getElementText(data, 'Series/Network'), Providers.TVDB))
                Log.Debug("Update() - TVDB Network : %s" % (getElementText(data, 'Series/Network')))
            if getElementText(data, 'Series/Overview') != "": 
                series.overview.append(WeightedEntry(getElementText(data, 'Series/Overview'), Providers.TVDB))
                Log.Debug("Update() - TVDB Overview : %s" % (getElementText(data, 'Series/Overview')))
            if getElementText(data, 'Series/FirstAired') != "":    
                series.firstAired.append(WeightedEntry(getElementText(data, 'Series/FirstAired'), Providers.TVDB))
                Log.Debug("Update() - TVDB FirstAired : %s" % (getElementText(data, 'Series/FirstAired')))
            if getElementText(data, 'Series/Genre') != "":
                series.genres.append(WeightedEntry(filter(None, getElementText(data, 'Series/Genre').split("|")), Providers.TVDB))
                Log.Debug("Update() - TVDB Genre : %s" % (filter(None, getElementText(data, 'Series/Genre').split("|"))))
            if getElementText(data, 'Series/ContentRating') != "":
                series.contentRating.append(WeightedEntry(getElementText(data, 'Series/ContentRating'), Providers.TVDB))
                Log.Debug("Update() - TVDB ContentRating : %s" % (getElementText(data, 'Series/ContentRating')))
            if '.' in getElementText(data, 'Series/Rating'): 
                try:    
                    series.rating.append(WeightedEntry(float(getElementText(data, 'Series/Rating')), Providers.TVDB))
                    Log.Debug("Update() - TVDB Rating : %s" % (float(getElementText(data, 'Series/Rating'))))
                except: pass
            if getElementText(data, 'Series/IMDB_ID') != "":
                self.imdb = getElementText(data, 'Series/IMDB_ID')
                Log.Debug("Update() - TVDB IMDB : %s" % (getElementText(data, 'Series/IMDB_ID'))) 
            if data.xpath('Episode'):
                summary_missing, summary_present, season, altSeason = [], [], [], []
                for episode in data.xpath('Episode'):  # Combined_episodenumber, Combined_season, DVD(_chapter, _discid, _episodenumber, _season), Director, EpImgFlag, EpisodeName, EpisodeNumber, FirstAired, GuestStars, IMDB_ID #seasonid, imdbd                       
                    series.episodes.append(WeightedEntry(Episode(getElementText(episode, 'EpisodeName'), getElementText(episode, 'EpisodeNumber'), 
                                                getElementText(episode, 'SeasonNumber'), getElementText(episode, 'FirstAired' ), 
                                                getElementText(episode, 'Rating') if '.' in getElementText(episode, 'Rating') else None, getElementText(episode, 'Overview'), 
                                                getElementText(episode, 'filename'), getElementText(episode, 'absolute_number'), 
                                                getElementText(episode, 'DVD_episodenumber'), getElementText(episode, 'DVD_season')), Providers.TVDB))
                    
                    if getElementText(episode, 'Overview'): summary_present.append("S%sE%s (S%sE%s|%s)" % (getElementText(episode, 'SeasonNumber'), getElementText(episode, 'EpisodeNumber'), getElementText(episode, 'DVD_season'), str(int(float(getElementText(episode, 'DVD_episodenumber')))) if getElementText(episode, 'DVD_episodenumber') else "", getElementText(episode, 'absolute_number')))
                    else: summary_missing.append("S%sE%s (S%sE%s|%s)" % (getElementText(episode, 'SeasonNumber'), getElementText(episode, 'EpisodeNumber'), getElementText(episode, 'DVD_season'), getElementText(episode, 'DVD_episodenumber'), getElementText(episode, 'absolute_number')))               
                                            
                    try: season.append(int(getElementText(episode, 'SeasonNumber')) if getElementText(episode, 'SeasonNumber').isdigit() else 0)
                    except: pass
                        
                    try: altSeason.append(int(getElementText(episode, 'DVD_season')) if getElementText(episode, 'DVD_season').isdigit() else 0)
                    except: pass
                        
                    Log.Debug("Update() - TVDB - Search For : S%sE%s (S%sE%s|%s) - %s  " % (getElementText(episode, 'SeasonNumber'), getElementText(episode, 'EpisodeNumber'), getElementText(episode, 'DVD_season'), getElementText(episode, 'DVD_episodenumber'), getElementText(episode, 'absolute_number'), getElementText(episode, 'EpisodeName')))
                    
                Log.Debug("Log: %s %s" % (season, altSeason))
                if len(season) > 0:
                    for tempSeason in sorted(season):
                        try: 
                            if len(series.tvdbSeasonLayout) < tempSeason + 1: 
                                while len(series.tvdbSeasonLayout) < tempSeason + 1:
                                    series.tvdbSeasonLayout.append(0)
                        except: 
                            Log.Debug("Log: Error")
                        if len(series.tvdbSeasonLayout) == tempSeason + 1: series.tvdbSeasonLayout[tempSeason] = series.tvdbSeasonLayout[tempSeason] + 1
                    Log.Debug("Update() - TVDB IMDB - Derived Season: %s" % (series.tvdbSeasonLayout))
                
                if len(altSeason) > 0:
                    for tempSeason in sorted(altSeason):
                        try: 
                            if len(series.tvdbAltSeasonLayout) < tempSeason + 1: 
                                while len(series.tvdbAltSeasonLayout) < tempSeason + 1:
                                    series.tvdbAltSeasonLayout.append(0)
                        except: 
                            Log.Debug("Log: Error")
                        if len(series.tvdbAltSeasonLayout) == tempSeason + 1: series.tvdbAltSeasonLayout[tempSeason] = series.tvdbAltSeasonLayout[tempSeason] + 1
                    Log.Debug("Update() - TVDB IMDB - Derived AltSeason: %s" % (series.tvdbAltSeasonLayout))


                Log.Debug("Update() - TVDB - Episodes: " + str(sorted(summary_present)) )
                Log.Debug("Update() - TVDB - Episodes without Summary: " + str(sorted(summary_missing)) )
            if Prefs['GetTvdbPosters'] or Prefs['GetTvdbFanart' ] or Prefs['GetTvdbBanners']:
                poster_id, force = "", False
                #Log.Debug("Update() - TVDB - Get Poster")
                if Helpers().getImagesFromTVDB(self.metadata, self.media, ID, self.movie, poster_id, force) == 0:
                    self.error_log['TVDB posters missing'].append(WEB_LINK % (TVDB_SERIE_URL % ID, ID))
                    Log.Debug("Update() - TVDB - No poster, check logs in ../../Plug-in Support/Data/com.plexapp.agents.Amsa/DataItems/TVDB posters missing.htm to update Metadata Source")
                                                       
class AniDB(Provider): 
    def populate(self, series, ID):
        series.ID.append(WeightedEntry(ID, SERIE_METADATE_PRIORITY.index('AniDB')))
        Log.Debug("Update() - AniDB Priority: %s" % (SERIE_METADATE_PRIORITY.index('AniDB')))
        tvdbid, tmdbid, imdbid, defaulttvdbseason, mapping_studio, poster_id, mappingList, anidbid_table = "", "", "", "", "", "", {}, []
        #tvdbid, tmdbid, imdbid, defaulttvdbseason, mappingList, mapping_studio, anidbid_table, poster_id = Helpers().anidbTvdbMapping(self.metadata, ID, self.error_log)
        Log.Debug("Update() - AniDB mode - AniDB Series XML: " + ANIDB_HTTP_API_URL + ID + ", " + "AniDB/"+ID+".xml" )    
        data = None
        try: data = Helpers().xmlElementFromFile ( ANIDB_HTTP_API_URL + ID, "AniDB/"+ID+".xml", True, CACHE_1HOUR * 24).xpath('/anime')[0]      # Put AniDB serie xml (cached if able) into 'anime'
        except: Log.Error("Update() - AniDB Series XML: Exception raised, probably no return in xmlElementFromFile") 
        if data:
            getElementText = lambda el, xp: el.xpath(xp)[0].text if el is not None and el.xpath(xp) and el.xpath(xp)[0].text else ""  # helper for getting text from XML element
            
            title, orig = Helpers().getAniDBTitle(data.xpath('/anime/titles/title'), SERIE_LANGUAGE_PRIORITY)
            if title != "": 
                series.title.append(WeightedEntry(title, Providers.AniDB))
                Log.Debug("Update() - AniDB Title : %s" % (title))
            if data.xpath('creators/name'):
                for creator in data.xpath('creators/name'):
                    if creator.get('type')  == "Animation Work": 
                        series.network.append(WeightedEntry(creator.text, Providers.AniDB))
                        Log.Debug("Update() - AniDB Network : %s" % (creator.text))
            if getElementText(data, 'startdate') != "": 
                series.firstAired.append(WeightedEntry(getElementText(data, 'startdate'), Providers.AniDB))
                Log.Debug("Update() - AniDB FirstAired : %s" % (getElementText(data, 'startdate')))

            if data.xpath('tags/tag'):
                genres = []
                isRestricted = False
                for tag in data.xpath('tags/tag'):
                    #Log.Debug("Update() - AniDB Tags : %s | %s | %s" % (getElementText(tag, 'name').title(), tag.get('weight'), Prefs['MinimumWeight']))
                    if getElementText(tag, 'name').title() in GENRE_NAMES and tag.get('weight') >= Prefs['MinimumWeight']: genres.append(getElementText(tag, 'name').title()) # Remove genre whitelist
                    if getElementText(tag, 'name').title() in RESTRICTED_GENRE_NAMES: isRestricted = True
                genre = Helpers().simplifyTags(genres)
                series.genres.append(WeightedEntry(genre, Providers.AniDB))
                Log.Debug("Update() - AniDB Genre : %s" % (genre))
                if isRestricted:
                    series.contentRating.append(WeightedEntry(RESTRICTED_CONTENT_RATING, Providers.AniDB))
            if getElementText(data, 'ratings/permanent') != "" and getElementText(data, 'ratings/temporary') != "": 
                series.rating.append(WeightedEntry((float(getElementText(data, 'ratings/permanent')) + float(getElementText(data, 'ratings/temporary'))) / 2, Providers.AniDB))   
                Log.Debug("Update() - AniDB Rating (pt) : %s" % ((float(getElementText(data, 'ratings/permanent')) + float(getElementText(data, 'ratings/temporary'))) / 2))
            elif getElementText(data, 'ratings/permanent') != "": 
                series.rating.append(WeightedEntry(float(getElementText(data, 'ratings/permanent')), Providers.AniDB))   
                Log.Debug("Update() - AniDB Rating (p) : %s" % (getElementText(data, 'ratings/permanent')))
            elif getElementText(data, 'ratings/temporary') != "": 
                series.rating.append(WeightedEntry(float(getElementText(data, 'ratings/temporary')), Providers.AniDB))  
                Log.Debug("Update() - AniDB Rating (t) : %s" % (getElementText(data, 'ratings/temporary')))           
            
            numEpisodes, totalDuration, mapped_eps, missing_eps, ending_table, op_nb = 0, 0, [], [], {}, 0
            specials = {'S': [0, 'Special'], 'C': [100, 'Opening/Ending'], 'T': [200, 'Trailer'], 'P': [300, 'Parody'], 'O': [400, 'Other']}
            summary_present = []
            
            try: description = re.sub(r'http://anidb\.net/[a-z]{2}[0-9]+ \[(.+?)\]', r'\1', getElementText(data, 'description')).replace("`", "'") # Remove wiki-style links to staff, characters etc
            except:  description = ""; Log.Debug("Exception ")
            description = re.sub(r'(?m)^\*.*\n?', '', description).strip()
            if description == "":  self.error_log['AniDB summaries missing'].append(WEB_LINK % (ANIDB_SERIE_URL % ID, ID) + " " + title)
            else: series.overview.append(WeightedEntry(description.replace("`", "'"),Providers.AniDB))
                
            loopID = ID 
            sequelIDs = []
            parsedIDs = []
            episodeCount = 0
            parenttvdbid = ""
            while loopID != "":
                for anime in AniDB_TVDB_mapping_tree.iter('anime') if AniDB_TVDB_mapping_tree else []:                  
                    #if tvdbid.isdigit():  poster_id_array [tvdbid] = poster_id_array [tvdbid] + 1 if tvdbid in poster_id_array else 0  # Count posters to have a unique poster per anidbid                                         
                    if anime.get("anidbid") == loopID and not(loopID in parsedIDs) : #manage all formats latter
                        parsedIDs.append(loopID)  
                        mappingList = {} 
                        anidbid, tvdbid, tmdbid, imdbid, defaulttvdbseason, episodeoffset, mappingList['episodeoffset'] = anime.get("anidbid"), anime.get('tvdbid'), anime.get('tmdbid'), anime.get('imdbid'), anime.get('defaulttvdbseason'), anime.get('episodeoffset'), anime.get('episodeoffset')                        
                        
                        name = anime.xpath("name")[0].text 
                        if tvdbid.isdigit():
                            try: ### mapping list ###
                                for season in anime.iter('mapping') if anime else []:
                                    if anime.get("offset"): 
                                        #Log.Debug( "S%s, Start: %s, End: %s, Offset: %s" % (season.get("tvdbseason"), anime.get("start"), anime.get("end"), anime.get("offset")))
                                        mappingList[ 's'+season.get("tvdbseason")] = [anime.get("start"), anime.get("end"), anime.get("offset")]
                                    for string in filter(None, season.text.split(';')): 
                                        #Log.Debug( "AniDB: S%sE%s, TVDB:S%sE%s" % (season.get("anidbseason"), string.split('-')[0], season.get("tvdbseason"), string.split('-')[1]))
                                        mappingList[ 's' + season.get("anidbseason") + 'e' + string.split('-')[0] ] = 's' + season.get("tvdbseason") + 'e' + string.split('-')[1]
                            except: Log.Debug("Mapping:  anidbTvdbMapping() - mappingList creation exception")
                        elif tvdbid in ("", "unknown"):  
                            self.error_log ['anime-list tvdbid missing'].append("anidbid: %s title: '%s' has no matching tvdbid ('%s') in mapping file" % (anidbid.zfill(5), name, tvdbid) + WEB_LINK % (ANIDB_TVDB_MAPPING_FEEDBACK % ("aid:%s &#39;%s&#39; tvdbid:" % (anidbid, name), String.StripTags( XML.StringFromElement(anime, encoding='utf8')) ), "Submit bug report"))
                            Log.Debug("Mapping:  Anidbid: %s title: '%s' has no matching Tvdbid ('%s') in mapping file" % (anidbid.zfill(5), name, tvdbid)) 
                        try:    mapping_studio  = anime.xpath("supplemental-info/studio")[0].text
                        except: mapping_studio  = ""
                        #Log.Debug("anidbTvdbMapping() - anidb: '%s', tvbdid: '%s', tmdbid: '%s', imbdid: '%s', studio: '%s', defaulttvdbseason: '%s', offset: '%s', name: '%s'" % (anidbid, tvdbid, tmdbid, imdbid, mapping_studio, defaulttvdbseason, episodeoffset, name) )
                        Log.Debug("Mapping: %s" % mappingList)
                        anidbid_table = []
                        for anime2 in AniDB_collection_tree.iter("anime") if AniDB_collection_tree else []:
                            if tvdbid == anime2.get('tvdbid'):  anidbid_table.append( anime2.get("anidbid") ) #collection gathering
                  
                if (parenttvdbid != "" and parenttvdbid != tvdbid):
                    Log.Debug("Mapping: Break | %s | %s" % (parenttvdbid,tvdbid))
                    break 
                else: 
                    parenttvdbid = tvdbid
                    
                if loopID != ID:
                    data = None
                    try: 
                        data = Helpers().xmlElementFromFile ( ANIDB_HTTP_API_URL + loopID, "AniDB/"+loopID+".xml", True, CACHE_1HOUR * 24).xpath('/anime')[0]      # Put AniDB serie xml (cached if able) into 'anime'
                        sequelIDs.append(loopID)  
                    except:
                        Log.Error("Update() - AniDB Series XML: Exception raised, probably no return in xmlElementFromFile")   
                Log.Debug("LoopID: %s" % loopID)         
                loopID = "" 
                if data:                               
                    if data.xpath('/anime/relatedanime/anime'):
                        for relatedAnime in data.xpath('/anime/relatedanime/anime'):    
                            if (relatedAnime.get('type') == "Sequel"): 
                                loopID = relatedAnime.get('id')    
                                Log.Debug("LoopID2: %s" % loopID)                              
                                        
                    for episode in data.xpath('episodes/episode'):   ### Episode Specific ###########################################################################################
                                 
                        ep_title, main   = Helpers().getAniDBTitle (episode.xpath('title'), EPISODE_LANGUAGE_PRIORITY)
                        epNum,    eid    = episode.xpath('epno')[0], episode.get('id')
                        epNumType        = epNum.get('type')
                        
                        if (getElementText(data, 'type') == "Movie" and ep_title == "Complete Movie") or (getElementText(data, 'type') == "OVA" and ep_title == "OAD"):
                            ep_title, orig = Helpers().getAniDBTitle(data.xpath('/anime/titles/title'), EPISODE_LANGUAGE_PRIORITY)
                            
                        Log.Debug("Type: %s" % getElementText(data, 'type'))
                        season, epNumVal = "1" if epNumType == "1"  else "0", epNum.text if epNumType == "1" else str( specials[ epNum.text[0] ][0] + int(epNum.text[1:]))
                                                
                        airdate = getElementText(episode, 'airdate')
                        rating = getElementText(episode, 'rating') #if rating =="":  Log.Debug(metadata.id + " Episode rating: ''") #elif rating == episodeObj.rating:  Log.Debug(metadata.id + " update - Episode rating: '%s'*" % rating )
                        
                        absoluteNumber = int(float(episodeCount + int(epNumVal))) if season != '0' and (getElementText(data, 'type') == "TV Series" or getElementText(data, 'type') ==  "Web") else 0
                        altSeason = len(sequelIDs) if season != '0' else 0
                           
                        Log.Debug("Sea Eps (S%sE%s)" % (season, epNumVal))                           
                        anidb_ep, tvdb_ep, summary= 's' + season + 'e' + epNumVal, "", "No summary in TheTVDB.com" #epNum
                        if anidb_ep in mappingList: 
                            matchedSeason = mappingList [ anidb_ep ].split("e")[0].replace("s","")
                            matchedEpisode = mappingList [ anidb_ep ].split("e")[1]
                            tvdb_ep = mappingList [ anidb_ep ]
                            Log.Debug("Type 1 (S%sE%s)" % (matchedSeason, matchedEpisode))
                        elif 's'+season in mappingList and epNumVal >= mappingList['s'+season][0] and epNumVal <= mappingList['s'+season][1]: 
                            matchedSeason = mappingList['s'+season][2]
                            matchedEpisode = epNumVal
                            tvdb_ep = mappingList['s'+season][2] + epNumVal  # season offset + ep number
                            Log.Debug("Type 2")
                        elif defaulttvdbseason=="a":     
                            matchedSeason = defaulttvdbseason
                            matchedEpisode = int(epNumVal) + int( mappingList [ 'episodeoffset' ] if 'episodeoffset' in mappingList and mappingList [ 'episodeoffset' ] != '' else 0 )
                            tvdb_ep = "s"+defaulttvdbseason+"e"+str(int(epNumVal) + int( mappingList [ 'episodeoffset' ] if 'episodeoffset' in mappingList and mappingList [ 'episodeoffset' ] != '' else 0 ))
                            absoluteNumber = matchedEpisode
                            Log.Debug("Type 3")
                        elif season=="0":                                                    
                            matchedSeason = season 
                            matchedEpisode = epNumVal
                            tvdb_ep = "s"+season+"e"+epNumVal
                            Log.Debug("Type 4")
                        else:           
                            matchedSeason = defaulttvdbseason if defaulttvdbseason != "" else 1
                            matchedEpisode = int(epNumVal) + int( mappingList [ 'episodeoffset' ] if 'episodeoffset' in mappingList and mappingList [ 'episodeoffset' ] != '' else 0 )
                            tvdb_ep = "s"+defaulttvdbseason+"e"+str(int(epNumVal) + int( mappingList [ 'episodeoffset' ] if 'episodeoffset' in mappingList and mappingList [ 'episodeoffset' ] != '' else 0 ))
                            Log.Debug("Type 5")
                        #summary = "TVDB summary missing" if tvdb_ep=="" or tvdb_ep not in tvdb_table else tvdb_table [tvdb_ep] ['Overview'].replace("`", "'")
                        #mapped_eps.append(  )
                        
                        if epNumType=="3":
                            if ep_title.startswith("Ending"):
                                if op_nb==0: op_nb = int(epNum.text[1:])-1 #first type 3 is first ending so epNum.text[1:] -1 = nb openings
                                epNumVal = str( int(epNumVal) +50-op_nb)   #shifted to 150 for 1st ending.  
                            absoluteNumber = None
                            matchedEpisode = None
                            matchedSeason = None                            
                            Log.Debug("Update() - AniDB specials title - Season: '%s', epNum.text: '%s', epNumVal: '%s', ep_title: '%s'" % (season, epNum.text, epNumVal, ep_title) )
                                                                            
                         
                        if season != "0": 
                            derivedSeason, derivedNumber  = Helpers().mapToTVDBSeasons(absoluteNumber, series.tvdbSeasonLayout)
                            if (derivedNumber == epNumVal and (derivedSeason == season or derivedSeason == altSeason)):
                                derivedNumber = None
                                derivedSeason = None
                        else:
                            derivedNumber = None
                            derivedSeason = None
                            
                        if altSeason != "0":                         
                            derivedAltSeason, derivedAltNumber = Helpers().mapToTVDBSeasons(absoluteNumber, series.tvdbAltSeasonLayout)
                            if (derivedAltNumber == epNumVal and (derivedAltSeason == season or derivedAltSeason == altSeason)):
                                derivedAltNumber = None
                                derivedAltSeason = None    
                        else:
                            derivedAltNumber = None
                            derivedAltSeason = None  
                            
                        if (matchedEpisode == int(epNumVal) and matchedSeason == int(season)):
                            matchedEpisode = None
                            matchedSeason = None
                            
                        if (defaulttvdbseason=="a" and season != "0"):
                            matchedEpisode = None
                            matchedSeason = None
                           
                        series.episodes.append(WeightedEntry(Episode(ep_title, epNumVal, 
                        season, airdate, 
                        rating, None, 
                        None, absoluteNumber, 
                        epNumVal, altSeason,
                        derivedNumber, derivedSeason,
                        derivedAltNumber, derivedAltSeason,
                        matchedEpisode, matchedSeason), Providers.AniDB))
                                  
                        Log.Debug("Update() - AniDB - Search For : S%sE%s (S%sE%s|%s) - %s  " % (season, epNumVal, altSeason, epNumVal, absoluteNumber, ep_title))
                        Log.Debug("Update() - AniDB - Matched : S%sE%s" % (derivedSeason, derivedNumber))
                        Log.Debug("Update() - AniDB - AltMatched : S%sE%s" % (derivedAltSeason, derivedAltNumber))
                        Log.Debug("Update() - AniDB - Mapping : S%sE%s" % (matchedSeason, matchedEpisode))
                        Log.Debug("Update() - AniDB - Mapping : %s > %s" % (anidb_ep, tvdb_ep))
                        Log.Debug("Update() - AniDB - Absolute : %s" % (absoluteNumber))
                        
                        summary_present.append("S%sE%s (S%sE%s|%s)" % (season, epNumVal, len(sequelIDs), epNum.text, absoluteNumber))
                        if epNumVal == '1':                                 
                            title, orig = Helpers().getAniDBTitle(data.xpath('/anime/titles/title'), SERIE_LANGUAGE_PRIORITY)     
                            if title != "": 
                                series.title.append(WeightedEntry(title, Providers.AniDB))
                                Log.Debug("Update() - AniDB Series Title : %s" % (title))                            
                            try: description = re.sub(r'http://anidb\.net/[a-z]{2}[0-9]+ \[(.+?)\]', r'\1', getElementText(data, 'description')).replace("`", "'") # Remove wiki-style links to staff, characters etc
                            except:  description = ""; Log.Debug("Exception ")
                            description = re.sub(r'(?m)^\*.*\n?', '', description).strip()
                            #Log.Debug("Description : %s | %s | %s | %s | %s" % (description, WEB_LINK, ANIDB_SERIE_URL, ID, self.metadata.title))
                            if description == "":  self.error_log['AniDB summaries missing'].append(WEB_LINK % (ANIDB_SERIE_URL % ID, ID) + " " + title)   
                            try: series.seasons.append(WeightedEntry(Season(title, season, description.replace("`", "'"), "", None, len(sequelIDs) if season != '0' else 0), Providers.AniDB))                                     
                            except: pass
                          
                    episodeCount = episodeCount + (int(getElementText(data, 'episodecount')) if getElementText(data, 'type') == "TV Series" else 0)
                                        
            ### AniDB Posters ###
            Log.Debug("Update() - AniDB Poster, url: '%s'" % (ANIDB_PIC_BASE_URL + getElementText(data, 'picture')))
            if getElementText(data, 'picture') == "": self.error_log['AniDB posters missing'].append(WEB_LINK % (ANIDB_SERIE_URL % ID, ID) + "" + title )
            elif Prefs['GetAnidbPoster']:  Helpers().metadata_download (self.metadata.posters, ANIDB_PIC_BASE_URL + getElementText(data, 'picture'), 99, "AniDB/%s" % getElementText(data, 'picture'))             
            Log.Debug("Update() - AniDB - Episodes: " + str(sorted(summary_present)) )    
                 
class Helpers:
    def getImagesFromTVDB(self, metadata, media, tvdbid, movie, poster_id=1, force=False):
        posternum, num, poster_total = 0, 0, 0
        try:     bannersXml = XML.ElementFromURL( TVDB_BANNERS_URL % tvdbid, cacheTime=CACHE_1HOUR * 24) # don't bother with the full zip, all we need is the banners
        except:  Log.Debug("getImagesFromTVDB() - Loading picture XML failed: " + TVDB_BANNERS_URL % tvdbid);  return
        else:    Log.Debug("getImagesFromTVDB() - Loaded picture XML: '%s'" % (TVDB_BANNERS_URL % tvdbid))
        for banner in bannersXml.xpath('Banner'): 
            if banner.xpath('BannerType')[0].text=="poster":  poster_total +=1
        for banner in bannersXml.xpath('Banner'): #rating   = banner.xpath('Rating'     )[0].text if banner.xpath('Rating') else ""  #Language = banner.xpath('Language'   )[0].text #if Language not in ['en', 'jp']: continue  #id       = banner.xpath('id'         )[0].text
            num, bannerType, bannerType2, bannerPath  = num+1, banner.xpath('BannerType' )[0].text, banner.xpath('BannerType2')[0].text, banner.xpath('BannerPath' )[0].text
            if bannerType == 'poster':  posternum += 1
            season = banner.xpath('Season')[0].text if banner.xpath('Season') else ""
            if movie and not bannerType in ('fanart', 'poster') or season and season not in media.seasons:  continue
            if Prefs['GetTvdbPosters'] and                  ( bannerType == 'poster' or bannerType2 == 'season' and not movie ) or \
                Prefs['GetTvdbFanart' ] and                    bannerType == 'fanart' or \
                Prefs['GetTvdbBanners'] and not movie and    ( bannerType == 'series' or bannerType2 == 'seasonwide'):
                metatype = (metadata.art                     if bannerType == 'fanart' else \
                            metadata.posters                 if bannerType == 'poster' else \
                            metadata.banners                 if bannerType == 'series' or bannerType2=='seasonwide' else \
                            metadata.seasons[season].posters if bannerType == 'season' and bannerType2=='season' else None)
                if metatype == metadata.posters:  rank = 1 if poster_id and poster_total and posternum == divmod(poster_id, poster_total)[1] + 1 else posternum+1
                else: rank = num
                bannerThumbUrl = TVDB_IMAGES_URL + (banner.xpath('ThumbnailPath')[0].text if bannerType=='fanart' else bannerPath)
                Helpers().metadata_download (metatype, TVDB_IMAGES_URL + bannerPath, rank, "TVDB/"+bannerPath, bannerThumbUrl)
        return posternum
        
    def anidbTvdbMapping(self, metadata, anidb_id, error_log):
        global AniDB_TVDB_mapping_tree         #if not AniDB_TVDB_mapping_tree: AniDB_TVDB_mapping_tree = Helpers().xmlElementFromFile(ANIDB_TVDB_MAPPING, ANIDB_TVDB_MAPPING, False, CACHE_1HOUR * 24) # Load XML file
        poster_id_array, mappingList = {}, {}
        for anime in AniDB_TVDB_mapping_tree.iter('anime') if AniDB_TVDB_mapping_tree else []:
            anidbid, tvdbid, tmdbid, imdbid, defaulttvdbseason, mappingList['episodeoffset'] = anime.get("anidbid"), anime.get('tvdbid'), anime.get('tmdbid'), anime.get('imdbid'), anime.get('defaulttvdbseason'), anime.get('episodeoffset')
            if tvdbid.isdigit():  poster_id_array [tvdbid] = poster_id_array [tvdbid] + 1 if tvdbid in poster_id_array else 0  # Count posters to have a unique poster per anidbid
            if anidbid == anidb_id: #manage all formats latter
                name = anime.xpath("name")[0].text 
                if tvdbid.isdigit():
                    try: ### mapping list ###
                        for season in anime.iter('mapping'):
                            if anime.get("offset"):  mappingList[ 's'+season.get("tvdbseason")] = [anime.get("start"), anime.get("end"), anime.get("offset")]
                            for string in filter(None, season.text.split(';')):  mappingList [ 's' + season.get("anidbseason") + 'e' + string.split('-')[0] ] = 's' + season.get("tvdbseason") + 'e' + string.split('-')[1]
                    except: Log.Debug("anidbTvdbMapping() - mappingList creation exception")
                elif tvdbid in ("", "unknown"):  error_log ['anime-list tvdbid missing'].append("anidbid: %s title: '%s' has no matching tvdbid ('%s') in mapping file" % (anidb_id.zfill(5), name, tvdbid) + WEB_LINK % (ANIDB_TVDB_MAPPING_FEEDBACK % ("aid:%s &#39;%s&#39; tvdbid:" % (anidb_id, name), String.StripTags( XML.StringFromElement(anime, encoding='utf8')) ), "Submit bug report"))
                try:    mapping_studio  = anime.xpath("supplemental-info/studio")[0].text
                except: mapping_studio  = ""
                Log.Debug("anidbTvdbMapping() - anidb: '%s', tvbdid: '%s', tmdbid: '%s', imbdid: '%s', studio: '%s', defaulttvdbseason: '%s', name: '%s'" % (anidbid, tvdbid, tmdbid, imdbid, mapping_studio, defaulttvdbseason, name) )
                anidbid_table = []
                for anime2 in AniDB_collection_tree.iter("anime"):
                    if tvdbid == anime2.get('tvdbid'):  anidbid_table.append( anime2.get("anidbid") ) #collection gathering
                return tvdbid, tmdbid, imdbid, defaulttvdbseason, mappingList, mapping_studio, anidbid_table, poster_id_array [tvdbid] if tvdbid in poster_id_array else {}
        else:
            Log.Debug("anidbTvdbMapping() - anidbid '%s' not found in file" % anidb_id)
            error_log['anime-list anidbid missing'].append("anidbid: " + anidb_id.zfill(5))
            return "", "", "", "", [], "", [], "0"
            
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
                            
    ### Clean duplicate tags            
    def simplifyTags(self, genres):
        if len(genres):
            if 'Contemporary Fantasy' in genres: 
                if 'Fantasy' in genres: genres.pop(genres.index('Fantasy'))
                if 'Fantasy World' in genres: genres.pop(genres.index('Fantasy World'))
            elif 'Fantasy' in genres:
                if 'Fantasy World' in genres: genres.pop(genres.index('Fantasy World'))
            elif 'Space Travel' in genres:
                if 'Space' in genres: genres.pop(genres.index('Space'))        
        return genres
        
    def mapToTVDBSeasons(self, absolute, TVDB_Layout):
        tempList = list(TVDB_Layout)       
        seasonCount = 1
        episodeCount = 1
        absoluteCount = 1
        if len(tempList) > 0: tempList.pop(0)
        for season in tempList:
            episodeCount = 1   
            while episodeCount <= season:
                #Log.Debug("Test %s %s %s %s" % (season, episodeCount, absoluteCount, absolute))
                if absoluteCount == absolute:
                    return seasonCount, episodeCount
                episodeCount = episodeCount + 1
                absoluteCount = absoluteCount + 1
            seasonCount = seasonCount + 1
        
        return None, None
                        
    def totalArray(self, arrayToTotal, startIndex, endIndex):
        if startIndex > endIndex: return 0
        count = 0
        sum = 0
        #Log.Debug("Map1: %s %s %s" % (arrayToTotal, startIndex, endIndex))
        while count <= endIndex:
            if count >= startIndex: sum = sum + int(arrayToTotal[count])
            count = count + 1 
        return sum
            
    #########################################################################################################################################################
    def metadata_download (self, metatype, url, num=99, filename="", url_thumbnail=None):  #if url in metatype:#  Log.Debug("metadata_download - url: '%s', num: '%s', filename: '%s'*" % (url, str(num), filename)) # Log.Debug(str(metatype))   #  return
        if url not in metatype:
            file = None
            if not filename.endswith("/"):
                if filename and Data.Exists(filename):  ### if stored locally load it                  
                    try:     file = Data.Load(filename)
                    except:  Log.Debug("metadata_download() - media_download - could not load file '%s' present in cache" % filename)
                if file == None: ### if not loaded locally download it
                    try:     file = HTTP.Request(url_thumbnail if url_thumbnail else url, cacheTime=None).content
                    except:  Log.Debug("metadata_download() - metadata_download - error downloading"); return
                    else:  ### if downloaded, try saving in cache but folders need to exist
                        if filename and not filename.endswith("/"):
                            try:     Data.Save(filename, file)
                            except:  Log.Debug("metadata_download() - metadata_download - could not write filename '%s' in Plugin Data Folder" % (filename)); return
                if file:
                    Log.Debug("metadata_download(): %s" % filename)
                    try:    metatype[ url ] = Proxy.Preview(file, sort_order=num) if url_thumbnail else Proxy.Media(file, sort_order=num) # or metatype[ url ] != proxy_item # proxy_item = 
                    except: Log.Debug("metadata_download() - metadata_download - issue adding picture to plex - url downloaded: '%s', filename: '%s'" % (url_thumbnail if url_thumbnail else url, filename))  #metatype.validate_keys( url_thumbnail if url_thumbnail else url ) # remove many posters, to avoid
                    else:   Log.Debug("metadata_download() - url: '%s', num: '%d', filename: '%s'" % (url, num, filename))
        else:  Log.Debug("metadata_download() - url: '%s', num: '%d', filename: '%s'*" % (url, num, filename))

    ### Pull down the XML from web and cache it or from local cache for a given anime ID ####################################################################
    def xmlElementFromFile (self, url, filename="", delay=True, cache=None):
        Log.Debug("xmlElementFromFile() - url: '%s', filename: '%s'" % (url, filename))
        if delay: time.sleep(4) #2s between anidb requests but 2 threads                                                                                                   # Ban after 160 series if too short, ban also if same serie xml downloaded repetitively, delay for AniDB only for now     e #try:    a = urllib.urlopen(url)#if a is not None and a.getcode()==200:
        try: result = str(HTTP.Request(url, headers={'Accept-Encoding':'gzip', 'content-type':'charset=utf8'}, timeout=20, cacheTime=cache))  # Loaded with Plex cache, str prevent AttributeError: 'HTTPRequest' object has no attribute 'find'
        except Exception as e: 
            result = None 
            Log.Debug("xmlElementFromFile() - XML issue loading url: '%s', Exception: '%s'" % (url, e))                                                     # issue loading, but not AniDB banned as it returns "<error>Banned</error>"
        
        if result and len(result)>1024 and filename:  # if loaded OK save else load from last saved file
            try:     Data.Save(filename, result)
            except:  Log.Debug("xmlElementFromFile() - url: '%s', filename: '%s' saving failed, probably missing folder" % (url, filename))
        elif filename and Data.Exists(filename):  # Loading locally if backup exists
            Log.Debug("xmlElementFromFile() - Loading locally since banned or empty file (result page <1024 bytes)")
            #Log.Debug("xmlElementFromFile() - %s" % (result))
            try:     result = Data.Load(filename)
            except:  Log.Debug("xmlElementFromFile() - Loading locally failed but data present - url: '%s', filename: '%s'" % (url, filename)); return
          
        if url==ANIDB_TVDB_MAPPING and Data.Exists(ANIDB_TVDB_MAPPING_CUSTOM):  # Special case: if importing anidb tvdb mapping, load custom mapping entries first
            if Data.Exists(AMSA_CORRECTIONS_URL):
                Log.Debug("xmlElementFromFile() - Loading remote custom mapping - url: '%s'" % AMSA_CORRECTIONS_URL)
                result_remote_custom = Data.Load(AMSA_CORRECTIONS_URL)
                result = result_remote_custom[:result_remote_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:] #cut both fiels together removing ending and starting tags to do so           
            Log.Debug("xmlElementFromFile() - Loading local custom mapping - url: '%s'" % ANIDB_TVDB_MAPPING_CUSTOM)
            result_custom = Data.Load(ANIDB_TVDB_MAPPING_CUSTOM)
            result = result_custom[:result_custom.rfind("</anime-list>")-1] + result[result.find("<anime-list>")+len("<anime-list>")+1:] #cut both fiels together removing ending and starting tags to do so
            #result        = result[:result.rfind("</anime-list>")-1] + result_custom[result_custom.find("<anime-list>")+len("<anime-list>")+1:] #cut both fiels together removing ending and starting tags to do so

        if result:
            element = XML.ElementFromString(result)
            if str(element).startswith("<Element error at "):  Log.Debug("xmlElementFromFile() - Not an XML file, AniDB banned possibly, result: '%s'" % result)
            else:       return element    

    ### Cleanse title of FILTER_CHARS and translate anidb '`' ############################################################################################################
    def cleanse_title(self, title):
        try:    title=title.encode('utf-8')
        except: pass
        title = " ".join(Helpers().splitByChars(title))
        return  title.replace("`", "'").lower() # None in the translate call was giving an error of 'TypeError: expected a character buffer object'. So, we construct a blank translation table instead.

    ### Split a string per list of chars #################################################################################################################################
    def splitByChars(self, string, separators=SPLIT_CHARS): #AttributeError: 'generator' object has no attribute 'split'  #return (string.replace(" ", i) for i in separators if i in string).split()
        for i in separators:
          if i in string:  string = string.replace(i, " ")
        return filter(None, string.split())
         
class AmsaCommonAgent:
    
    ### Serie search ######################################################################################################################################################
    def Search(self, results, media, lang, manual, movie):
        Log.Debug("=== Search - Begin - ================================================================================================")
        orig_title = ( media.title if movie else media.show )
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

    ### Parse the AniDB anime title XML ##################################################################################################################################
    def Update(self, metadata, media, lang, force, movie):

        Log.Debug('--- Update Begin -------------------------------------------------------------------------------------------')
        if not "-" in metadata.id:  metadata.id = "anidb-" + metadata.id  # Old metadata from when the id was only the anidbid
        Log.Debug("Update - metadata source: '%s', id: '%s', Title: '%s',(%s, %s, %s)" % (metadata.id.split('-')[0], metadata.id.split('-')[1], metadata.title, "[...]", "[...]", force) )
        global SERIE_LANGUAGE_PRIORITY, EPISODE_LANGUAGE_PRIORITY
        error_log = { 'anime-list anidbid missing': [], 'anime-list tvdbid missing': [], 'anime-list studio logos': [], 'Missing episodes'    : [], 'Plex themes missing'    : [],
                      'AniDB summaries missing'   : [], 'AniDB posters missing'    : [], 'TVDB summaries missing' : [], 'TVDB posters missing': []}
        getElementText = lambda el, xp: el.xpath(xp)[0].text if el is not None and el.xpath(xp) and el.xpath(xp)[0].text else ""  # helper for getting text from XML element
        series = Series()
     
        ### Get tvdbid, tmdbid, imdbid (+etc...) through mapping file ###
        tvdbid, tmdbid, imdbid, defaulttvdbseason, mapping_studio, poster_id, mappingList, anidbid_table = "", "", "", "", "", "", {}, []
        tvdbposternumber, tvdb_table, tvdbtitle, tvdbOverview, tvdbNetwork, tvdbFirstAired, tvdbRating, tvdbContentRating, tvdbgenre = 0, {}, "", "", "", "", None, None, ()
        if   metadata.id.startswith("tvdb-"):  tvdbid = metadata.id [len("tvdb-"):]
        elif metadata.id.startswith("anidb-"):
            anidbid=metadata.id[len("anidb-"):]
            tvdbid, tmdbid, imdbid, defaulttvdbseason, mappingList, mapping_studio, anidbid_table, poster_id = Helpers().anidbTvdbMapping(metadata, anidbid, error_log)

        if tvdbid.isdigit(): ### TVDB ID exists ####
            newTVDB = TVDB(metadata, media, lang, force, movie)
            newTVDB.populate(series, tvdbid)
          
            newPlex = Plex(metadata, media, lang, force, movie)
            newPlex.populate(series, tvdbid)
        
        if anidbid.isdigit(): ### ANIDB ID exists ####        
            newAniDB = AniDB(metadata, media, lang, force, movie)
            newAniDB.populate(series, anidbid)            
            
        ### TVDB mode when a season 2 or more exist ############################################################################################################
        providerNum = 0

        try: 
            data = sorted(series.title, key=lambda x: x.provider,  reverse=False)[0].value      
            metadata.title = data
        except: Log.Debug("Update() - Error Title")
        try: 
            data = sorted(series.rating, key=lambda x: x.provider,  reverse=False)[0].value
            metadata.rating = data
        except: Log.Debug("Update() - Error Rating")
        try: 
            data = sorted(series.overview, key=lambda x: x.provider,  reverse=False)[0].value
            metadata.summary = data
        except: Log.Debug("Update() - Error Overview")
        try:
            data = sorted(series.network, key=lambda x: x.provider,  reverse=False)[0].value
            metadata.studio = data
        except: Log.Debug("Update() - Error Network")
        try: 
            data = sorted(series.contentRating, key=lambda x: x.provider,  reverse=False)[0].value
            metadata.content_rating = data
        except: Log.Debug("Update() - Error Content Rating")
        try: 
            data = sorted(series.firstAired, key=lambda x: x.provider,  reverse=False)[0].value
            metadata.originally_available_at = data
        except: Log.Debug("Update() - Error Aired")
        try: 
            data = sorted(series.genres, key=lambda x: x.provider,  reverse=False)[0].value
            metadata.genres.clear()
            for genre in data: metadata.genres.add(genre)
        except: Log.Debug("Update() - Error Genre")
        list_eps = ""
        
        for media_season in sorted(media.seasons, key=lambda x: int(x),  reverse=False): 
            # try: 
                # data = sorted(filter(lambda i: i.value.name != None, filter(lambda i: i.value.altNumber == media_season, series.seasons)), key=lambda x: x.provider,  reverse=False)      
                # metadata.seasons[media_season].title = data[0].value.name
                # Log.Debug("Update() - Season Title: %s" % data[0].value.name)
            # except: Log.Debug("Update() - Error Season Title")
            # try: 
                # data = sorted(filter(lambda i: i.value.name != None, filter(lambda i: i.value.altNumber == media_season, series.seasons)), key=lambda x: x.provider,  reverse=False)      
                # metadata.seasons[media_season].summary = data[0].value.overview
                # Log.Debug("Update() - Season Overview: %s" % data[0].value.overview)
            # except: Log.Debug("Update() - Error Season Overview")
            # try: 
                # data = sorted(filter(lambda i: i.value.name != None, filter(lambda i: i.value.altNumber == media_season, series.seasons)), key=lambda x: x.provider,  reverse=False)      
                # metadata.seasons[media_season].show = data[0].value.show
                # metadata.seasons[media_season].show = metadata.title
                # Log.Debug("Update() - Season Show: %s" % data[0].value.show)
            # except: Log.Debug("Update() - Error Season Show")
            # try: 
                # data = sorted(filter(lambda i: i.value.name != None, filter(lambda i: i.value.altNumber == media_season, series.seasons)), key=lambda x: x.provider,  reverse=False)              
                # metadata.seasons[media_season].network = data[0].value.network
                # Log.Debug("Update() - Season Network: %s" % data[0].value.network)
            # except: Log.Debug("Update() - Error Season Network")
            ##metadata.seasons[media_season].summary, metadata.seasons[media_season].title, metadata.seasons[media_season].show, metadata.seasons[media_season].source_title = "#" + series.overview[providerNum].value, "#" + series.title[providerNum].value, "#" + series.title[providerNum].value, "#" + series.network[providerNum].value      
            for media_episode in sorted(media.seasons[media_season].episodes, key=lambda x: int(x),  reverse=False):
                Log.Debug("-----------")
                try: seasonEpisodeCount = Helpers().totalArray(series.tvdbSeasonLayout, 1, int(media_season ) - 1)
                except: seasonEpisodeCount = 0
                episode = []
                episodeTemp = []
                episodeTemp = filter(lambda i: (i.value.mappedNumber and i.value.mappedSeason) 
                and i.value.mappedSeason == media_season and i.value.mappedNumber == media_episode 
                and len(filter(lambda x: x.provider == i.provider , episode)) == 0 , series.episodes)
                if len(episodeTemp) > 0: 
                    episode = episode + episodeTemp
                    for matchedEps in episodeTemp:
                        Log.Debug("Update() - Match by Mapping | Provider: %s - %s" % (matchedEps.provider, matchedEps.value.name))
                    episodeTemp = []        
                if len(episode) < 2:
                    episodeTemp = filter(lambda i: i.value.season == media_season and i.value.number == media_episode 
                    #and (i.value.altSeason == None and i.value.derivedSeason == None and i.value.derivedAltSeason == None)
                    and (i.value.mappedNumber == None and i.value.mappedSeason == None)
                    and len(filter(lambda x: x.provider == i.provider , episode)) == 0, series.episodes)  
                    if len(episodeTemp) > 0:
                        for matchedEps in episodeTemp:
                            Log.Debug("Update() - Match by Season | Provider: %s - %s" % (matchedEps.provider, matchedEps.value.name))
                        episode = episode + episodeTemp
                        episodeTemp = []                                          
                if len(episode) < 2:
                    episodeTemp = filter(lambda i: (i.value.derivedNumber and i.value.derivedSeason)
                    and i.value.derivedSeason == media_season and i.value.derivedNumber == media_episode
                    and (i.value.mappedNumber == None and i.value.mappedSeason == None)
                    and len(filter(lambda x: x.provider == i.provider , episode)) == 0 , series.episodes)
                    if len(episodeTemp) > 0: 
                        episode = episode + episodeTemp
                        for matchedEps in episodeTemp:
                            Log.Debug("Update() - Match by Derived | Provider: %s - %s" % (matchedEps.provider, matchedEps.value.name))
                        episodeTemp = []
                if len(episode) < 2: 
                    episodeTemp = filter(lambda i: str(i.value.absolute) == str(int(seasonEpisodeCount) + int(media_episode)) and media_season != "0"
                    and (i.value.mappedNumber == None and i.value.mappedSeason == None)
                    and len(filter(lambda x: x.provider == i.provider , episode)) == 0 , series.episodes)
                    if len(episodeTemp) > 0: 
                        episode = episode + episodeTemp
                        for matchedEps in episodeTemp:
                            Log.Debug("Update() - Match by Absolute | Provider: %s - %s" % (matchedEps.provider, matchedEps.value.name))
                        Log.Debug("Update() - Map: %s %s" % (series.tvdbSeasonLayout, media_season))
                        seasonEpisodeCount = Helpers().totalArray(series.tvdbSeasonLayout, 1, int(media_season) - 1)
                        episodeTemp = []   
                if len(episode) == 0 and int(media_episode) > 150 and re.match(r'.*\b(?:NCED|ED)+\d*\b.*', str(os.path.splitext(os.path.basename(media.seasons[media_season].episodes[media_episode].items[0].parts[0].file))[0]), re.IGNORECASE):
                    episode.append(WeightedEntry(Episode("Ending " + str(int(media_episode)-150) , media_episode, 
                        media_season, "", 
                        "", None, 
                        None, None, 
                        None, None,
                        None, None,
                        None, None,
                        None, None), Providers.Plex))
                    Log.Debug("Update() - Added Additional ED: %s | %s" % ("Ending " + str(int(media_episode)-150), str(os.path.splitext(os.path.basename(media.seasons[media_season].episodes[media_episode].items[0].parts[0].file))[0])))                
                if len(episode) == 0 and int(media_episode) > 100 and re.match(r'.*\b(?:NCOP|OP)+\d*\b.*', str(os.path.splitext(os.path.basename(media.seasons[media_season].episodes[media_episode].items[0].parts[0].file))[0]), re.IGNORECASE):
                    episode.append(WeightedEntry(Episode("Opening " + str(int(media_episode)-100) , media_episode, 
                        media_season, "", 
                        "", None, 
                        None, None, 
                        None, None,
                        None, None,
                        None, None,
                        None, None), Providers.Plex))
                    Log.Debug("Update() - Added Additional OP: %s | %s" % ("Opening " + str(int(media_episode)-100), str(os.path.splitext(os.path.basename(media.seasons[media_season].episodes[media_episode].items[0].parts[0].file))[0])))    
                Log.Debug("Update() - Search For : S%sE%s (%s | %s) | %s" % (media_season, media_episode, str(int(float(int(seasonEpisodeCount) + int(media_episode)))), seasonEpisodeCount, os.path.splitext(os.path.basename(media.seasons[media_season].episodes[media_episode].items[0].parts[0].file))[0]))
                Log.Debug("Update() - Episodes Matched: %s" % (len(episode)))
                if len(episode) > 0:    
                  
                  
                    #Log.Debug("Update() - Provider: %s " % (episode[0].provider))
                    #data = sorted(episode.value.ranking, key=lambda x: x.provider,  reverse=False)
                    
                    #episode = episode[0].value 
                    #Log.Debug("%s" % series.tvdbSeasonLayout)
                    #Log.Debug("Update() - Provider: %s, %s, %s | %s" % (episode[0].value.season, episode[0].value.number, episode[0].value.altSeason, episode[0].provider))
                    #Log.Debug("Update() - Provider: %s, %s" % (episode[1].value.overview, episode[1].provider))
                    #Log.Debug("Update() - Provider: %s, %s" % (episode[0].value.overview, episode[0].provider))
                    for matchedEps in episode:
                        Log.Debug("Update() - Match: Provider: %s | Original: S%sE%s, Alt: S%sE%s, Derived: S%sE%s, DerAlt: S%sE%s, Map: S%sE%s, Abs: %s| Media: S%sE%s, Abs: %s" % (matchedEps.provider ,matchedEps.value.season, matchedEps.value.number, matchedEps.value.altSeason, matchedEps.value.altNumber,
                        matchedEps.value.derivedSeason, matchedEps.value.derivedNumber, matchedEps.value.derivedAltSeason, matchedEps.value.derivedAltNumber, matchedEps.value.mappedSeason, matchedEps.value.mappedNumber, matchedEps.value.absolute, media_season, media_episode, str(int(seasonEpisodeCount) + int(media_episode))))
                          
                    if media_season > 0:
                        ep, episode_count = "s%se%s" % (media_season, media_episode), 0
                        ##if ep in series.episodes:
                        try:
                            data = sorted(filter(lambda i: i.value.overview != None, episode), key=lambda x: x.provider,  reverse=False)[0].value.overview
                            metadata.seasons[media_season].episodes[media_episode].summary = data
                        except: Log.Debug("Update() - Episode Error Overview")
                        try:
                            data = sorted(filter(lambda i: i.value.name != None, episode), key=lambda x: x.provider,  reverse=False)[0].value.name
                            metadata.seasons[media_season].episodes[media_episode].title = data
                        except: Log.Debug("Update() - Episode Error Name")    
                        try:
                            data = sorted(filter(lambda i: i.value.rating != None, episode), key=lambda x: x.provider,  reverse=False)[0].value.rating
                            metadata.seasons[media_season].episodes[media_episode].rating = float(data)
                        except: Log.Debug("Update() - Episode Error Rating")  
                        try:
                            data = sorted(filter(lambda i: i.value.firstAired != None, episode), key=lambda x: x.provider,  reverse=False)[0].value.firstAired
                            metadata.seasons[media_season].episodes[media_episode].originally_available_at = datetime.datetime.strptime(data, "%Y-%m-%d").date()
                        except: Log.Debug("Update() - Episode Error Aired") 
                        try:
                            data = sorted(filter(lambda i: i.value.filename != None, episode), key=lambda x: x.provider,  reverse=False)[0].value.filename
                            Helpers().metadata_download (metadata.seasons[media_season].episodes[media_episode].thumbs, TVDB_IMAGES_URL + data, 1, "TVDB/episodes/"+ os.path.basename(data)) 
                        except: Log.Debug("Update() - Episode Error Filename")              
                        for media_item in media.seasons[media_season].episodes[media_episode].items:
                            for item_part in media_item.parts:  Log("File: '%s', %s" % (item_part.file, item_part.streams[0]))
                              
                      
                        list_eps = list_eps + ep + ", "
            metadata.seasons[media_season].episode_count = seasonEpisodeCount #len(media.seasons[media_season].episodes) #An integer specifying the number of episodes in the season.
            
        if list_eps !="":  Log.Debug("Update() - On Disk: " + list_eps)    
        Log.Debug("Update() - On Web: %s" % str([str('s' + i.value.season + 'e' + i.value.number) for i in series.episodes]))   
          

        ### AMSA - Load logs, add non-present entried then Write log files to Plug-in /Support/Data/com.plexapp.agents.Amsa/DataItems ###
        for log in error_log:
            if error_log[log] != []:
                if Data.Exists(log+".htm"):  string = Data.Load(log+".htm")
                else:
                    string=""
                    if log == 'TVDB posters missing': string = WEB_LINK % ("http://thetvdb.com/wiki/index.php/Posters",              "Restrictions") + "<br />\n"
                    if log == 'Plex themes missing':  string = WEB_LINK % ("https://plexapp.zendesk.com/hc/en-us/articles/201572843","Restrictions") + "<br />\n"
                for entry in error_log[log]:
                    if entry not in string:  Data.Save(log+".htm", string + entry + "<br />\r\n")
        Log.Debug('--- Update end -------------------------------------------------------------------------------------------------')
   
### Agent declaration ###############################################################################################################################################
class AmsaTVAgent(Agent.TV_Shows, AmsaCommonAgent):
    name, primary_provider, fallback_agent, contributes_to, languages, accepts_from = ('Anime Multi Source Agent', True, False, None, [Locale.Language.English,], ['com.plexapp.agents.localmedia'] ) #, 'com.plexapp.agents.opensubtitles'
    def search(self, results,  media, lang, manual): self.Search(results,  media, lang, manual, False )
    def update(self, metadata, media, lang, force ): self.Update(metadata, media, lang, force,  False )

    
