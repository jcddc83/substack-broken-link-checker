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


class TestHostIsParsedNotStringSliced:
    """A URL's host must come from `urlparse(...).hostname`.

    `netloc` keeps the port and any userinfo, so slicing it by hand means a
    port silently defeats the flag -- the user asks to skip wikipedia.org and
    `https://wikipedia.org:443/...` gets checked anyway -- while userinfo can
    make a third-party host read as the allowed one.
    """

    def test_port_does_not_defeat_skip_domains(self):
        checker = SubstackLinkChecker(
            base_url="https://example.substack.com", skip_domains=["wikipedia.org"]
        )
        assert checker.should_skip_domain("https://wikipedia.org:443/wiki/X") is True

    def test_port_does_not_defeat_broken_domains(self):
        checker = SubstackLinkChecker(
            base_url="https://example.substack.com", broken_domains=["dead.example.com"]
        )
        assert checker.is_broken_domain("https://dead.example.com:8080/x") is True

    def test_userinfo_cannot_impersonate_a_skip_domain(self):
        """The request goes to evil.example, so it must still be checked."""
        checker = SubstackLinkChecker(
            base_url="https://example.substack.com", skip_domains=["wikipedia.org"]
        )
        assert checker.should_skip_domain("https://wikipedia.org@evil.example/w") is False

    def test_userinfo_cannot_impersonate_a_broken_domain(self):
        checker = SubstackLinkChecker(
            base_url="https://example.substack.com", broken_domains=["dead.example.com"]
        )
        assert checker.is_broken_domain("https://dead.example.com@evil.example/x") is False
