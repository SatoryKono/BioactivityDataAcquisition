"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _is_doc_artifact_file
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_repo_zone_doc_artifact",
    "_add_repo_zone_file_surface",
]


def _add_repo_zone_file_surface(
    snapshot: GraphSnapshot,
    directory: NodeKey,
    relative_file: str,
    today: str,
    *,
    zone_name: str,
    filename: str,
) -> NodeKey:
    file_surface = snapshot.add_node(
        "file_surface",
        relative_file,
        summary=f"Repository file `{relative_file}`.",
        source_path=relative_file,
        source_kind="file_structure_file",
        repo_zone=zone_name,
        file_extension=Path(filename).suffix[1:] if Path(filename).suffix else None,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        directory, "CONTAINS", file_surface, provenance="file_structure"
    )
    return file_surface


def _add_repo_zone_doc_artifact(
    snapshot: GraphSnapshot,
    project: NodeKey,
    file_surface: NodeKey,
    relative_file: str,
    today: str,
    *,
    zone_name: str,
) -> None:
    file_extension = Path(relative_file).suffix.lower()
    if not _is_doc_artifact_file(relative_file, file_extension):
        return
    doc_artifact = snapshot.add_node(
        "doc_artifact",
        relative_file,
        summary=f"Documentation artifact `{relative_file}`.",
        source_path=relative_file,
        source_kind="doc_artifact",
        repo_zone=zone_name,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )
    snapshot.add_relation(
        project, "HAS_DOC_ARTIFACT", doc_artifact, provenance="file_structure"
    )
    snapshot.add_relation(
        doc_artifact, "BACKED_BY", file_surface, provenance="file_structure"
    )
