class ConfigurationManager(object):
    def __init__(self):
        """
        Initialize the stack.

        Args:
            self: (todo): write your description
        """
        self.stack = [
            Configuration(self)
        ]

    @property
    def current(self):
        """
        Return the current stack.

        Args:
            self: (todo): write your description
        """
        return self.stack[-1]

    @property
    def defaults(self):
        """
        Returns the default stack of the stack.

        Args:
            self: (todo): write your description
        """
        return self.stack[0]

    def authentication(self, token):
        """
        Returns the given token.

        Args:
            self: (todo): write your description
            token: (str): write your description
        """
        return Configuration(self).authentication(token)

    def cache(self, **definitions):
        """
        A decorator.

        Args:
            self: (todo): write your description
            definitions: (todo): write your description
        """
        return Configuration(self).cache(**definitions)

    def client(self, identifier, product, version):
        """
        Creates a client object for the given identifier.

        Args:
            self: (todo): write your description
            identifier: (todo): write your description
            product: (str): write your description
            version: (tuple): write your description
        """
        return Configuration(self).client(identifier, product, version)

    def device(self, name, system):
        """
        Returns a device.

        Args:
            self: (todo): write your description
            name: (str): write your description
            system: (todo): write your description
        """
        return Configuration(self).device(name, system)

    def headers(self, headers):
        """
        Return the headers object.

        Args:
            self: (todo): write your description
            headers: (dict): write your description
        """
        return Configuration(self).headers(headers)

    def platform(self, name, version):
        """
        Return the platform for the given name.

        Args:
            self: (todo): write your description
            name: (str): write your description
            version: (str): write your description
        """
        return Configuration(self).platform(name, version)

    def server(self, host='127.0.0.1', port=32400):
        """
        Return a server instance.

        Args:
            self: (todo): write your description
            host: (str): write your description
            port: (int): write your description
        """
        return Configuration(self).server(host, port)

    def get(self, key, default=None):
        """
        Returns the value of the key.

        Args:
            self: (todo): write your description
            key: (todo): write your description
            default: (todo): write your description
        """
        for x in range(len(self.stack) - 1, -1, -1):
            value = self.stack[x].get(key)

            if value is not None:
                return value

        return default

    def __getitem__(self, key):
        """
        Returns the value of a cache.

        Args:
            self: (dict): write your description
            key: (str): write your description
        """
        return self.get(key)

    def __setitem__(self, key, value):
        """
        Sets the value of a key.

        Args:
            self: (todo): write your description
            key: (str): write your description
            value: (str): write your description
        """
        self.current[key] = value


class Configuration(object):
    def __init__(self, manager):
        """
        Initialize the manager.

        Args:
            self: (todo): write your description
            manager: (todo): write your description
        """
        self.manager = manager

        self.data = {}

    def authentication(self, token):
        """
        Authentication token.

        Args:
            self: (todo): write your description
            token: (str): write your description
        """
        self.data['authentication.token'] = token

        return self

    def cache(self, **definitions):
        """
        Add cached definitions.

        Args:
            self: (todo): write your description
            definitions: (dict): write your description
        """
        for key, value in definitions.items():
            self.data['cache.%s' % key] = value

        return self

    def client(self, identifier, product, version):
        """
        Creates a product.

        Args:
            self: (todo): write your description
            identifier: (todo): write your description
            product: (str): write your description
            version: (tuple): write your description
        """
        self.data['client.identifier'] = identifier

        self.data['client.product'] = product
        self.data['client.version'] = version

        return self

    def device(self, name, system):
        """
        Returns the device.

        Args:
            self: (todo): write your description
            name: (str): write your description
            system: (todo): write your description
        """
        self.data['device.name'] = name
        self.data['device.system'] = system

        return self

    def headers(self, headers):
        """
        Return a dictionary of headers.

        Args:
            self: (todo): write your description
            headers: (dict): write your description
        """
        self.data['headers'] = headers

        return self

    def platform(self, name, version):
        """
        Return the platform name.

        Args:
            self: (todo): write your description
            name: (str): write your description
            version: (str): write your description
        """
        self.data['platform.name'] = name
        self.data['platform.version'] = version

        return self

    def server(self, host='127.0.0.1', port=32400):
        """
        Return the server instance.

        Args:
            self: (todo): write your description
            host: (str): write your description
            port: (int): write your description
        """
        self.data['server.host'] = host
        self.data['server.port'] = port

        return self

    def get(self, key, default=None):
        """
        Returns the value of a given key.

        Args:
            self: (todo): write your description
            key: (todo): write your description
            default: (todo): write your description
        """
        return self.data.get(key, default)

    def __enter__(self):
        """
        Enter the context manager.

        Args:
            self: (todo): write your description
        """
        self.manager.stack.append(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the given exception.

        Args:
            self: (todo): write your description
            exc_type: (todo): write your description
            exc_val: (todo): write your description
            exc_tb: (todo): write your description
        """
        item = self.manager.stack.pop()

        assert item == self

    def __getitem__(self, key):
        """
        Returns the value of a key.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        return self.data[key]

    def __setitem__(self, key, value):
        """
        Sets the value for a key.

        Args:
            self: (todo): write your description
            key: (str): write your description
            value: (str): write your description
        """
        self.data[key] = value
