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
"""Tests for file-backed workflow transform artifact persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from bioetl.application.services.workflow.workflow_transform_artifacts import (
    WorkflowTransformArtifactContext,
)
from bioetl.infrastructure.control_plane.file_workflow_transform_artifact_store import (
    FileWorkflowTransformArtifactStore,
)

pytestmark = pytest.mark.unit


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


def test_workflow_transform_artifact_store_writes_result_and_debug_refs(
    tmp_path,
) -> None:
    store = FileWorkflowTransformArtifactStore(
        base_path=tmp_path / "control" / "workflow_transform_results",
        clock=_FixedClock(),
    )
    context = WorkflowTransformArtifactContext(
        workflow_name="chembl_baseline",
        workflow_run_id="workflow-run-1",
        manifest_id="manifest-1",
        step_id="reconcile_target_assay_orphans",
        transform_name="reconcile_foreign_keys",
        debug_export_enabled=True,
        debug_export_dir=str(tmp_path / "debug_exports"),
        created_at=datetime(2026, 7, 7, 12, 1, tzinfo=UTC),
    )
    request = SimpleNamespace(
        source_table="chembl.target",
        reference_table="chembl.assay",
        source_layer="gold",
        reference_layer="gold",
        effective_source_keys=("target_id",),
        primary_keys=("target_id",),
    )
    result = SimpleNamespace(
        mutation_layer="gold",
        scanned_rows=2,
        retained_rows=1,
        orphan_rows_deleted=1,
        mutated=True,
        dry_run=False,
        would_mutate=False,
        mutation_mode="gold_scd2_expiry",
        quarantine_rows_written=1,
        quarantine_error_code="FILTERED_OUT_GOLD",
    )

    debug_refs = store.write_reconcile_debug_artifacts(
        context=context,
        request=request,
        result=result,
        retained_rows=({"target_id": "CHEMBL_T1"},),
        orphan_rows=({"target_id": "CHEMBL_T999", "name": "orphan"},),
    )
    refs = store.write_reconcile_result_artifact(
        context=context,
        payload={
            "workflow_name": "chembl_baseline",
            "workflow_run_id": "workflow-run-1",
            "manifest_id": "manifest-1",
            "step_id": "reconcile_target_assay_orphans",
            "transform_name": "reconcile_foreign_keys",
            "orphan_rows_deleted": 1,
        },
    )

    result_path = (
        tmp_path
        / "control"
        / "workflow_transform_results"
        / "workflow-run-1"
        / "reconcile_target_assay_orphans"
        / "result.json"
    )
    debug_root = (
        tmp_path
        / "debug_exports"
        / "chembl_baseline"
        / "workflow_transforms"
        / "workflow-run-1"
        / "reconcile_target_assay_orphans"
    )
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))

    assert result_path.exists()
    assert (debug_root / "orphan_rows.csv").exists()
    assert len(debug_refs) == 4
    assert len(refs) == 5
    assert result_payload["schema_version"] == 1
    assert result_payload["artifact_refs"] == [dict(ref) for ref in debug_refs]
