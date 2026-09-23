"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_curated_doc_artifact import (
    _add_summary_identifiers,
    _evidence_summary_doc,
    _summary_identifier_matches,
)
from memory.graph.sync_pkg.package_topology_summary_specs import (
    _package_topology_summary_specs,
)

__all__ = [
    "_add_package_topology_decisions_and_risks",
]


def _add_package_topology_decisions_and_risks(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    summary_path = (
        root / "docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md"
    )
    if not summary_path.is_file():
        return
    package_summary, package_doc = _evidence_summary_doc(
        snapshot,
        root,
        today,
        path="docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md",
        summary="Accepted package topology decisions and risks.",
    )
    source_path = _rel_path(root, package_summary)
    for identifier_kind, pattern, summary in _package_topology_summary_specs():
        _add_summary_identifiers(
            snapshot,
            project,
            today,
            doc=package_doc,
            provenance="package_topology_summary",
            identifier_kind=identifier_kind,
            matches=_summary_identifier_matches(package_summary, pattern),
            summary=summary,
            source_path=source_path,
        )
