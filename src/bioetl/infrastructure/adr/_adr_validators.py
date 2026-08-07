"""ADR validation utilities."""

from __future__ import annotations

import re
from pathlib import Path

from bioetl.domain.ports import AdrIssueSeverity, AdrValidationIssue

from ._adr_file_utils import ADR_FILENAME_RE
from ._adr_metadata_extractors import extract_meta, parse_h1_title


def validate_filename(
    p: Path,
    issues: list[AdrValidationIssue],
) -> re.Match[str] | None:
    """Validate ADR filename matches pattern.

    Args:
        p: Path to ADR file.
        issues: List to append validation issues.

    Returns:
        Regex match or None.
    """
    m = ADR_FILENAME_RE.match(p.name)
    if not m:
        issues.append(
            AdrValidationIssue(
                number=None,
                path=str(p),
                message="Filename does not match ADR-XXX-title.md",
                severity=AdrIssueSeverity.ERROR,
            )
        )
    return m


def validate_duplicate_number(
    number: int,
    p: Path,
    seen_numbers: set[int],
    issues: list[AdrValidationIssue],
) -> None:
    """Check for duplicate ADR numbers.

    Args:
        number: ADR number.
        p: Path to ADR file.
        seen_numbers: Set of seen ADR numbers.
        issues: List to append validation issues.
    """
    if number in seen_numbers:
        issues.append(
            AdrValidationIssue(
                number=number,
                path=str(p),
                message="Duplicate ADR number",
                severity=AdrIssueSeverity.ERROR,
            )
        )
    else:
        seen_numbers.add(number)


def read_adr_text(
    p: Path,
    number: int,
    issues: list[AdrValidationIssue],
) -> str | None:
    """Read ADR file text.

    Args:
        p: Path to ADR file.
        number: ADR number.
        issues: List to append validation issues.

    Returns:
        File text or None on IO errors.
    """
    try:
        return p.read_text(encoding="utf-8")
    except (
        OSError,
        UnicodeError,
    ) as exc:
        issues.append(
            AdrValidationIssue(
                number=number,
                path=str(p),
                message=f"Cannot read file: {exc}",
                severity=AdrIssueSeverity.ERROR,
            )
        )
        return None


def validate_title(
    text: str,
    number: int,
    p: Path,
    issues: list[AdrValidationIssue],
) -> None:
    """Validate H1 title presence and ADR number consistency.

    Args:
        text: ADR text.
        number: ADR number.
        p: Path to ADR file.
        issues: List to append validation issues.
    """
    title = parse_h1_title(text)
    if not title:
        issues.append(
            AdrValidationIssue(
                number=number,
                path=str(p),
                message="Missing H1 title ('# ...')",
                severity=AdrIssueSeverity.ERROR,
            )
        )
    else:
        m_h1 = re.search(r"ADR-(\d+)", title, flags=re.IGNORECASE)
        if m_h1 and int(m_h1.group(1)) != number:
            issues.append(
                AdrValidationIssue(
                    number=number,
                    path=str(p),
                    message="ADR number mismatch between filename and H1",
                    severity=AdrIssueSeverity.WARNING,
                )
            )


def validate_status(
    text: str,
    number: int,
    p: Path,
    issues: list[AdrValidationIssue],
) -> None:
    """Validate status metadata presence.

    Args:
        text: ADR text.
        number: ADR number.
        p: Path to ADR file.
        issues: List to append validation issues.
    """
    status, _ = extract_meta(text)
    if status is None:
        issues.append(
            AdrValidationIssue(
                number=number,
                path=str(p),
                message="Missing status metadata (Status/Статус)",
                severity=AdrIssueSeverity.WARNING,
            )
        )
