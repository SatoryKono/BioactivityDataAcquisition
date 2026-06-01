"""Unit tests for PublicationTypeClassificationLoader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.infrastructure.config.publication_type_classification_loader import (
    PublicationTypeClassificationLoader,
    _build_row_index,
)


pytestmark = pytest.mark.unit

_DASH = "\u2014"


class TestBuildRowIndex:
    """Tests for _build_row_index."""

    def test_basic_index(self) -> None:
        """Should build index mapping lowercase keys to 1-based row index."""
        rows = [
            [
                "Journal Article",
                "JA",
                "primary",
                "article",
                "journal-article",
                "Journal Article",
                "JournalArticle",
            ],
            ["Review", "RV", "secondary", "review", "review", "Review", "Review"],
        ]
        result = _build_row_index(rows, col=3)
        assert result == {"article": 1, "review": 2}

    def test_skips_dash_sentinel(self) -> None:
        """Should skip rows with dash sentinel value."""
        rows = [
            ["Type1", "T1", "cat", "article", "journal-article", "Type1", "Type1"],
            ["Type2", "T2", "cat", _DASH, "preprint", "Type2", "Type2"],
        ]
        result = _build_row_index(rows, col=3)
        assert "article" in result
        assert len(result) == 1

    def test_strips_trailing_asterisk(self) -> None:
        """Should strip trailing * from keys."""
        rows = [
            ["Type1", "T1", "cat", "article*", "journal-article", "T", "T"],
        ]
        result = _build_row_index(rows, col=3)
        assert "article" in result

    def test_first_occurrence_wins(self) -> None:
        """Should keep first occurrence when keys collide."""
        rows = [
            ["Type1", "T1", "cat", "Article", "j1", "T", "T"],
            ["Type2", "T2", "cat", "article", "j2", "T", "T"],
        ]
        result = _build_row_index(rows, col=3)
        assert result["article"] == 1

    def test_empty_rows(self) -> None:
        """Should return empty dict for empty rows."""
        result = _build_row_index([], col=3)
        assert result == {}


class TestPublicationTypeClassificationLoader:
    """Tests for PublicationTypeClassificationLoader."""

    def test_loads_valid_asset(self, tmp_path: Path) -> None:
        """Should load and parse a valid classification asset."""
        enums_dir = tmp_path / "enums"
        enums_dir.mkdir()

        asset = {
            "rows": [
                [
                    "Journal Article",
                    "JA",
                    "primary",
                    "article",
                    "journal-article",
                    "Journal Article",
                    "JournalArticle",
                ],
                ["Review", "RV", "secondary", "review", "review", "Review", "Review"],
            ]
        }
        (enums_dir / "publication_type_classification.asset.v1.json").write_text(
            json.dumps(asset)
        )

        loader = PublicationTypeClassificationLoader(tmp_path)
        result = loader.load()

        assert len(result.entry_cores) == 2
        assert result.entry_cores[0] == ("Journal Article", "JA", "primary")
        assert "article" in result.openalex_row_index
        assert "journal-article" in result.crossref_row_index
        assert "journal article" in result.pubmed_row_index
        assert "journalarticle" in result.s2_row_index

    def test_classification_loader__missing_file_raises__2379d0b1(self, tmp_path: Path) -> None:
        """Should raise when asset file is missing."""
        loader = PublicationTypeClassificationLoader(tmp_path)
        with pytest.raises(FileNotFoundError):
            loader.load()
