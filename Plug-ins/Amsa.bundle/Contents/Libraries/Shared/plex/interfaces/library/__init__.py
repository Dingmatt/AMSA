from plex.core.idict import idict
from plex.interfaces.core.base import Interface


class LibraryInterface(Interface):
    path = 'library'

    def metadata(self, rating_key):
        """
        Get the metadata dictionary.

        Args:
            self: (todo): write your description
            rating_key: (str): write your description
        """
        response = self.http.get('metadata', rating_key)

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

    def on_deck(self):
        """
        The deck

        Args:
            self: (todo): write your description
        """
        response = self.http.get('onDeck')

        return self.parse(response, idict({
            'MediaContainer': ('MediaContainer', idict({
                'Video': {
                    'movie':    'Movie',
                    'episode':  'Episode'
                }
            }))
        }))

    def recently_added(self):
        """
        Returns a dictionary of the most recent recent recent.

        Args:
            self: (todo): write your description
        """
        response = self.http.get('recentlyAdded')

        return self.parse(response, idict({
            'MediaContainer': ('MediaContainer', idict({
                'Directory': {
                    'album':    'Album',
                    'season':   'Season'
                },
                'Video': {
                    'movie':    'Movie'
                }
            }))
        }))

    def sections(self):
        """
        Returns a dictionary.

        Args:
            self: (todo): write your description
        """
        response = self.http.get('sections')

        return self.parse(response, idict({
            'MediaContainer': ('SectionContainer', idict({
                'Directory': ('Section', idict({
                    'Location': 'Location'
                }))
            }))
        }))

    #
    # Item actions
    #

    def rate(self, key, rating):
        """
        The rate. rate

        Args:
            self: (todo): write your description
            key: (str): write your description
            rating: (int): write your description
        """
        response = self.http.get(
            '/:/rate',
            query={
                'identifier': 'com.plexapp.plugins.library',
                'key': key,
                'rating': int(round(rating, 0))
            }
        )

        return response.status_code == 200

    def scrobble(self, key):
        """
        Retrieve a scrobble

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        response = self.http.get(
            '/:/scrobble',
            query={
                'identifier': 'com.plexapp.plugins.library',
                'key': key
            }
        )

        return response.status_code == 200

    def unscrobble(self, key):
        """
        Removes a scrobble

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        response = self.http.get(
            '/:/unscrobble',
            query={
                'identifier': 'com.plexapp.plugins.library',
                'key': key
            }
        )

        return response.status_code == 200
