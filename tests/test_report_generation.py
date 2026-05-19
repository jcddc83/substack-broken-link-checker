"""Tests for CSV report generation."""

import csv

from substack_link_checker import BrokenLinkRecord, SubstackLinkChecker


def test_empty_results_skips_file_creation(tmp_path, capsys):
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    output = tmp_path / "report.csv"
    checker.generate_report(str(output))
    assert not output.exists(), "report file should not be created when there are no broken links"
    assert "No broken links found" in capsys.readouterr().out


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
    assert first_line == "post_title,post_url,broken_link,error_type"
