"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_curated_doc_source import _add_curated_doc_source
from memory.graph.sync_pkg.add_package_topology_decisions_and_risks import (
    _add_package_topology_decisions_and_risks,
)
from memory.graph.sync_pkg.add_provider_surfaces import _add_provider_surfaces
from memory.graph.sync_pkg.default_batch_size import CURATED_DOC_SOURCES
from memory.graph.sync_pkg.entity_config_identity import _add_composite_config_surfaces
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.package_topology_summary_specs import (
    _add_governance_decisions_and_risks,
)
from memory.graph.sync_pkg.provider_config_properties import _add_entity_config_surfaces

__all__ = [
    "_add_curated_docs",
    "_add_decisions_and_risks",
    "_add_provider_and_config_graph",
]


def _add_curated_docs(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    for entry in CURATED_DOC_SOURCES:
        _add_curated_doc_source(snapshot, root, project, today, entry)


def _add_decisions_and_risks(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    _add_package_topology_decisions_and_risks(snapshot, root, project, today)
    _add_governance_decisions_and_risks(snapshot, root, project, today)


def _add_provider_and_config_graph(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    provider_nodes = _add_provider_surfaces(snapshot, root, project, today)
    entity_nodes = _add_entity_config_surfaces(snapshot, root, today, provider_nodes)
    _add_composite_config_surfaces(snapshot, root, project, today, entity_nodes)
