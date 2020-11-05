from plex.core.idict import idict
from plex.interfaces.core.base import Interface


class SectionInterface(Interface):
    path = 'library/sections'

    def all(self, key):
        """
        Retrieves all of the keys.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        response = self.http.get(key, 'all')

        return self.parse(response, idict({
            'MediaContainer': ('MediaContainer', idict({
                'Directory': {
                    'artist':   'Artist',
                    'show':     'Show'
                },
                'Video': {
                    'movie':    'Movie'
                }
            }))
        }))

    def recently_added(self, key):
        """
        Retrieves a deferred.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        response = self.http.get(key, 'recentlyAdded')

        return self.parse(response, idict({
            'MediaContainer': ('MediaContainer', idict({
                'Directory': {
                    'artist':   'Artist',
                    'show':     'Show'
                },
                'Video': {
                    'movie':    'Movie',
                    'episode':  'Episode',
                    'clip':     'Clip',
                }
            }))
        }))

    def first_character(self, key, character=None):
        """
        This method is used to get a character.

        Args:
            self: (todo): write your description
            key: (str): write your description
            character: (todo): write your description
        """
        if character:
            response = self.http.get(key, ['firstCharacter', character])

            # somehow plex wrongly returns items of other libraries when character is #
            return self.parse(response, idict({
                'MediaContainer': ('MediaContainer', idict({
                    'Directory': {
                        'album':    'Album',
                        'artist':   'Artist',

                        'season':   'Season',
                        'show':     'Show'
                    },
                    'Video': {
                        'episode':  'Episode',
                        'clip':     'Clip',
                        'movie':    'Movie'
                    },
                    'Track': 'Track'
                }))
            }))

        response = self.http.get(key, 'firstCharacter')

        return self.parse(response, idict({
            'MediaContainer': ('MediaContainer', idict({
                'Directory': 'Directory'
            }))
        }))
