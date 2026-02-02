"""Tests for canonical publication field order.

Verifies that PUBLICATION_FIELD_ORDER constant matches the reference CSV
and that field groupings are internally consistent.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from bioetl.domain.schemas._field_orders import (
    PUBLICATION_CANONICAL_CATEGORIES,
    PUBLICATION_FIELD_ORDER,
)


_CSV_PATH = Path("docs/schemas/publication_field_order.csv")


class TestPublicationFieldOrder:
    """Tests for PUBLICATION_FIELD_ORDER constant."""

    def test_total_field_count(self) -> None:
        """Canonical order has exactly 167 fields."""
        assert len(PUBLICATION_FIELD_ORDER) == 167

    def test_no_duplicates(self) -> None:
        """No duplicate fields in canonical order."""
        assert len(PUBLICATION_FIELD_ORDER) == len(set(PUBLICATION_FIELD_ORDER))

    def test_all_fields_qualified(self) -> None:
        """All fields follow provider.entity.field naming convention."""
        for field in PUBLICATION_FIELD_ORDER:
            parts = field.split(".")
            assert len(parts) == 3, f"Field {field!r} is not fully qualified"
            assert parts[1] == "publication", (
                f"Field {field!r} entity is {parts[1]!r}, expected 'publication'"
            )

    def test_providers_are_known(self) -> None:
        """All providers in field order are from the known set."""
        known_providers = {
            "chembl",
            "crossref",
            "openalex",
            "pubmed",
            "semanticscholar",
        }
        providers_found = {f.split(".")[0] for f in PUBLICATION_FIELD_ORDER}
        assert providers_found == known_providers

    @pytest.mark.skipif(
        not _CSV_PATH.exists(),
        reason="Canonical CSV not found at docs/schemas/publication_field_order.csv",
    )
    def test_matches_canonical_csv(self) -> None:
        """PUBLICATION_FIELD_ORDER matches docs/schemas/publication_field_order.csv."""
        csv_fields: list[str] = []
        with _CSV_PATH.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_fields.append(row["Full"])

        assert len(PUBLICATION_FIELD_ORDER) == len(csv_fields), (
            f"Length mismatch: constant={len(PUBLICATION_FIELD_ORDER)}, "
            f"CSV={len(csv_fields)}"
        )
        for i, (const_field, csv_field) in enumerate(
            zip(PUBLICATION_FIELD_ORDER, csv_fields, strict=True)
        ):
            assert const_field == csv_field, (
                f"Order mismatch at position {i + 1}: "
                f"constant={const_field!r}, CSV={csv_field!r}"
            )


class TestPublicationCanonicalCategories:
    """Tests for PUBLICATION_CANONICAL_CATEGORIES."""

    def test_six_categories(self) -> None:
        """Exactly 6 canonical categories are defined."""
        assert len(PUBLICATION_CANONICAL_CATEGORIES) == 6

    def test_expected_categories(self) -> None:
        """All expected categories are present."""
        expected = {
            "id",
            "bibliography",
            "author_and_affiliation",
            "date",
            "topics_and_keywords",
            "publication",
        }
        assert set(PUBLICATION_CANONICAL_CATEGORIES.keys()) == expected

    def test_categories_cover_all_fields(self) -> None:
        """Category ranges cover all 167 fields without gaps."""
        ranges = sorted(PUBLICATION_CANONICAL_CATEGORIES.values())
        # First category starts at 1
        assert ranges[0][0] == 1
        # Last category ends at 167
        assert ranges[-1][1] == 167
        # No gaps between consecutive categories
        for i in range(1, len(ranges)):
            assert ranges[i][0] == ranges[i - 1][1] + 1, (
                f"Gap between categories at positions {ranges[i - 1][1]} "
                f"and {ranges[i][0]}"
            )

    def test_category_field_counts(self) -> None:
        """Category field counts match expected values."""
        expected_counts = {
            "id": 24,
            "bibliography": 59,
            "author_and_affiliation": 21,
            "date": 10,
            "topics_and_keywords": 16,
            "publication": 37,
        }
        for cat, (start, end) in PUBLICATION_CANONICAL_CATEGORIES.items():
            actual_count = end - start + 1
            assert actual_count == expected_counts[cat], (
                f"Category {cat!r}: expected {expected_counts[cat]} fields, "
                f"got {actual_count}"
            )
