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
        "source_keys": ["target_id"],
        "reference_keys": ["target_id"],
        "action": "delete_orphans",
        "nulls_equal": False,
        "scanned_rows": 3,
        "retained_rows": 2,
        "orphan_rows_deleted": 1,
        "mutated": True,
    }
