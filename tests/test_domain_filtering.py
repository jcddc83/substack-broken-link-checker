"""Tests for domain filtering helpers on SubstackLinkChecker."""

import pytest

from substack_link_checker import SubstackLinkChecker


@pytest.fixture
def checker():
    return SubstackLinkChecker(base_url="https://example.substack.com")


class TestShouldSkipDomain:
    def test_no_skip_domains_returns_false(self, checker):
        assert checker.should_skip_domain("https://example.com/page") is False

    def test_exact_match(self):
        c = SubstackLinkChecker(
            base_url="https://example.substack.com",
            skip_domains=["wikipedia.org"],
        )
        assert c.should_skip_domain("https://wikipedia.org/wiki/Foo") is True

    def test_subdomain_match(self):
        c = SubstackLinkChecker(
            base_url="https://example.substack.com",
            skip_domains=["wikipedia.org"],
        )
        assert c.should_skip_domain("https://en.wikipedia.org/wiki/Foo") is True

    def test_non_match(self):
        c = SubstackLinkChecker(
            base_url="https://example.substack.com",
            skip_domains=["wikipedia.org"],
        )
        assert c.should_skip_domain("https://example.com/page") is False

    def test_lookalike_domain_not_matched(self):
        """notwikipedia.org should NOT match wikipedia.org."""
        c = SubstackLinkChecker(
            base_url="https://example.substack.com",
            skip_domains=["wikipedia.org"],
        )
        assert c.should_skip_domain("https://notwikipedia.org/foo") is False

    def test_case_insensitive(self):
        c = SubstackLinkChecker(
            base_url="https://example.substack.com",
            skip_domains=["wikipedia.org"],
        )
        assert c.should_skip_domain("https://Wikipedia.ORG/wiki/Foo") is True

    def test_malformed_url_returns_false(self):
        c = SubstackLinkChecker(
            base_url="https://example.substack.com",
            skip_domains=["wikipedia.org"],
        )
        assert c.should_skip_domain("not a url at all") is False


class TestIsBrokenDomain:
    def test_no_broken_domains_returns_false(self, checker):
        assert checker.is_broken_domain("https://example.com/page") is False

    def test_exact_match(self):
        c = SubstackLinkChecker(
            base_url="https://example.substack.com",
            broken_domains=["defunct.example.com"],
        )
        assert c.is_broken_domain("https://defunct.example.com/x") is True

    def test_subdomain_match(self):
        c = SubstackLinkChecker(
            base_url="https://example.substack.com",
            broken_domains=["example.com"],
        )
        assert c.is_broken_domain("https://sub.example.com/x") is True

    def test_non_match(self):
        c = SubstackLinkChecker(
            base_url="https://example.substack.com",
            broken_domains=["defunct.example.com"],
        )
        assert c.is_broken_domain("https://live.example.com/x") is False
