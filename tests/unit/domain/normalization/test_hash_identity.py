"""Tests for the canonical hash-identity normalization seam."""

from __future__ import annotations

from datetime import UTC, date, datetime, timezone, timedelta

from bioetl.domain.normalization import (
    normalize_hash_identity_record,
    serialize_hash_identity_canonical_json,
)
from bioetl.domain.transformations import generate_content_hash


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


def test_hash_identity_v2_preserves_full_utc_datetime_precision() -> None:
    """v2 datetime policy distinguishes same-day business timestamp changes."""
    record = {
        "measured_at": datetime(
            2025,
            12,
            15,
            10,
            30,
            0,
            123456,
            tzinfo=timezone(timedelta(hours=3)),
        ),
    }

    normalized = normalize_hash_identity_record(
        record,
        datetime_policy="v2_datetime_utc",
    )

    assert normalized == {"measured_at": "2025-12-15T07:30:00.123456Z"}


def test_generate_content_hash_v2_distinguishes_same_day_timestamps() -> None:
    """v1 compatibility collapses dates; v2 timestamp-sensitive policy does not."""
    first = {"measured_at": datetime(2025, 12, 15, 10, 30, tzinfo=UTC)}
    second = {"measured_at": datetime(2025, 12, 15, 11, 30, tzinfo=UTC)}

    assert generate_content_hash(first, "test") == generate_content_hash(
        second,
        "test",
    )
    assert generate_content_hash(
        first,
        "test",
        datetime_policy="v2_datetime_utc",
    ) != generate_content_hash(
        second,
        "test",
        datetime_policy="v2_datetime_utc",
    )


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
