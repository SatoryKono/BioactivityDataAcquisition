from bioetl.infrastructure.clients.chembl.serializers import (
    _flatten_value,
    flatten_chembl_payload,
)


def test_flatten_dict_to_pipe_string():
    assert _flatten_value({"k1": "v1", "k2": 2}) == "k1:v1|k2:2"


def test_flatten_list_of_dicts_and_scalars():
    assert _flatten_value([{"a": 1}, "b", {"c": None}]) == "a:1|b"


def test_flatten_empty_or_none_returns_none():
    assert _flatten_value({}) is None
    assert _flatten_value([]) is None
    assert _flatten_value(None) is None


def test_flatten_payload_keeps_bypass_fields():
    payload = flatten_chembl_payload(
        {
            "activity_properties": [{"potency": 5, "unit": "uM"}, {"ignored": None}],
            "ligand_efficiency": {"le": 0.5, "note": None},
            "standard_value": 7.0,
        }
    )

    # activity_properties and ligand_efficiency are bypassed and kept as-is
    assert payload["activity_properties"] == [
        {"potency": 5, "unit": "uM"},
        {"ignored": None},
    ]
    assert payload["ligand_efficiency"] == {"le": 0.5, "note": None}
    assert payload["standard_value"] == 7.0


def test_flatten_payload_keeps_empty_for_bypass_fields():
    payload = flatten_chembl_payload(
        {"activity_properties": [], "ligand_efficiency": None}
    )

    assert payload["activity_properties"] == []
    assert payload["ligand_efficiency"] is None
