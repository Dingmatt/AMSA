from plex import Plex
from plex.objects.core.base import DescriptorMixin


class ScrobbleMixin(DescriptorMixin):
    def scrobble(self):
        """
        Returns a screenshot for this user.

        Args:
            self: (todo): write your description
        """
        return Plex['library'].scrobble(self.rating_key)
