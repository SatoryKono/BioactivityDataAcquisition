import pandas as pd
import pytest
from unittest.mock import MagicMock

from bioetl.domain.transform.impl.normalize import (
    serialize_list,
    serialize_dict,
    NestedFieldNormalizerMixin,
)


class TestSerializeList:
    def test_none_or_empty(self):
        assert serialize_list(None) is None
        assert serialize_list([]) is None

    def test_primitives(self):
        assert serialize_list(["A", "B", 123]) == "A|B|123"
        assert serialize_list(["A"]) == "A"

    def test_dicts(self):
        input_list = [
            {"k1": "v1", "k2": 2},
            {"k3": "v3"}
        ]
        # Ожидаем объединение key:val
        # Порядок ключей в Py3.7+ сохраняется, если создавались так.
        expected = "k1:v1|k2:2|k3:v3"
        assert serialize_list(input_list) == expected

    def test_mixed_ignored(self):
        # Примитивы и словари
        input_list = ["A", {"k": "v"}, 1]
        assert serialize_list(input_list) == "A|k:v|1"

    def test_nested_ignored(self):
        # Вложенный список должен быть проигнорирован или приведен к строке?
        # Реализация: if isinstance(item, dict) -> serialize_dict, else -> str(item).
        # Значит список станет "[...]"
        input_list = ["A", ["B", "C"]]
        assert serialize_list(input_list) == "A|['B', 'C']"
        
        # А если внутри словаря вложенный список - он пропускается serialize_dict
        input_list_2 = [{"k": ["nested"]}]
        # serialize_dict вернет None (пусто), т.к. значение список
        assert serialize_list(input_list_2) is None


class TestSerializeDict:
    def test_none_or_empty(self):
        assert serialize_dict(None) is None
        assert serialize_dict({}) is None

    def test_simple_dict(self):
        d = {"a": 1, "b": "text"}
        assert serialize_dict(d) == "a:1|b:text"

    def test_nested_structures_skipped(self):
        d = {
            "a": 1,
            "list_val": [1, 2],
            "dict_val": {"x": 1},
            "b": 2
        }
        # list_val и dict_val пропускаются
        assert serialize_dict(d) == "a:1|b:2"

    def test_none_values_skipped(self):
        d = {"a": 1, "b": None}
        assert serialize_dict(d) == "a:1"


class TestNestedFieldNormalizerMixin:
    class PipelineMock(NestedFieldNormalizerMixin):
        def __init__(self, fields_config):
            self._config = MagicMock()
            self._config.fields = fields_config

    def test_normalize_nested_fields(self):
        fields_config = [
            {"name": "simple_col", "data_type": "string"},
            {"name": "array_col", "data_type": "array"},
            {"name": "object_col", "data_type": "object"},
            {"name": "missing_col", "data_type": "array"},  # not in df
        ]
        
        pipeline = self.PipelineMock(fields_config)
        
        df = pd.DataFrame({
            "simple_col": ["val1", "val2"],
            "array_col": [["a", "b"], None],
            "object_col": [{"k": "v"}, {}],  # {} -> None
            "extra_col": [1, 2]
        })
        
        result = pipeline.normalize_nested_fields(df)
        
        # simple_col не меняется
        assert result["simple_col"].tolist() == ["val1", "val2"]
        
        # array_col сериализуется
        assert result["array_col"].iloc[0] == "a|b"
        assert pd.isna(result["array_col"].iloc[1])
        
        # object_col сериализуется
        assert result["object_col"].iloc[0] == "k:v"
        assert pd.isna(result["object_col"].iloc[1]) # empty dict -> None
        
        # extra_col не тронут
        assert result["extra_col"].tolist() == [1, 2]

