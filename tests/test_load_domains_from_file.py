"""Tests for the load_domains_from_file helper."""

from substack_link_checker import load_domains_from_file


def test_loads_one_per_line(tmp_path):
    p = tmp_path / "domains.txt"
    p.write_text("example.com\nwikipedia.org\n")
    assert load_domains_from_file(str(p)) == ["example.com", "wikipedia.org"]


def test_skips_blank_lines_and_comments(tmp_path):
    p = tmp_path / "domains.txt"
    p.write_text("# header comment\n\nexample.com\n   \n# another comment\nwikipedia.org\n")
    assert load_domains_from_file(str(p)) == ["example.com", "wikipedia.org"]


def test_strips_whitespace(tmp_path):
    p = tmp_path / "domains.txt"
    p.write_text("  example.com  \n\twikipedia.org\t\n")
    assert load_domains_from_file(str(p)) == ["example.com", "wikipedia.org"]


def test_missing_file_returns_empty_list(tmp_path, capsys):
    result = load_domains_from_file(str(tmp_path / "does-not-exist.txt"))
    assert result == []
    captured = capsys.readouterr()
    assert "not found" in captured.out.lower()
