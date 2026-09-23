"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _read_text, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import GOVERNANCE_DECISIONS_SUMMARY_PATH
from memory.graph.sync_pkg.governance_summary_table_specs import (
    _governance_summary_table_specs,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_curated_doc_artifact import (
    _add_summary_table_identifiers,
    _evidence_summary_doc,
    _summary_table_rows,
)

__all__ = [
    "_add_governance_decisions_and_risks",
    "_package_topology_summary_specs",
]


def _package_topology_summary_specs() -> tuple[tuple[str, str, str], ...]:
    return (
        ("decision", r"DEC-[a-z0-9-]+", "Accepted package-topology decision."),
        (
            "risk",
            r"RISK-[a-z0-9-]+",
            "Package-topology risk captured in evidence decisions.",
        ),
    )


def _add_governance_decisions_and_risks(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    summary_path = root / GOVERNANCE_DECISIONS_SUMMARY_PATH
    if not summary_path.is_file():
        return
    governance_summary, governance_doc = _evidence_summary_doc(
        snapshot,
        root,
        today,
        path=GOVERNANCE_DECISIONS_SUMMARY_PATH,
        summary="Accepted governance decisions and associated risks.",
    )
    governance_text = _read_text(governance_summary)
    source_path = _rel_path(root, governance_summary)
    for identifier_kind, prefix in _governance_summary_table_specs():
        _add_summary_table_identifiers(
            snapshot,
            project,
            today,
            doc=governance_doc,
            provenance="governance_summary",
            identifier_kind=identifier_kind,
            rows=_summary_table_rows(governance_text, prefix),
            source_path=source_path,
        )
