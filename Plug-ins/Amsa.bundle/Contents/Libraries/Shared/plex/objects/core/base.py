from plex.lib.six import add_metaclass
from plex.interfaces.core.base import Interface

import logging
import traceback
import types

log = logging.getLogger(__name__)


class Property(object):
    helpers = Interface.helpers

    def __init__(self, name=None, type=None, resolver=None):
        """
        Initialize the resolver.

        Args:
            self: (todo): write your description
            name: (str): write your description
            type: (str): write your description
            resolver: (todo): write your description
        """
        self.name = name
        self.type = type
        self.resolver = resolver

    def value(self, client, key, node, keys_used):
        """
        Get the value of a node.

        Args:
            self: (todo): write your description
            client: (todo): write your description
            key: (str): write your description
            node: (todo): write your description
            keys_used: (str): write your description
        """
        if self.resolver is not None:
            return self.value_func(client, node, keys_used)

        return self.value_node(key, node, keys_used)

    def value_node(self, key, node, keys_used):
        """
        Return the value of a given key.

        Args:
            self: (todo): write your description
            key: (str): write your description
            node: (todo): write your description
            keys_used: (list): write your description
        """
        value = self.helpers.get(node, key)
        keys_used.append(key.lower())

        if value is None:
            return None

        return self.value_convert(value)

    def value_convert(self, value):
        """
        Convert the value to the given type.

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        if not self.type:
            return value

        types = self.type if type(self.type) is list else [self.type]
        result = value

        for target_type in types:
            try:
                result = target_type(result)
            except:
                return None

        return result

    def value_func(self, client, node, keys_used):
        """
        Execute the value.

        Args:
            self: (todo): write your description
            client: (todo): write your description
            node: (todo): write your description
            keys_used: (todo): write your description
        """
        func = self.resolver()

        try:
            keys, value = func(client, node)

            keys_used.extend([k.lower() for k in keys])
            return value
        except Exception as ex:
            log.warn('Exception in value function (%s): %s - %s', func, ex, traceback.format_exc())
            return None


class DescriptorMeta(type):
    def __init__(self, name, bases, attrs):
        """
        Initialize the field.

        Args:
            self: (todo): write your description
            name: (str): write your description
            bases: (float): write your description
            attrs: (dict): write your description
        """
        super(DescriptorMeta, self).__init__(name, bases, attrs)

        Interface.object_map[self.__name__] = self


@add_metaclass(DescriptorMeta)
class Descriptor(Interface):
    attribute_map = None

    def __init__(self, client, path):
        """
        Initialize the client.

        Args:
            self: (todo): write your description
            client: (todo): write your description
            path: (str): write your description
        """
        super(Descriptor, self).__init__(client)
        self.path = path

        self._children = None

    @classmethod
    def properties(cls):
        """
        Return an iterator over all the properties of the class.

        Args:
            cls: (todo): write your description
        """
        keys = [k for k in dir(cls) if not k.startswith('_')]

        #log.debug('%s - keys: %s', self, keys)

        for key in keys:
            if key.startswith('_'):
                continue

            value = getattr(cls, key)

            if value is Property:
                yield key, Property(key)
            elif isinstance(value, Property):
                yield key, value

    @classmethod
    def construct(cls, client, node, attribute_map=None, path=None, child=False):
        """
        Construct a key object from a node.

        Args:
            cls: (todo): write your description
            client: (todo): write your description
            node: (todo): write your description
            attribute_map: (dict): write your description
            path: (str): write your description
            child: (todo): write your description
        """
        if node is None:
            return [], None

        keys_available = [k.lower() for k in node.keys()]
        keys_used = []

        if attribute_map is None:
            attribute_map = cls.attribute_map or {}

        require_map = attribute_map.get('*') != '*'

        # Determine path from object "key"
        key = cls.helpers.get(node, 'key')

        if key is not None:
            path = key[:key.rfind('/')]

        # Construct object
        obj = cls(client, path)

        #log.debug('%s - Properties: %s', cls.__name__, list(obj.properties()))

        for key, prop in cls.properties():
            node_key = prop.name or key

            if attribute_map:
                if node_key in attribute_map:
                    node_key = attribute_map.get(node_key)
                elif require_map:
                    setattr(obj, key, None)
                    continue

            #log.debug('%s - Found property "%s"', cls.__name__, key)
            setattr(obj, key, prop.value(client, node_key, node, keys_used))

        # Post-fill transformation
        obj.__transform__()

        # Look for omitted keys
        omitted = list(set(keys_available) - set(keys_used))
        omitted.sort()

        if omitted and not child:
            log.warn('%s - Omitted attributes: %s', cls.__name__, ', '.join(omitted))

        return keys_used, obj

    def __transform__(self):
        """
        Returns the : py : param transform.

        Args:
            self: (array): write your description
        """
        pass

    def __iter__(self):
        """
        Returns an iterator over all children of this node.

        Args:
            self: (todo): write your description
        """
        return self._children or []

    def __getstate__(self):
        """
        Return a generator of ( key / value pairs.

        Args:
            self: (todo): write your description
        """
        data = self.__dict__

        def build():
            """
            Builds a list of key value pairs.

            Args:
            """
            for key, value in data.items():
                if isinstance(value, types.GeneratorType):
                    value = list(value)

                if key in ['client']:
                    continue

                yield key, value

        return dict(build())


class DescriptorMixin(Descriptor):
    pass
