# coding=utf-8

import plex

def Get(item_id, plexRequest):
    plex.request.Request = plexRequest
    Plex = plex.Plex
    return Plex["library"].metadata(item_id)
