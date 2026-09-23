"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _as_mapping, _optional_text, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import (
    RUN_MANIFEST_INSPECTION_DOC_PATH,
    RUN_MANIFEST_LEDGER_DOC_PATH,
)
from memory.graph.sync_pkg.graph_contexts import CompositePipelineContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "CONTROL_PLANE_LEDGER_DOCS",
    "EFFECTIVE_CONFIG_RUNTIME_MODULES",
    "LINEAGE_RUNTIME_MODULES",
    "RUN_LEDGER_RUNTIME_MODULES",
    "RUN_MANIFEST_RUNTIME_MODULES",
    "_composite_storage_context",
    "_link_composite_layer_promotions",
]


def _link_composite_layer_promotions(
    snapshot: GraphSnapshot,
    layer_nodes: dict[str, NodeKey],
    field_nodes_by_layer: dict[str, dict[str, NodeKey]],
) -> None:
    silver_layer = layer_nodes.get("silver")
    gold_layer = layer_nodes.get("gold")
    if silver_layer is None or gold_layer is None:
        return
    snapshot.add_relation(
        silver_layer,
        "PROMOTES_TO",
        gold_layer,
        provenance="storage_surfaces",
    )
    gold_fields = field_nodes_by_layer.get("gold", {})
    for field_name, silver_field in field_nodes_by_layer.get("silver", {}).items():
        gold_field = gold_fields.get(field_name)
        if gold_field is None:
            continue
        snapshot.add_relation(
            silver_field,
            "PROMOTES_FIELD_TO",
            gold_field,
            provenance="schema_fields",
        )


def _composite_storage_context(
    root: Path,
    composite_path: Path,
    payload: dict[str, object],
    *,
    today: str,
) -> tuple[CompositePipelineContext, dict[str, object], object]:
    composite_payload = _as_mapping(payload.get("composite"))
    composite_name = str(composite_payload.get("name", composite_path.stem))
    context = CompositePipelineContext(
        composite_name=composite_name,
        pipeline_key=NodeKey("pipeline_surface", composite_name),
        config_artifact=NodeKey("config_artifact", _rel_path(root, composite_path)),
        today=today,
        composite_version=_optional_text(composite_payload.get("version")),
    )
    return context, composite_payload, composite_payload.get("dependencies")


CONTROL_PLANE_LEDGER_DOCS = (
    RUN_MANIFEST_LEDGER_DOC_PATH,
    RUN_MANIFEST_INSPECTION_DOC_PATH,
    "docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md",
)

RUN_MANIFEST_RUNTIME_MODULES = (
    "src/bioetl/domain/control_plane/run_manifest.py",
    "src/bioetl/application/services/control_plane/run_manifest_service.py",
    "src/bioetl/application/services/control_plane/run_manifest_diagnostics.py",
    "src/bioetl/application/services/control_plane/run_manifest_inspection_service.py",
    "src/bioetl/interfaces/cli/commands/run_manifest.py",
    "src/bioetl/composition/bootstrap/cli/run_manifest.py",
    "src/bioetl/composition/runtime_builders/run_manifest_builder.py",
)

RUN_LEDGER_RUNTIME_MODULES = (
    "src/bioetl/domain/control_plane/run_ledger.py",
    "src/bioetl/application/services/control_plane/run_ledger_service.py",
)

EFFECTIVE_CONFIG_RUNTIME_MODULES = (
    "src/bioetl/domain/control_plane/effective_config_artifact.py",
    "src/bioetl/composition/services/effective_config_serializer.py",
    "src/bioetl/infrastructure/control_plane/file_effective_config_artifact_store.py",
)

LINEAGE_RUNTIME_MODULES = (
    "src/bioetl/application/services/lineage/lineage_inspection_service.py",
    "src/bioetl/composition/bootstrap/cli/lineage.py",
    "src/bioetl/infrastructure/control_plane/file_lineage_store.py",
)
