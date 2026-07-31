"""Console encoding setup for the CLI.

Windows falls back to the locale encoding -- cp1252 on most machines --
whenever stdout is redirected rather than attached to a terminal. A scheduled
task does exactly that, as does `... > run.log`. cp1252 cannot encode the
U+2717 mark used to flag a broken link, so the first broken link the tool
found raised UnicodeEncodeError and killed the run.

That made the failure mode perverse: the checker only survived runs in which
it found nothing wrong. A monthly scheduled job looked healthy for weeks while
dying on its first real result, which is the one thing the tool exists to
report. Non-ASCII characters in scraped URLs and post titles hit the same
wall.

Replacing unencodable characters is preferred over raising: a mangled glyph in
a log costs nothing next to a report that never gets written.
"""

import sys


def configure_stdio() -> None:
    """Make stdout and stderr tolerant of non-ASCII output.

    Safe to call repeatedly. Streams that cannot be reconfigured are skipped
    rather than treated as an error -- pytest's capture objects and a plain
    ``io.StringIO`` have no ``reconfigure``, and a detached stream raises.
    Neither is a reason to abort a run.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            continue
