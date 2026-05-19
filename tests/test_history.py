"""Tests for the history-tracking persistence and filtering."""

import json

from substack_link_checker import SubstackLinkChecker


def test_load_history_missing_file_starts_empty(tmp_path):
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    checker.load_history(str(tmp_path / "no-such-file.json"))
    assert checker.checked_posts == {}


def test_save_and_reload_roundtrip(tmp_path):
    history = tmp_path / "history.json"

    a = SubstackLinkChecker(base_url="https://example.substack.com")
    a.load_history(str(history))
    a.mark_post_checked("https://example.substack.com/p/one")
    a.mark_post_checked("https://example.substack.com/p/two")
    a.save_history()

    on_disk = json.loads(history.read_text(encoding="utf-8"))
    assert "last_updated" in on_disk
    assert set(on_disk["checked_posts"].keys()) == {
        "https://example.substack.com/p/one",
        "https://example.substack.com/p/two",
    }

    b = SubstackLinkChecker(base_url="https://example.substack.com")
    b.load_history(str(history))
    assert set(b.checked_posts.keys()) == set(on_disk["checked_posts"].keys())


def test_filter_unchecked_posts_skips_known_urls(tmp_path):
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    checker.checked_posts = {"https://example.substack.com/p/one": "2026-01-01T00:00:00"}

    inputs = [
        "https://example.substack.com/p/one",
        "https://example.substack.com/p/two",
        "https://example.substack.com/p/three",
    ]
    result = checker.filter_unchecked_posts(inputs)
    assert result == [
        "https://example.substack.com/p/two",
        "https://example.substack.com/p/three",
    ]
    assert checker.stats["posts_skipped"] == 1


def test_load_history_corrupt_json_starts_empty(tmp_path, capsys):
    history = tmp_path / "bad.json"
    history.write_text("not valid json {")
    checker = SubstackLinkChecker(base_url="https://example.substack.com")
    checker.load_history(str(history))
    assert checker.checked_posts == {}
    assert "Warning" in capsys.readouterr().out
