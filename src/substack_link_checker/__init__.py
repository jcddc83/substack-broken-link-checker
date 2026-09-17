"""Substack Broken Link Checker — async link checker for Substack newsletters."""

from ._cli_check import load_domains_from_file
from .checker import (
    CATEGORY_BLOCKED,
    CATEGORY_BROKEN,
    CATEGORY_INCONCLUSIVE,
    BrokenLinkRecord,
    LinkCheckResult,
    SubstackLinkChecker,
    classify_error,
)

__version__ = "1.3.0"

__all__ = [
    "BrokenLinkRecord",
    "LinkCheckResult",
    "SubstackLinkChecker",
    "CATEGORY_BROKEN",
    "CATEGORY_BLOCKED",
    "CATEGORY_INCONCLUSIVE",
    "classify_error",
    "load_domains_from_file",
    "__version__",
]
