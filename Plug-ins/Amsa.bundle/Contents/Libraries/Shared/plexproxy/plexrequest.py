# coding=utf-8

import plex

def Get(item_id, plexRequest):
    """
    Retrieves a single item from an item.

    Args:
        item_id: (str): write your description
        plexRequest: (todo): write your description
    """
    plex.request.Request = plexRequest
    Plex = plex.Plex
    return Plex["library"].metadata(item_id)
