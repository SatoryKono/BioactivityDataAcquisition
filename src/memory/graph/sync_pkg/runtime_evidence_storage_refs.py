"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Iterable

from memory.graph.sync_pkg._core_models import (
    ControlPlaneArtifactSpec,
    NodeKey,
    StorageSurfaceSpec,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.merge_field_validation_item import _add_storage_surface
from memory.graph.sync_pkg.storage_surface_format import (
    RUN_INSTANCE_SPECS,
    _run_instance_definition_spec,
    _storage_surface_format,
)
from memory.graph.sync_pkg.storage_surface_state import (
    _add_control_plane_artifact_surface,
)

__all__ = [
    "_add_runtime_evidence_storage_artifact",
    "_control_plane_run_instance_specs",
    "_iter_object_values",
    "_link_runtime_evidence_docs",
    "_link_runtime_evidence_modules",
    "_runtime_evidence_storage_refs",
]


def _runtime_evidence_storage_refs(
    storage_refs: object,
) -> tuple[tuple[str, str, str], ...]:
    if not isinstance(storage_refs, Iterable) or isinstance(
        storage_refs, str | bytes | dict
    ):
        return ()
    refs: list[tuple[str, str, str]] = []
    for candidate in storage_refs:
        if not isinstance(candidate, tuple | list) or len(candidate) != 3:
            continue
        if all(isinstance(item, str) for item in candidate):
            refs.append((candidate[0], candidate[1], candidate[2]))
    return tuple(refs)


def _iter_object_values(values: object) -> tuple[object, ...]:
    if not isinstance(values, Iterable) or isinstance(values, str | bytes | dict):
        return ()
    return tuple(values)


def _link_runtime_evidence_docs(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    doc_paths: object,
) -> None:
    for doc_path in _iter_object_values(doc_paths):
        doc_key = NodeKey("doc_artifact", str(doc_path))
        if doc_key in snapshot.nodes:
            snapshot.add_relation(
                surface, "DESCRIBED_IN", doc_key, provenance="runtime_evidence"
            )


def _link_runtime_evidence_modules(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    module_paths: object,
) -> None:
    for module_path in _iter_object_values(module_paths):
        module_key = NodeKey("module_surface", str(module_path))
        if module_key in snapshot.nodes:
            snapshot.add_relation(
                surface, "BACKED_BY", module_key, provenance="runtime_evidence"
            )


def _add_runtime_evidence_storage_artifact(
    snapshot: GraphSnapshot,
    project: NodeKey,
    surface: NodeKey,
    *,
    evidence_name: str,
    storage_ref: str,
    suffix: str,
    key_template: str,
    today: str,
) -> None:
    storage = _add_storage_surface(
        snapshot,
        project,
        StorageSurfaceSpec(
            ref=storage_ref,
            summary=f"Control-plane storage surface `{storage_ref}`.",
            layer="control",
            today=today,
            storage_kind="control_plane_artifact",
        ),
    )
    snapshot.add_relation(
        surface, "WRITES_TO", storage, provenance="runtime_evidence", suffix=suffix
    )
    artifact = _add_control_plane_artifact_surface(
        snapshot,
        project,
        ControlPlaneArtifactSpec(
            artifact_name=f"{evidence_name}::{suffix}",
            summary=f"{evidence_name} control-plane artifact `{storage_ref}`.",
            today=today,
            artifact_family=evidence_name,
            artifact_kind=suffix,
            storage_ref=storage_ref,
            artifact_format=_storage_surface_format(snapshot, storage),
            key_template=key_template,
        ),
    )
    snapshot.add_relation(
        surface, "EMITS_ARTIFACT", artifact, provenance="runtime_evidence"
    )
    snapshot.add_relation(
        artifact, "MATERIALIZED_AS", storage, provenance="runtime_evidence"
    )


def _control_plane_run_instance_specs() -> tuple[dict[str, object], ...]:
    return tuple(
        _run_instance_definition_spec(definition) for definition in RUN_INSTANCE_SPECS
    )
