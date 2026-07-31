"""Tests for console encoding setup.

The bug these guard against: on Windows, a redirected stdout defaults to
cp1252, which cannot encode the U+2717 mark used to flag a broken link. The
run died on the first broken link it found -- so the checker only ever
survived clean runs, and a scheduled job looked healthy while producing
nothing.
"""

import io
import sys

import pytest

from substack_link_checker import cli
from substack_link_checker._console import configure_stdio

# The mark checker.py prints for a broken link, and the character that
# actually triggered the crash.
BROKEN_MARK = "✗"


def cp1252_stream():
    """A text stream behaving like a redirected Windows stdout."""
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")


def test_cp1252_stream_reproduces_the_crash():
    """Without the fix, writing the broken-link mark raises."""
    stream = cp1252_stream()
    with pytest.raises(UnicodeEncodeError):
        stream.write(BROKEN_MARK)
        stream.flush()


def test_configure_stdio_makes_the_mark_writable(monkeypatch):
    """After the fix, the same write succeeds."""
    stream = cp1252_stream()
    monkeypatch.setattr(sys, "stdout", stream)

    configure_stdio()

    print(f"    {BROKEN_MARK} BROKEN: https://example.com/gone")
    stream.flush()
    assert stream.encoding == "utf-8"


def test_configure_stdio_covers_stderr(monkeypatch):
    stream = cp1252_stream()
    monkeypatch.setattr(sys, "stderr", stream)

    configure_stdio()

    assert stream.encoding == "utf-8"


def test_unencodable_characters_are_replaced_not_raised(monkeypatch):
    """Scraped titles carry all sorts of characters; none should stop a run."""
    stream = cp1252_stream()
    monkeypatch.setattr(sys, "stdout", stream)

    configure_stdio()

    print("✗ 中文 \U0001f600 café")
    stream.flush()  # must not raise


def test_streams_without_reconfigure_are_skipped(monkeypatch):
    """StringIO has no reconfigure; that must not be an error."""
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    monkeypatch.setattr(sys, "stderr", io.StringIO())

    configure_stdio()  # must not raise


def test_detached_stream_does_not_abort_the_run(monkeypatch):
    """A stream that refuses reconfiguration is skipped, not fatal."""

    class Hostile:
        encoding = "cp1252"

        def reconfigure(self, **kwargs):
            raise ValueError("cannot reconfigure a detached stream")

    monkeypatch.setattr(sys, "stdout", Hostile())

    configure_stdio()  # must not raise


def test_configure_stdio_is_idempotent(monkeypatch):
    stream = cp1252_stream()
    monkeypatch.setattr(sys, "stdout", stream)

    configure_stdio()
    configure_stdio()

    assert stream.encoding == "utf-8"


def test_cli_main_configures_stdio(monkeypatch):
    """Every entry point reaches the console via cli.main, so it must set up.

    Note the em dash in the help text is *not* the problem -- cp1252 encodes
    U+2014 happily. Only the U+2713/U+2717 marks fail, and those are printed
    by the check and demo subcommands.
    """
    calls = []
    monkeypatch.setattr(cli, "configure_stdio", lambda: calls.append(True))

    cli.main([])

    assert calls, "cli.main must call configure_stdio()"
