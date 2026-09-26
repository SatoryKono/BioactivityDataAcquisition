"""Volume/issue parsing for Semantic Scholar records.

Handles S2 API quirks like combined volume/issue strings ("32 4").
Split from extractors.py per audit-package-structure-2026-02-07.

Page range parsing (including abbreviated expansion) is delegated to
the canonical implementation in ``bioetl.domain.normalization``.
"""

from __future__ import annotations

import re

from bioetl.domain.normalization import parse_page_range

# Patterns for parsing combined volume/issue strings from S2 API.
# The API sometimes returns both values in the volume field (e.g., "32 4").
_VOLUME_ISSUE_PATTERNS = [
    # "32 4" -> vol=32, issue=4 (space-separated, common S2 format)
    re.compile(r"^(\d+)\s+(\d+)$"),
    # "32(4)" or "32 (4)" -> vol=32, issue=4
    re.compile(r"^(\d+)\s*\((\d+)\)$"),
    # "Vol. 32, No. 4" or "Vol 32 No 4"
    re.compile(r"^[Vv]ol\.?\s*(\d+)[,\s]+[Nn]o\.?\s*(\d+)$"),
    # "32:4" -> vol=32, issue=4
    re.compile(r"^(\d+):(\d+)$"),
]


def parse_volume_issue(volume_str: str | None) -> tuple[str | None, str | None]:
    """Parse volume string that may contain issue number.

    Semantic Scholar API sometimes returns combined volume/issue in the
    volume field (e.g., "32 4" for volume 32, issue 4).

    Args:
        volume_str: Raw volume string from S2 API.

    Returns:
        Tuple of (volume, issue). Issue is None if not embedded.

    Examples:
        >>> parse_volume_issue("32 4")
        ('32', '4')
        >>> parse_volume_issue("523")
        ('523', None)
        >>> parse_volume_issue("40(3)")
        ('40', '3')
        >>> parse_volume_issue(None)
        (None, None)

    """
    if not volume_str:
        return (None, None)

    cleaned = volume_str.strip()
    if not cleaned:
        return (None, None)

    # Try each pattern for combined volume/issue
    for pattern in _VOLUME_ISSUE_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            return (match.group(1), match.group(2))

    # No issue found - return volume as-is
    return (cleaned, None)


__all__ = [
    "parse_page_range",
    "parse_volume_issue",
]
