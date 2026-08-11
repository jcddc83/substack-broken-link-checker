"""Tests for failure classification.

`classify_error` reads the human-readable strings that
`SubstackLinkChecker._check_link_once` produces. That coupling is invisible:
reword an error message and everything it described silently becomes
*inconclusive* rather than raising, so a report quietly stops being useful
while still looking fine.

`test_every_error_string_the_checker_emits_is_classified` is the guard. If you
add or reword an error string in `_check_link_once`, add it there too.
"""

import pytest

from substack_link_checker import (
    CATEGORY_BLOCKED,
    CATEGORY_BROKEN,
    CATEGORY_INCONCLUSIVE,
    BrokenLinkRecord,
    LinkCheckResult,
    SubstackLinkChecker,
    classify_error,
)
from substack_link_checker.checker import _is_malformed_url

# Every error_type string _check_link_once can return, with the category it
# must map to. Sourced by reading that method, not by running it.
ERROR_STRINGS = [
    # Dead: the page is genuinely gone.
    ("HTTP 404", CATEGORY_BROKEN),
    ("HTTP 410", CATEGORY_BROKEN),
    ("Soft 404 (page title indicates error)", CATEGORY_BROKEN),
    ("DNS Failure", CATEGORY_BROKEN),
    ("Known broken domain", CATEGORY_BROKEN),
    ("Malformed URL (link text used as address)", CATEGORY_BROKEN),
    # Blocked: we were refused, the link is probably fine.
    ("HTTP 401", CATEGORY_BLOCKED),
    ("HTTP 403", CATEGORY_BLOCKED),
    ("HTTP 406", CATEGORY_BLOCKED),
    ("HTTP 429", CATEGORY_BLOCKED),
    ("HTTP 451", CATEGORY_BLOCKED),
    # Inconclusive: says more about the moment than about the link.
    ("HTTP 500", CATEGORY_INCONCLUSIVE),
    ("HTTP 502", CATEGORY_INCONCLUSIVE),
    ("HTTP 400", CATEGORY_INCONCLUSIVE),
    ("Timeout", CATEGORY_INCONCLUSIVE),
    ("SSL Error: certificate verify failed", CATEGORY_INCONCLUSIVE),
    ("Connection Error: Cannot connect to host", CATEGORY_INCONCLUSIVE),
    ("Client Error: something went wrong", CATEGORY_INCONCLUSIVE),
    ("Unknown Error: something went wrong", CATEGORY_INCONCLUSIVE),
]


@pytest.mark.parametrize("error_type,expected", ERROR_STRINGS)
def test_every_error_string_the_checker_emits_is_classified(error_type, expected):
    assert classify_error(error_type) == expected


def test_unrecognised_string_is_inconclusive_not_broken():
    """The safe default. Guessing "dead" would put work in front of the user
    that does not exist."""
    assert classify_error("something nobody has seen before") == CATEGORY_INCONCLUSIVE


def test_malformed_http_status_does_not_raise():
    assert classify_error("HTTP notanumber") == CATEGORY_INCONCLUSIVE
    assert classify_error("HTTP ") == CATEGORY_INCONCLUSIVE


def test_result_category_is_derived_from_error_type():
    assert LinkCheckResult(True, "HTTP 403").category == CATEGORY_BLOCKED
    assert LinkCheckResult(True, "HTTP 404").category == CATEGORY_BROKEN


def test_record_defaults_to_inconclusive():
    """A record built without a category must not claim a link is dead."""
    record = BrokenLinkRecord(post_title="t", post_url="u", broken_link="b", error_type="HTTP 404")
    assert record.category == CATEGORY_INCONCLUSIVE


@pytest.mark.parametrize(
    "url",
    [
        # Two URLs glued together with no path on the first, so the space
        # lands inside what should be the hostname.
        "https://example.com https://other.com",
        "http://'https://example.com",  # stray quote where the host should be
        "http://notahost",  # no dot at all
    ],
)
def test_malformed_urls_detected(url):
    assert _is_malformed_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/path",
        "https://sub.example.co.uk/path?q=1#frag",
        "https://xn--bcher-kva.example/path",  # punycode
        "not a url at all",  # no scheme: not our business
        "mailto:someone@example.com",
        # Concatenated *after* a path: the hostname parses cleanly, so this is
        # deliberately not caught here. It is a real defect, but finding it
        # needs the whole string rather than the host -- that is the triage
        # pass's job, not this narrow guard's.
        "https://example.com/a https://example.com/b",
    ],
)
def test_wellformed_urls_are_not_flagged(url):
    assert _is_malformed_url(url) is False


def test_malformed_short_circuit_skips_the_network_and_the_cache():
    """It counts as broken but not as a link checked, and is never cached --
    nothing was checked, so there is nothing to remember."""
    import asyncio

    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    link = "https://example.com https://other.com"

    result = asyncio.run(checker.check_link_with_retry(None, link))

    assert result.is_broken is True
    assert result.category == CATEGORY_BROKEN
    assert checker.stats["broken_links"] == 1
    assert checker.stats["total_links_checked"] == 0
    assert link not in checker.link_cache
