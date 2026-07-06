"""Unit tests for the workflow foreign-key reconciliation transform."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
    _build_request,
    build_reconcile_foreign_keys_executor,
)
from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
)
from bioetl.domain.workflow import TransformStepConfig, WorkflowTransformSpec


pytestmark = pytest.mark.unit


@dataclass
class _RecordingPort:
    request: ForeignKeyReconciliationRequest | None = None

    async def reconcile_foreign_keys(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        self.request = request
        return ForeignKeyReconciliationResult(
            source_table=request.source_table,
            reference_table=request.reference_table,
            source_key=request.source_key,
            reference_key=request.reference_key,
            action=request.action,
            scanned_rows=3,
            retained_rows=2,
            orphan_rows_deleted=1,
            mutated=True,
            source_layer=request.source_layer,
            reference_layer=request.reference_layer,
            mutation_layer=request.effective_mutation_layer,
            dry_run=request.dry_run,
            would_mutate=False,
        )


@dataclass
class _RecordingRuntimeContext:
    dry_run: bool = False
    workflow_name: str | None = None
    calls: list[dict[str, object]] | None = None

    def record_destructive_commit(self, **details: object) -> None:
        if self.calls is None:
            self.calls = []
        self.calls.append(dict(details))


@dataclass
class _WouldMutatePort:
    async def reconcile_foreign_keys(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        return ForeignKeyReconciliationResult(
            source_table=request.source_table,
            reference_table=request.reference_table,
            source_key=request.source_key,
            reference_key=request.reference_key,
            action=request.action,
            scanned_rows=5,
            retained_rows=5,
            orphan_rows_deleted=0,
            mutated=False,
            source_layer=request.source_layer,
            reference_layer=request.reference_layer,
            mutation_layer=request.effective_mutation_layer,
            dry_run=True,
            would_mutate=True,
        )


def test_build_request_supports_composite_keys_and_null_policy() -> None:
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_assay_target_orphans",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_keys": ["target_id", "target_type"],
                "reference_keys": ["target_id", "target_type"],
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
                "nulls_equal": True,
            },
        )
    )

    request = _build_request(spec)

    assert request.source_key == "target_id"
    assert request.reference_key == "target_id"
    assert request.effective_source_keys == ("target_id", "target_type")
    assert request.effective_reference_keys == ("target_id", "target_type")
    assert request.nulls_equal is True
    assert request.dry_run is False
    assert request.source_layer == "silver"
    assert request.reference_layer == "silver"
    assert request.effective_mutation_layer == "silver"


def test_build_request_parses_gold_layers() -> None:
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_assay_target_orphans",
            transform_name="reconcile_foreign_keys",
            config={
                "source_layer": "gold",
                "reference_layer": "gold",
                "mutation_layer": "gold",
                "source_table": "chembl.assay",
                "reference_table": "chembl.target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
            },
        )
    )

    request = _build_request(spec)

    assert request.source_layer == "gold"
    assert request.reference_layer == "gold"
    assert request.effective_mutation_layer == "gold"


def test_build_request_requires_delete_orphans_action() -> None:
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_invalid_action",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "primary_keys": ["assay_id"],
                "action": "noop",
            },
        )
    )

    with pytest.raises(ValueError, match="supports only action=delete_orphans"):
        _build_request(spec)


def test_build_request_requires_non_empty_primary_keys() -> None:
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_missing_primary_keys",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "primary_keys": [],
                "action": "delete_orphans",
            },
        )
    )

    with pytest.raises(ValueError, match=r"requires config.primary_keys"):
        _build_request(spec)


def test_build_request_requires_matching_composite_key_lengths() -> None:
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_mismatched_keys",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_keys": ["target_id", "target_type"],
                "reference_keys": ["target_id"],
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
            },
        )
    )

    with pytest.raises(ValueError, match="same length"):
        _build_request(spec)


def test_build_request_requires_source_and_reference_key_lists_together() -> None:
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_half_composite_key",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_keys": ["target_id"],
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
            },
        )
    )

    with pytest.raises(ValueError, match="requires source_keys and reference_keys"):
        _build_request(spec)


@pytest.mark.asyncio
async def test_executor_returns_serializable_metadata_only() -> None:
    port = _RecordingPort()
    executor = build_reconcile_foreign_keys_executor(port)
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_assay_target_orphans",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
            },
        )
    )

    payload = await executor(spec, upstream_outputs={})

    assert port.request is not None
    assert payload == {
        "transform_name": "reconcile_foreign_keys",
        "fingerprint": spec.fingerprint,
        "source_table": "chembl_assay",
        "reference_table": "chembl_target",
        "source_key": "target_id",
        "reference_key": "target_id",
        "source_layer": "silver",
        "reference_layer": "silver",
        "mutation_layer": "silver",
        "source_keys": ["target_id"],
        "reference_keys": ["target_id"],
        "action": "delete_orphans",
        "nulls_equal": False,
        "scanned_rows": 3,
        "retained_rows": 2,
        "orphan_rows_deleted": 1,
        "mutated": True,
        "dry_run": False,
        "would_mutate": False,
    }


@pytest.mark.asyncio
async def test_executor_passes_workflow_dry_run_to_reconciliation_request() -> None:
    port = _RecordingPort()
    executor = build_reconcile_foreign_keys_executor(port)
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_assay_target_orphans",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
            },
        )
    )

    payload = await executor(
        spec,
        upstream_outputs={},
        runtime_context=type("_RuntimeContext", (), {"dry_run": True})(),
    )

    assert port.request is not None
    assert port.request.dry_run is True
    assert payload["dry_run"] is True
    assert payload["would_mutate"] is False


@pytest.mark.asyncio
async def test_executor_passes_workflow_name_to_request() -> None:
    port = _RecordingPort()
    executor = build_reconcile_foreign_keys_executor(port)
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_assay_target_orphans",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
            },
        )
    )

    await executor(
        spec,
        upstream_outputs={},
        runtime_context=type(
            "_RuntimeContext",
            (),
            {
                "dry_run": False,
                "workflow_name": "chembl_baseline",
            },
        )(),
    )

    assert port.request is not None
    assert port.request.workflow_name == "chembl_baseline"


@pytest.mark.asyncio
async def test_executor_marks_mutation_blocked_reason_for_dry_run_mutation() -> None:
    executor = build_reconcile_foreign_keys_executor(_WouldMutatePort())
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_dry_run_block",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
            },
        )
    )

    payload = await executor(spec, upstream_outputs={})

    assert payload["dry_run"] is True
    assert payload["would_mutate"] is True
    assert payload["mutation_blocked_reason"] == "workflow_dry_run"


@pytest.mark.asyncio
async def test_executor_records_destructive_commit_when_mutation_persists() -> None:
    port = _RecordingPort()
    executor = build_reconcile_foreign_keys_executor(port)
    spec = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_record_commit",
            transform_name="reconcile_foreign_keys",
            config={
                "source_table": "chembl_assay",
                "reference_table": "chembl_target",
                "source_key": "target_id",
                "reference_key": "target_id",
                "primary_keys": ["assay_id"],
                "action": "delete_orphans",
            },
        )
    )
    runtime_context = _RecordingRuntimeContext(
        dry_run=False,
        workflow_name="chembl_baseline",
    )

    payload = await executor(
        spec,
        upstream_outputs={},
        runtime_context=runtime_context,
    )

    assert payload["mutated"] is True
    assert runtime_context.calls is not None
    assert len(runtime_context.calls) == 1
    call = runtime_context.calls[0]
    assert call["step_id"] == "reconcile_record_commit"
    assert call["transform_name"] == "reconcile_foreign_keys"
    assert call["fingerprint"] == spec.fingerprint
    assert call["details"] == payload
