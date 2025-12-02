import pandas as pd
import pytest
from bioetl.domain.transform.impl.normalize import (
    NormalizerMixin,
    serialize_dict,
    serialize_list,
    normalize_scalar,
)


def test_serialize_list_primitives():
    assert serialize_list(["a", "b"]) == "a|b"
    assert serialize_list([1, 2]) == "1|2"
    assert serialize_list([]) is pd.NA
    assert serialize_list(None) is pd.NA


def test_serialize_list_dicts():
    val = [{"k1": "v1"}, {"k2": "v2"}]
    # serialize_dict: "k1:v1" and "k2:v2"
    assert serialize_list(val) == "k1:v1|k2:v2"


def test_serialize_list_mixed_skip_nested():
    # List of lists -> skipped/omitted logic check
    val = ["a", ["b"]]
    # serialize_list checks if element is list/dict and skips it
    assert serialize_list(val) == "a"


def test_serialize_dict_simple():
    val = {"a": 1, "b": "2"}
    assert serialize_dict(val) == "a:1|b:2"


def test_serialize_dict_determinism():
    val = {"b": 2, "a": 1}
    assert serialize_dict(val) == "a:1|b:2"


def test_serialize_dict_nested_skip():
    val = {"a": 1, "nested": {"x": 1}}
    assert serialize_dict(val) == "a:1"


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


class MockNormalizer(NormalizerMixin):
    def __init__(self, config):
        self._config = config


def test_normalizer_mixin_full():
    fields = [
        {"name": "simple", "data_type": "string"},
        {"name": "id_col", "data_type": "string"},
        {"name": "num", "data_type": "float"},
        {"name": "nested_list", "data_type": "array"},
        {"name": "nested_obj", "data_type": "object"},
        {"name": "doi", "data_type": "string"},
    ]
    config = MockConfig(fields)
    normalizer = MockNormalizer(config)

    # Mock ID detection by manually patching if needed, 
    # but "id_col" ends with _id so is_id_field should catch it.
    
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

    res = normalizer.normalize_fields(df)

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


def test_normalizer_mixin_raises_on_invalid_custom_value():
    config = MockConfig([{"name": "doi", "data_type": "string"}])
    normalizer = MockNormalizer(config)

    df = pd.DataFrame({"doi": ["invalid-doi"]})

    with pytest.raises(ValueError):
        normalizer.normalize_fields(df)
