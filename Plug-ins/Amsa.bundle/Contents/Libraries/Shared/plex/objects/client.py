from plex.core.helpers import to_iterable
from plex.objects.container import Container
from plex.objects.core.base import Property
from plex.objects.server import Server


class Client(Server):
    product = Property
    device_class = Property('deviceClass')

    protocol = Property
    protocol_version = Property('protocolVersion', type=int)
    protocol_capabilities = Property('protocolCapabilities')


class ClientContainer(Container):
    filter_passes = lambda _, allowed, value: allowed is None or value in allowed

    def filter(self, identifiers=None):
        """
        Yield : type.

        Args:
            self: (todo): write your description
            identifiers: (todo): write your description
        """
        identifiers = to_iterable(identifiers)

        for client in self:
            if not self.filter_passes(identifiers, client.machine_identifier):
                continue

            yield client

    def get(self, identifier):
        """
        Get an item from the identifier.

        Args:
            self: (todo): write your description
            identifier: (str): write your description
        """
        for item in self.filter(identifier):
            return item

        return None
