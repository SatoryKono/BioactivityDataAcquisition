from unittest.mock import patch

import pandas as pd
import pytest

from bioetl.domain.transform.impl.normalize import (
    NormalizationService,
    normalize_scalar,
)
from bioetl.domain.transform.normalizers.registry import (
    CUSTOM_FIELD_NORMALIZERS,
)


def test_normalize_scalar():
    # Default: lower + trim
    assert normalize_scalar("  ABC  ") == "abc"
    assert normalize_scalar(1.23456) == 1.235
    assert normalize_scalar(1.0) == 1.0
    assert normalize_scalar(10) == 10

    # ID: upper + trim
    assert normalize_scalar(" chembl123 ", mode="id") == "CHEMBL123"

    # Sensitive: trim only
    assert normalize_scalar("  AbC  ", mode="sensitive") == "AbC"


class MockNormalizationConfig:
    def __init__(
        self,
        case_sensitive_fields=None,
        id_fields=None,
        custom_normalizers=None
    ):
        self.case_sensitive_fields = case_sensitive_fields or []
        self.id_fields = id_fields or []
        self.custom_normalizers = custom_normalizers or {}


class MockConfig:
    def __init__(self, fields, normalization=None):
        self.fields = fields
        self.normalization = normalization or MockNormalizationConfig()


def test_normalization_service_full():
    fields = [
        {"name": "simple", "data_type": "string"},
        {"name": "id_col", "data_type": "string"},
        {"name": "num", "data_type": "float"},
        {"name": "nested_list", "data_type": "array"},
        {"name": "nested_obj", "data_type": "object"},
        {"name": "doi", "data_type": "string"},
    ]

    norm_config = MockNormalizationConfig(id_fields=["id_col"])
    config = MockConfig(fields, normalization=norm_config)

    # Note: 'doi' is registered globally in
    # src/bioetl/domain/transform/normalizers/registry.py
    # We rely on that global registration here.

    service = NormalizationService(config)

    df = pd.DataFrame(
        {
            "simple": ["  Value  ", "TEST"],
            "id_col": [" chembl_1 ", "x_id"],
            "num": [1.23456, 2.0],
            "nested_list": [["A", "B"], ["C"]],
            "nested_obj": [{"K": "V"}, {"X": "Y"}],
            "doi": ["https://doi.org/10.1000/ABC", None],
        }
    )

    res = service.normalize_fields(df)

    # Simple: lower + trim
    assert res["simple"].iloc[0] == "value"

    # ID: upper + trim
    assert res["id_col"].iloc[0] == "CHEMBL_1"

    # Num: round 3
    assert res["num"].iloc[0] == 1.235

    # Nested: serialized with normalization (default lower for strings)
    # "A" -> "a", "K" -> "k", "V" -> "v"
    assert res["nested_list"].iloc[0] == "a|b"
    assert res["nested_obj"].iloc[0] == "K:v"
    # Keys preserve case, values normalized

    # DOI normalized via custom normalizer
    assert res["doi"].iloc[0] == "10.1000/abc"


def test_normalization_service_raises_on_invalid_custom_value():
    norm_config = MockNormalizationConfig()
    config = MockConfig(
        [{"name": "fail_field", "data_type": "string"}],
        normalization=norm_config
    )

    service = NormalizationService(config)

    def fail_normalizer(val):
        raise ValueError("Test failure")

    # Use the imported CUSTOM_FIELD_NORMALIZERS directly
    with patch.dict(CUSTOM_FIELD_NORMALIZERS, {"fail_field": fail_normalizer}):
        config.fields = [{"name": "fail_field", "data_type": "string"}]
        df = pd.DataFrame({"fail_field": ["any"]})

        with pytest.raises(ValueError) as excinfo:
            service.normalize_fields(df)
        assert "fail_field" in str(excinfo.value)


def test_normalize_scalar_edge_cases():
    """Test scalar normalizer edge cases."""
    assert normalize_scalar(None) is None
    assert normalize_scalar([]) is None
    assert normalize_scalar({}) is None
    assert normalize_scalar(float('nan')) is None

    # Boolean pass-through (not explicitly handled but falls to return value)
    assert normalize_scalar(True) is True
    assert normalize_scalar(False) is False

    # Empty string -> None
    assert normalize_scalar("   ") is None

    with pytest.raises(ValueError, match="Expected scalar"):
        normalize_scalar(["not empty"])


def test_normalization_service_id_detection():
    """Test automatic ID field detection."""
    fields = [
        {"name": "some_chembl_id", "data_type": "string"},
        {"name": "id_prefix", "data_type": "string"},
        {"name": "normal_col", "data_type": "string"},
    ]
    config = MockConfig(fields)
    service = NormalizationService(config)

    df = pd.DataFrame({
        "some_chembl_id": [" lower "],
        "id_prefix": [" lower "],
        "normal_col": [" UPPER "],
    })

    res = service.normalize_fields(df)

    # _chembl_id -> ID mode (upper)
    assert res["some_chembl_id"].iloc[0] == "LOWER"
    # id_ prefix -> ID mode (upper)
    assert res["id_prefix"].iloc[0] == "LOWER"
    # normal -> default mode (lower)
    assert res["normal_col"].iloc[0] == "upper"


def test_normalization_service_case_sensitive():
    """Test case sensitive field normalization."""
    fields = [{"name": "secret_code", "data_type": "string"}]
    norm_config = MockNormalizationConfig(
        case_sensitive_fields=["secret_code"]
    )
    config = MockConfig(fields, normalization=norm_config)

    service = NormalizationService(config)

    df = pd.DataFrame({"secret_code": ["  MixEd  "]})
    res = service.normalize_fields(df)

    # Sensitive -> trim only, preserve case
    assert res["secret_code"].iloc[0] == "MixEd"


def test_normalization_service_missing_field():
    """Test graceful handling of configured fields missing from DataFrame."""
    fields = [
        {"name": "exists", "data_type": "string"},
        {"name": "missing", "data_type": "string"}
    ]
    config = MockConfig(fields)
    service = NormalizationService(config)

    df = pd.DataFrame({"exists": ["A"]})
    # Should not raise error
    res = service.normalize_fields(df)
    assert "exists" in res.columns
    assert "missing" not in res.columns


def test_normalization_service_nested_fallback_error():
    """Test error handling when nested normalizer fails on scalar fallback."""
    fields = [{"name": "bad_nested", "data_type": "array"}]
    config = MockConfig(fields)
    service = NormalizationService(config)

    def fail_norm(val):
        raise ValueError("Scalar fail")

    with patch.dict(CUSTOM_FIELD_NORMALIZERS, {"bad_nested": fail_norm}):
        # Pass a scalar so it hits the fallback at end of _serialize_wrapper
        df = pd.DataFrame({"bad_nested": ["scalar_val"]})

        with pytest.raises(ValueError) as excinfo:
            service.normalize_fields(df)
        assert "bad_nested" in str(excinfo.value)
        assert "Scalar fail" in str(excinfo.value)


def test_normalization_service_nested_na():
    """Test handling of pd.NA in nested fields."""
    fields = [{"name": "list_col", "data_type": "array"}]
    config = MockConfig(fields)
    service = NormalizationService(config)

    df = pd.DataFrame({"list_col": [pd.NA, None]})
    res = service.normalize_fields(df)

    assert pd.isna(res["list_col"].iloc[0])
    assert pd.isna(res["list_col"].iloc[1])


def test_normalization_service_nested_scalar_success():
    """Test scalar value successfully normalized in nested field."""
    fields = [{"name": "arr_col", "data_type": "array"}]
    config = MockConfig(fields)
    service = NormalizationService(config)

    # Pass a scalar string to an array field
    df = pd.DataFrame({"arr_col": ["  Value  "]})
    res = service.normalize_fields(df)

    # Should normalize string (default) and return it
    assert res["arr_col"].iloc[0] == "value"


def test_normalization_service_nested_complex_structures():
    """Test normalization of list of dicts."""
    fields = [{"name": "complex_col", "data_type": "array"}]
    config = MockConfig(fields)
    service = NormalizationService(config)

    # List of dicts
    data = [[{"k1": " V1 "}, {"k2": " V2 "}]]
    df = pd.DataFrame({"complex_col": data})

    res = service.normalize_fields(df)

    # Default scalar normalizer: V1 -> v1, V2 -> v2
    # serialize_list([serialize_dict(d1), serialize_dict(d2)])
    # {"k1": "v1"} -> "k1:v1"
    # {"k2": "v2"} -> "k2:v2"
    # List -> "k1:v1|k2:v2"
    assert res["complex_col"].iloc[0] == "k1:v1|k2:v2"


def test_normalization_service_nested_errors_list():
    """Test error propagation in list items."""
    fields = [{"name": "err_list", "data_type": "array"}]
    config = MockConfig(fields)
    service = NormalizationService(config)

    def fail_on_x(val):
        if not isinstance(val, str):
            raise TypeError("Expected string")
        if val == "X":
            raise ValueError("Cannot process X")
        return val.lower()

    with patch.dict(CUSTOM_FIELD_NORMALIZERS, {"err_list": fail_on_x}):
        df = pd.DataFrame({"err_list": [["A", "X"]]})
        with pytest.raises(ValueError) as excinfo:
            service.normalize_fields(df)
        assert "err_list" in str(excinfo.value)
        assert "Cannot process X" in str(excinfo.value)


def test_normalization_service_custom_container_normalizer():
    """Test a custom normalizer that returns a list/dict itself."""
    fields = [{"name": "custom_container", "data_type": "array"}]
    config = MockConfig(fields)
    service = NormalizationService(config)

    def list_producer(val):
        return ["a", "b"]

    with patch.dict(
        CUSTOM_FIELD_NORMALIZERS, {"custom_container": list_producer}
    ):
        df = pd.DataFrame({"custom_container": ["input"]})
        res = service.normalize_fields(df)
        # Should be serialized list "a|b"
        assert res["custom_container"].iloc[0] == "a|b"
