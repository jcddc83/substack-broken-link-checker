"""Tests for skipping Substack's own UI links.

These links are excluded from the scan deliberately: a subscribe or comments
URL is Substack chrome, not something the author linked to. The matching has
to be done on hostname and path -- a substring search over the whole URL also
matches a third-party address that merely mentions substack.com, and silently
dropping somebody's real link is the opposite of what this tool is for.
"""

import pytest

from substack_link_checker.checker import _is_substack_ui_link


@pytest.mark.parametrize(
    "link",
    [
        "https://example.substack.com/subscribe",
        "https://example.substack.com/p/some-post/comments",
        "https://example.substack.com/p/some-post/share",
        "https://substack.com/subscribe",
        "https://EXAMPLE.SUBSTACK.COM/subscribe",  # host match is case-insensitive
        "https://example.substack.com:443/subscribe",  # explicit port
    ],
)
def test_substack_ui_links_are_skipped(link):
    assert _is_substack_ui_link(link) is True


@pytest.mark.parametrize(
    "link",
    [
        # A real post link is content, not chrome.
        "https://example.substack.com/p/some-post",
        # Somebody else's site that merely mentions substack.com. The old
        # substring test matched these and dropped them from the scan.
        "https://evil.example.com/?next=https://x.substack.com/share",
        "https://notsubstack.com/share",
        "https://example.com/how-to-share-on-substack.com",
        # A lookalike host must not match on suffix alone.
        "https://mysubstack.com/subscribe",
        # The segment must be in the path. "action=share" in a query string
        # is a tracking parameter on a real post link, not Substack chrome.
        "https://example.substack.com/p/some-post?utm=x&action=share",
        # Userinfo in the netloc. The request goes to evil.example; reading
        # everything before the first colon would call it substack.com and
        # silently skip a third-party link.
        "https://SUBSTACK.COM:443@evil.example/subscribe",
        "https://example.substack.com@evil.example/comments",
        "https://user:pass@evil.example/share",
        # Unrelated links.
        "https://example.com/subscribe",
        "https://example.com/",
        # Relative links reach this check before being made absolute; they
        # have no host, so they are not ours to skip.
        "/p/some-post/comments",
        "",
    ],
)
def test_other_links_are_not_skipped(link):
    assert _is_substack_ui_link(link) is False
