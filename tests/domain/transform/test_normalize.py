import pandas as pd
import pytest
from bioetl.domain.transform.impl.normalize import (
    NormalizationService,
    normalize_scalar,
)
from bioetl.domain.transform.impl.registry import NormalizerRegistry
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


class MockConfig:
    def __init__(self, fields):
        self.fields = fields


def test_normalization_service_full():
    fields = [
        {"name": "simple", "data_type": "string"},
        {"name": "id_col", "data_type": "string"},
        {"name": "num", "data_type": "float"},
        {"name": "nested_list", "data_type": "array"},
        {"name": "nested_obj", "data_type": "object"},
        {"name": "doi", "data_type": "string"},
    ]
    config = MockConfig(fields)
    
    registry = NormalizerRegistry()
    registry.register("doi", normalize_doi)
    registry.set_id_fields(["id_col"])
    
    service = NormalizationService(registry, config)

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
    config = MockConfig([{"name": "doi", "data_type": "string"}])
    registry = NormalizerRegistry()
    registry.register("doi", normalize_doi)
    
    service = NormalizationService(registry, config)

    df = pd.DataFrame({"doi": ["invalid-doi"]})

    with pytest.raises(ValueError):
        service.normalize_fields(df)
