from plex.core.idict import idict
from plex.interfaces.core.base import Interface


class LibraryMetadataInterface(Interface):
    path = 'library/metadata'

    def refresh(self, key):
        """
        Refresh the key

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
	response = self.http.put(str(key) + "/refresh")

    def all_leaves(self, key):
        """
        Retrieves all leaves.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        response = self.http.get(key, 'allLeaves')

        return self.parse(response, idict({
            'MediaContainer': {
                '_': 'viewGroup',

                'episode': ('ShowLeavesContainer', idict({
                    'Video': {
                        'episode': 'Episode'
                    }
                })),

                'track': ('ArtistLeavesContainer', idict({
                    'Track': 'Track'
                }))
            }
        }))

    def children(self, key):
        """
        The children of the children.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        response = self.http.get(key, 'children')

        return self.parse(response, idict({
            'MediaContainer': {
                '_': 'viewGroup',

                # ---------------------------------------
                # Music
                # ---------------------------------------
                'album': ('ArtistChildrenContainer', idict({
                    'Directory': {
                        'album': 'Album'
                    }
                })),

                'track': ('AlbumChildrenContainer', idict({
                    'Track': 'Track'
                })),

                # ---------------------------------------
                # TV
                # ---------------------------------------
                'season': ('ShowChildrenContainer', idict({
                    'Directory': {
                        'season': 'Season'
                    }
                })),

                'episode': ('SeasonChildrenContainer', idict({
                    'Video': {
                        'episode': 'Episode'
                    }
                }))
            }
        }))
