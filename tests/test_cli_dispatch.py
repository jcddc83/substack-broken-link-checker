"""Tests for the top-level subcommand dispatcher in cli.py."""

import pytest

from substack_link_checker import cli


def test_no_args_prints_help_and_returns(capsys):
    """Running with no args should print top-level help, not error."""
    cli.main([])
    out = capsys.readouterr().out
    assert "substack-link-checker" in out
    assert "check" in out


def test_help_flag_prints_help(capsys):
    cli.main(["--help"])
    out = capsys.readouterr().out
    assert "<subcommand>" in out


def test_unknown_subcommand_errors():
    with pytest.raises(SystemExit):
        cli.main(["nonsense-subcommand"])


def test_dispatches_to_subcommand(monkeypatch):
    """`cli.main(["check", ...])` should invoke the check subcommand's main."""
    called = {}

    def fake_check_main():
        import sys

        called["argv"] = list(sys.argv)

    monkeypatch.setitem(cli.SUBCOMMANDS, "check", ("check", fake_check_main))

    cli.main(["check", "--base-url", "https://x.substack.com", "--year", "2024"])
    assert called["argv"][0] == "substack-link-checker check"
    assert "--base-url" in called["argv"]
    assert "https://x.substack.com" in called["argv"]


def test_sys_argv_restored_after_dispatch(monkeypatch):
    """After dispatching, sys.argv should be back to its original value."""
    import sys

    monkeypatch.setattr(sys, "argv", ["original", "argv"])

    def noop():
        pass

    monkeypatch.setitem(cli.SUBCOMMANDS, "check", ("check", noop))

    cli.main(["check"])
    assert sys.argv == ["original", "argv"]


def test_version_flag(capsys):
    from substack_link_checker import __version__

    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
