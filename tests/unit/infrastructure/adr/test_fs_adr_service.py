"""Unit tests for FilesystemAdrCatalog (filesystem-backed ADR catalog).

Tests use tmp_path to create fake ADR markdown files without touching
the real repository docs. All paths are injected via DI constructor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.adr.fs_adr_service import (
    FilesystemAdrCatalog,
    _extract_meta,
    _extract_with_patterns,
    _iter_adr_files,
    _parse_h1_title,
    DATE_PATTERNS,
    STATUS_PATTERNS,
)


# ---------------------------------------------------------------------------
# Helpers to create fake ADR files
# ---------------------------------------------------------------------------


def _write_adr(
    base: Path,
    number: int,
    slug: str,
    content: str,
) -> Path:
    """Write a fake ADR markdown file into base_path."""
    name = f"ADR-{number:03d}-{slug}.md"
    path = base / name
    path.write_text(content, encoding="utf-8")
    return path


def _minimal_adr(number: int, title: str, status: str = "Accepted") -> str:
    return (
        f"# ADR-{number:03d}: {title}\n\n"
        f"**Status:** {status}\n\n"
        f"**Date:** 2026-01-01\n\n"
        "## Context\n\nSome context here.\n"
    )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIterAdrFiles:
    """Tests for _iter_adr_files() helper."""

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        """No ADR files in directory returns empty iterable."""
        files = list(_iter_adr_files(tmp_path))
        assert files == []

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent directory returns empty iterable."""
        files = list(_iter_adr_files(tmp_path / "nonexistent"))
        assert files == []

    def test_finds_adr_files(self, tmp_path: Path) -> None:
        """Finds ADR-*.md files and ignores others."""
        _write_adr(tmp_path, 1, "first", "content")
        _write_adr(tmp_path, 2, "second", "content")
        (tmp_path / "README.md").write_text("not an ADR")
        (tmp_path / "ADR-notes.txt").write_text("not md")

        files = list(_iter_adr_files(tmp_path))
        assert len(files) == 2

    def test_files_sorted_alphabetically(self, tmp_path: Path) -> None:
        """Files are returned in sorted order."""
        _write_adr(tmp_path, 10, "tenth", "content")
        _write_adr(tmp_path, 2, "second", "content")
        _write_adr(tmp_path, 1, "first", "content")

        files = list(_iter_adr_files(tmp_path))
        names = [f.name for f in files]
        assert names == sorted(names)


@pytest.mark.unit
class TestParseH1Title:
    """Tests for _parse_h1_title() helper."""

    def test_extracts_h1_title(self) -> None:
        """Extracts title from first H1 line."""
        text = "# ADR-001: My Title\n\nSome content"
        assert _parse_h1_title(text) == "ADR-001: My Title"

    def test_returns_none_when_no_h1(self) -> None:
        """Returns None when no H1 line found."""
        text = "## Section\n### Subsection\nContent"
        assert _parse_h1_title(text) is None

    def test_returns_first_h1_only(self) -> None:
        """Returns only the first H1."""
        text = "# First Title\n# Second Title"
        assert _parse_h1_title(text) == "First Title"

    def test_strips_whitespace(self) -> None:
        """Strips surrounding whitespace from title."""
        text = "#   Spaced Title   "
        assert _parse_h1_title(text) == "Spaced Title"


@pytest.mark.unit
class TestExtractWithPatterns:
    """Tests for _extract_with_patterns() helper."""

    def test_extracts_bold_status(self) -> None:
        """Extracts status from **Status:** pattern."""
        text = "**Status:** Accepted\n\nOther content"
        result = _extract_with_patterns(text, STATUS_PATTERNS)
        assert result == "Accepted"

    def test_extracts_russian_status(self) -> None:
        """Extracts status from **Статус:** pattern."""
        text = "**Статус:** Принято"
        result = _extract_with_patterns(text, STATUS_PATTERNS)
        assert result == "Принято"

    def test_extracts_date_pattern(self) -> None:
        """Extracts date from **Date:** pattern."""
        text = "**Date:** 2026-01-15"
        result = _extract_with_patterns(text, DATE_PATTERNS)
        assert result == "2026-01-15"

    def test_returns_none_when_no_match(self) -> None:
        """Returns None when no pattern matches."""
        text = "No status or date here"
        result = _extract_with_patterns(text, STATUS_PATTERNS)
        assert result is None

    def test_table_format_status(self) -> None:
        """Extracts status from table format."""
        text = "| **Status** | Accepted |"
        result = _extract_with_patterns(text, STATUS_PATTERNS)
        assert result == "Accepted"


@pytest.mark.unit
class TestExtractMeta:
    """Tests for _extract_meta() composite helper."""

    def test_extracts_both_status_and_date(self) -> None:
        """Extracts status and date from standard ADR format."""
        text = "**Status:** Accepted\n**Date:** 2026-01-15"
        status, date = _extract_meta(text)
        assert status == "Accepted"
        assert date == "2026-01-15"

    def test_returns_none_when_missing(self) -> None:
        """Returns (None, None) when neither found."""
        text = "No metadata here"
        status, date = _extract_meta(text)
        assert status is None
        assert date is None

    def test_partial_metadata(self) -> None:
        """Returns partial when only status found."""
        text = "**Status:** Superseded"
        status, date = _extract_meta(text)
        assert status == "Superseded"
        assert date is None


# ---------------------------------------------------------------------------
# FilesystemAdrCatalog.list_adrs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilesystemAdrCatalogListAdrs:
    """Tests for FilesystemAdrCatalog.list_adrs()."""

    def test_list_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns empty list."""
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        result = service.list_adrs()
        assert result == []

    def test_list_nonexistent_directory(self, tmp_path: Path) -> None:
        """Non-existent directory returns empty list."""
        service = FilesystemAdrCatalog(base_path=str(tmp_path / "nonexistent"))
        result = service.list_adrs()
        assert result == []

    def test_list_returns_sorted_by_number(self, tmp_path: Path) -> None:
        """ADRs are returned sorted by number."""
        _write_adr(tmp_path, 10, "tenth", _minimal_adr(10, "Tenth"))
        _write_adr(tmp_path, 2, "second", _minimal_adr(2, "Second"))
        _write_adr(tmp_path, 1, "first", _minimal_adr(1, "First"))

        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        result = service.list_adrs()

        numbers = [a.number for a in result]
        assert numbers == [1, 2, 10]

    def test_list_extracts_h1_title(self, tmp_path: Path) -> None:
        """list_adrs uses H1 title from file content."""
        _write_adr(
            tmp_path, 1, "first", "# ADR-001: My Real Title\n\n**Status:** Accepted\n"
        )
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        result = service.list_adrs()
        assert result[0].title == "ADR-001: My Real Title"

    def test_list_falls_back_to_filename_slug(self, tmp_path: Path) -> None:
        """Falls back to filename slug when no H1 found."""
        _write_adr(tmp_path, 1, "my-first-adr", "No h1 here\n\n**Status:** Draft\n")
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        result = service.list_adrs()
        # Falls back to slug with dashes replaced by spaces
        assert result[0].title == "my first adr"

    def test_list_skips_invalid_filenames(self, tmp_path: Path) -> None:
        """Files not matching ADR-XXX-title.md pattern are skipped in list."""
        _write_adr(tmp_path, 1, "valid", _minimal_adr(1, "Valid"))
        (tmp_path / "invalid-name.md").write_text("invalid")
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        result = service.list_adrs()
        assert len(result) == 1
        assert result[0].number == 1

    def test_list_provides_path(self, tmp_path: Path) -> None:
        """AdrInfo includes path to the file."""
        _write_adr(tmp_path, 1, "first", _minimal_adr(1, "First"))
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        result = service.list_adrs()
        assert Path(result[0].path).exists()


# ---------------------------------------------------------------------------
# FilesystemAdrCatalog.get_adr
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilesystemAdrCatalogGetAdr:
    """Tests for FilesystemAdrCatalog.get_adr()."""

    def test_get_existing_adr(self, tmp_path: Path) -> None:
        """Returns AdrDocument for an existing ADR number."""
        _write_adr(tmp_path, 1, "first", _minimal_adr(1, "First ADR"))
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        doc = service.get_adr(1)
        assert doc.number == 1
        assert "First ADR" in doc.title
        assert doc.status == "Accepted"
        assert doc.date == "2026-01-01"

    def test_get_raises_file_not_found(self, tmp_path: Path) -> None:
        """Raises FileNotFoundError for missing ADR number."""
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        with pytest.raises(FileNotFoundError, match="ADR-099"):
            service.get_adr(99)

    def test_get_adr_includes_content(self, tmp_path: Path) -> None:
        """AdrDocument.content includes the full file text."""
        content = _minimal_adr(5, "Fifth ADR")
        _write_adr(tmp_path, 5, "fifth", content)
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        doc = service.get_adr(5)
        assert doc.content == content

    def test_get_adr_with_multiple_matches_picks_first(self, tmp_path: Path) -> None:
        """When multiple files match (duplicates), picks lexicographic first."""
        _write_adr(tmp_path, 1, "alpha", _minimal_adr(1, "Alpha ADR"))
        _write_adr(tmp_path, 1, "beta", _minimal_adr(1, "Beta ADR"))
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        doc = service.get_adr(1)
        # Should pick alpha (lexicographically first)
        assert "Alpha ADR" in doc.title

    def test_get_adr_without_h1_uses_stem(self, tmp_path: Path) -> None:
        """When no H1 found, uses file stem as title."""
        _write_adr(tmp_path, 3, "my-slug", "**Status:** Draft\n\nContent")
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        doc = service.get_adr(3)
        assert doc.title == "ADR-003-my-slug"


# ---------------------------------------------------------------------------
# FilesystemAdrCatalog.validate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilesystemAdrCatalogValidate:
    """Tests for FilesystemAdrCatalog.validate()."""

    def test_validate_empty_directory(self, tmp_path: Path) -> None:
        """Validates empty directory as valid (no files = no errors)."""
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        report = service.validate()
        assert report.valid is True
        assert report.total == 0
        assert report.errors == 0

    def test_validate_valid_adrs(self, tmp_path: Path) -> None:
        """Valid ADR files produce no validation issues."""
        _write_adr(tmp_path, 1, "first", _minimal_adr(1, "First"))
        _write_adr(tmp_path, 2, "second", _minimal_adr(2, "Second"))
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        report = service.validate()
        assert report.valid is True
        assert report.total == 2
        assert report.errors == 0

    def test_validate_duplicate_numbers(self, tmp_path: Path) -> None:
        """Duplicate ADR numbers are flagged as errors."""
        _write_adr(tmp_path, 1, "alpha", _minimal_adr(1, "Alpha"))
        _write_adr(tmp_path, 1, "beta", _minimal_adr(1, "Beta"))
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        report = service.validate()
        assert report.errors > 0
        assert report.valid is False
        error_messages = [i.message for i in report.issues]
        assert any("Duplicate" in m for m in error_messages)

    def test_validate_missing_h1_title(self, tmp_path: Path) -> None:
        """ADR without H1 title is flagged as error."""
        _write_adr(tmp_path, 1, "missing-title", "**Status:** Accepted\nNo H1 here\n")
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        report = service.validate()
        assert report.errors > 0
        error_messages = [i.message for i in report.issues]
        assert any("H1" in m for m in error_messages)

    def test_validate_missing_status_is_warning(self, tmp_path: Path) -> None:
        """ADR without status metadata is flagged as warning (not error)."""
        _write_adr(tmp_path, 1, "no-status", "# ADR-001: No Status\n\nContent")
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        report = service.validate()
        # Missing status → warning severity
        assert report.valid is True  # no errors, only warnings
        assert report.warnings > 0
        warning_messages = [i.message for i in report.issues if i.severity == "warning"]
        assert any("status" in m.lower() for m in warning_messages)

    def test_validate_adr_number_mismatch_h1_vs_filename(self, tmp_path: Path) -> None:
        """H1 number mismatch with filename is flagged as warning."""
        # File is ADR-001 but H1 says ADR-002
        _write_adr(
            tmp_path,
            1,
            "mismatch",
            "# ADR-002: Wrong Number\n\n**Status:** Accepted\n",
        )
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        report = service.validate()
        warning_messages = [i.message for i in report.issues if i.severity == "warning"]
        assert any("mismatch" in m.lower() for m in warning_messages)

    def test_validate_report_counts(self, tmp_path: Path) -> None:
        """Report counts match actual errors and warnings."""
        # 1 valid, 1 missing title (error), 1 missing status (warning)
        _write_adr(tmp_path, 1, "valid", _minimal_adr(1, "Valid"))
        _write_adr(tmp_path, 2, "no-title", "**Status:** Draft\n")
        _write_adr(tmp_path, 3, "no-status", "# ADR-003: No Status\n")

        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        report = service.validate()

        assert report.total == 3
        assert report.errors == 1
        assert report.warnings == 1

    def test_validate_includes_path_in_issues(self, tmp_path: Path) -> None:
        """Validation issues include the file path."""
        _write_adr(tmp_path, 1, "no-title", "**Status:** Draft\n")
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        report = service.validate()
        assert all(i.path for i in report.issues)

    def test_validate_includes_number_in_issues(self, tmp_path: Path) -> None:
        """Validation issues include the ADR number."""
        _write_adr(tmp_path, 42, "some-adr", "# ADR-042: Title\n")  # missing status
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        report = service.validate()
        issues_with_number = [i for i in report.issues if i.number == 42]
        assert len(issues_with_number) > 0


# ---------------------------------------------------------------------------
# FilesystemAdrCatalog default path property
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilesystemAdrCatalogDefaultPath:
    """Tests for default base_path behavior."""

    def test_default_base_path(self) -> None:
        """Default base_path is set correctly."""
        service = FilesystemAdrCatalog()
        assert service.base_path == "docs/02-architecture/decisions"

    def test_custom_base_path(self, tmp_path: Path) -> None:
        """Custom base_path is used."""
        service = FilesystemAdrCatalog(base_path=str(tmp_path))
        assert service.base_path == str(tmp_path)
