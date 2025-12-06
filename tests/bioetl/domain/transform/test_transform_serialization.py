"""
Tests for serialization utilities.
"""

import pandas as pd

from bioetl.domain.transform.impl.serializer import serialize_dict, serialize_list


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
