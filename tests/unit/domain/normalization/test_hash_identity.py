"""Tests for the canonical hash-identity normalization seam."""

from __future__ import annotations

from datetime import date, datetime

from bioetl.domain.normalization import (
    normalize_hash_identity_record,
    serialize_hash_identity_canonical_json,
)


def test_hash_identity_normalizes_datetime_to_date_iso() -> None:
    """Hash identity keeps the historical date-only datetime contract."""
    record = {
        "published_on": date(2025, 12, 15),
        "measured_at": datetime(2025, 12, 15, 10, 30, 0),
    }

    normalized = normalize_hash_identity_record(record)

    assert normalized == {
        "published_on": "2025-12-15",
        "measured_at": "2025-12-15",
    }


def test_hash_identity_can_sort_nested_sequence_fields() -> None:
    """Only explicitly set-like fields become permutation-invariant."""
    record_a = {
        "tags": [{"name": "a"}, {"name": "b"}],
        "ordered": [2, 1],
    }
    record_b = {
        "tags": [{"name": "b"}, {"name": "a"}],
        "ordered": [2, 1],
    }

    normalized_a = normalize_hash_identity_record(
        record_a,
        sort_nested_sequence_fields={"tags"},
    )
    normalized_b = normalize_hash_identity_record(
        record_b,
        sort_nested_sequence_fields={"tags"},
    )

    assert normalized_a == normalized_b
    assert normalized_a["ordered"] == [2, 1]


def test_hash_identity_json_bytes_are_canonical() -> None:
    """Hash-identity JSON must be stable and compact."""
    normalized = normalize_hash_identity_record({"z": 3, "a": 1, "m": 2})

    assert serialize_hash_identity_canonical_json(normalized) == '{"a":1,"m":2,"z":3}'
