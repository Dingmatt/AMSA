from plex.core.helpers import to_iterable
from plex.objects.library.container import MediaContainer


class SessionContainer(MediaContainer):
    filter_passes = lambda _, allowed, value: allowed is None or value in allowed

    def filter(self, keys=None):
        """
        Filter the set of keys.

        Args:
            self: (todo): write your description
            keys: (list): write your description
        """
        keys = to_iterable(keys)

        for item in self:
            if not self.filter_passes(keys, item.session.key):
                continue

            yield item

    def get(self, key):
        """
        Returns the value of a key.

        Args:
            self: (todo): write your description
            key: (todo): write your description
        """
        for item in self.filter(key):
            return item

        return None
