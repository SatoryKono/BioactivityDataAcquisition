"""Referential-closure helpers for operator-facing lineage evidence."""

from __future__ import annotations

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.lineage import LineageGraphFragment


def closure_gaps(
    fragments: tuple[LineageGraphFragment, ...],
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    """Return unresolved edge-node and ledger-fragment references."""
    return [
        *(
            f"edge_endpoint_missing:{node_id}"
            for node_id in _missing_edge_nodes(fragments)
        ),
        *(
            f"ledger_fragment_missing:{fragment_id}"
            for fragment_id in _missing_ledger_fragments(fragments, ledger_entries)
        ),
    ]


def _missing_edge_nodes(fragments: tuple[LineageGraphFragment, ...]) -> list[str]:
    node_ids = {node.node_id for fragment in fragments for node in fragment.nodes}
    return sorted(
        {
            node_id
            for fragment in fragments
            for edge in fragment.edges
            for node_id in (edge.source.node_id, edge.target.node_id)
            if node_id not in node_ids
        }
    )


def _missing_ledger_fragments(
    fragments: tuple[LineageGraphFragment, ...],
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    stored_ids = {
        identifier
        for fragment in fragments
        for identifier in (fragment.fragment_id, fragment.stored_fragment_id)
        if identifier
    }
    return sorted(
        {
            entry.lineage_fragment_id
            for entry in ledger_entries
            if entry.lineage_fragment_id and entry.lineage_fragment_id not in stored_ids
        }
    )


__all__ = ["closure_gaps"]
