from bioetl.domain.schemas.chembl.models import RawActivityPayload, _flatten_value


def test_flatten_dict_to_pipe_string():
    assert _flatten_value({"k1": "v1", "k2": 2}) == "k1:v1|k2:2"


def test_flatten_list_of_dicts_and_scalars():
    assert _flatten_value([{"a": 1}, "b", {"c": None}]) == "a:1|b"


def test_flatten_empty_or_none_returns_none():
    assert _flatten_value({}) is None
    assert _flatten_value([]) is None
    assert _flatten_value(None) is None


def test_activity_model_serializes_nested_fields():
    model = RawActivityPayload(
        activity_properties=[{"potency": 5, "unit": "uM"}, {"ignored": None}],
        ligand_efficiency={"le": 0.5, "note": None},
        standard_value=7.0,
    )

    payload = model.model_dump()

    # activity_properties and ligand_efficiency are in _BYPASS_FLATTEN_FIELDS
    # so they are not flattened by the model serializer
    assert payload["activity_properties"] == [{"potency": 5, "unit": "uM"}, {"ignored": None}]
    assert payload["ligand_efficiency"] == {"le": 0.5, "note": None}
    assert payload["standard_value"] == 7.0


def test_activity_model_keeps_none_for_empty_nested():
    model = RawActivityPayload(activity_properties=[], ligand_efficiency=None)

    payload = model.model_dump()

    # Empty list is kept as-is for bypass fields
    assert payload["activity_properties"] == []
    assert payload["ligand_efficiency"] is None
