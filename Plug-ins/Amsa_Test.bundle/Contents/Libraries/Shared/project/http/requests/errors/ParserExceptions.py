class ParserException(Exception):
    def __init___(self, dErrorArguments):
        Exception.__init__(self, " was raised with arguments {0}".format(dErrorArguments))
        self.dErrorArguments = dErrorArguments
