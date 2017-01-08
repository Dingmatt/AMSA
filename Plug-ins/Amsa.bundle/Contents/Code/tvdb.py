import constants, functions
from functions import XMLFromURL, GetElementText

class TvDB(constants.Series):
    def __init__(self, id):
        data = XMLFromURL(constants.TVDB_HTTP_API_URL % id, id + ".xml", "TvDB\\" + id, CACHE_1HOUR * 24).xpath("""/Data""")[0]
        if GetElementText(data, 'Series/SeriesName'):
            self.Title = GetElementText(data, 'Series/SeriesName')
        if GetElementText(data, 'Series/Network'):
            self.Network = GetElementText(data, 'Series/Network')
        if GetElementText(data, 'Series/Overview'): 
            self.Overview = GetElementText(data, 'Series/Overview')
        if GetElementText(data, 'Series/FirstAired'):
            self.FirstAired = GetElementText(data, 'Series/FirstAired')
        if GetElementText(data, 'Series/Genre'):
            self.Genre = filter(None, GetElementText(data, 'Series/Genre').split("|"))
        if GetElementText(data, 'Series/ContentRating'):
            self.ContentRating = GetElementText(data, 'Series/ContentRating')
        if GetElementText(data, 'Series/Rating'):    
            self.Rating = GetElementText(data, 'Series/Rating')
        if GetElementText(data, 'Series/IMDB_ID'):
            self.Title = GetElementText(data, 'Series/IMDB_ID')
        if len(data.xpath("""./Episode""")) > 0:
            self.Episodes = []
            for item in data.xpath("""./Episode"""):
                self.Episodes.append(self.Episode(item))
        
    class Episode(constants.Episode):
        def __init__(self, data):
            if GetElementText(data, 'EpisodeName'):
                self.Name = GetElementText(data, 'EpisodeName')
            if GetElementText(data, 'EpisodeNumber'):
                self.Number = str(GetElementText(data, 'EpisodeNumber')).zfill(2)
            if GetElementText(data, 'SeasonNumber'):
                self.Season = str(GetElementText(data, 'SeasonNumber')).zfill(2)
            if GetElementText(data, 'FirstAired' ):
                self.FirstAired = GetElementText(data, 'FirstAired' )
            if GetElementText(data, 'Rating'):
                self.Rating = GetElementText(data, 'Rating')
            if GetElementText(data, 'Overview'):
                self.Overview = GetElementText(data, 'Overview')
            if GetElementText(data, 'filename'):
                self.Filename = GetElementText(data, 'filename')
            if GetElementText(data, 'absolute_number'):
                self.Absolute = int(GetElementText(data, 'absolute_number'))
