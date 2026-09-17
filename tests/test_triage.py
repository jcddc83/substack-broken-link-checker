"""Tests for the triage pass."""

import csv

import pytest

from substack_link_checker import CATEGORY_BLOCKED, CATEGORY_BROKEN, CATEGORY_INCONCLUSIVE
from substack_link_checker.triage import (
    CLASS_ORDER,
    FIELDNAMES,
    _plausible,
    classify,
    split_concatenated,
    triage_rows,
)

NO_RETIRED = frozenset()


def row(link, category, post_url="https://example.substack.com/p/a"):
    return {
        "broken_link": link,
        "category": category,
        "post_title": "A Post",
        "post_url": post_url,
        "error_type": "HTTP 404",
    }


class TestSplitConcatenated:
    def test_two_urls_glued_returns_the_leading_one(self):
        url = "https://example.com/a https://example.com/b"
        assert split_concatenated(url) == "https://example.com/a "

    def test_single_url_returns_none(self):
        assert split_concatenated("https://example.com/a") is None

    def test_wayback_url_is_not_a_concatenation(self):
        """Archive services legitimately embed a second scheme in their path."""
        url = "https://web.archive.org/web/20200101000000/http://example.com/a"
        assert split_concatenated(url) is None

    def test_loc_webarchive_is_not_a_concatenation(self):
        url = "https://webarchive.loc.gov/all/20200101000000/http://example.com/a"
        assert split_concatenated(url) is None

    def test_wayback_url_that_is_genuinely_doubled_is_caught(self):
        url = "https://web.archive.org/web/20200101000000/http://example.com/ahttps://example.com/b"
        assert split_concatenated(url) is not None

    def test_mangled_leading_half_prefers_the_trailing_half(self):
        """ "http://'https://real.example.com" has a stray quote where the host
        should be, so the real link is the second half."""
        assert split_concatenated("http://'https://real.example.com/x") == (
            "https://real.example.com/x"
        )


class TestPlausible:
    @pytest.mark.parametrize("url", ["https://example.com/a", "http://a.io"])
    def test_real_hosts(self, url):
        assert _plausible(url) is True

    @pytest.mark.parametrize("url", ["https://'", "http://ab", "not a url"])
    def test_junk(self, url):
        assert _plausible(url) is False


class TestClassify:
    def test_malformed_href_beats_category(self):
        klass, fix = classify(
            row("https://a.example.com/x https://b.example.com/y", CATEGORY_BROKEN), NO_RETIRED
        )
        assert klass == "malformed_href"
        assert fix.startswith("https://a.example.com/x")

    def test_retired_host_overrides_inconclusive(self):
        """A retired subdomain often serves a mismatched certificate, so the
        check aborts before reading a status. It is dead, not unknown."""
        retired = frozenset({"old.example.com"})
        klass, _ = classify(row("https://old.example.com/x", CATEGORY_INCONCLUSIVE), retired)
        assert klass == "retired_host"

    def test_retired_host_matching_is_case_insensitive(self):
        retired = frozenset({"old.example.com"})
        klass, _ = classify(row("https://OLD.example.com/x", CATEGORY_INCONCLUSIVE), retired)
        assert klass == "retired_host"

    def test_without_a_retired_list_nothing_is_reclassified(self):
        klass, _ = classify(row("https://old.example.com/x", CATEGORY_INCONCLUSIVE), NO_RETIRED)
        assert klass == "inconclusive_other"

    def test_categories_map_through(self):
        assert (
            classify(row("https://a.example.com/x", CATEGORY_BROKEN), NO_RETIRED)[0]
            == "dead_target"
        )
        assert (
            classify(row("https://a.example.com/x", CATEGORY_BLOCKED), NO_RETIRED)[0] == "blocked"
        )
        assert (
            classify(row("https://a.example.com/x", CATEGORY_INCONCLUSIVE), NO_RETIRED)[0]
            == "inconclusive_other"
        )


class TestTriageRows:
    def test_sorted_most_actionable_first(self):
        rows = [
            row("https://a.example.com/x", CATEGORY_BLOCKED),
            row("https://b.example.com/y", CATEGORY_INCONCLUSIVE),
            row("https://c.example.com/z", CATEGORY_BROKEN),
            row("https://d.example.com/p https://e.example.com/q", CATEGORY_BROKEN),
        ]
        out = triage_rows(rows, NO_RETIRED)
        assert [r["class"] for r in out] == [
            "malformed_href",
            "dead_target",
            "inconclusive_other",
            "blocked",
        ]

    def test_every_class_has_an_action(self):
        rows = [
            row("https://a.example.com/x", CATEGORY_BROKEN),
            row("https://b.example.com/y", CATEGORY_BLOCKED),
            row("https://c.example.com/z", CATEGORY_INCONCLUSIVE),
        ]
        for r in triage_rows(rows, NO_RETIRED):
            assert r["action"]
            assert r["class"] in CLASS_ORDER

    def test_empty_input_produces_no_rows_and_does_not_raise(self):
        """The original script crashed twice on an empty report -- once
        indexing out[0] for the header, once taking max() of no classes."""
        assert triage_rows([], NO_RETIRED) == []


def test_end_to_end_via_csv(tmp_path):
    report = tmp_path / "report.csv"
    with report.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["category", "post_title", "post_url", "broken_link", "error_type"]
        )
        writer.writeheader()
        writer.writerow(
            {
                "category": CATEGORY_BROKEN,
                "post_title": "A Post",
                "post_url": "https://example.substack.com/p/a",
                "broken_link": "https://dead.example.com/x",
                "error_type": "HTTP 404",
            }
        )

    with report.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    out = triage_rows(rows, NO_RETIRED)
    assert len(out) == 1
    assert out[0]["class"] == "dead_target"
    assert list(out[0].keys()) == FIELDNAMES


class TestRetiredHostIsParsedNotStringSliced:
    """See TestHostIsParsedNotStringSliced in test_domain_filtering.py -- a
    port must not stop a listed host from matching, and userinfo must not let
    an unlisted host borrow a listed one's name."""

    RETIRED = frozenset({"old.example.com"})

    def test_port_does_not_defeat_retired_hosts(self):
        klass, _ = classify(
            row("https://old.example.com:443/x", CATEGORY_INCONCLUSIVE), self.RETIRED
        )
        assert klass == "retired_host"

    def test_userinfo_cannot_impersonate_a_retired_host(self):
        klass, _ = classify(
            row("https://old.example.com@evil.example/x", CATEGORY_INCONCLUSIVE), self.RETIRED
        )
        assert klass == "inconclusive_other"
