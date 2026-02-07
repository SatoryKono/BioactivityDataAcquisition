"""Volume/issue and page range parsing for Semantic Scholar records.

Handles S2 API quirks like combined volume/issue strings ("32 4")
and abbreviated page ranges ("737-9" → 737-739).
Split from extractors.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

import re

# Patterns for parsing combined volume/issue strings from S2 API.
# The API sometimes returns both values in the volume field (e.g., "32 4").
_VOLUME_ISSUE_PATTERNS = [
    # "32 4" → vol=32, issue=4 (space-separated, common S2 format)
    re.compile(r"^(\d+)\s+(\d+)$"),
    # "32(4)" or "32 (4)" → vol=32, issue=4
    re.compile(r"^(\d+)\s*\((\d+)\)$"),
    # "Vol. 32, No. 4" or "Vol 32 No 4"
    re.compile(r"^[Vv]ol\.?\s*(\d+)[,\s]+[Nn]o\.?\s*(\d+)$"),
    # "32:4" → vol=32, issue=4
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


def _extract_digits(s: str) -> str:
    """Extract only digit characters from a string."""
    return "".join(c for c in s if c.isdigit())


def _extract_non_digits(s: str) -> str:
    """Extract only non-digit characters from a string."""
    return "".join(c for c in s if not c.isdigit())


def _expand_abbreviated_page(first_page: str, tmp_last_page: str) -> str:
    """Expand abbreviated last page number.

    Academic publishing often abbreviates page ranges:
    - "737-9" means 737-739 (not 737-9)
    - "737-39" means 737-739
    - "199-3" means 199-203 (rollover case)

    Algorithm:
    1. If tmp_last_page has >= digits than first_page, return as-is
    2. Otherwise: last_page = (first_page // 10^n2) * 10^n2 + tmp_last_page
    3. Handle rollover: if expanded < first_page, add 10^n2

    Args:
        first_page: First page (e.g., "737")
        tmp_last_page: Potentially abbreviated last page (e.g., "9", "39", "839")

    Returns:
        Expanded last page string.

    """
    first_digits = _extract_digits(first_page)
    last_digits = _extract_digits(tmp_last_page)

    # If either is non-numeric, return as-is (e.g., "S1-S5")
    if not first_digits or not last_digits:
        return tmp_last_page

    # If last page has same or more digits, it's a full number
    if len(last_digits) >= len(first_digits):
        return tmp_last_page

    # Expand abbreviated page number
    first_num = int(first_digits)
    last_num = int(last_digits)
    divisor = 10 ** len(last_digits)

    expanded = (first_num // divisor) * divisor + last_num

    # Handle rollover case: "199-3" should be "199-203", not "199-193"
    if expanded < first_num:
        expanded += divisor

    # Preserve any prefix from tmp_last_page (e.g., "S" in "S5")
    prefix = _extract_non_digits(tmp_last_page)
    return f"{prefix}{expanded}" if prefix else str(expanded)


def parse_page_range(pages_str: str | None) -> tuple[str | None, str | None]:
    """Parse page range with abbreviated last page expansion.

    Academic publishing often abbreviates page ranges:
    - "737-9" means 737-739 (not 737-9)
    - "737-39" means 737-739
    - "737-839" means 737-839 (full number, no expansion)

    Also handles whitespace, en-dashes (–), and em-dashes (—).

    Args:
        pages_str: Raw pages string (e.g., "737-9", "123-145").

    Returns:
        Tuple of (first_page, last_page). Both are strings or None.

    Examples:
        >>> parse_page_range("737-9")
        ('737', '739')
        >>> parse_page_range("737-39")
        ('737', '739')
        >>> parse_page_range("737-839")
        ('737', '839')
        >>> parse_page_range("123")
        ('123', None)
        >>> parse_page_range("S1-S5")
        ('S1', 'S5')

    """
    if not pages_str:
        return (None, None)

    cleaned = pages_str.strip()
    if not cleaned:
        return (None, None)

    # Normalize various dash types to hyphen
    # EN DASH (U+2013) and EM DASH (U+2014) → HYPHEN-MINUS (U+002D)
    cleaned = cleaned.replace("\u2013", "-").replace("\u2014", "-")

    # Split on "-" (only first occurrence)
    parts = cleaned.split("-", 1)

    first_page = parts[0].strip()
    if not first_page:
        return (None, None)

    # No range separator - single page
    if len(parts) == 1:
        return (first_page, None)

    tmp_last_page = parts[1].strip()
    if not tmp_last_page:
        return (first_page, None)

    # Expand abbreviated page number
    last_page = _expand_abbreviated_page(first_page, tmp_last_page)

    return (first_page, last_page)
