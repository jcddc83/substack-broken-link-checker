"""Tests for CSV report generation."""

import csv

from substack_link_checker import (
    CATEGORY_BLOCKED,
    CATEGORY_BROKEN,
    CATEGORY_INCONCLUSIVE,
    BrokenLinkRecord,
    SubstackLinkChecker,
)


def test_empty_results_skips_file_creation(tmp_path, capsys):
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    output = tmp_path / "report.csv"
    checker.generate_report(str(output))
    assert not output.exists(), "report file should not be created when there are no broken links"
    assert "Every link checked out fine" in capsys.readouterr().out


def test_writes_csv_with_expected_columns_and_rows(tmp_path):
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    checker.results = [
        BrokenLinkRecord(
            post_title="My Post",
            post_url="https://example.substack.com/p/my-post",
            broken_link="https://defunct.example.com/x",
            error_type="HTTP 404",
        ),
        BrokenLinkRecord(
            post_title="Another, with comma",
            post_url="https://example.substack.com/p/other",
            broken_link="https://no-dns.invalid/y",
            error_type="DNS Failure",
        ),
    ]
    output = tmp_path / "report.csv"
    checker.generate_report(str(output))

    assert output.exists()
    with output.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert rows[0]["post_title"] == "My Post"
    assert rows[0]["broken_link"] == "https://defunct.example.com/x"
    assert rows[0]["error_type"] == "HTTP 404"
    assert rows[1]["post_title"] == "Another, with comma"
    assert rows[1]["error_type"] == "DNS Failure"


def test_csv_header_present(tmp_path):
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    checker.results = [
        BrokenLinkRecord(
            post_title="t",
            post_url="u",
            broken_link="b",
            error_type="HTTP 404",
        ),
    ]
    output = tmp_path / "report.csv"
    checker.generate_report(str(output))

    first_line = output.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "category,post_title,post_url,broken_link,error_type"


def test_default_filename_is_timestamped(tmp_path, monkeypatch):
    """A fixed default meant a scheduled run overwrote last month's report, so
    the history this tool builds up never survived."""
    monkeypatch.chdir(tmp_path)
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    checker.results = [
        BrokenLinkRecord(
            post_title="t",
            post_url="u",
            broken_link="b",
            error_type="HTTP 404",
            category=CATEGORY_BROKEN,
        ),
    ]
    checker.generate_report()

    written = list(tmp_path.glob("broken_links_report_*.csv"))
    assert len(written) == 1
    assert not (tmp_path / "broken_links_report.csv").exists()


def test_clean_run_writes_no_file_even_without_a_filename(tmp_path, monkeypatch):
    """No results means no report, so it should not mint a filename either."""
    monkeypatch.chdir(tmp_path)
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    checker.generate_report()
    assert list(tmp_path.glob("*.csv")) == []


def test_rows_are_sorted_most_actionable_first(tmp_path):
    """A dead target needs an edit; a blocked host needs nothing. The top of
    the file should be the work."""
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    checker.results = [
        BrokenLinkRecord(
            post_title="c",
            post_url="https://example.substack.com/p/c",
            broken_link="https://slow.example.com/",
            error_type="Timeout",
            category=CATEGORY_INCONCLUSIVE,
        ),
        BrokenLinkRecord(
            post_title="b",
            post_url="https://example.substack.com/p/b",
            broken_link="https://blocks-bots.example.com/",
            error_type="HTTP 403",
            category=CATEGORY_BLOCKED,
        ),
        BrokenLinkRecord(
            post_title="a",
            post_url="https://example.substack.com/p/a",
            broken_link="https://defunct.example.com/x",
            error_type="HTTP 404",
            category=CATEGORY_BROKEN,
        ),
    ]
    output = tmp_path / "report.csv"
    checker.generate_report(str(output))

    with output.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert [r["category"] for r in rows] == [
        CATEGORY_BROKEN,
        CATEGORY_BLOCKED,
        CATEGORY_INCONCLUSIVE,
    ]


def test_summary_breaks_the_count_down_by_category(tmp_path, capsys):
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    checker.results = [
        BrokenLinkRecord(
            post_title="a",
            post_url="u",
            broken_link="b",
            error_type="HTTP 404",
            category=CATEGORY_BROKEN,
        ),
        BrokenLinkRecord(
            post_title="b",
            post_url="u",
            broken_link="b",
            error_type="HTTP 403",
            category=CATEGORY_BLOCKED,
        ),
    ]
    checker.generate_report(str(tmp_path / "report.csv"))

    out = capsys.readouterr().out
    assert "Failed checks: 2" in out
    assert "genuinely broken: 1" in out
    assert "blocked (likely fine): 1" in out
    assert "inconclusive: 0" in out
