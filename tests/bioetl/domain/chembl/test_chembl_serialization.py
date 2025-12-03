from bioetl.domain.schemas.chembl.models import ActivityModel, _flatten_value


def test_flatten_dict_to_pipe_string():
    assert _flatten_value({"k1": "v1", "k2": 2}) == "k1:v1|k2:2"


def test_flatten_list_of_dicts_and_scalars():
    assert _flatten_value([{"a": 1}, "b", {"c": None}]) == "a:1|b"


def test_flatten_empty_or_none_returns_none():
    assert _flatten_value({}) is None
    assert _flatten_value([]) is None
    assert _flatten_value(None) is None


def test_activity_model_serializes_nested_fields():
    model = ActivityModel(
        activity_properties=[{"potency": 5, "unit": "uM"}, {"ignored": None}],
        ligand_efficiency={"le": 0.5, "note": None},
        standard_value=7.0,
    )

    payload = model.model_dump()

    assert payload["activity_properties"] == "potency:5|unit:uM"
    assert payload["ligand_efficiency"] == "le:0.5"
    assert payload["standard_value"] == 7.0


def test_activity_model_keeps_none_for_empty_nested():
    model = ActivityModel(activity_properties=[], ligand_efficiency=None)

    payload = model.model_dump()

    assert payload["activity_properties"] is None
    assert payload["ligand_efficiency"] is None

