import logging

import requests
from bs4 import BeautifulSoup

from http_request_randomizer.requests.parsers.UrlParser import UrlParser

logger = logging.getLogger(__name__)
__author__ = 'pgaref'


class ProxyForEuParser(UrlParser):
    def __init__(self, web_url, bandwithdh=None, timeout=None):
        """
        Initialize the web url.

        Args:
            self: (todo): write your description
            web_url: (str): write your description
            bandwithdh: (str): write your description
            timeout: (int): write your description
        """
        UrlParser.__init__(self, web_url, bandwithdh, timeout)

    def parse_proxyList(self):
        """
        Parse proxy proxy proxy.

        Args:
            self: (todo): write your description
        """
        curr_proxy_list = []
        try:
            response = requests.get(self.get_URl(), timeout=self.timeout)

            if not response.ok:
                logger.warn("Proxy Provider url failed: {}".format(self.get_URl()))
                return []

            content = response.content
            soup = BeautifulSoup(content, "html.parser")
            table = soup.find("table", attrs={"class": "proxy_list"})

            # The first tr contains the field names.
            headings = [th.get_text() for th in table.find("tr").find_all("th")]

            datasets = []
            for row in table.find_all("tr")[1:]:
                dataset = zip(headings, (td.get_text() for td in row.find_all("td")))
                datasets.append(dataset)

            for dataset in datasets:
                # Check Field[0] for tags and field[1] for values!
                address = ""
                proxy_straggler = False
                for field in dataset:
                    # Discard slow proxies! Speed is in KB/s
                    if field[0] == 'Speed':
                        if float(field[1]) < self.get_min_bandwidth():
                            proxy_straggler = True
                    if field[0] == 'IP':
                        # Make sure it is a Valid IP
                        if not UrlParser.valid_ip(field[1]):
                            logger.debug("IP with Invalid format: {}".format(field[1]))
                            break
                        else:
                            address += field[1] + ':'
                    elif field[0] == 'Port':
                        address += field[1]
                # Avoid Straggler proxies and make sure it is a Valid Proxy Address
                if not proxy_straggler and UrlParser.valid_ip_port(address):
                    proxy = "http://" + address
                    curr_proxy_list.append(proxy.__str__())
                    # print "{0:<10}: {1}".format(field[0], field[1])
            # print "ALL: ", curr_proxy_list
        except:
            pass
        return curr_proxy_list

    def __str__(self):
        """
        The minimum bandwidth.

        Args:
            self: (todo): write your description
        """
        return "ProxyForEU Parser of '{0}' with required bandwidth: '{1}' KBs" \
            .format(self.url, self.minimum_bandwidth_in_KBs)
