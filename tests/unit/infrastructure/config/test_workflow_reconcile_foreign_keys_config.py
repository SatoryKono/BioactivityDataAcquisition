"""Unit tests for reconcile_foreign_keys workflow config validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.domain.workflow import TransformStepConfig
from bioetl.infrastructure.schemas.workflow_config import WorkflowConfigFileSchema

pytestmark = pytest.mark.unit


def _payload(config: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "workflow": {
            "name": "reconcile_foreign_keys_smoke",
            "version": "1.0.0",
            "steps": [
                {
                    "kind": "transform",
                    "step_id": "reconcile_assay_target_orphans",
                    "transform_name": "reconcile_foreign_keys",
                    "config": config,
                }
            ],
        },
    }


def _valid_config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "source_layer": "gold",
        "reference_layer": "gold",
        "mutation_layer": "gold",
        "source_table": " chembl.assay ",
        "reference_table": "chembl.target",
        "source_key": " target_id ",
        "reference_key": "target_id",
        "primary_keys": [" assay_id "],
        "action": "delete_orphans",
        "nulls_equal": False,
    }
    config.update(overrides)
    return config


def test_reconcile_foreign_keys_config_is_normalized_into_domain_config() -> None:
    schema = WorkflowConfigFileSchema.model_validate(_payload(_valid_config()))

    workflow = schema.to_domain()

    step = workflow.steps[0]
    assert isinstance(step, TransformStepConfig)
    assert step.config == {
        "source_layer": "gold",
        "reference_layer": "gold",
        "mutation_layer": "gold",
        "source_table": "chembl.assay",
        "reference_table": "chembl.target",
        "source_key": "target_id",
        "reference_key": "target_id",
        "primary_keys": ["assay_id"],
        "action": "delete_orphans",
        "nulls_equal": False,
    }


def test_reconcile_foreign_keys_config_preserves_silver_defaults() -> None:
    config = _valid_config()
    config.pop("source_layer")
    config.pop("reference_layer")
    config.pop("mutation_layer")

    schema = WorkflowConfigFileSchema.model_validate(_payload(config))

    step = schema.to_domain().steps[0]
    assert isinstance(step, TransformStepConfig)
    assert step.config is not None
    assert step.config["source_layer"] == "silver"
    assert step.config["reference_layer"] == "silver"
    assert "mutation_layer" not in step.config


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"source_layer": "bronze"}, "source_layer"),
        ({"reference_layer": "bronze"}, "reference_layer"),
        ({"mutation_layer": "silver"}, "mutation_layer must match source_layer"),
        ({"action": "noop"}, "action"),
        ({"primary_keys": []}, "primary_keys"),
        ({"source_key": None}, "source_key and reference_key together"),
        ({"reference_key": None}, "source_key and reference_key together"),
        (
            {"source_keys": ["target_id", "target_type"], "reference_keys": ["target_id"]},
            "same length",
        ),
        ({"unexpected": True}, "Extra inputs"),
    ],
)
def test_reconcile_foreign_keys_config_rejects_invalid_contract(
    override: dict[str, object],
    match: str,
) -> None:
    config = _valid_config()
    config.update(override)

    with pytest.raises(ValidationError, match=match):
        WorkflowConfigFileSchema.model_validate(_payload(config))
