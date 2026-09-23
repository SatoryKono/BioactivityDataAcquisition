"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _optional_text
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_run_instance_contract_dependency",
    "_link_run_instance_pipeline_dependency",
    "_run_instance_properties",
]


def _run_instance_properties(
    spec: dict[str, object],
    *,
    manifest_id: str,
) -> dict[str, object]:
    return {
        "manifest_id": manifest_id,
        "run_id": _optional_text(spec.get("run_id")),
        "pipeline_name": _optional_text(spec.get("pipeline_name")),
        "provider": _optional_text(spec.get("provider")),
        "entity": _optional_text(spec.get("entity")),
        "run_type": _optional_text(spec.get("run_type")),
        "execution_fingerprint": _optional_text(spec.get("execution_fingerprint")),
        "created_at": _optional_text(spec.get("created_at")),
        "contract_ref": _optional_text(spec.get("contract_ref")),
        "contract_version": _optional_text(spec.get("contract_version")),
        "effective_config_artifact_id": _optional_text(
            spec.get("effective_config_artifact_id")
        ),
        "config_hash": _optional_text(spec.get("config_hash")),
        "replay_capability": _optional_text(spec.get("replay_capability")),
        "lifecycle_status": _optional_text(spec.get("lifecycle_status")),
        "dq_disposition": _optional_text(spec.get("dq_disposition")),
        "dq_rule_id": _optional_text(spec.get("dq_rule_id")),
        "dq_report_path": _optional_text(spec.get("dq_report_path")),
        "published_dataset_ref": _optional_text(spec.get("published_dataset_ref")),
        "lineage_fragment_id": _optional_text(spec.get("lineage_fragment_id")),
        "replay_contract": _optional_text(spec.get("replay_contract")),
        "diagnostic_scope": _optional_text(spec.get("diagnostic_scope")),
        "last_event_at": _optional_text(spec.get("last_event_at")),
        "surface_kind": _optional_text(spec.get("surface_kind")),
        "source_path": _optional_text(spec.get("source_path")),
    }


def _link_run_instance_pipeline_dependency(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    pipeline_name = _optional_text(spec.get("pipeline_name"))
    if pipeline_name is None:
        return
    pipeline_key = NodeKey("pipeline_surface", pipeline_name)
    if pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            surface, "DEPENDS_ON", pipeline_key, provenance="runtime_evidence"
        )


def _link_run_instance_contract_dependency(
    snapshot: GraphSnapshot,
    surface: NodeKey,
    spec: dict[str, object],
) -> None:
    contract_ref = _optional_text(spec.get("contract_ref"))
    if contract_ref is None:
        return
    contract_key = NodeKey("contract_surface", contract_ref)
    if contract_key in snapshot.nodes:
        snapshot.add_relation(
            surface, "DEPENDS_ON", contract_key, provenance="runtime_evidence"
        )
