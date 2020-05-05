class ParserException(Exception):
    def __init___(self, extraArguments):
        Exception.__init__(self, " was raised with arguments {0}".format(extraArguments))
        self.dErrorArguments = extraArguments
