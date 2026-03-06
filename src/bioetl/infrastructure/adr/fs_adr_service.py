"""Filesystem-based ADR service implementation.

Reads ADR markdown files from the repository (default path:
``docs/02-architecture/decisions``) and provides list/show/validate
operations via the AdrServicePort.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.ports import (
    AdrDocument,
    AdrInfo,
    AdrServicePort,
    AdrValidationIssue,
    AdrValidationReport,
)

ADR_FILENAME_RE = re.compile(r"^ADR-(\d+)-(.+)\.md$", re.IGNORECASE)
STATUS_PATTERNS = (
    re.compile(r"^\*\*Status:\*\*\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\*\*Статус:\*\*\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Status:\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Статус:\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^\|\s*\*\*(?:Status|Статус)\*\*\s*\|\s*([^|]+?)\s*\|",
        flags=re.IGNORECASE | re.MULTILINE,
    ),
)
DATE_PATTERNS = (
    re.compile(r"^\*\*Date:\*\*\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\*\*Дата:\*\*\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Date:\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Дата:\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^\|\s*\*\*(?:Date|Дата)\*\*\s*\|\s*([^|]+?)\s*\|",
        flags=re.IGNORECASE | re.MULTILINE,
    ),
)


def _iter_adr_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists():
        return []
    # Sort for deterministic order
    return sorted(p for p in base_dir.glob("ADR-*.md") if p.is_file())


def _parse_h1_title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _extract_with_patterns(
    text: str, patterns: tuple[re.Pattern[str], ...]
) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _extract_from_section(
    text: str,
    section_names: tuple[str, ...],
) -> str | None:
    lines = text.splitlines()[:120]
    normalized_names = {name.lower() for name in section_names}

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue

        heading = stripped.lstrip("#").strip()
        heading_lower = heading.lower()

        for name in normalized_names:
            if heading_lower == name:
                for candidate in lines[index + 1 : index + 8]:
                    value = candidate.strip()
                    if not value:
                        continue
                    if value.startswith("#") or value.startswith("|"):
                        break
                    return value
            prefix = f"{name}:"
            if heading_lower.startswith(prefix):
                value = heading[len(prefix) :].strip()
                if value:
                    return value
    return None


def _extract_meta(text: str) -> tuple[str | None, str | None]:
    """Extract status and date from common ADR metadata formats."""
    status = _extract_with_patterns(text, STATUS_PATTERNS)
    if status is None:
        status = _extract_from_section(text, ("Status", "Статус"))

    date = _extract_with_patterns(text, DATE_PATTERNS)
    if date is None:
        date = _extract_from_section(text, ("Date", "Дата"))

    return status, date


@dataclass(slots=True)
class FsAdrService(AdrServicePort):
    """Filesystem-backed ADR service."""

    base_path: str = "docs/02-architecture/decisions"

    @property
    def _base(self) -> Path:
        return Path(self.base_path)

    def list_adrs(self) -> list[AdrInfo]:
        """Return all ADR documents sorted by number.

        Returns:
            List of AdrInfo objects sorted ascending by ADR number.
        """
        items: list[AdrInfo] = []
        for p in _iter_adr_files(self._base):
            m = ADR_FILENAME_RE.match(p.name)
            if not m:
                # Skip invalid files in list; validator will report
                continue
            num = int(m.group(1))
            # Prefer H1 as title; fall back to filename tail
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                text = ""
            title = _parse_h1_title(text) or m.group(2).replace("-", " ")
            items.append(AdrInfo(number=num, title=title, path=str(p)))
        items.sort(key=lambda x: x.number)
        return items

    def get_adr(self, number: int) -> AdrDocument:
        """Read and parse a single ADR by its number.

        Args:
            number: ADR number to look up.

        Returns:
            AdrDocument with content, title, status, and date parsed from the ADR file.
        """
        pattern = f"ADR-{number:03d}-*.md"
        matches = list(self._base.glob(pattern))
        if not matches:
            raise FileNotFoundError(f"ADR-{number:03d} not found in {self.base_path}")
        # If multiple, pick lexicographically first for determinism
        p = sorted(matches)[0]
        text = p.read_text(encoding="utf-8")
        title = _parse_h1_title(text) or p.stem
        status, date = _extract_meta(text)
        return AdrDocument(
            number=number,
            title=title,
            content=text,
            path=str(p),
            status=status,
            date=date,
        )

    def validate(self) -> AdrValidationReport:
        """Validate all ADR files for naming, numbering and metadata consistency.

        Returns:
            AdrValidationReport with valid flag, counts, and list of issues found.
        """
        issues: list[AdrValidationIssue] = []
        files = list(_iter_adr_files(self._base))
        seen_numbers: set[int] = set()

        for p in files:
            name = p.name
            m = ADR_FILENAME_RE.match(name)
            if not m:
                issues.append(
                    AdrValidationIssue(
                        number=None,
                        path=str(p),
                        message="Filename does not match ADR-XXX-title.md",
                        severity="error",
                    )
                )
                continue

            number = int(m.group(1))
            if number in seen_numbers:
                issues.append(
                    AdrValidationIssue(
                        number=number,
                        path=str(p),
                        message="Duplicate ADR number",
                        severity="error",
                    )
                )
            else:
                seen_numbers.add(number)

            try:
                text = p.read_text(encoding="utf-8")
            except (
                OSError,
                UnicodeError,
            ) as exc:  # pragma: no cover - rare IO error path
                issues.append(
                    AdrValidationIssue(
                        number=number,
                        path=str(p),
                        message=f"Cannot read file: {exc}",
                        severity="error",
                    )
                )
                continue

            title = _parse_h1_title(text)
            if not title:
                issues.append(
                    AdrValidationIssue(
                        number=number,
                        path=str(p),
                        message="Missing H1 title ('# ...')",
                        severity="error",
                    )
                )
            else:
                # Optional: check number consistency if ADR-XXX appears in H1
                m_h1 = re.search(r"ADR-(\d+)", title, flags=re.IGNORECASE)
                if m_h1 and int(m_h1.group(1)) != number:
                    issues.append(
                        AdrValidationIssue(
                            number=number,
                            path=str(p),
                            message="ADR number mismatch between filename and H1",
                            severity="warning",
                        )
                    )

            status, _ = _extract_meta(text)
            if status is None:
                issues.append(
                    AdrValidationIssue(
                        number=number,
                        path=str(p),
                        message="Missing status metadata (Status/Статус)",
                        severity="warning",
                    )
                )

        total = len(files)
        errors = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")
        return AdrValidationReport(
            valid=errors == 0,
            total=total,
            errors=errors,
            warnings=warnings,
            issues=issues,
        )


__all__ = ["FsAdrService"]
