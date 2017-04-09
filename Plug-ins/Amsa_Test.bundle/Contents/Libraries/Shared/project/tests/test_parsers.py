import unittest

from http.requests.parsers.UrlParser import UrlParser

__author__ = 'pgaref'


class testBaseParser(unittest.TestCase):
    def setUp(self):
        self.normal_parser = UrlParser("http://proxy-test.com", bandwidthKBs=50)
        self.no_bdwidthParser = UrlParser("http://slow-proxy.com")

    def test_normal_parser(self):
        self.assertEqual(self.normal_parser.get_URl(), "http://proxy-test.com", "incorrect parser URL")
        self.assertEqual(self.normal_parser.get_min_bandwidth(), 50, "incorrect parser bandwidth")

    def test_no_bdwidth_parser(self):
        self.assertEqual(self.no_bdwidthParser.get_URl(), "http://slow-proxy.com", "incorrect parser URL")
        self.assertEqual(self.no_bdwidthParser.get_min_bandwidth(), 150, "incorrect parser bandwidth")


if __name__ == '__main__':
    unittest.main()
