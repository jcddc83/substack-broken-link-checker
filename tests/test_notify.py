"""Tests for failure alerting.

The notifier runs inside a failure handler, so its own failure modes matter
more than usual: anything it raises replaces the error it was trying to report.
"""

import substack_link_checker.notify as notify_mod
from substack_link_checker.notify import DEFAULT_SMTP_HOST, DEFAULT_SMTP_PORT, send_failure_email

NOTIFY_VARS = (
    "NOTIFY_EMAIL",
    "NOTIFY_PASSWORD",
    "NOTIFY_TO",
    "NOTIFY_SMTP_HOST",
    "NOTIFY_SMTP_PORT",
)


def clear_notify_env(monkeypatch):
    for var in NOTIFY_VARS:
        monkeypatch.delenv(var, raising=False)


class FakeSMTP:
    """Records what would have been sent. Never touches the network."""

    instances = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.logged_in_as = None
        self.sent = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        self.logged_in_as = user

    def send_message(self, msg):
        self.sent.append(msg)


def configure(monkeypatch, **overrides):
    clear_notify_env(monkeypatch)
    monkeypatch.setenv("NOTIFY_EMAIL", "sender@example.com")
    monkeypatch.setenv("NOTIFY_PASSWORD", "app-password")
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)
    FakeSMTP.instances = []
    monkeypatch.setattr(notify_mod.smtplib, "SMTP", FakeSMTP)


def test_unconfigured_returns_false_and_does_not_raise(monkeypatch, capsys):
    """The whole point: a missing alert must not crash the error handler."""
    clear_notify_env(monkeypatch)
    assert send_failure_email("Link Checker", "boom") is False
    assert "not configured" in capsys.readouterr().out


def test_password_without_email_is_still_unconfigured(monkeypatch):
    clear_notify_env(monkeypatch)
    monkeypatch.setenv("NOTIFY_PASSWORD", "app-password")
    assert send_failure_email("Link Checker", "boom") is False


def test_sends_to_the_sender_when_no_recipient_given(monkeypatch):
    configure(monkeypatch)
    assert send_failure_email("Link Checker", "boom") is True
    msg = FakeSMTP.instances[0].sent[0]
    assert msg["To"] == "sender@example.com"


def test_explicit_recipient_is_used(monkeypatch):
    configure(monkeypatch, NOTIFY_TO="ops@example.com")
    send_failure_email("Link Checker", "boom")
    assert FakeSMTP.instances[0].sent[0]["To"] == "ops@example.com"


def test_defaults_to_gmail(monkeypatch):
    configure(monkeypatch)
    send_failure_email("Link Checker", "boom")
    assert FakeSMTP.instances[0].host == DEFAULT_SMTP_HOST
    assert FakeSMTP.instances[0].port == DEFAULT_SMTP_PORT


def test_smtp_host_and_port_are_configurable(monkeypatch):
    configure(monkeypatch, NOTIFY_SMTP_HOST="mail.example.org", NOTIFY_SMTP_PORT="2525")
    send_failure_email("Link Checker", "boom")
    assert FakeSMTP.instances[0].host == "mail.example.org"
    assert FakeSMTP.instances[0].port == 2525


def test_nonsense_port_falls_back_rather_than_raising(monkeypatch, capsys):
    configure(monkeypatch, NOTIFY_SMTP_PORT="not-a-port")
    assert send_failure_email("Link Checker", "boom") is True
    assert FakeSMTP.instances[0].port == DEFAULT_SMTP_PORT
    assert "not a number" in capsys.readouterr().out


def test_cookie_error_is_flagged_in_the_subject(monkeypatch):
    configure(monkeypatch)
    send_failure_email("Link Checker", "403 Forbidden", is_cookie_error=True)
    assert "Cookie likely expired" in FakeSMTP.instances[0].sent[0]["Subject"]


def test_cookie_error_body_explains_the_fix(monkeypatch):
    configure(monkeypatch)
    send_failure_email("Link Checker", "403 Forbidden", is_cookie_error=True)
    body = FakeSMTP.instances[0].sent[0].get_payload()[0].get_payload()
    assert "SUBSTACK_COOKIE" in body


def test_error_text_reaches_the_body(monkeypatch):
    configure(monkeypatch)
    send_failure_email("Link Checker", "compare failed (exit 1)")
    body = FakeSMTP.instances[0].sent[0].get_payload()[0].get_payload()
    assert "compare failed (exit 1)" in body


def test_smtp_failure_is_reported_not_raised(monkeypatch, capsys):
    """A dead mail server should not mask the failure being reported."""
    configure(monkeypatch)

    class ExplodingSMTP(FakeSMTP):
        def login(self, user, password):
            raise OSError("connection refused")

    monkeypatch.setattr(notify_mod.smtplib, "SMTP", ExplodingSMTP)
    assert send_failure_email("Link Checker", "boom") is False
    assert "Failed to send notification email" in capsys.readouterr().out
