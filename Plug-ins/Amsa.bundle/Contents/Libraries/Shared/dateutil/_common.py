"""
Common code used in multiple modules.
"""

class weekday(object):
    __slots__ = ["weekday", "n"]

    def __init__(self, weekday, n=None):
        """
        Initialize a week.

        Args:
            self: (todo): write your description
            weekday: (todo): write your description
            n: (int): write your description
        """
        self.weekday = weekday
        self.n = n

    def __call__(self, n):
        """
        Calls the function call.

        Args:
            self: (todo): write your description
            n: (array): write your description
        """
        if n == self.n:
            return self
        else:
            return self.__class__(self.weekday, n)

    def __eq__(self, other):
        """
        Return true if two dates.

        Args:
            self: (todo): write your description
            other: (todo): write your description
        """
        try:
            if self.weekday != other.weekday or self.n != other.n:
                return False
        except AttributeError:
            return False
        return True

    __hash__ = None

    def __repr__(self):
        """
        Return a human - friendly representation.

        Args:
            self: (todo): write your description
        """
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "%s(%+d)" % (s, self.n)
