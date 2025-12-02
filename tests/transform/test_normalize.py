import pandas as pd
import pytest
from unittest.mock import MagicMock

from bioetl.domain.transform.impl.normalize import (
    serialize_list,
    serialize_dict,
    normalize_scalar,
    NormalizerMixin,
)


class TestNormalizeScalar:
    def test_none(self):
        assert normalize_scalar(None) is pd.NA
        assert normalize_scalar(float("nan")) is pd.NA

    def test_float(self):
        # Keeps as float, rounded
        assert normalize_scalar(1.23456) == 1.235
        assert normalize_scalar(1.0) == 1.0
        assert normalize_scalar(0.0) == 0.0
        assert normalize_scalar(1.2344) == 1.234

    def test_int(self):
        # Keeps as int
        assert normalize_scalar(123) == 123

    def test_string_default(self):
        # default: trim + lower
        assert normalize_scalar("  TeSt  ") == "test"
        assert normalize_scalar("TEST") == "test"

    def test_string_id(self):
        # id: trim + upper
        assert normalize_scalar("  chembl123  ", mode="id") == "CHEMBL123"
        assert normalize_scalar("doi:10.123", mode="id") == "DOI:10.123"

    def test_string_sensitive(self):
        # sensitive: trim only
        assert normalize_scalar("  SMILES  ", mode="sensitive") == "SMILES"
        assert normalize_scalar("c1ccccc1", mode="sensitive") == "c1ccccc1"


class TestSerializeList:
    def test_none_or_empty(self):
        assert serialize_list(None) is pd.NA
        assert serialize_list([]) is pd.NA

    def test_primitives_default(self):
        # Default normalization (identity for primitive in tests if not specified? No, defaults to x)
        assert serialize_list(["A", "B", 123]) == "A|B|123"

    def test_with_normalizer(self):
        # Custom normalizer
        norm = lambda x: x.lower() if isinstance(x, str) else x
        assert serialize_list(["A", "B"], value_normalizer=norm) == "a|b"

    def test_dicts_recursive_normalizer(self):
        # Normalizer should propagate to dicts
        input_list = [{"k": "V"}]
        norm = lambda x: x.lower() if isinstance(x, str) else x
        assert serialize_list(input_list, value_normalizer=norm) == "k:v"


class TestNormalizerMixin:
    class PipelineMock(NormalizerMixin):
        def __init__(self, fields_config):
            self._config = MagicMock()
            self._config.fields = fields_config

    def test_normalize_fields(self):
        fields_config = [
            {"name": "description", "data_type": "string"},      # default (lower)
            {"name": "assay_chembl_id", "data_type": "string"},  # ID (upper)
            {"name": "canonical_smiles", "data_type": "string"}, # Sensitive
            {"name": "pchembl_value", "data_type": "float"},     # Float (round)
            {"name": "properties", "data_type": "array"},        # Array (nested)
        ]
        
        pipeline = self.PipelineMock(fields_config)
        
        df = pd.DataFrame({
            "description": ["  Some Text  ", None],
            "assay_chembl_id": ["chembl1", "CHEMBL2"],
            "canonical_smiles": ["c1ccccc1", "C1CCCCC1"],
            "pchembl_value": [1.23456, None],
            "properties": [[{"key": "Val"}], None]
        })
        
        result = pipeline.normalize_fields(df)
        
        # Description -> lower, trimmed
        assert result["description"].iloc[0] == "some text"
        assert pd.isna(result["description"].iloc[1])
        
        # ID -> upper
        assert result["assay_chembl_id"].iloc[0] == "CHEMBL1"
        assert result["assay_chembl_id"].iloc[1] == "CHEMBL2"
        
        # SMILES -> preserved
        assert result["canonical_smiles"].iloc[0] == "c1ccccc1"
        assert result["canonical_smiles"].iloc[1] == "C1CCCCC1"
        
        # Float -> float rounded
        assert result["pchembl_value"].iloc[0] == 1.235
        assert pd.isna(result["pchembl_value"].iloc[1])
        
        # Array -> serialized with normalization
        # "properties" uses default mode -> lower strings
        # {"key": "Val"} -> "key:val"
        assert result["properties"].iloc[0] == "key:val"
