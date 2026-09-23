"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_iterable, _optional_text
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import (
    EFFECTIVE_CONFIG_ARTIFACT_REF,
    RUN_LEDGER_ARTIFACT_REF,
    RUN_MANIFEST_ARTIFACT_REF,
    RUN_MANIFEST_INSPECTION_DOC_PATH,
    RUN_MANIFEST_LEDGER_DOC_PATH,
    TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
)

__all__ = [
    "_run_instance_artifact_targets",
    "_run_instance_doc_targets",
    "_runtime_state_specs",
]


def _run_instance_doc_targets(spec: dict[str, object]) -> tuple[NodeKey, ...]:
    targets: list[NodeKey] = []
    source_path = _optional_text(spec.get("source_path"))
    if source_path is not None:
        targets.append(NodeKey("test_artifact", source_path))
    targets.extend(
        NodeKey("doc_artifact", str(doc_path))
        for doc_path in _as_iterable(spec.get("doc_paths"))
    )
    return tuple(targets)


def _run_instance_artifact_targets(spec: dict[str, object]) -> tuple[NodeKey, ...]:
    return tuple(
        NodeKey("control_plane_artifact_surface", str(artifact_name))
        for artifact_name in _as_iterable(spec.get("artifact_refs"))
    )


def _runtime_state_specs() -> tuple[dict[str, object], ...]:
    return (
        {
            "name": "manifest-left::active-window",
            "manifest_id": "manifest-left",
            "state_kind": "active_run",
            "state_status": "in_progress",
            "retry_count": 0,
            "lock_key": "pipeline:chembl_activity:run",
            "lock_scope": "pipeline_execution",
            "owner_hint": "run_manifest_service",
            "workflow_name": "tests",
            "artifact_refs": (RUN_MANIFEST_ARTIFACT_REF, EFFECTIVE_CONFIG_ARTIFACT_REF),
            "runtime_evidence_refs": ("run_manifest", "effective_config_artifact"),
            "doc_paths": (RUN_MANIFEST_INSPECTION_DOC_PATH,),
        },
        {
            "name": "manifest-chain-2::retry-window",
            "manifest_id": "manifest-chain-2",
            "state_kind": "retry_state",
            "state_status": "retrying",
            "retry_count": 1,
            "retry_strategy": "resume_failed_only",
            "workflow_name": "tests",
            "artifact_refs": (RUN_LEDGER_ARTIFACT_REF, EFFECTIVE_CONFIG_ARTIFACT_REF),
            "runtime_evidence_refs": ("run_ledger", "effective_config_artifact"),
            "doc_paths": (RUN_MANIFEST_LEDGER_DOC_PATH,),
        },
        {
            "name": "chembl_activity::composite-lock",
            "manifest_id": "manifest-composite-quarantine",
            "state_kind": "lock_state",
            "state_status": "locked",
            "retry_count": 0,
            "lock_key": "composite:activity:cross_validation",
            "lock_scope": "cross_validation_quarantine",
            "owner_hint": "workflow_lock_service",
            "workflow_name": "tests",
            "artifact_refs": (RUN_LEDGER_ARTIFACT_REF,),
            "runtime_evidence_refs": ("run_ledger",),
            "doc_paths": (TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,),
        },
    )
