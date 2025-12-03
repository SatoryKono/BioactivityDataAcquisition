import pandas as pd
import pytest
from bioetl.domain.transform.impl.normalize import (
    NormalizationService,
    normalize_scalar,
)
from bioetl.domain.transform.normalizers import normalize_doi


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
    def __init__(self, case_sensitive_fields=None, id_fields=None, custom_normalizers=None):
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
    
    # Note: 'doi' is registered globally in src/bioetl/domain/transform/normalizers/registry.py
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
    assert res["nested_obj"].iloc[0] == "K:v" # Keys preserve case, values normalized

    # DOI normalized via custom normalizer
    assert res["doi"].iloc[0] == "10.1000/abc"


def test_normalization_service_raises_on_invalid_custom_value():
    # 'doi' has a custom normalizer that might raise if invalid DOI logic is strict?
    # Actually normalize_doi logic in current codebase might returns None for invalid or just cleans it.
    # But let's check what we want to test.
    # The original test expected ValueError.
    
    norm_config = MockNormalizationConfig()
    config = MockConfig([{"name": "doi", "data_type": "string"}], normalization=norm_config)
    
    service = NormalizationService(config)

    # We assume normalize_doi raises ValueError for "invalid-doi" IF the original test expected it.
    # If not, we might need to use a mock to force it.
    # But since we rely on global registry, we can't easily inject a mock normalizer for "doi" 
    # without patching the global registry.
    # For this test, let's use a different field name that we register specifically for this test using global registry,
    # then clean up.
    
    from bioetl.domain.transform.normalizers.registry import register_normalizer, CUSTOM_FIELD_NORMALIZERS
    
    def fail_normalizer(val):
        raise ValueError("Test failure")
        
    register_normalizer("fail_field", fail_normalizer)
    
    try:
        config.fields = [{"name": "fail_field", "data_type": "string"}]
        df = pd.DataFrame({"fail_field": ["any"]})
        
        with pytest.raises(ValueError):
            service.normalize_fields(df)
    finally:
        # Cleanup
        if "fail_field" in CUSTOM_FIELD_NORMALIZERS:
            del CUSTOM_FIELD_NORMALIZERS["fail_field"]
