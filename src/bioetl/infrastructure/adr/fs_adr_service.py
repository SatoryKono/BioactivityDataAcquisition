"""Filesystem-based ADR catalog implementation.

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
STATUS_LABELS = ("Status", "Статус")
DATE_LABELS = ("Date", "Дата")
STATUS_PATTERNS = STATUS_LABELS
DATE_PATTERNS = DATE_LABELS


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


def _extract_prefixed_line_value(
    stripped: str,
    lowered: str,
    label_variants: tuple[str, ...],
) -> str | None:
    for label in label_variants:
        for prefix in (f"**{label}:**", f"{label}:"):
            if lowered.startswith(prefix):
                value = stripped[len(prefix) :].strip()
                return value or None
    return None


def _extract_table_line_value(
    stripped: str,
    label_variants: tuple[str, ...],
) -> str | None:
    if not stripped.startswith("|"):
        return None
    cells = [cell.strip() for cell in stripped.split("|") if cell.strip()]
    if len(cells) < 2:
        return None
    header = cells[0].strip("* ").casefold()
    if header in label_variants and cells[1]:
        return cells[1]
    return None


def _extract_labeled_line_value(text: str, labels: tuple[str, ...]) -> str | None:
    label_variants = tuple(label.casefold() for label in labels)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        lowered = stripped.casefold()
        prefixed_value = _extract_prefixed_line_value(
            stripped,
            lowered,
            label_variants,
        )
        if prefixed_value is not None:
            return prefixed_value

        table_value = _extract_table_line_value(stripped, label_variants)
        if table_value is not None:
            return table_value
    return None


def _extract_with_patterns(text: str, patterns: tuple[str, ...]) -> str | None:
    """Backward-compatible wrapper kept for unit tests and callers."""
    return _extract_labeled_line_value(text, patterns)


def _first_content_line(lines: list[str], start: int) -> str | None:
    """Return first non-empty content line after a heading (up to 7 lines ahead)."""
    for candidate in lines[start + 1 : start + 8]:
        value = candidate.strip()
        if not value:
            continue
        if value.startswith("#") or value.startswith("|"):
            return None
        return value
    return None


def _match_heading_to_section(
    heading: str,
    normalized_names: set[str],
) -> tuple[str | None, bool]:
    """Check heading against section names. Returns (inline_value, is_exact_match)."""
    heading_lower = heading.lower()
    for name in normalized_names:
        if heading_lower == name:
            return None, True
        prefix = f"{name}:"
        if heading_lower.startswith(prefix):
            value = heading[len(prefix) :].strip()
            return (value if value else None), False
    return None, False


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
        inline_value, is_exact = _match_heading_to_section(heading, normalized_names)

        if is_exact:
            result = _first_content_line(lines, index)
            if result is not None:
                return result
        elif inline_value is not None:
            return inline_value
    return None


def _extract_meta(text: str) -> tuple[str | None, str | None]:
    """Extract status and date from common ADR metadata formats."""
    status = _extract_labeled_line_value(text, STATUS_LABELS)
    if status is None:
        status = _extract_from_section(text, ("Status", "Статус"))

    date = _extract_labeled_line_value(text, DATE_LABELS)
    if date is None:
        date = _extract_from_section(text, ("Date", "Дата"))

    return status, date


@dataclass(slots=True)
class FilesystemAdrCatalog(AdrServicePort):
    """Filesystem-backed ADR catalog."""

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

    @staticmethod
    def _validate_filename(
        p: Path,
        issues: list[AdrValidationIssue],
    ) -> re.Match[str] | None:
        """Validate ADR filename matches pattern. Returns match or None."""
        m = ADR_FILENAME_RE.match(p.name)
        if not m:
            issues.append(
                AdrValidationIssue(
                    number=None,
                    path=str(p),
                    message="Filename does not match ADR-XXX-title.md",
                    severity="error",
                )
            )
        return m

    @staticmethod
    def _validate_duplicate_number(
        number: int,
        p: Path,
        seen_numbers: set[int],
        issues: list[AdrValidationIssue],
    ) -> None:
        """Check for duplicate ADR numbers."""
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

    @staticmethod
    def _read_adr_text(
        p: Path,
        number: int,
        issues: list[AdrValidationIssue],
    ) -> str | None:
        """Read ADR file text. Returns None on IO errors."""
        try:
            return p.read_text(encoding="utf-8")
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
            return None

    @staticmethod
    def _validate_title(
        text: str,
        number: int,
        p: Path,
        issues: list[AdrValidationIssue],
    ) -> None:
        """Validate H1 title presence and ADR number consistency."""
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

    @staticmethod
    def _validate_status(
        text: str,
        number: int,
        p: Path,
        issues: list[AdrValidationIssue],
    ) -> None:
        """Validate status metadata presence."""
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

    def _validate_single_adr_file(
        self,
        p: Path,
        *,
        seen_numbers: set[int],
        issues: list[AdrValidationIssue],
    ) -> None:
        """Validate one ADR file and append issues in place."""
        match = self._validate_filename(p, issues)
        if match is None:
            return

        number = int(match.group(1))
        self._validate_duplicate_number(number, p, seen_numbers, issues)

        text = self._read_adr_text(p, number, issues)
        if text is None:
            return

        self._validate_title(text, number, p, issues)
        self._validate_status(text, number, p, issues)

    @staticmethod
    def _build_validation_report(
        *,
        files: list[Path],
        issues: list[AdrValidationIssue],
    ) -> AdrValidationReport:
        """Build aggregate validation report from discovered files and issues."""
        errors = sum(1 for issue in issues if issue.severity == "error")
        warnings = sum(1 for issue in issues if issue.severity == "warning")
        return AdrValidationReport(
            valid=errors == 0,
            total=len(files),
            errors=errors,
            warnings=warnings,
            issues=issues,
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
            self._validate_single_adr_file(p, seen_numbers=seen_numbers, issues=issues)

        return self._build_validation_report(
            files=files,
            issues=issues,
        )


FsAdrService = FilesystemAdrCatalog

__all__ = ["FilesystemAdrCatalog", "FsAdrService"]
