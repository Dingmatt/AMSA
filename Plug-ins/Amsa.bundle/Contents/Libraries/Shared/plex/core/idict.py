from plex.lib.six import string_types

class idict(dict):
    def __init__(self, initial=None):
        """
        Initialize the object

        Args:
            self: (todo): write your description
            initial: (todo): write your description
        """
        if initial:
            self.update(initial)

    def get(self, k, d=None):
        """
        Returns the value of k.

        Args:
            self: (todo): write your description
            k: (str): write your description
            d: (int): write your description
        """
        if isinstance(k, string_types):
            k = k.lower()

        if super(idict, self).__contains__(k):
            return self[k]

        return d

    def update(self, E=None, **F):
        """
        R update the dictionary.

        Args:
            self: (todo): write your description
            E: (array): write your description
            F: (array): write your description
        """
        if E:
            if hasattr(E, 'keys'):
                # Update with `E` dictionary
                for k in E:
                    self[k] = E[k]
            else:
                # Update with `E` items
                for (k, v) in E:
                    self[k] = v

        # Update with `F` dictionary
        for k in F:
            self[k] = F[k]

    def __contains__(self, k):
        """
        Determine if k is contained in k.

        Args:
            self: (todo): write your description
            k: (str): write your description
        """
        if isinstance(k, string_types):
            k = k.lower()

        return super(idict, self).__contains__(k)

    def __delitem__(self, k):
        """
        Removes an item.

        Args:
            self: (todo): write your description
            k: (str): write your description
        """
        if isinstance(k, string_types):
            k = k.lower()

        super(idict, self).__delitem__(k)

    def __getitem__(self, k):
        """
        Returns the value from k from k.

        Args:
            self: (todo): write your description
            k: (str): write your description
        """
        if isinstance(k, string_types):
            k = k.lower()

        return super(idict, self).__getitem__(k)

    def __setitem__(self, k, value):
        """
        Sets the k.

        Args:
            self: (todo): write your description
            k: (str): write your description
            value: (str): write your description
        """
        if isinstance(k, string_types):
            k = k.lower()

        super(idict, self).__setitem__(k, value)
