import logging

import requests
from bs4 import BeautifulSoup

from http_request_randomizer.requests.parsers.UrlParser import UrlParser

logger = logging.getLogger(__name__)
__author__ = 'pgaref'


class SamairProxyParser(UrlParser):
    def __init__(self, web_url, timeout=None):
        UrlParser.__init__(self, web_url, timeout)

    def parse_proxyList(self):
        curr_proxy_list = []
        response = requests.get(self.get_URl(), timeout=self.timeout)

        if not response.ok:
            logger.warn("Proxy Provider url failed: {}".format(self.get_URl()))
            return []
        try:
            content = response.content
            soup = BeautifulSoup(content, "html.parser")
            # css provides the port number so we reverse it
            # for href in soup.findAll('link'):
            #     if '/styles/' in href.get('href'):
            #         style = "http://www.samair.ru" + href.get('href')
            #         break
            # css = requests.get(style).content.split('\n')
            # css.pop()
            # ports = {}
            # for l in css:
            #     p = l.split(' ')
            #     key = p[0].split(':')[0][1:]
            #     value = p[1].split('\"')[1]
            #     ports[key] = value

            table = soup.find("table", attrs={"id": "proxylist"})
            # The first tr contains the field names.
            headings = [th.get_text() for th in table.find("tr").find_all("th")]
            for row in table.find_all("tr")[1:]:
                td_row = row.find("td")
                # curr_proxy_list.append('http://' + row.text + ports[row['class'][0]])
                # Make sure it is a Valid Proxy Address
                if UrlParser.valid_ip_port(td_row.text):
                    curr_proxy_list.append('http://' +td_row.text)
                else:
                    logger.debug("Address with Invalid format: {}".format(td_row.text))
        except:
            pass
        return curr_proxy_list

    def __str__(self):
        return "SemairProxy Parser of '{0}' with required bandwidth: '{1}' KBs" \
            .format(self.url, self.minimum_bandwidth_in_KBs)
