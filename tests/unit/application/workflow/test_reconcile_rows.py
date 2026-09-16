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
"""Unit tests for the workflow row reconciliation transform."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.workflow.transforms import WorkflowTransformRuntimeContext
from bioetl.application.workflow.transforms.reconcile_rows import (
    _build_config,
    _optional_runtime_str,
    _persist_reconcile_rows_artifact,
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


def _spec_with_config(config: dict[str, object]) -> WorkflowTransformSpec:
    return WorkflowTransformSpec(
        step_id="reconcile_activity_rows",
        transform_name="reconcile_rows",
        config=config,
    )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"left_columns": ["a", "b"]}, "matching lengths"),
        ({"left_primary_keys": ["a", "b"]}, "length to be <="),
        ({"layer": " "}, "config.layer"),
        ({"left_columns": "target_id"}, "config.left_columns as a non-empty list"),
        ({"left_columns": [" "]}, r"config\.left_columns\[0\]"),
        ({"left_columns": []}, "config.left_columns as a non-empty list"),
    ],
)
def test_build_config_rejects_invalid_contracts(
    change: dict[str, object], message: str
) -> None:
    config = dict(_spec().config or {})
    config.update(change)
    with pytest.raises(ValueError, match=message):
        _build_config(_spec_with_config(config))


@pytest.mark.asyncio
async def test_executor_persists_artifact_refs_when_runtime_identity_is_complete() -> None:
    sink = MagicMock()
    sink.write_reconcile_result_artifact.return_value = (
        {"kind": "reconcile_result", "ref": "artifact.json"},
    )
    context = WorkflowTransformRuntimeContext(
        workflow_name="nightly",
        workflow_run_id="workflow-run-1",
        manifest_id="manifest-1",
        debug_export_enabled=True,
        debug_export_dir=123,
        artifact_sink=sink,
    )

    payload = await build_reconcile_rows_executor(_RecordingPort())(
        _spec(), upstream_outputs={}, runtime_context=context
    )

    assert payload["artifact_refs"] == [
        {"kind": "reconcile_result", "ref": "artifact.json"}
    ]
    artifact_context = sink.write_reconcile_result_artifact.call_args.kwargs["context"]
    assert artifact_context.workflow_name == "nightly"
    assert artifact_context.debug_export_dir == "123"


@pytest.mark.asyncio
async def test_persist_artifact_skips_absent_runtime_sink_and_writer() -> None:
    spec = _spec()
    assert (
        await _persist_reconcile_rows_artifact(None, spec=spec, payload={}) == ()
    )
    assert (
        await _persist_reconcile_rows_artifact(
            WorkflowTransformRuntimeContext(workflow_name="nightly"),
            spec=spec,
            payload={},
        )
        == ()
    )
    assert (
        await _persist_reconcile_rows_artifact(
            SimpleNamespace(
                artifact_sink=SimpleNamespace(write_reconcile_result_artifact=None),
                workflow_name="nightly",
                workflow_run_id="run-1",
                manifest_id="manifest-1",
            ),
            spec=spec,
            payload={},
        )
        == ()
    )


@pytest.mark.asyncio
async def test_persist_artifact_logs_missing_runtime_identifiers() -> None:
    logger = MagicMock()
    context = SimpleNamespace(
        artifact_sink=MagicMock(),
        workflow_name="nightly",
        workflow_run_id=None,
        manifest_id="manifest-1",
        logger=logger,
    )
    assert (
        await _persist_reconcile_rows_artifact(context, spec=_spec(), payload={}) == ()
    )
    logger.debug.assert_called_once()


def test_optional_runtime_str_handles_missing_context_and_value() -> None:
    assert _optional_runtime_str(None, "debug_export_dir") is None
    assert _optional_runtime_str(SimpleNamespace(), "debug_export_dir") is None
    assert (
        _optional_runtime_str(SimpleNamespace(debug_export_dir=123), "debug_export_dir")
        == "123"
    )
