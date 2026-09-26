"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from memory.graph.sync_pkg.add_ci_workflow_graph import _add_ci_workflow_graph
from memory.graph.sync_pkg.add_control_plane_runtime_evidence import (
    _add_control_plane_runtime_evidence,
)
from memory.graph.sync_pkg.add_curated_docs import (
    _add_curated_docs,
    _add_decisions_and_risks,
    _add_provider_and_config_graph,
)
from memory.graph.sync_pkg.add_docs_to_code_drift_edges import (
    _add_adr_constraint_edges,
    _add_docs_to_code_drift_edges,
)
from memory.graph.sync_pkg.add_file_structure_surfaces import (
    _add_file_structure_surfaces,
)
from memory.graph.sync_pkg.add_impact_analysis_surfaces import (
    _add_impact_analysis_surfaces,
)
from memory.graph.sync_pkg.add_pipeline_doc_edges import _add_pipeline_doc_edges
from memory.graph.sync_pkg.add_provider_surfaces import _add_policy_surfaces
from memory.graph.sync_pkg.add_storage_data_surfaces import _add_storage_data_surfaces
from memory.graph.sync_pkg.composite_config_dependency_entries import (
    _add_cli_command_graph,
    _add_quality_and_scripts,
)
from memory.graph.sync_pkg.composite_dependency_target import _add_dashboard_graph
from memory.graph.sync_pkg.duplication_cluster_thresholds import (
    _add_complexity_analysis_surfaces,
    _add_retirement_analysis_surfaces,
)
from memory.graph.sync_pkg.governance_summary_table_specs import _add_layer_topology
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.is_describes_doc_to_module import (
    _add_reverse_module_doc_edges,
)
from memory.graph.sync_pkg.link_composite_config_dependencies import _add_test_graph
from memory.graph.sync_pkg.mapping_io import _load_memory_mapping

__all__ = [
    "build_snapshot",
]


def build_snapshot(root: Path, verified_at: str | None = None) -> GraphSnapshot:
    snapshot = GraphSnapshot()
    today = verified_at or date.today().isoformat()
    memory_mapping = _load_memory_mapping(root)
    project = snapshot.add_node(
        "project",
        "BioETL",
        summary="Python ETL framework for bioactivity data acquisition.",
        source_path="docs/00-project/ai/memory/agent-memory.md",
        source_kind="memory_entrypoint",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    _add_curated_docs(snapshot, root, project, today)
    _add_decisions_and_risks(snapshot, root, project, today)
    _add_layer_topology(snapshot, root, project, today)
    _add_provider_and_config_graph(snapshot, root, project, today)
    _add_dashboard_graph(snapshot, root, project, today)
    _add_quality_and_scripts(snapshot, root, project, today)
    _add_test_graph(snapshot, root, project, today)
    _add_policy_surfaces(snapshot, root, project, today)
    _add_impact_analysis_surfaces(snapshot, root, project, today)
    _add_file_structure_surfaces(snapshot, root, project, today)
    _add_storage_data_surfaces(snapshot, root, project, today)
    _add_control_plane_runtime_evidence(snapshot, root, project, today)
    _add_ci_workflow_graph(snapshot, root, project, today)
    _add_cli_command_graph(snapshot, root, project, today)
    _add_docs_to_code_drift_edges(snapshot, root)
    _add_pipeline_doc_edges(snapshot)
    _add_reverse_module_doc_edges(snapshot)
    _add_adr_constraint_edges(snapshot, root, project, today)
    _add_retirement_analysis_surfaces(snapshot, root, project, today, memory_mapping)
    _add_complexity_analysis_surfaces(snapshot, root, project, today, memory_mapping)
    return snapshot
