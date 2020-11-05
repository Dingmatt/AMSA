from plex.core.configuration import ConfigurationManager
from plex.core.http import HttpClient
from plex.helpers import has_attribute
from plex.interfaces import construct_map
from plex.interfaces.core.base import InterfaceProxy
from plex.lib.six import add_metaclass
from plex.objects.core.manager import ObjectManager

import logging
import socket

log = logging.getLogger(__name__)


class PlexClient(object):
    __interfaces = None

    def __init__(self):
        """
        Initialize the configuration.

        Args:
            self: (todo): write your description
        """
        # Construct interfaces
        self.http = HttpClient(self)
        self.configuration = ConfigurationManager()

        self.__interfaces = construct_map(self)

        # Discover modules
        ObjectManager.construct()

    @property
    def base_url(self):
        """
        The base url.

        Args:
            self: (todo): write your description
        """
        host = self.configuration.get('server.host', '127.0.0.1')
        port = self.configuration.get('server.port', 32400)

        return 'http://%s:%s' % (host, port)

    def __getitem__(self, path):
        """
        Gets an item from a path.

        Args:
            self: (todo): write your description
            path: (str): write your description
        """
        parts = path.strip('/').split('/')

        cur = self.__interfaces
        parameters = []

        while parts and type(cur) is dict:
            key = parts.pop(0)

            if key == '*':
                key = None
            elif key not in cur:
                if None in cur:
                    parameters.append(key)

                    cur = cur[None]
                    continue

                return None

            cur = cur[key]

        while type(cur) is dict:
            cur = cur.get(None)

        if parts:
            parameters.extend(parts)

        if parameters:
            return InterfaceProxy(cur, parameters)

        return cur

    def __getattr__(self, name):
        """
        Returns an attribute of an attribute.

        Args:
            self: (todo): write your description
            name: (str): write your description
        """
        interface = self.__interfaces.get(None)

        if not interface:
            raise Exception("Root interface not found")

        return getattr(interface, name)


class PlexMeta(type):
    @property
    def client(cls):
        """
        Return a : class.

        Args:
            cls: (todo): write your description
        """
        if cls._client is None:
            cls.construct()

        return cls._client

    def __getattr__(self, name):
        """
        Returns the attribute of an attribute.

        Args:
            self: (todo): write your description
            name: (str): write your description
        """
        if has_attribute(self, name):
            return super(PlexMeta, self).__getattribute__(name)

        if self.client is None:
            self.construct()

        return getattr(self.client, name)

    def __setattr__(self, name, value):
        """
        Sets the value of an object.

        Args:
            self: (todo): write your description
            name: (str): write your description
            value: (todo): write your description
        """
        if has_attribute(self, name):
            return super(PlexMeta, self).__setattr__(name, value)

        if self.client is None:
            self.construct()

        setattr(self.client, name, value)

    def __getitem__(self, key):
        """
        Returns the value from the key.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        if self.client is None:
            self.construct()

        return self.client[key]


@add_metaclass(PlexMeta)
class Plex(object):
    _client = None

    @classmethod
    def construct(cls):
        """
        Construct a new client.

        Args:
            cls: (todo): write your description
        """
        cls._client = PlexClient()
