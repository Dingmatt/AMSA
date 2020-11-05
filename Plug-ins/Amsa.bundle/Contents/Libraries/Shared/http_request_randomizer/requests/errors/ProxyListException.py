class ProxyListException(Exception):
    def __init___(self, extraArguments):
        """
        Initialize the arguments.

        Args:
            self: (todo): write your description
            extraArguments: (str): write your description
        """
        Exception.__init__(self, " was raised - {0}".format(extraArguments))
        self.dErrorArguments = extraArguments