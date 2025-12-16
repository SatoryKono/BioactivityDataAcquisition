from datetime import datetime

from bioetl.domain.transformations import (
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


def test_normalize_for_hash_basic():
    """Tests basic normalization of a record."""
    record = {
        "value": 3.141592653589793,
        "date": datetime(2025, 12, 15),
        "name": "  aspirin  ",
        "_run_id": "uuid-123",
    }
    expected = {
        "value": 3.1415926536,
        "date": "2025-12-15",
        "name": "aspirin",
    }
    assert normalize_for_hash(record) == expected


def test_normalize_for_hash_nan_inf():
    """Tests normalization of NaN and infinity values."""
    record = {"a": float("nan"), "b": float("inf"), "c": float("-inf")}
    expected = {"a": None, "b": None, "c": None}
    assert normalize_for_hash(record) == expected


def test_normalize_for_hash_nested():
    """Tests normalization of nested structures."""
    record = {
        "level1": {
            "value": 1.23456789012,
            "name": "  nested  ",
            "list": [1, "  a  ", 3.141592653589793],
        }
    }
    expected = {
        "level1": {
            "value": 1.2345678901,
            "name": "nested",
            "list": [1, "a", 3.1415926536],
        }
    }
    assert normalize_for_hash(record) == expected


def test_normalize_for_hash_empty():
    """Tests normalization of an empty record."""
    assert normalize_for_hash({}) == {}


def test_normalize_for_hash_meta_fields_only():
    """Tests normalization of a record with only meta-fields."""
    record = {"_run_id": "123", "_ingestion_ts": "ts"}
    assert normalize_for_hash(record) == {}


def test_canonical_json_dumps():
    """Tests canonical JSON dumping."""
    assert canonical_json_dumps({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert canonical_json_dumps({}) == "{}"


def test_generate_content_hash():
    """Tests content hash generation."""
    record = {"id": "CHEMBL123", "value": 5.5}
    provider = "chembl"
    # Updated hash based on actual implementation: sha256("chembl" + '{"id":"CHEMBL123","value":5.5}')
    expected_hash = "950b83a6e5adc291f087d6be215d5b76f372f6359518aa65bdb0cae5dcaa6a5b"
    hash_val = generate_content_hash(record, provider)
    assert hash_val == expected_hash


def test_generate_entity_id_with_stable_id():
    """Tests entity ID generation with a stable source ID."""
    record = {"chembl_id": "CHEMBL123"}
    provider = "chembl"
    id_field = "chembl_id"
    entity_id = generate_entity_id(record, provider, id_field)
    assert entity_id == "chembl:CHEMBL123"


def test_generate_entity_id_fallback_to_hash():
    """Tests entity ID generation falling back to content hash."""
    record = {"name": "aspirin"}
    provider = "custom"
    # Updated hash prefix based on actual implementation: sha256("custom" + '{"name":"aspirin"}')[:16]
    expected_hash_prefix = "d6c5208de5db5062"
    entity_id = generate_entity_id(record, provider, id_field=None)
    assert entity_id == f"custom:{expected_hash_prefix}"


def test_detect_schema_drift_no_drift():
    """Tests schema drift detection with no changes."""
    old = {"id", "name"}
    new = {"id", "name"}
    level, details = detect_schema_drift(old, new)
    assert level == DriftLevel.INFO
    assert not details["added_fields"] and not details["removed_fields"]


def test_detect_schema_drift_info():
    """Tests schema drift detection for informational level drift."""
    old = {"id", "name", "value"}
    new = {"id", "name", "value", "description"}
    level, details = detect_schema_drift(old, new, required_fields={"id"})
    assert level == DriftLevel.INFO
    assert details["added_fields"] == ["description"]


def test_detect_schema_drift_warn():
    """Tests schema drift detection for warning level drift."""
    old = {"id"}
    new = {"id", "f1", "f2", "f3", "f4"}
    level, details = detect_schema_drift(old, new)
    assert level == DriftLevel.WARN
    assert len(details["added_fields"]) == 4


def test_detect_schema_drift_critical():
    """Tests schema drift detection for critical level drift."""
    old = {"id", "name"}
    new = {"name"}
    level, details = detect_schema_drift(old, new, required_fields={"id"})
    assert level == DriftLevel.CRITICAL
    assert details["missing_required"] == ["id"]


def test_calculate_dq_score():
    """Tests data quality score calculation."""
    assert calculate_dq_score(95, 100) == 0.95
    assert calculate_dq_score(0, 100) == 0.0
    assert calculate_dq_score(100, 100) == 1.0
    assert calculate_dq_score(0, 0) == 1.0


def test_exceeds_threshold():
    """Tests error threshold checking."""
    assert exceeds_threshold(4, 100) == (False, False)
    assert exceeds_threshold(6, 100) == (True, False)
    assert exceeds_threshold(21, 100) == (True, True)
    assert exceeds_threshold(0, 100) == (False, False)
    assert exceeds_threshold(0, 0) == (False, False)


def test_detect_hash_collision():
    """Tests content hash collision detection."""
    assert detect_hash_collision("abc", "id_1", "id_2") is True
    assert detect_hash_collision("abc", "id_1", "id_1") is False
    assert detect_hash_collision("abc", "id_1", None) is False
