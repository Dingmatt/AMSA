from plex.interfaces.core.base import Interface


class ChannelInterface(Interface):
    path = 'channels'

    def all(self):
        """
        Returns a list of the result.

        Args:
            self: (todo): write your description
        """
        raise NotImplementedError()
