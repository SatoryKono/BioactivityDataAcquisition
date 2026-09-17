"""Residual branch coverage for reconcile_foreign_keys in #10518."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
    _build_request,
    _run_ids_from_upstream,
    build_reconcile_foreign_keys_executor,
)
from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationResult,
)
from bioetl.domain.workflow import TransformStepConfig, WorkflowTransformSpec


pytestmark = pytest.mark.unit


def _spec(**config: object) -> WorkflowTransformSpec:
    base: dict[str, object] = {
        "source_table": "chembl_assay",
        "reference_table": "chembl_target",
        "source_key": "target_id",
        "reference_key": "target_id",
        "primary_keys": ["assay_id"],
        "action": "delete_orphans",
    }
    base.update(config)
    return WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="reconcile_residual",
            transform_name="reconcile_foreign_keys",
            config=base,
        )
    )


@dataclass
class _MutatingPort:
    async def reconcile_foreign_keys(
        self, request: object
    ) -> ForeignKeyReconciliationResult:
        return ForeignKeyReconciliationResult(
            source_table="chembl_assay",
            reference_table="chembl_target",
            source_key="target_id",
            reference_key="target_id",
            action="delete_orphans",
            scanned_rows=3,
            retained_rows=2,
            orphan_rows_deleted=1,
            mutated=True,
        )


@dataclass
class _BlockedSnapshotPort:
    async def reconcile_foreign_keys(
        self, request: object
    ) -> ForeignKeyReconciliationResult:
        return ForeignKeyReconciliationResult(
            source_table="chembl_assay",
            reference_table="chembl_target",
            source_key="target_id",
            reference_key="target_id",
            action="delete_orphans",
            scanned_rows=4,
            retained_rows=4,
            orphan_rows_deleted=0,
            mutated=False,
            mutation_blocked_reason="storage_blocked",
            source_snapshot={"kept": 2},
        )


@pytest.mark.asyncio
async def test_payload_carries_blocked_reason_and_snapshot() -> None:
    executor = build_reconcile_foreign_keys_executor(_BlockedSnapshotPort())

    payload = await executor(_spec(), upstream_outputs={})

    assert payload["mutation_blocked_reason"] == "storage_blocked"
    assert payload["source_snapshot"] == {"kept": 2}


@dataclass
class _ArtifactSink:
    refs: tuple[dict[str, object], ...] = ({"artifact": "reconcile/a"},)
    context: object | None = None

    def write_reconcile_result_artifact(
        self, *, context: object, payload: object
    ) -> tuple[dict[str, object], ...]:
        self.context = context
        return self.refs


@pytest.mark.asyncio
async def test_payload_includes_artifact_refs_when_sink_writes() -> None:
    sink = _ArtifactSink()
    runtime_context = SimpleNamespace(
        artifact_sink=sink,
        workflow_name="chembl_baseline",
        workflow_run_id="run-7",
        manifest_id="manifest-7",
        debug_export_enabled=False,
        debug_export_dir=None,
        created_at=None,
    )
    executor = build_reconcile_foreign_keys_executor(_MutatingPort())

    payload = await executor(
        _spec(), upstream_outputs={}, runtime_context=runtime_context
    )

    assert payload["artifact_refs"] == [{"artifact": "reconcile/a"}]
    assert runtime_context is not None


@pytest.mark.asyncio
async def test_artifact_persistence_skipped_without_identifiers() -> None:
    logger = SimpleNamespace(debug_calls=[])
    logger.debug = lambda *args, **kwargs: logger.debug_calls.append((args, kwargs))
    executor = build_reconcile_foreign_keys_executor(_MutatingPort())

    payload = await executor(
        _spec(),
        upstream_outputs={},
        runtime_context=SimpleNamespace(
            artifact_sink=_ArtifactSink(),
            workflow_name=None,
            workflow_run_id="run-7",
            manifest_id="manifest-7",
            logger=logger,
        ),
    )
    assert "artifact_refs" not in payload
    assert len(logger.debug_calls) == 1

    payload_no_logger = await executor(
        _spec(),
        upstream_outputs={},
        runtime_context=SimpleNamespace(
            artifact_sink=_ArtifactSink(),
            workflow_name="chembl_baseline",
            workflow_run_id=None,
            manifest_id="manifest-7",
        ),
    )
    assert "artifact_refs" not in payload_no_logger


@pytest.mark.asyncio
async def test_artifact_persistence_skipped_when_writer_missing() -> None:
    executor = build_reconcile_foreign_keys_executor(_MutatingPort())

    payload = await executor(
        _spec(),
        upstream_outputs={},
        runtime_context=SimpleNamespace(
            artifact_sink=SimpleNamespace(),
            workflow_name="chembl_baseline",
            workflow_run_id="run-7",
            manifest_id="manifest-7",
        ),
    )

    assert "artifact_refs" not in payload


def test_build_request_rejects_bad_source_scope() -> None:
    with pytest.raises(ValueError, match="must be all_current or current_run"):
        _build_request(_spec(source_scope="everything"))


def test_run_ids_from_non_mapping_payload_object() -> None:
    assert _run_ids_from_upstream(
        {"step": SimpleNamespace(run_id="run-9")},
        workflow_run_id=None,
    ) == ("run-9",)


def test_run_ids_respect_depends_on_filter() -> None:
    assert _run_ids_from_upstream(
        {
            "keep": {"run_id": "run-keep"},
            "drop": {"run_id": "run-drop"},
        },
        workflow_run_id=None,
        depends_on=("keep",),
    ) == ("run-keep",)


def test_completeness_unproven_without_evidence() -> None:
    request = _build_request(_spec())

    assert request.reference_completeness == "unproven"
    assert request.reference_identity is None
    assert request.completeness_evidence_ref is None


def test_completeness_unproven_on_identity_mismatch() -> None:
    request = _build_request(
        _spec(
            reference_completeness_evidence={
                "status": "complete",
                "reference_identity": "other_table",
                "snapshot_version": "v3",
                "evidence_ref": "ref-3",
            }
        )
    )

    assert request.reference_completeness == "unproven"
    assert request.reference_identity == "other_table"
    assert request.reference_snapshot_version == "v3"
    assert request.completeness_evidence_ref == "ref-3"


def test_completeness_unproven_when_upstream_evidence_never_matches() -> None:
    request = _build_request(
        _spec(),
        upstream_outputs={
            "scalar": 42,
            "bare": {"outputs": 1},
            "wrong": {
                "reference_completeness_evidence": {
                    "status": "complete",
                    "reference_identity": "other_table",
                    "evidence_ref": "ref-x",
                }
            },
        },
    )

    assert request.reference_completeness == "unproven"


def test_completeness_complete_from_upstream_evidence() -> None:
    request = _build_request(
        _spec(),
        upstream_outputs={
            "check": {
                "reference_completeness_evidence": {
                    "status": "complete",
                    "reference_identity": "chembl_target",
                    "snapshot_version": "v1",
                    "evidence_ref": "ref-1",
                }
            },
        },
    )

    assert request.reference_completeness == "complete"
    assert request.reference_identity == "chembl_target"
    assert request.completeness_evidence_ref == "ref-1"


def test_build_request_rejects_blank_source_table() -> None:
    with pytest.raises(ValueError, match=r"requires config.source_table"):
        _build_request(_spec(source_table="  "))


def test_build_request_rejects_unknown_layer() -> None:
    with pytest.raises(ValueError, match="as 'silver' or 'gold'"):
        _build_request(_spec(source_layer="bronze"))


def test_build_request_rejects_non_list_key_tuple() -> None:
    with pytest.raises(ValueError, match="as a non-empty list"):
        _build_request(_spec(source_keys="target_id"))


def test_build_request_rejects_blank_primary_key_entries() -> None:
    with pytest.raises(ValueError, match="cannot contain blank entries"):
        _build_request(_spec(primary_keys=["assay_id", "  "]))


def test_build_request_rejects_blank_key_tuple_entries() -> None:
    with pytest.raises(ValueError, match="cannot contain blank entries"):
        _build_request(
            _spec(
                source_keys=["target_id", " "],
                reference_keys=["target_id", "target_type"],
            )
        )
