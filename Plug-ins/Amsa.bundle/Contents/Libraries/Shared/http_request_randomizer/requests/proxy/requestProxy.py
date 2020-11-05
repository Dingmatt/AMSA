import logging
import os
import random
import sys
import time

import requests
from requests.exceptions import ChunkedEncodingError
from requests.exceptions import ConnectionError
from requests.exceptions import ReadTimeout

from http_request_randomizer.requests.errors.ProxyListException import ProxyListException
from http_request_randomizer.requests.parsers.FreeProxyParser import FreeProxyParser
from http_request_randomizer.requests.parsers.ProxyForEuParser import ProxyForEuParser
from http_request_randomizer.requests.parsers.RebroWeeblyParser import RebroWeeblyParser
from http_request_randomizer.requests.parsers.SamairProxyParser import SamairProxyParser
from http_request_randomizer.requests.useragent.userAgent import UserAgentManager

__author__ = 'pgaref'
sys.path.insert(0, os.path.abspath('../../../../'))

# Push back requests library to at least warnings
logging.getLogger("requests").setLevel(logging.WARNING)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-6s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)


class RequestProxy:
    def __init__(self, web_proxy_list=[], sustain=False, timeout=5):
        """
        Initialize the proxy

        Args:
            self: (todo): write your description
            web_proxy_list: (str): write your description
            sustain: (todo): write your description
            timeout: (int): write your description
        """
        self.userAgent = UserAgentManager()
        self.logger = logging.getLogger()
        self.logger.addHandler(handler)
        self.logger.setLevel(0)

        #####
        # Each of the classes below implements a specific URL Parser
        #####
        parsers = list([])
        parsers.append(FreeProxyParser('http://free-proxy-list.net', timeout=timeout))
        parsers.append(ProxyForEuParser('http://proxyfor.eu/geo.php', 1.0, timeout=timeout))
        parsers.append(RebroWeeblyParser('http://rebro.weebly.com', timeout=timeout))
        parsers.append(SamairProxyParser('http://samair.ru/proxy/time-01.htm', timeout=timeout))

        self.logger.debug("=== Initialized Proxy Parsers ===")
        for i in range(len(parsers)):
            self.logger.debug("\t {0}".format(parsers[i].__str__()))
        self.logger.debug("=================================")

        self.sustain = sustain
        self.parsers = parsers
        self.proxy_list = web_proxy_list
        for i in range(len(parsers)):
            try:
                self.proxy_list += parsers[i].parse_proxyList()
            except ReadTimeout:
                self.logger.warn("Proxy Parser: '{}' TimedOut!".format(parsers[i].url))
        self.current_proxy = self.randomize_proxy()

    def set_logger_level(self, level):
        """
        Set the logging level.

        Args:
            self: (todo): write your description
            level: (str): write your description
        """
        self.logger.setLevel(level)

    def get_proxy_list(self):
        """
        Return a list of proxy_proxy objects.

        Args:
            self: (todo): write your description
        """
        return self.proxy_list
        
    def current_proxy_ip(self):
        """
        Return the current proxy ip.

        Args:
            self: (todo): write your description
        """
        return str(self.current_proxy)
        
    def generate_random_request_headers(self):
        """
        Generate a random http request header.

        Args:
            self: (todo): write your description
        """
        headers = {
            "Connection": "close",  # another way to cover tracks
            "User-Agent": self.userAgent.get_random_user_agent()
        }  # select a random user agent
        return headers

    def randomize_proxy(self):
        """
        Randomly select a random proxy.

        Args:
            self: (todo): write your description
        """
        if len(self.proxy_list) == 0:
            raise ProxyListException("list is empty")
        rand_proxy = random.choice(self.proxy_list)
        while not rand_proxy:
            rand_proxy = random.choice(self.proxy_list)
        self.current_proxy = rand_proxy
        return rand_proxy

    #####
    # Proxy format:
    # http://<USERNAME>:<PASSWORD>@<IP-ADDR>:<PORT>
    #####
    def generate_proxied_request(self, url, method="GET", params={}, data={}, headers={}, req_timeout=30):
        """
        Generate a http request.

        Args:
            self: (todo): write your description
            url: (str): write your description
            method: (str): write your description
            params: (dict): write your description
            data: (str): write your description
            headers: (dict): write your description
            req_timeout: (todo): write your description
        """
        try:
            random.shuffle(self.proxy_list)
            # req_headers = dict(params.items() + self.generate_random_request_headers().items())

            req_headers = dict(params.items())
            req_headers_random = dict(self.generate_random_request_headers().items())
            req_headers.update(req_headers_random)

            if not self.sustain:
                self.randomize_proxy()

            headers.update(req_headers)

            self.logger.debug("Using proxy: {0}".format(str(self.current_proxy)))
            request = requests.request(method, url, proxies={"http": self.current_proxy},
                                       headers=headers, data=data, params=params, timeout=req_timeout)
            # Avoid HTTP request errors
            if request.status_code == 409:
                raise ConnectionError("HTTP Response [409] - Possible Cloudflare DNS resolution error")
            elif request.status_code == 403:
                raise ConnectionError("HTTP Response [403] - Permission denied error")
            elif request.status_code == 503:
                raise ConnectionError("HTTP Response [503] - Service unavailable error")
            print('RR Status {}'.format(request.status_code))
            return request
        except ConnectionError:
            try:
                self.proxy_list.remove(self.current_proxy)
            except ValueError:
                pass
            self.logger.debug("Proxy unreachable - Removed Straggling proxy: {0} PL Size = {1}".format(
                self.current_proxy, len(self.proxy_list)))
            self.randomize_proxy()
        except ReadTimeout:
            try:
                self.proxy_list.remove(self.current_proxy)
            except ValueError:
                pass
            self.logger.debug("Read timed out - Removed Straggling proxy: {0} PL Size = {1}".format(
                self.current_proxy, len(self.proxy_list)))
            self.randomize_proxy()
        except ChunkedEncodingError:
            try:
                self.proxy_list.remove(self.current_proxy)
            except ValueError:
                pass
            self.logger.debug("Wrong server chunked encoding - Removed Straggling proxy: {0} PL Size = {1}".format(
                self.current_proxy, len(self.proxy_list)))
            self.randomize_proxy()


if __name__ == '__main__':

    start = time.time()
    req_proxy = RequestProxy()
    print("Initialization took: {0} sec".format((time.time() - start)))
    print("Size: {0}".format(len(req_proxy.get_proxy_list())))
    print("ALL = {0} ".format(req_proxy.get_proxy_list()))

    test_url = 'http://ipv4.icanhazip.com'

    while True:
        start = time.time()
        request = req_proxy.generate_proxied_request(test_url)
        print("Proxied Request Took: {0} sec => Status: {1}".format((time.time() - start), request.__str__()))
        if request is not None:
            print("\t Response: ip={0}".format(u''.join(request.text).encode('utf-8')))
        print("Proxy List Size: {0}".format(len(req_proxy.get_proxy_list())))

        print("-> Going to sleep..")
        time.sleep(10)
