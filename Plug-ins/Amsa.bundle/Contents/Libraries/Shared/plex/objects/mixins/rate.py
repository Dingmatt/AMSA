from plex import Plex
from plex.objects.core.base import Property, DescriptorMixin


class RateMixin(DescriptorMixin):
    rating = Property(type=float)
    user_rating = Property('userRating', type=float)

    def rate(self, value):
        """
        Return the rate.

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        return Plex['library'].rate(self.rating_key, value)
