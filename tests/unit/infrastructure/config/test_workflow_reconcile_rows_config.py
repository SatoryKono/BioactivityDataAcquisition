"""Unit tests for reconcile_rows workflow config validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.domain.workflow import TransformStepConfig
from bioetl.infrastructure.schemas.workflow_config import (
    WorkflowConfigFileSchema,
    validate_workflow_config_payload,
)

pytestmark = pytest.mark.unit


def _payload(config: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "workflow": {
            "name": "reconcile_rows_smoke",
            "version": "1.0.0",
            "steps": [
                {
                    "kind": "transform",
                    "step_id": "reconcile_activity_rows",
                    "transform_name": "reconcile_rows",
                    "config": config,
                }
            ],
        },
    }


def _valid_config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "layer": "silver",
        "left_table": " chembl.activity ",
        "right_table": "chembl.target",
        "left_columns": [" target_id "],
        "right_columns": ["target_id"],
        "left_primary_keys": [" activity_id "],
        "nulls_equal": False,
        "type_policy": "strict",
        "report_only": True,
        "preserve_order": True,
    }
    config.update(overrides)
    return config


def test_reconcile_rows_config_is_normalized_into_domain_config() -> None:
    schema = validate_workflow_config_payload(_payload(_valid_config()))

    workflow = schema.to_domain()

    step = workflow.steps[0]
    assert isinstance(step, TransformStepConfig)
    assert step.config == {
        "layer": "silver",
        "left_table": "chembl.activity",
        "right_table": "chembl.target",
        "left_columns": ["target_id"],
        "right_columns": ["target_id"],
        "left_primary_keys": ["activity_id"],
        "nulls_equal": False,
        "type_policy": "strict",
        "report_only": True,
        "preserve_order": True,
    }


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"layer": "bronze"}, "layer"),
        (
            {"left_columns": ["target_id", "assay_id"], "right_columns": ["target_id"]},
            "same length",
        ),
        ({"left_columns": ["target_id", " target_id "]}, "duplicates"),
        ({"type_policy": "coerce"}, "type_policy"),
        ({"unexpected": True}, "Extra inputs"),
    ],
)
def test_reconcile_rows_config_rejects_invalid_contract(
    override: dict[str, object],
    match: str,
) -> None:
    config = _valid_config()
    config.update(override)

    with pytest.raises(ValidationError, match=match):
        WorkflowConfigFileSchema.model_validate(_payload(config))
