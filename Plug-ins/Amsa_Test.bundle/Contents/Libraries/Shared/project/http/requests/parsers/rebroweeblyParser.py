import requests
from bs4 import BeautifulSoup

from http.requests.parsers.UrlParser import UrlParser

__author__ = 'pgaref'


class rebroweeblyParser(UrlParser):
    def __init__(self, web_url):
        UrlParser.__init__(self, web_url)

    def parse_proxyList(self):
        curr_proxy_list = []
        content = requests.get(self.get_URl()).content
        soup = BeautifulSoup(content, "html.parser")
        table = soup.find("div", attrs={"class": "paragraph", 'style': "text-align:left;"}).find('font', attrs={
            'color': '#33a27f'})

        for row in [x for x in table.contents if getattr(x, 'name', None) != 'br']:
            proxy = "http://" + row
            curr_proxy_list.append(proxy.__str__())
        return curr_proxy_list

    def __str__(self):
        return "RebroWeebly Parser of '{0}' with required bandwidth: '{1}' KBs" \
            .format(self.url, self.minimum_bandwidth_in_KBs)
