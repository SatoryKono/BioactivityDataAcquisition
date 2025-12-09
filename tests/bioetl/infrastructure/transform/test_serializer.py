import pandas as pd

from bioetl.domain.transform.serializers import serialize_nested


def test_serialize_list_pipe_mode():
    assert serialize_nested(["a", "b"], mode="pipe") == "a|b"


def test_serialize_dict_pipe_mode_sorted_and_compact():
    assert serialize_nested({"b": 2, "a": 1}, mode="pipe") == "a:1|b:2"


def test_serialize_nested_structures_pipe_mode():
    payload = {"items": [1, 2], "meta": {"kind": "x"}}
    assert serialize_nested(payload, mode="pipe") == "items:1|2|meta:kind:x"


def test_serialize_json_mode_preserves_structure():
    payload = {"b": {"c": "d"}, "a": [1, 2]}
    assert serialize_nested(payload, mode="json") == '{"a":[1,2],"b":{"c":"d"}}'


def test_serialize_flat_mode_with_nested():
    payload = {"items": ["x", "y"], "extra": {"a": "b"}}
    assert serialize_nested(payload, mode="flat") == "extra=a=b,items=x,y"


def test_serialize_none_returns_empty_string():
    assert serialize_nested(None, mode="json") == ""
    assert serialize_nested(pd.NA, mode="pipe") == ""
