# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
            {
                "source_keys": ["target_id", "target_type"],
                "reference_keys": ["target_id"],
            },
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


def test_delete_orphans_rejects_independently_limited_pipeline_deps() -> None:
    payload = {
        "schema_version": "1.0.0",
        "workflow": {
            "name": "limited_orphan_delete",
            "version": "1.0.0",
            "steps": [
                {
                    "kind": "pipeline",
                    "step_id": "chembl_assay_ingest",
                    "pipeline_name": "chembl_assay",
                    "run_options": {"limit": 250},
                },
                {
                    "kind": "pipeline",
                    "step_id": "chembl_target_ingest",
                    "pipeline_name": "chembl_target",
                    "run_options": {"limit": 250},
                },
                {
                    "kind": "transform",
                    "step_id": "reconcile_assay_target_orphans",
                    "transform_name": "reconcile_foreign_keys",
                    "depends_on": ["chembl_assay_ingest", "chembl_target_ingest"],
                    "config": _valid_config(),
                },
            ],
        },
    }

    with pytest.raises(ValidationError, match="run_options.limit"):
        WorkflowConfigFileSchema.model_validate(payload)


def test_chembl_core_workflow_loads_without_limited_orphan_delete() -> None:
    from bioetl.infrastructure.config.workflow_config_api import load_workflow_config

    workflow = load_workflow_config("chembl_core")
    steps = {step.step_id: step for step in workflow.steps}
    assert "reconcile_assay_target_orphans" in steps
    assert steps["chembl_activity_ingest"].run_options.limit is None
    assert steps["chembl_assay_ingest"].run_options.limit is None
    assert steps["chembl_target_ingest"].run_options.limit is None


def test_delete_orphans_rejects_limited_pipeline_behind_intermediary() -> None:
    payload = {
        "schema_version": "1.0.0",
        "workflow": {
            "name": "limited_orphan_delete_indirect",
            "version": "1.0.0",
            "steps": [
                {
                    "kind": "pipeline",
                    "step_id": "chembl_target_ingest",
                    "pipeline_name": "chembl_target",
                    "run_options": {"limit": 250},
                },
                {
                    "kind": "transform",
                    "step_id": "summarize_targets",
                    "transform_name": "reconcile_rows",
                    "depends_on": ["chembl_target_ingest"],
                    "config": {
                        "layer": "gold",
                        "left_table": "chembl.target",
                        "right_table": "chembl.target",
                        "left_columns": ["target_id"],
                        "right_columns": ["target_id"],
                        "left_primary_keys": ["target_id"],
                    },
                },
                {
                    "kind": "transform",
                    "step_id": "reconcile_assay_target_orphans",
                    "transform_name": "reconcile_foreign_keys",
                    "depends_on": ["summarize_targets"],
                    "config": _valid_config(),
                },
            ],
        },
    }

    with pytest.raises(ValidationError, match="run_options.limit"):
        WorkflowConfigFileSchema.model_validate(payload)


def test_cli_limit_override_scopes_delete_orphans_to_current_run() -> None:
    from bioetl.infrastructure.config.workflow_config_api import load_workflow_config
    from bioetl.interfaces.cli.commands._workflow_override_support import (
        apply_cli_overrides,
    )

    workflow = load_workflow_config("chembl_core")
    updated = apply_cli_overrides(workflow, limit=250)
    steps = {step.step_id: step for step in updated.steps}
    assert steps["chembl_assay_ingest"].run_options.limit == 250
    assert steps["chembl_target_ingest"].run_options.limit == 250
    reconcile = steps["reconcile_assay_target_orphans"]
    assert reconcile.config is not None
    assert reconcile.config["action"] == "delete_orphans"
    assert reconcile.config["source_scope"] == "current_run"


def test_cli_limit_override_allows_chembl_baseline_delete_orphans() -> None:
    from bioetl.infrastructure.config.workflow_config_api import load_workflow_config
    from bioetl.interfaces.cli.commands._workflow_override_support import (
        apply_cli_overrides,
    )

    workflow = load_workflow_config("chembl_baseline")
    updated = apply_cli_overrides(workflow, limit=1000)
    scoped = [
        step.step_id
        for step in updated.steps
        if getattr(step, "transform_name", None) == "reconcile_foreign_keys"
        and (step.config or {}).get("source_scope") == "current_run"
    ]
    assert scoped == [
        "reconcile_assay_target_orphans",
        "reconcile_assay_publication_orphans",
        "reconcile_target_assay_orphans",
        "reconcile_publication_assay_orphans",
    ]
