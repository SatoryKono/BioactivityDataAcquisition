"""Unit tests for domain transformations.

Tests pure domain logic (no I/O, no mocks).
Uses property-based testing with Hypothesis for robustness.

Requirements tested:
- REQ-ID-001 to REQ-ID-008: Content hash algorithm
- REQ-SCHEMA-001 to REQ-SCHEMA-004: Schema drift detection
- REQ-THRESHOLD-001, REQ-THRESHOLD-002: DQ thresholds
"""

from __future__ import annotations

import math
from datetime import date, datetime

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.domain.transformations import (
    META_FIELDS,
    calculate_dq_score,
    canonical_json_dumps,
    detect_hash_collision,
    detect_schema_drift,
    exceeds_threshold,
    generate_content_hash,
    generate_entity_id,
    normalize_for_hash,
)
from bioetl.domain.types import DriftLevel

# =============================================================================
# Content Hash Tests (RULES.md §2.8)
# =============================================================================


@pytest.mark.unit
class TestNormalizeForHash:
    """Test record normalization before hashing."""

    def test_nan_and_inf_to_null(self):
        """REQ-ID-004: NaN and Inf should be converted to None."""
        record = {"value_nan": float("nan"), "value_inf": float("inf")}
        normalized = normalize_for_hash(record)
        assert normalized == {"value_nan": None, "value_inf": None}

    def test_float_rounding(self):
        """REQ-ID-003: Floats should be rounded to 10 decimals."""
        record = {"pi": 3.141592653589793}
        normalized = normalize_for_hash(record)
        assert normalized == {"pi": 3.1415926536}

    def test_date_to_iso(self):
        """REQ-ID-005: Dates should be converted to ISO format."""
        record = {
            "date": date(2025, 12, 15),
            "datetime": datetime(2025, 12, 15, 10, 30, 0),
        }
        normalized = normalize_for_hash(record)
        assert normalized == {"date": "2025-12-15", "datetime": "2025-12-15"}

    def test_string_strip(self):
        """REQ-ID-006: Strings should be stripped."""
        record = {"name": "  aspirin  ", "code": "\tCHEMBL123\n"}
        normalized = normalize_for_hash(record)
        assert normalized == {"name": "aspirin", "code": "CHEMBL123"}

    def test_meta_fields_excluded(self):
        """REQ-ID-007: Meta-fields should be excluded from hash."""
        record = {
            "id": "CHEMBL123",
            "_ingestion_ts": "2025-12-15T10:00:00",
            "_run_id": "uuid-123",
            "_run_type": "incremental",
        }
        normalized = normalize_for_hash(record)
        assert normalized == {"id": "CHEMBL123"}
        # Verify all meta-fields excluded
        for meta_field in META_FIELDS:
            assert meta_field not in normalized

    def test_nested_normalization(self):
        """Nested structures should be normalized recursively."""
        record = {
            "nested": {"value": 3.141592653589793, "text": "  hello  "},
            "list": [float("nan"), "  item  "],
        }
        normalized = normalize_for_hash(record)
        assert normalized == {
            "nested": {"value": 3.1415926536, "text": "hello"},
            "list": [None, "item"],
        }

    def test_set_like_fields_ignore_list_order(self):
        """Set-like fields should be order-insensitive while other lists stay stable."""
        record_a = {
            "tags": [{"name": "a"}, {"name": "b"}],
            "ordered": [2, 1],
        }
        record_b = {
            "tags": [{"name": "b"}, {"name": "a"}],
            "ordered": [2, 1],
        }

        normalized_a = normalize_for_hash(record_a, set_like_fields={"tags"})
        normalized_b = normalize_for_hash(record_b, set_like_fields={"tags"})

        assert normalized_a == normalized_b
        assert normalized_a["ordered"] == [2, 1]


@pytest.mark.unit
class TestCanonicalJson:
    """Test canonical JSON serialization."""

    def test_sorted_keys(self):
        """REQ-ID-002: Keys should be sorted."""
        obj = {"z": 3, "a": 1, "m": 2}
        result = canonical_json_dumps(obj)
        assert result == '{"a":1,"m":2,"z":3}'

    def test_no_spaces(self):
        """REQ-ID-002: No spaces in output."""
        obj = {"key": "value", "number": 42}
        result = canonical_json_dumps(obj)
        assert " " not in result
        assert result == '{"key":"value","number":42}'

    def test_ensure_ascii(self):
        """REQ-ID-002: Non-ASCII should be escaped."""
        obj = {"name": "café"}
        result = canonical_json_dumps(obj)
        assert "\\u" in result  # Unicode escape


@pytest.mark.unit
class TestGenerateContentHash:
    """Test content hash generation."""

    def test_deterministic(self):
        """Hash should be deterministic (same input → same output)."""
        record = {"id": "CHEMBL123", "value": 5.5}
        hash1 = generate_content_hash(record, "chembl")
        hash2 = generate_content_hash(record, "chembl")
        assert hash1 == hash2

    def test_different_providers(self):
        """Same record, different providers → different hashes."""
        record = {"id": "123", "value": 5.5}
        hash_chembl = generate_content_hash(record, "chembl")
        hash_pubchem = generate_content_hash(record, "pubchem")
        assert hash_chembl != hash_pubchem

    def test_sha256_length(self):
        """REQ-ID-001: Hash should be SHA256 (64 hex chars)."""
        record = {"test": "data"}
        hash_val = generate_content_hash(record, "test")
        assert len(hash_val) == 64
        assert all(c in "0123456789abcdef" for c in hash_val)

    def test_meta_fields_ignored(self):
        """Meta-fields should not affect hash."""
        record1 = {"id": "123", "_run_id": "uuid-1"}
        record2 = {"id": "123", "_run_id": "uuid-2"}
        hash1 = generate_content_hash(record1, "test")
        hash2 = generate_content_hash(record2, "test")
        assert hash1 == hash2

    def test_set_like_json_string_fields_ignore_array_order(self):
        """JSON array strings can participate in order-insensitive hashing."""
        record1 = {"activity_properties": '[{"name":"a"},{"name":"b"}]'}
        record2 = {"activity_properties": '[{"name":"b"},{"name":"a"}]'}

        hash1 = generate_content_hash(
            record1,
            "chembl",
            set_like_fields={"activity_properties"},
        )
        hash2 = generate_content_hash(
            record2,
            "chembl",
            set_like_fields={"activity_properties"},
        )

        assert hash1 == hash2

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.floats(allow_nan=False, allow_infinity=False), st.text()),
        )
    )
    def test_hash_always_valid(self, record):
        """Property: Hash generation should never fail."""
        hash_val = generate_content_hash(record, "test")
        assert len(hash_val) == 64


@pytest.mark.unit
class TestGenerateEntityId:
    """Test entity ID generation."""

    def test_stable_id_from_source(self):
        """Should use stable ID if provided."""
        record = {"chembl_id": "CHEMBL123", "value": 5.5}
        entity_id = generate_entity_id(record, "chembl", id_field="chembl_id")
        assert entity_id == "chembl:CHEMBL123"

    def test_fallback_to_hash(self):
        """Should use content hash if no stable ID."""
        record = {"name": "aspirin", "value": 5.5}
        entity_id = generate_entity_id(record, "custom", id_field=None)
        assert entity_id.startswith("custom:")
        assert len(entity_id) > len("custom:")

    def test_missing_id_field(self):
        """Should fallback to hash if id_field not in record."""
        record = {"name": "aspirin"}
        entity_id = generate_entity_id(record, "custom", id_field="missing_id")
        assert entity_id.startswith("custom:")


# =============================================================================
# Schema Drift Tests (RULES.md §2.2)
# =============================================================================


@pytest.mark.unit
class TestSchemaDrift:
    """Test schema drift detection."""

    def test_no_drift(self):
        """Identical schemas should report no drift."""
        old = {"id", "name", "value"}
        new = {"id", "name", "value"}
        level, details = detect_schema_drift(old, new, required_fields={"id"})
        assert level == DriftLevel.INFO
        assert details["added_fields"] == []
        assert details["removed_fields"] == []

    def test_info_level_new_field(self):
        """REQ-SCHEMA-002: New optional field → INFO."""
        old = {"id", "name"}
        new = {"id", "name", "description"}
        level, details = detect_schema_drift(old, new, required_fields={"id"})
        assert level == DriftLevel.INFO
        assert "description" in details["added_fields"]

    def test_info_level_many_fields(self):
        """REQ-SCHEMA-003: >3 new fields remains informational drift."""
        old = {"id", "name"}
        new = {"id", "name", "field1", "field2", "field3", "field4"}
        level, details = detect_schema_drift(old, new, required_fields={"id"})
        assert level == DriftLevel.INFO
        assert len(details["added_fields"]) == 4

    def test_critical_level_missing_required(self):
        """REQ-SCHEMA-001: Missing required field → CRITICAL."""
        old = {"id", "name", "value"}
        new = {"name", "value"}  # 'id' removed
        level, details = detect_schema_drift(old, new, required_fields={"id"})
        assert level == DriftLevel.CRITICAL
        assert "id" in details["missing_required"]

    def test_field_count_delta(self):
        """Should correctly calculate field count delta."""
        old = {"a", "b"}
        new = {"a", "b", "c", "d"}  # +2 fields
        _, details = detect_schema_drift(old, new)
        assert details["field_count_delta"] == 2


# =============================================================================
# Data Quality Tests (RULES.md §3.1.2)
# =============================================================================


@pytest.mark.unit
class TestDataQuality:
    """Test DQ score and threshold calculations."""

    def test_perfect_quality(self):
        """All valid records → score 1.0."""
        score = calculate_dq_score(100, 100)
        assert score == pytest.approx(1.0)

    def test_partial_quality(self):
        """95 valid out of 100 → score 0.95."""
        score = calculate_dq_score(95, 100)
        assert score == pytest.approx(0.95)

    def test_zero_quality(self):
        """All invalid → score 0.0."""
        score = calculate_dq_score(0, 100)
        assert score == pytest.approx(0.0)

    def test_empty_batch(self):
        """Empty batch → score 1.0 (no errors)."""
        score = calculate_dq_score(0, 0)
        assert score == pytest.approx(1.0)

    def test_soft_threshold_exceeded(self):
        """REQ-THRESHOLD-001: >5% errors → soft threshold."""
        soft, hard = exceeds_threshold(6, 100)  # 6% error rate
        assert soft is True
        assert hard is False

    def test_hard_threshold_exceeded(self):
        """REQ-THRESHOLD-002: >20% errors → hard threshold."""
        soft, hard = exceeds_threshold(25, 100)  # 25% error rate
        assert soft is True
        assert hard is True

    def test_thresholds_not_exceeded(self):
        """<5% errors → no thresholds exceeded."""
        soft, hard = exceeds_threshold(4, 100)  # 4% error rate
        assert soft is False
        assert hard is False

    def test_zero_total(self):
        """Empty batch → no thresholds exceeded."""
        soft, hard = exceeds_threshold(0, 0)
        assert soft is False
        assert hard is False


@pytest.mark.unit
class TestHashCollision:
    """Test hash collision detection."""

    def test_collision_detected(self):
        """REQ-ID-008: Different source IDs, same hash → collision."""
        collision = detect_hash_collision("hash123", "id_1", "id_2")
        assert collision is True

    def test_no_collision_same_record(self):
        """Same source ID → no collision."""
        collision = detect_hash_collision("hash123", "id_1", "id_1")
        assert collision is False

    def test_no_collision_no_existing(self):
        """No existing record → no collision."""
        collision = detect_hash_collision("hash123", "id_1", None)
        assert collision is False


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================


@pytest.mark.unit
@given(st.floats())
def test_float_normalization_properties(value):
    """Property: Float normalization should handle all float values."""
    if math.isnan(value) or math.isinf(value):
        record = {"value": value}
        normalized = normalize_for_hash(record)
        assert normalized["value"] is None
    else:
        record = {"value": value}
        normalized = normalize_for_hash(record)
        # Should be rounded to 10 decimals
        assert isinstance(normalized["value"], float)


@pytest.mark.unit
@given(st.text())
def test_string_strip_properties(text):
    """Property: String stripping should always succeed."""
    record = {"text": text}
    normalized = normalize_for_hash(record)
    assert normalized["text"] == text.strip()


@pytest.mark.unit
@given(
    st.integers(min_value=0, max_value=1000), st.integers(min_value=0, max_value=1000)
)
def test_dq_score_bounds(valid, total):
    """Property: DQ score should always be between 0.0 and 1.0."""
    if valid <= total:
        score = calculate_dq_score(valid, total)
        assert 0.0 <= score <= 1.0
