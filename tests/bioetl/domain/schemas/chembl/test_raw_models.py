import pytest

from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel


def test_action_type_accepts_nested_dict() -> None:
    record = ActivityRawModel.model_validate(
        {
            "activity_id": 1,
            "standard_flag": True,
            "standard_value": 1.0,
            "action_type": {
                "action_type": "ANTAGONIST",
                "description": "NEGATIVE MODULATOR",
            },
        }
    )

    assert record.action_type == "ANTAGONIST"


def test_action_type_normalizes_list() -> None:
    record = ActivityRawModel.model_validate(
        {
            "activity_id": 2,
            "standard_flag": True,
            "standard_value": 1.0,
            "action_type": ["AGONIST", "MODULATOR"],
        }
    )

    assert record.action_type == "AGONIST;MODULATOR"

