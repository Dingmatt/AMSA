import logging

import requests
from bs4 import BeautifulSoup

from http_request_randomizer.requests.parsers.UrlParser import UrlParser

logger = logging.getLogger(__name__)
__author__ = 'pgaref'


class RebroWeeblyParser(UrlParser):
    def __init__(self, web_url, timeout=None):
        """
        Initialize web proxy

        Args:
            self: (todo): write your description
            web_url: (str): write your description
            timeout: (int): write your description
        """
        self.top_proxy_path = "proxy-list.html"
        self.txt_proxy_path = "txt-lists.html"
        UrlParser.__init__(self, web_url, timeout)

    def parse_proxyList(self, use_top15k=False):
        """
        Parse proxy proxy.

        Args:
            self: (todo): write your description
            use_top15k: (bool): write your description
        """
        curr_proxy_list = []
        try:
            response = requests.get(self.get_URl()+"/"+self.top_proxy_path, timeout=self.timeout)

            if not response.ok:
                logger.warn("Proxy Provider url failed: {}".format(self.get_URl()))
                return []

            content = response.content
            soup = BeautifulSoup(content, "html.parser")
            table = soup.find("div", attrs={"class": "paragraph", 'style': "text-align:left;"}).find('font', attrs={
                'color': '#33a27f'})
            # Parse Top Proxy List page
            for row in [x for x in table.contents if getattr(x, 'name', None) != 'br']:
                # Make sure it is a Valid Proxy Address
                if UrlParser.valid_ip_port(row):
                    proxy = "http://" + row
                    curr_proxy_list.append(proxy.__str__())
                else:
                    logger.debug("Address with Invalid format: {}".format(row))
            # Usually these proxies are stale
            if use_top15k:
                # Parse 15k Nodes Text file (named *-all-*.txt)
                content = requests.get(self.get_URl() + "/" + self.txt_proxy_path).content
                soup = BeautifulSoup(content, "html.parser")
                table = soup.find("div", attrs={"class": "wsite-multicol-table-wrap"})
                for link in table.findAll('a'):
                    current_link = link.get('href')
                    if current_link is not None and "all" in current_link:
                        self.txt_proxy_path = current_link
                more_content = requests.get(self.get_URl()+self.txt_proxy_path).text
                for proxy_address in more_content.split():
                    if UrlParser.valid_ip_port(proxy_address):
                        curr_proxy_list.append(proxy_address)
        except:
            pass
        return curr_proxy_list

    def __str__(self):
        """
        The minimum bandwidth.

        Args:
            self: (todo): write your description
        """
        return "RebroWeebly Parser of '{0}' with required bandwidth: '{1}' KBs" \
            .format(self.url, self.minimum_bandwidth_in_KBs)
