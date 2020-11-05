from plex.lib import six

import re
import unicodedata

def flatten(text):
    """
    Flatten a string.

    Args:
        text: (str): write your description
    """
    if text is None:
        return None

    # Normalize `text` to ascii
    text = normalize(text)

    # Remove special characters
    text = re.sub('[^A-Za-z0-9\s]+', '', text)

    # Merge duplicate spaces
    text = ' '.join(text.split())

    # Convert to lower-case
    return text.lower()

def normalize(text):
    """
    Normalize text.

    Args:
        text: (str): write your description
    """
    if text is None:
        return None

    # Normalize unicode characters
    if type(text) is six.text_type:
        text = unicodedata.normalize('NFKD', text)

    # Ensure text is ASCII, ignore unknown characters
    text = text.encode('ascii', 'ignore')

    # Return decoded `text`
    return text.decode('ascii')

def to_iterable(value):
    """
    Convert value to iterable.

    Args:
        value: (todo): write your description
    """
    if value is None:
        return None

    if isinstance(value, (list, tuple)):
        return value

    return [value]


def synchronized(func):
    """
    Decorator for a function. task.

    Args:
        func: (todo): write your description
    """
    def wrapper(self, *__args, **__kw):
        """
        Decorator for the wrapped call.

        Args:
            self: (todo): write your description
            __args: (tuple): write your description
            __kw: (todo): write your description
        """
        self._lock.acquire()

        try:
            return func(self, *__args, **__kw)
        finally:
            self._lock.release()

    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__

    return wrapper
