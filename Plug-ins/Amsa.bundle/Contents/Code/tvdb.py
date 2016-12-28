
class TvDB():
    TVDB_HTTP_API_URL            = 'http://thetvdb.com/api/A27AD9BE0DA63333/series/%s/all/en.xml'                                     # TVDB Serie XML for episodes sumaries for now
    TVDB_BANNERS_URL             = 'http://thetvdb.com/api/A27AD9BE0DA63333/series/%s/banners.xml'                                    # TVDB Serie pictures xml: fanarts, posters, banners
    TVDB_SERIE_SEARCH            = 'http://thetvdb.com/api/GetSeries.php?seriesname='                                                 #
    TVDB_IMAGES_URL              = 'http://thetvdb.com/banners/'                                                                      # TVDB picture directory
    TVDB_SERIE_URL               = 'http://thetvdb.com/?tab=series&id=%s'  