"""Email alerts for unattended runs.

A scheduled link check that fails silently is worse than no scheduled check,
because nothing distinguishes "no broken links this month" from "the run died".
This sends an alert when a run fails, and calls out an expired session cookie
specifically, since that is the failure that recurs.

Configuration is entirely environment variables, so no credential ever lands in
a file:

    NOTIFY_EMAIL      the account that sends the alert
    NOTIFY_PASSWORD   its password -- an app password, if your provider uses them
    NOTIFY_TO         where to send the alert (defaults to NOTIFY_EMAIL)
    NOTIFY_SMTP_HOST  SMTP server (default: smtp.gmail.com)
    NOTIFY_SMTP_PORT  SMTP port, STARTTLS (default: 587)
    NOTIFY_SMTP_TIMEOUT  seconds to wait on the SMTP server (default: 30)

Never put real values in this file. An earlier version of it carried a live app
password in this docstring, and because the file was saved as UTF-16 no secret
scanner could see it. Environment variables are not a style preference here.

Usage from a scheduler script:

    python -m substack_link_checker.notify --project "Link Checker" \\
        --error "compare failed (exit 1)" --cookie-error
"""

import argparse
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
# Seconds. Without an explicit timeout smtplib uses the socket default, which
# is no timeout at all -- so a network outage or a silently-dropped port 587
# can hang the alert indefinitely. That blocks the failure handler on exactly
# the path this notifier exists to make observable, leaving the scheduler
# without a result. A late alert is still useful; a hung one is not.
DEFAULT_SMTP_TIMEOUT = 30


def _int_env(name, default):
    """Read an integer environment variable, warning rather than raising."""
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"WARNING: {name} is not a number; using {default}.")
        return default


def send_failure_email(project_name, error_message, is_cookie_error=False):
    """Send a failure alert. Returns True if it was sent.

    Returns False rather than raising when the notifier is not configured: a
    missing alert should not turn a recoverable failure into a crash inside
    the error handler that was trying to report it.
    """
    smtp_user = os.environ.get("NOTIFY_EMAIL", "")
    smtp_password = os.environ.get("NOTIFY_PASSWORD", "")
    recipient = os.environ.get("NOTIFY_TO", smtp_user)
    smtp_host = os.environ.get("NOTIFY_SMTP_HOST", DEFAULT_SMTP_HOST)

    smtp_port = _int_env("NOTIFY_SMTP_PORT", DEFAULT_SMTP_PORT)
    smtp_timeout = _int_env("NOTIFY_SMTP_TIMEOUT", DEFAULT_SMTP_TIMEOUT)

    if not smtp_user or not smtp_password:
        print("WARNING: Email notification not configured.")
        print("  Set NOTIFY_EMAIL and NOTIFY_PASSWORD environment variables.")
        print("  On Windows these come from secrets.ps1 -- see secrets.ps1.example.")
        return False

    subject = f"[FAILED] {project_name}"
    if is_cookie_error:
        subject += " - Cookie likely expired"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_type = "Cookie/Authentication Error (403)" if is_cookie_error else "General Error"

    body = f"""Scheduled Task Failure
========================================

Project:    {project_name}
Time:       {timestamp}
Error Type: {error_type}

Error Details:
----------------------------------------
{error_message}
----------------------------------------
"""

    if is_cookie_error:
        body += """
ACTION REQUIRED: your Substack session cookie has likely expired.

Sign in to Substack, copy a fresh `substack.sid` from your browser's
developer tools (Application -> Cookies), and update the SUBSTACK_COOKIE
environment variable your scheduled run reads.
"""

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=smtp_timeout) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        print(f"Failure notification sent to {recipient}")
        return True
    except Exception as e:
        # Deliberately broad: this runs inside a failure handler, and every
        # SMTP problem is a reason to log and move on, never to raise.
        print(f"Failed to send notification email: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        prog="python -m substack_link_checker.notify",
        description=(
            "Send an email alert that a scheduled run failed. Reads its "
            "credentials from NOTIFY_* environment variables."
        ),
    )
    parser.add_argument("--project", required=True, help="Name to identify the run in the subject")
    parser.add_argument("--error", required=True, help="The error text to include")
    parser.add_argument(
        "--cookie-error",
        action="store_true",
        help="Flag this as an expired-cookie failure and include renewal steps",
    )
    args = parser.parse_args()

    sent = send_failure_email(args.project, args.error, args.cookie_error)
    # Non-zero when the alert did not go out, so a scheduler can see that the
    # failure was never reported to anyone.
    sys.exit(0 if sent else 1)


if __name__ == "__main__":
    main()
