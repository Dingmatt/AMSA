import re

from http_request_randomizer.requests.errors.ParserExceptions import ParserException

__author__ = 'pgaref'


class UrlParser(object):
    """
        An abstract class representing any URL containing Proxy information
        To add an extra Proxy URL just implement this class and provide a 'url specific' parse_proxyList method

    Attributes:
        site url (hhtp)
        minimum_bandwidth_in_KBs (to avoid straggling proxies when having the extra info from proxy provider)
    """

    def __init__(self, web_url, bandwidthKBs=None, timeout=None):
        self.url = web_url
        self.timeout = timeout
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

    @staticmethod
    def valid_ip(address):
        """Return ``True`` if the the given *IP* is a *valid* IPv4 address

        :param address: ip address
        :type address: string
        :rtype: bool

        """
        try:
            host_bytes = address.split('.')
            valid = [int(b) for b in host_bytes]
            valid = [b for b in valid if b >= 0 and b <= 255]
            return len(host_bytes) == 4 and len(valid) == 4
        except:
            return False

    @staticmethod
    def valid_ip_port(address):
        """Return ``True`` if the the given *Port* is a *valid* IPv4 port

        :param address: ip address
        :type address: string
        :rtype: bool

        """
        match = re.findall(r'[0-9]+(?:\.[0-9]+){3}:[0-9]+', address)
        # hostIP = re.compile("\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}")
        if not match:
            return False
        return True
