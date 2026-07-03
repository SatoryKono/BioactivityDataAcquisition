"""Unit tests for the workflow row reconciliation transform."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from bioetl.application.workflow.transforms import WorkflowTransformRuntimeContext
from bioetl.application.workflow.transforms.reconcile_rows import (
    _build_config,
    build_reconcile_rows_executor,
)
from bioetl.domain.ports import (
    RowReconciliationConfig,
    RowReconciliationLayer,
    RowReconciliationResult,
    RowReconciliationTypePolicy,
)
from bioetl.domain.workflow import TransformStepConfig, WorkflowTransformSpec

pytestmark = pytest.mark.unit


@dataclass
class _RecordingPort:
    config: RowReconciliationConfig | None = None

    async def reconcile_rows(
        self,
        config: RowReconciliationConfig,
    ) -> RowReconciliationResult:
        self.config = config
        return RowReconciliationResult(
            layer=RowReconciliationLayer(config.layer),
            left_table=config.left_table,
            right_table=config.right_table,
            left_columns=config.left_columns,
            right_columns=config.right_columns,
            left_primary_keys=config.left_primary_keys,
            input_left_rows=4,
            input_right_rows=3,
            kept_rows=2,
            excluded_rows=2,
            null_key_rows_left=1,
            null_key_rows_right=1,
            distinct_right_keys=2,
            rows=({"activity_id": "A1"}, {"activity_id": "A2"}),
            implementation="test_reconcile_rows",
            nulls_equal=config.nulls_equal,
            type_policy=RowReconciliationTypePolicy(config.type_policy),
            preserve_order=config.preserve_order,
            report_only=config.report_only,
            mutated=False,
        )


def _spec() -> WorkflowTransformSpec:
    return WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_activity_rows",
            transform_name="reconcile_rows",
            config={
                "layer": "silver",
                "left_table": "chembl.activity",
                "right_table": "chembl.target",
                "left_columns": ["target_id"],
                "right_columns": ["target_id"],
                "left_primary_keys": ["activity_id"],
                "nulls_equal": True,
                "type_policy": "strict",
                "report_only": True,
                "preserve_order": True,
            },
        )
    )


def test_build_config_preserves_workflow_context_and_flags() -> None:
    config = _build_config(_spec(), workflow_name="nightly")

    assert config.layer is RowReconciliationLayer.SILVER
    assert config.left_table == "chembl.activity"
    assert config.right_table == "chembl.target"
    assert config.left_columns == ("target_id",)
    assert config.right_columns == ("target_id",)
    assert config.left_primary_keys == ("activity_id",)
    assert config.nulls_equal is True
    assert config.workflow_name == "nightly"


@pytest.mark.asyncio
async def test_executor_returns_deterministic_report_without_rows() -> None:
    port = _RecordingPort()
    executor = build_reconcile_rows_executor(port)
    spec = _spec()

    payload = await executor(
        spec,
        upstream_outputs={"ignored": object()},
        runtime_context=WorkflowTransformRuntimeContext(workflow_name="nightly"),
    )

    assert port.config is not None
    assert port.config.workflow_name == "nightly"
    assert "rows" not in payload
    assert payload == {
        "transform_name": "reconcile_rows",
        "fingerprint": spec.fingerprint,
        "implementation": "test_reconcile_rows",
        "layer": "silver",
        "left_table": "chembl.activity",
        "right_table": "chembl.target",
        "left_columns": ["target_id"],
        "right_columns": ["target_id"],
        "left_primary_keys": ["activity_id"],
        "input_left_rows": 4,
        "input_right_rows": 3,
        "kept_rows": 2,
        "excluded_rows": 2,
        "null_key_rows_left": 1,
        "null_key_rows_right": 1,
        "distinct_right_keys": 2,
        "nulls_equal": True,
        "type_policy": "strict",
        "preserve_order": True,
        "report_only": True,
        "mutated": False,
    }
