from .core import *
from .codec import *

def ToASCII(label):
    """
    Convert a label string.

    Args:
        label: (str): write your description
    """
    return encode(label)

def ToUnicode(label):
    """
    Convert a label to a string.

    Args:
        label: (str): write your description
    """
    return decode(label)

def nameprep(s):
    """
    Prepares the string name.

    Args:
        s: (todo): write your description
    """
    raise NotImplementedError("IDNA 2008 does not utilise nameprep protocol")

