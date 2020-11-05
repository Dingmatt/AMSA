"""Tests of the builder registry."""

import unittest
import warnings

from bs4 import BeautifulSoup
from bs4.builder import (
    builder_registry as registry,
    HTMLParserTreeBuilder,
    TreeBuilderRegistry,
)

try:
    from bs4.builder import HTML5TreeBuilder
    HTML5LIB_PRESENT = True
except ImportError:
    HTML5LIB_PRESENT = False

try:
    from bs4.builder import (
        LXMLTreeBuilderForXML,
        LXMLTreeBuilder,
        )
    LXML_PRESENT = True
except ImportError:
    LXML_PRESENT = False


class BuiltInRegistryTest(unittest.TestCase):
    """Test the built-in registry with the default builders registered."""

    def test_combination(self):
        """
        Test that the test tree.

        Args:
            self: (todo): write your description
        """
        if LXML_PRESENT:
            self.assertEqual(registry.lookup('fast', 'html'),
                             LXMLTreeBuilder)

        if LXML_PRESENT:
            self.assertEqual(registry.lookup('permissive', 'xml'),
                             LXMLTreeBuilderForXML)
        self.assertEqual(registry.lookup('strict', 'html'),
                          HTMLParserTreeBuilder)
        if HTML5LIB_PRESENT:
            self.assertEqual(registry.lookup('html5lib', 'html'),
                              HTML5TreeBuilder)

    def test_lookup_by_markup_type(self):
        """
        Test whether the given type in the registry type.

        Args:
            self: (todo): write your description
        """
        if LXML_PRESENT:
            self.assertEqual(registry.lookup('html'), LXMLTreeBuilder)
            self.assertEqual(registry.lookup('xml'), LXMLTreeBuilderForXML)
        else:
            self.assertEqual(registry.lookup('xml'), None)
            if HTML5LIB_PRESENT:
                self.assertEqual(registry.lookup('html'), HTML5TreeBuilder)
            else:
                self.assertEqual(registry.lookup('html'), HTMLParserTreeBuilder)

    def test_named_library(self):
        """
        Set up the named library

        Args:
            self: (todo): write your description
        """
        if LXML_PRESENT:
            self.assertEqual(registry.lookup('lxml', 'xml'),
                             LXMLTreeBuilderForXML)
            self.assertEqual(registry.lookup('lxml', 'html'),
                             LXMLTreeBuilder)
        if HTML5LIB_PRESENT:
            self.assertEqual(registry.lookup('html5lib'),
                              HTML5TreeBuilder)

        self.assertEqual(registry.lookup('html.parser'),
                          HTMLParserTreeBuilder)

    def test_beautifulsoup_constructor_does_lookup(self):
        """
        Constructs up a list of the features in the soup.

        Args:
            self: (todo): write your description
        """

        with warnings.catch_warnings(record=True) as w:
            # This will create a warning about not explicitly
            # specifying a parser, but we'll ignore it.

            # You can pass in a string.
            BeautifulSoup("", features="html")
            # Or a list of strings.
            BeautifulSoup("", features=["html", "fast"])

        # You'll get an exception if BS can't find an appropriate
        # builder.
        self.assertRaises(ValueError, BeautifulSoup,
                          "", features="no-such-feature")

class RegistryTest(unittest.TestCase):
    """Test the TreeBuilderRegistry class in general."""

    def setUp(self):
        """
        Sets the registry.

        Args:
            self: (todo): write your description
        """
        self.registry = TreeBuilderRegistry()

    def builder_for_features(self, *feature_list):
        """
        Return a list of features for a given feature_list.

        Args:
            self: (todo): write your description
            feature_list: (list): write your description
        """
        cls = type('Builder_' + '_'.join(feature_list),
                   (object,), {'features' : feature_list})

        self.registry.register(cls)
        return cls

    def test_register_with_no_features(self):
        """
        Perform test with the test.

        Args:
            self: (todo): write your description
        """
        builder = self.builder_for_features()

        # Since the builder advertises no features, you can't find it
        # by looking up features.
        self.assertEqual(self.registry.lookup('foo'), None)

        # But you can find it by doing a lookup with no features, if
        # this happens to be the only registered builder.
        self.assertEqual(self.registry.lookup(), builder)

    def test_register_with_features_makes_lookup_succeed(self):
        """
        Perform with test case with test case.

        Args:
            self: (todo): write your description
        """
        builder = self.builder_for_features('foo', 'bar')
        self.assertEqual(self.registry.lookup('foo'), builder)
        self.assertEqual(self.registry.lookup('bar'), builder)

    def test_lookup_fails_when_no_builder_implements_feature(self):
        """
        Perform lookup lookup on all lookup.

        Args:
            self: (todo): write your description
        """
        builder = self.builder_for_features('foo', 'bar')
        self.assertEqual(self.registry.lookup('baz'), None)

    def test_lookup_gets_most_recent_registration_when_no_feature_specified(self):
        """
        This function is_lookup_when_most_most_most_most_most_most_most_most_most_most_no

        Args:
            self: (todo): write your description
        """
        builder1 = self.builder_for_features('foo')
        builder2 = self.builder_for_features('bar')
        self.assertEqual(self.registry.lookup(), builder2)

    def test_lookup_fails_when_no_tree_builders_registered(self):
        """
        Lookup all possible possible possible to be executed.

        Args:
            self: (todo): write your description
        """
        self.assertEqual(self.registry.lookup(), None)

    def test_lookup_gets_most_recent_builder_supporting_all_features(self):
        """
        Compute all features in all features.

        Args:
            self: (todo): write your description
        """
        has_one = self.builder_for_features('foo')
        has_the_other = self.builder_for_features('bar')
        has_both_early = self.builder_for_features('foo', 'bar', 'baz')
        has_both_late = self.builder_for_features('foo', 'bar', 'quux')
        lacks_one = self.builder_for_features('bar')
        has_the_other = self.builder_for_features('foo')

        # There are two builders featuring 'foo' and 'bar', but
        # the one that also features 'quux' was registered later.
        self.assertEqual(self.registry.lookup('foo', 'bar'),
                          has_both_late)

        # There is only one builder featuring 'foo', 'bar', and 'baz'.
        self.assertEqual(self.registry.lookup('foo', 'bar', 'baz'),
                          has_both_early)

    def test_lookup_fails_when_cannot_reconcile_requested_features(self):
        """
        Perform some lookup of all features.

        Args:
            self: (todo): write your description
        """
        builder1 = self.builder_for_features('foo', 'bar')
        builder2 = self.builder_for_features('foo', 'baz')
        self.assertEqual(self.registry.lookup('bar', 'baz'), None)
