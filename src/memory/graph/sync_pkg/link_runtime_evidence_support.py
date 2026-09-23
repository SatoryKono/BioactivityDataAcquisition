"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.run_instance_properties import _run_instance_properties
from memory.graph.sync_pkg.runtime_evidence_storage_refs import (
    _add_runtime_evidence_storage_artifact,
    _link_runtime_evidence_docs,
    _link_runtime_evidence_modules,
    _runtime_evidence_storage_refs,
)

__all__ = [
    "_add_run_instance_surface",
    "_add_runtime_evidence_storage_refs",
    "_link_runtime_evidence_support",
]


def _link_runtime_evidence_support(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_runtime_evidence_docs(snapshot, surface, spec["docs"])
    _link_runtime_evidence_modules(snapshot, surface, spec["modules"])


def _add_runtime_evidence_storage_refs(
    snapshot: GraphSnapshot,
    project: NodeKey,
    surface: NodeKey,
    *,
    evidence_name: str,
    storage_refs: object,
    today: str,
) -> None:
    for storage_ref, suffix, key_template in _runtime_evidence_storage_refs(
        storage_refs
    ):
        _add_runtime_evidence_storage_artifact(
            snapshot,
            project,
            surface,
            evidence_name=evidence_name,
            storage_ref=storage_ref,
            suffix=suffix,
            key_template=key_template,
            today=today,
        )


def _add_run_instance_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    spec: dict[str, object],
) -> NodeKey:
    manifest_id = str(spec["manifest_id"])
    surface = snapshot.add_node(
        "run_instance_surface",
        manifest_id,
        summary=f"Deterministic control-plane run instance surface for `{manifest_id}`.",
        **_run_instance_properties(spec, manifest_id=manifest_id),
        source_kind="run_instance_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_RUN_INSTANCE", surface, provenance="runtime_evidence"
    )
    return surface
