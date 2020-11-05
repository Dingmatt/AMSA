from plex.core.idict import idict
from plex.objects.core.base import Property
from plex.objects.directory import Directory


class Section(Directory):
    uuid = Property

    filters = Property(type=bool)
    refreshing = Property(type=bool)

    agent = Property
    scanner = Property
    language = Property

    composite = Property
    type = Property

    created_at = Property('createdAt', int)

    def __transform__(self):
        """
        Transform the transform

        Args:
            self: (array): write your description
        """
        self.path = '/library/sections/%s' % self.key

    def all(self):
        """
        Returns all the list of all the jobs.

        Args:
            self: (todo): write your description
        """
        response = self.http.get('all')

        return self.parse(response, idict({
            'MediaContainer': ('MediaContainer', idict({
                'Directory': {
                    'artist':    'Artist',
                    'show':     'Show'
                },
                'Video': {
                    'movie':    'Movie'
                }
            }))
        }))
