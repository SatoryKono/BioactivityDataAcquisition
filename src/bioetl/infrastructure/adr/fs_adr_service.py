"""Filesystem-based ADR catalog implementation.

Reads ADR markdown files from the repository (default path:
``docs/02-architecture/decisions``) and provides list/show/validate
operations via the AdrServicePort.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.ports.adr import (
    AdrDocument,
    AdrInfo,
    AdrServicePort,
    AdrIssueSeverity,
    AdrValidationIssue,
    AdrValidationReport,
)

from ._adr_file_utils import find_adr_by_number, iter_adr_files, parse_adr_filename
from ._adr_metadata_extractors import extract_meta, parse_h1_title
from ._adr_validators import (
    read_adr_text,
    validate_duplicate_number,
    validate_filename,
    validate_status,
    validate_title,
)


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
        for p in iter_adr_files(self._base):
            parsed = parse_adr_filename(p)
            if not parsed:
                # Skip invalid files in list; validator will report
                continue
            num, title_from_filename = parsed
            # Prefer H1 as title; fall back to filename tail
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                text = ""
            title = parse_h1_title(text) or title_from_filename
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
        p = find_adr_by_number(self._base, number)
        if p is None:
            raise FileNotFoundError(f"ADR-{number:03d} not found in {self.base_path}")
        text = p.read_text(encoding="utf-8")
        title = parse_h1_title(text) or p.stem
        status, date = extract_meta(text)
        return AdrDocument(
            number=number,
            title=title,
            content=text,
            path=str(p),
            status=status,
            date=date,
        )

    def _validate_single_adr_file(
        self,
        p: Path,
        *,
        seen_numbers: set[int],
        issues: list[AdrValidationIssue],
    ) -> None:
        """Validate one ADR file and append issues in place."""
        match = validate_filename(p, issues)
        if match is None:
            return

        number = int(match.group(1))
        validate_duplicate_number(number, p, seen_numbers, issues)

        text = read_adr_text(p, number, issues)
        if text is None:
            return

        validate_title(text, number, p, issues)
        validate_status(text, number, p, issues)

    @staticmethod
    def _build_validation_report(
        *,
        files: list[Path],
        issues: list[AdrValidationIssue],
    ) -> AdrValidationReport:
        """Build aggregate validation report from discovered files and issues."""
        errors = sum(1 for issue in issues if issue.severity == AdrIssueSeverity.ERROR)
        warnings = sum(1 for issue in issues if issue.severity == AdrIssueSeverity.WARNING)
        return AdrValidationReport(
            valid=errors == 0,
            total=len(files),
            errors=errors,
            warnings=warnings,
            issues=tuple(issues),
        )

    def validate(self) -> AdrValidationReport:
        """Validate all ADR files for naming, numbering and metadata consistency.

        Returns:
            AdrValidationReport with valid flag, counts, and list of issues found.
        """
        issues: list[AdrValidationIssue] = []
        files = list(iter_adr_files(self._base))
        seen_numbers: set[int] = set()

        for p in files:
            self._validate_single_adr_file(p, seen_numbers=seen_numbers, issues=issues)

        return self._build_validation_report(
            files=files,
            issues=issues,
        )


__all__ = ["FilesystemAdrCatalog"]
