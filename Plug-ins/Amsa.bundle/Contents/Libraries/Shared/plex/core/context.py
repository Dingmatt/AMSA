from threading import Lock


class Context(object):
    def __init__(self, **kwargs):
        """
        Initialize the instance.

        Args:
            self: (todo): write your description
        """
        self.kwargs = kwargs

    def __getattr__(self, key):
        """
        Return the value of a key.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        return self.kwargs.get(key)


class ContextStack(object):
    def __init__(self):
        """
        Initialize the internal list.

        Args:
            self: (todo): write your description
        """
        self._list = []
        self._lock = Lock()

    def pop(self):
        """
        Remove and return the last element from the queue.

        Args:
            self: (todo): write your description
        """
        context = self._list.pop()

        self._lock.release()
        return context

    def push(self, **kwargs):
        """
        Pushes a list of lock.

        Args:
            self: (todo): write your description
        """
        self._lock.acquire()

        return self._list.append(Context(**kwargs))
