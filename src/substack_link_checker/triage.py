"""Turn a report into a work list, grouped by what you would actually do.

`check` sorts failures by how much to trust them. This goes one step further
and groups them by the *action* required, which is not the same axis. Two
findings from a real full-archive audit drive the distinction:

  * Many genuinely-broken rows are malformed hrefs -- two URLs concatenated in
    the post's HTML. There is no dead target to replace; the fix is editing
    the post.
  * A host that has retired a subdomain may serve a certificate that does not
    match, so the check aborts before reading a status and files the row
    inconclusive. Those are dead, not unknown -- but only you know which hosts
    they are, which is what `--retired-hosts` is for.

Usage:
    substack-link-checker triage report.csv triaged.csv
    substack-link-checker triage report.csv triaged.csv --retired-hosts hosts.txt
"""

import argparse
import csv
import re
import sys
from collections import Counter
from typing import Optional, Tuple
from urllib.parse import urlparse

from ._cli_check import load_domains_from_file
from .checker import CATEGORY_BLOCKED, CATEGORY_BROKEN

# Archive services embed the archived URL in their own path, so a second
# scheme is legitimate there and must not be read as a concatenation.
ARCHIVE_PREFIX = re.compile(r"https?://(?:web\.archive\.org/web|webarchive\.loc\.gov/all)/[^/]+/")
SCHEME = re.compile(r"https?://")

# Most actionable first. The report is sorted by this order.
CLASS_ORDER = [
    "malformed_href",
    "retired_host",
    "dead_target",
    "inconclusive_other",
    "blocked",
]

ACTIONS = {
    "malformed_href": "Edit post: remove the duplicated second URL from the href",
    "retired_host": "Replace: host is on your retired list, find the current URL or an archive",
    "dead_target": "Replace or drop: target page is gone",
    "inconclusive_other": "Re-check: timeout or transient failure, not confirmed dead",
    "blocked": "No action: site blocks automated requests, link is probably fine",
}

FIELDNAMES = [
    "class",
    "action",
    "post_title",
    "post_url",
    "broken_link",
    "suggested_fix",
    "error_type",
    "original_category",
]


def split_concatenated(url: str) -> Optional[str]:
    """Return the leading URL if `url` is two or more glued together, else None.

    A Wayback URL legitimately embeds a second scheme
    (web.archive.org/web/<ts>/http://...), so that prefix is skipped before
    looking for the join.
    """
    match = ARCHIVE_PREFIX.match(url)
    offset = match.end() if match else 0
    rest = url[offset:]

    joins = list(SCHEME.finditer(rest))
    if len(joins) < 2:
        return None

    # The first join is the URL's own scheme; the second starts the glued copy.
    leading = url[: offset + joins[1].start()]

    # A few hrefs are mangled rather than simply doubled -- "http://'https://..."
    # has a stray quote where the host should be, so the leading half is junk
    # and the trailing half is the real link. Prefer whichever half parses.
    if _plausible(leading):
        return leading
    trailing = rest[joins[1].start() :]
    return trailing if _plausible(trailing) else leading


def _plausible(url: str) -> bool:
    """True if `url` has something that looks like a hostname."""
    host = urlparse(url).netloc
    return "." in host and len(host) > 3


def classify(row: dict, retired_hosts: frozenset) -> Tuple[str, str]:
    """Sort one report row into a class, with a suggested fix where we have one."""
    url = row["broken_link"]
    category = row["category"]

    leading = split_concatenated(url)
    if leading is not None:
        return "malformed_href", leading

    if urlparse(url).netloc.lower() in retired_hosts:
        return "retired_host", ""

    if category == CATEGORY_BROKEN:
        return "dead_target", ""
    if category == CATEGORY_BLOCKED:
        return "blocked", ""
    return "inconclusive_other", ""


def triage_rows(rows, retired_hosts: frozenset):
    """Build the triaged rows, most actionable first."""
    out = []
    for row in rows:
        klass, suggested = classify(row, retired_hosts)
        out.append(
            {
                "class": klass,
                "action": ACTIONS[klass],
                "post_title": row.get("post_title", ""),
                "post_url": row.get("post_url", ""),
                "broken_link": row["broken_link"],
                "suggested_fix": suggested,
                "error_type": row.get("error_type", ""),
                "original_category": row["category"],
            }
        )

    out.sort(key=lambda r: (CLASS_ORDER.index(r["class"]), r["post_url"], r["broken_link"]))
    return out


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Triage a broken-link report into actionable classes. Reads a CSV "
            "written by `substack-link-checker check` and groups its rows by "
            "the work each one implies."
        ),
    )
    parser.add_argument("report", help="Report CSV written by `check`")
    parser.add_argument("output", help="Where to write the triaged CSV")
    parser.add_argument(
        "--retired-hosts",
        help=(
            "File of hostnames you know are retired, one per line, blank lines "
            "and # comments ignored. These are reported as dead even when the "
            "check was inconclusive -- a retired subdomain often serves a "
            "mismatched certificate, which aborts the check before any status "
            "is read."
        ),
    )
    args = parser.parse_args()

    retired_hosts = frozenset(
        host.lower()
        for host in (load_domains_from_file(args.retired_hosts) if args.retired_hosts else [])
    )

    with open(args.report, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "category" not in reader.fieldnames:
            sys.exit(
                "Error: this report has no 'category' column. It was written by a "
                "version older than 1.2.0 -- re-run `check` to produce a current one."
            )
        rows = list(reader)

    out = triage_rows(rows, retired_hosts)

    # utf-8-sig so Excel opens it without mangling non-ASCII post titles.
    with open(args.output, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(out)

    if not out:
        print(f"No rows to triage. Wrote an empty report to {args.output}.")
        return

    counts = Counter(r["class"] for r in out)
    posts = {k: len({r["post_url"] for r in out if r["class"] == k}) for k in counts}
    width = max(len(k) for k in counts)
    print(f"{len(out)} rows -> {args.output}\n")
    for klass in CLASS_ORDER:
        if klass in counts:
            print(f"  {klass:<{width}}  {counts[klass]:>5} links across {posts[klass]:>3} posts")

    actionable = counts["malformed_href"] + counts["retired_host"] + counts["dead_target"]
    print(f"\n  actionable total: {actionable}")


if __name__ == "__main__":
    main()
