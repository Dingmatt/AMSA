"""Tests to ensure that the html.parser tree builder generates good
trees."""

from pdb import set_trace
import pickle
from bs4.testing import SoupTest, HTMLTreeBuilderSmokeTest
from bs4.builder import HTMLParserTreeBuilder

class HTMLParserTreeBuilderSmokeTest(SoupTest, HTMLTreeBuilderSmokeTest):

    @property
    def default_builder(self):
        """
        Return the default builder

        Args:
            self: (todo): write your description
        """
        return HTMLParserTreeBuilder()

    def test_namespaced_system_doctype(self):
        """
        Test if the system type is a system type.

        Args:
            self: (todo): write your description
        """
        # html.parser can't handle namespaced doctypes, so skip this one.
        pass

    def test_namespaced_public_doctype(self):
        """
        Test if public_namespaced_publicctype.

        Args:
            self: (todo): write your description
        """
        # html.parser can't handle namespaced doctypes, so skip this one.
        pass

    def test_builder_is_pickled(self):
        """Unlike most tree builders, HTMLParserTreeBuilder and will
        be restored after pickling.
        """
        tree = self.soup("<a><b>foo</a>")
        dumped = pickle.dumps(tree, 2)
        loaded = pickle.loads(dumped)
        self.assertTrue(isinstance(loaded.builder, type(tree.builder)))

    def test_redundant_empty_element_closing_tags(self):
        """
        Perform content of the element.

        Args:
            self: (todo): write your description
        """
        self.assertSoupEquals('<br></br><br></br><br></br>', "<br/><br/><br/>")
        self.assertSoupEquals('</br></br></br>', "")
