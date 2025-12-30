"""Unit tests for IdentityService.

Tests cover:
- Determinism (same input → same hash)
- Float normalization (round to 10 decimals)
- Meta-field exclusion
- Canonical JSON (sorted keys)
- Entity ID generation from source_id and hash fallback
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from bioetl.domain.services.identity_service import IdentityService, META_FIELDS


class TestIdentityServiceDeterminism:
    """Test determinism of content hash generation."""

    def test_same_input_produces_same_hash(self) -> None:
        """Same input should always produce the same content hash."""
        service = IdentityService()
        record = {"field_a": "value1", "field_b": 42, "field_c": 3.14}

        hash1 = service.compute_content_hash("chembl", record)
        hash2 = service.compute_content_hash("chembl", record)

        assert hash1 == hash2
        # ContentHash is a NewType (str alias), check it's a valid hex string
        assert isinstance(hash1, str)
        assert len(hash1) == 64

    def test_different_providers_produce_different_hashes(self) -> None:
        """Different providers should produce different hashes for same data."""
        service = IdentityService()
        record = {"id": "123", "value": 100}

        hash_chembl = service.compute_content_hash("chembl", record)
        hash_pubchem = service.compute_content_hash("pubchem", record)

        assert hash_chembl != hash_pubchem

    def test_field_order_does_not_affect_hash(self) -> None:
        """Field order should not affect hash (canonical JSON uses sorted keys)."""
        service = IdentityService()
        record1 = {"a": 1, "b": 2, "c": 3}
        record2 = {"c": 3, "a": 1, "b": 2}

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        assert hash1 == hash2


class TestFloatNormalization:
    """Test float normalization for consistent hashing."""

    def test_float_rounded_to_10_decimals(self) -> None:
        """Floats should be rounded to 10 decimal places."""
        service = IdentityService()

        # These should produce the same hash after rounding
        record1 = {"value": 3.14159265358979323846}
        record2 = {"value": 3.1415926536}  # Rounded to 10 decimals

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        assert hash1 == hash2

    def test_nan_normalized_to_none(self) -> None:
        """NaN values should be normalized to None."""
        service = IdentityService()
        record_with_nan = {"value": float("nan")}
        record_with_none = {"value": None}

        hash1 = service.compute_content_hash("test", record_with_nan)
        hash2 = service.compute_content_hash("test", record_with_none)

        assert hash1 == hash2

    def test_inf_normalized_to_none(self) -> None:
        """Infinity values should be normalized to None."""
        service = IdentityService()
        record_with_inf = {"value": float("inf")}
        record_with_none = {"value": None}

        hash1 = service.compute_content_hash("test", record_with_inf)
        hash2 = service.compute_content_hash("test", record_with_none)

        assert hash1 == hash2

    def test_negative_inf_normalized_to_none(self) -> None:
        """Negative infinity values should be normalized to None."""
        service = IdentityService()
        record_with_neg_inf = {"value": float("-inf")}
        record_with_none = {"value": None}

        hash1 = service.compute_content_hash("test", record_with_neg_inf)
        hash2 = service.compute_content_hash("test", record_with_none)

        assert hash1 == hash2


class TestMetaFieldExclusion:
    """Test that meta-fields are excluded from hash calculation."""

    @pytest.mark.parametrize(
        "meta_field",
        [
            "_ingestion_ts",
            "_run_id",
            "_run_type",
            "_dq_warn",
            "_dq_error",
            "_source_batch_id",
        ],
    )
    def test_meta_field_excluded_from_hash(self, meta_field: str) -> None:
        """Meta-fields should not affect content hash."""
        service = IdentityService()
        base_record = {"id": "123", "value": 100}

        record_with_meta = {**base_record, meta_field: "should_be_ignored"}

        hash_base = service.compute_content_hash("test", base_record)
        hash_with_meta = service.compute_content_hash("test", record_with_meta)

        assert hash_base == hash_with_meta

    def test_all_meta_fields_in_constant(self) -> None:
        """Verify META_FIELDS constant contains expected fields."""
        expected = {
            "_ingestion_ts",
            "_run_id",
            "_run_type",
            "_dq_warn",
            "_dq_error",
            "_source_batch_id",
        }
        assert META_FIELDS == expected


class TestCanonicalJSON:
    """Test canonical JSON serialization."""

    def test_nested_dicts_sorted(self) -> None:
        """Nested dictionaries should also have sorted keys."""
        service = IdentityService()
        record1 = {"outer": {"z": 1, "a": 2}}
        record2 = {"outer": {"a": 2, "z": 1}}

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        assert hash1 == hash2

    def test_list_order_preserved(self) -> None:
        """List order should be preserved (not sorted)."""
        service = IdentityService()
        record1 = {"items": [1, 2, 3]}
        record2 = {"items": [3, 2, 1]}

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        # Different order should produce different hashes
        assert hash1 != hash2


class TestDateNormalization:
    """Test date/datetime normalization."""

    def test_datetime_normalized_to_date_iso(self) -> None:
        """Datetime should be normalized to date ISO string."""
        service = IdentityService()

        # Different times on same date should produce same hash
        dt1 = datetime(2024, 1, 15, 10, 30, 0)
        dt2 = datetime(2024, 1, 15, 23, 59, 59)

        record1 = {"timestamp": dt1}
        record2 = {"timestamp": dt2}

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        assert hash1 == hash2

    def test_date_normalized_to_iso(self) -> None:
        """Date should be normalized to ISO string."""
        service = IdentityService()
        d = date(2024, 1, 15)

        record = {"date_field": d}
        normalized = service._normalize_for_hash(record)

        assert normalized["date_field"] == "2024-01-15"


class TestStringNormalization:
    """Test string normalization."""

    def test_string_stripped(self) -> None:
        """Strings should be stripped of whitespace."""
        service = IdentityService()
        record1 = {"name": "  test  "}
        record2 = {"name": "test"}

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        assert hash1 == hash2


class TestEntityIdGeneration:
    """Test entity ID generation."""

    def test_entity_id_with_source_id(self) -> None:
        """Entity ID should use source_id when provided."""
        service = IdentityService()

        entity_id = service.compute_entity_id(
            provider="chembl",
            entity_type="activity",
            source_id="12345",
            record={"any": "data"},
        )

        assert entity_id == "chembl:12345"

    def test_entity_id_without_source_id_uses_hash(self) -> None:
        """Entity ID should use hash prefix when source_id is None."""
        service = IdentityService()

        entity_id = service.compute_entity_id(
            provider="chembl",
            entity_type="activity",
            source_id=None,
            record={"field": "value"},
        )

        # Should start with provider and be based on hash
        assert str(entity_id).startswith("chembl:")
        # Hash prefix should be 16 characters
        assert len(str(entity_id)) == len("chembl:") + 16

    def test_entity_id_format(self) -> None:
        """Entity ID should have correct format."""
        service = IdentityService()

        entity_id = service.compute_entity_id(
            provider="pubchem",
            entity_type="compound",
            source_id="CID123",
            record={},
        )

        # EntityID is a NewType (str alias)
        assert isinstance(entity_id, str)
        assert entity_id == "pubchem:CID123"

    def test_entity_id_deterministic_without_source(self) -> None:
        """Entity ID without source_id should be deterministic."""
        service = IdentityService()
        record = {"stable": "data"}

        id1 = service.compute_entity_id("test", "entity", None, record)
        id2 = service.compute_entity_id("test", "entity", None, record)

        assert id1 == id2


class TestExcludeNone:
    """Test exclude_none parameter behavior."""

    def test_exclude_none_true(self) -> None:
        """When exclude_none=True, None values should be excluded."""
        service = IdentityService()
        record_with_none = {"a": 1, "b": None}
        record_without_none = {"a": 1}

        hash1 = service.compute_content_hash(
            "test", record_with_none, exclude_none=True
        )
        hash2 = service.compute_content_hash(
            "test", record_without_none, exclude_none=True
        )

        assert hash1 == hash2

    def test_exclude_none_false(self) -> None:
        """When exclude_none=False, None values should be included."""
        service = IdentityService()
        record_with_none = {"a": 1, "b": None}
        record_without_none = {"a": 1}

        hash1 = service.compute_content_hash(
            "test", record_with_none, exclude_none=False
        )
        hash2 = service.compute_content_hash(
            "test", record_without_none, exclude_none=False
        )

        assert hash1 != hash2


class TestNestedStructures:
    """Test normalization of nested structures."""

    def test_nested_dict_normalized(self) -> None:
        """Nested dicts should be normalized recursively."""
        service = IdentityService()
        record = {"outer": {"inner": {"value": 3.14159265358979}}}

        normalized = service._normalize_for_hash(record)

        # Float should be rounded
        assert normalized["outer"]["inner"]["value"] == round(3.14159265358979, 10)

    def test_nested_list_normalized(self) -> None:
        """Lists should have elements normalized recursively."""
        service = IdentityService()
        record = {"items": [1.23456789012345, "  text  ", {"key": float("nan")}]}

        normalized = service._normalize_for_hash(record)

        assert normalized["items"][0] == round(1.23456789012345, 10)
        assert normalized["items"][1] == "text"
        assert normalized["items"][2]["key"] is None


class TestHashFormat:
    """Test hash output format."""

    def test_hash_is_sha256_hex(self) -> None:
        """Hash should be SHA256 hex digest (64 characters)."""
        service = IdentityService()
        content_hash = service.compute_content_hash("test", {"id": "123"})

        assert len(str(content_hash)) == 64
        assert all(c in "0123456789abcdef" for c in str(content_hash))


class TestServiceStateless:
    """Test that service is stateless and reusable."""

    def test_multiple_calls_independent(self) -> None:
        """Multiple calls should be independent (no state)."""
        service = IdentityService()

        hash1 = service.compute_content_hash("provider1", {"a": 1})
        hash2 = service.compute_content_hash("provider2", {"b": 2})
        hash3 = service.compute_content_hash("provider1", {"a": 1})

        # First and third should be equal (same input)
        assert hash1 == hash3
        # Different inputs should be different
        assert hash1 != hash2
