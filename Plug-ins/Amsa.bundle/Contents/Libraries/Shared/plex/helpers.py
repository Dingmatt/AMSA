def has_attribute(obj, name):
    """
    Returns true if the object has an attribute.

    Args:
        obj: (todo): write your description
        name: (str): write your description
    """
    try:
        object.__getattribute__(obj, name)
        return True
    except AttributeError:
        return False
