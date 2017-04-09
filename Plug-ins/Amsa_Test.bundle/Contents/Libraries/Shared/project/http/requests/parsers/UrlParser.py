from http.requests.errors.ParserExceptions import ParserException

__author__ = 'pgaref'


class UrlParser(object):
    """
        An abstract class representing any URL containing Proxy information
        To add an extra Proxy URL just implement this class and provide a 'url specific' parse_proxyList method

    Attributes:
        site url (hhtp)
        minimum_bandwidth_in_KBs (to avoid straggling proxies when having the extra info from proxy provider)
    """

    def __init__(self, web_url, bandwidthKBs=None):
        self.url = web_url
        if bandwidthKBs is not None:
            self.minimum_bandwidth_in_KBs = bandwidthKBs
        else:
            self.minimum_bandwidth_in_KBs = 150

    def get_URl(self):
        if self.url is None:
            raise ParserException("webURL is NONE")
        return self.url

    def get_min_bandwidth(self):
        if self.minimum_bandwidth_in_KBs < 0:
            raise ParserException("invalid minimum bandwidth limit {0} ".format(self.minimum_bandwidth_in_KBs))
        return self.minimum_bandwidth_in_KBs

    def parse_proxyList(self):
        raise ParserException(" abstract method should be implemented by each subclass")

    def __str__(self):
        return "URL Parser of '{0}' with required bandwidth: '{1}' KBs" \
            .format(self.url, self.minimum_bandwidth_in_KBs)
