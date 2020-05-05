class ProxyListException(Exception):
    def __init___(self, extraArguments):
        Exception.__init__(self, " was raised - {0}".format(extraArguments))
        self.dErrorArguments = extraArguments