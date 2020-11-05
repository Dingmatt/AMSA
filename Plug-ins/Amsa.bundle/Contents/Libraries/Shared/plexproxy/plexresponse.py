
class plexResponse(object):
    data = None
    headers = None
    response_code = None
    request = None

    def __init__(self, response, status_code, request):
        """
        Initialize the response.

        Args:
            self: (todo): write your description
            response: (list): write your description
            status_code: (int): write your description
            request: (dict): write your description
        """
        if response:
            self.data = response.content
            self.headers = response.headers
        self.response_code = status_code
        self.request = request

    def content(self):
        """
        Returns the content of the response.

        Args:
            self: (todo): write your description
        """
        return self.data

    content = property(content)

    def status_code(self):
        """
        Return the status code.

        Args:
            self: (todo): write your description
        """
        return self.response_code

    status_code = property(status_code)

    def url(self):
        """
        The url for this url.

        Args:
            self: (todo): write your description
        """
        return self.request.url

    url = property(url)

    def __str__(self):
        """
        Return the string representation of the string.

        Args:
            self: (todo): write your description
        """
        return str(self.data)

    def __unicode__(self):
        """
        Return unicode string.

        Args:
            self: (todo): write your description
        """
        return unicode(self.data)

    def __repr__(self):
        """
        Return a repr representation of this object.

        Args:
            self: (todo): write your description
        """
        return repr(self.data)


