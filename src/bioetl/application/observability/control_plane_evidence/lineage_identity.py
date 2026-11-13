"""Identity-consistency helpers for persisted lineage evidence."""

from __future__ import annotations

from bioetl.application.observability.control_plane_evidence.lineage_graph_validation import (
    conflicting_node_ids,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.lineage import (
    LineageEdge,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)


def identity_gaps(
    *,
    manifest: RunManifest,
    fragments: tuple[LineageGraphFragment, ...],
    ledger_entries: tuple[RunLedgerEntry, ...] = (),
) -> list[str]:
    """Return stable identity mismatches across selected fragments.

    After successor adoption the run ledger may span predecessor manifests.
    Fragment/edge/manifest-node anchors may then name any ``manifest_id`` that
    appears in that chain (plus the current scope manifest), while ``run_id``
    must still match the selected run. Shared ``run:<UUID>`` nodes may also
    differ on ``attributes.manifest_id`` / ``execution_fingerprint`` (see
    ``conflicting_node_ids``); other RUN-field contradictions remain errors.
    """
    expected_run = str(manifest.run_id)
    allowed_manifests = frozenset(
        {
            *(entry.manifest_id for entry in ledger_entries if entry.manifest_id),
            manifest.manifest_id,
        }
    )
    gaps = {
        f"node_definition_conflict:{node_id}"
        for node_id in conflicting_node_ids(fragments)
    }
    for fragment in fragments:
        gaps.update(_fragment_anchor_gaps(fragment, expected_run, allowed_manifests))
        for edge in fragment.edges:
            gaps.update(_edge_anchor_gaps(edge, expected_run, allowed_manifests))
        for node in fragment.nodes:
            node_gap = _special_node_gap(node, expected_run, allowed_manifests)
            if node_gap is not None:
                gaps.add(node_gap)
    return sorted(gaps)


def _fragment_anchor_gaps(
    fragment: LineageGraphFragment,
    expected_run: str,
    allowed_manifests: frozenset[str],
) -> set[str]:
    fragment_key = fragment.stored_fragment_id or fragment.fragment_id
    gaps: set[str] = set()
    if fragment.run_id != expected_run:
        gaps.add(f"fragment_run:{fragment_key}")
    if fragment.manifest_id not in allowed_manifests:
        gaps.add(f"fragment_manifest:{fragment_key}")
    return gaps


def _edge_anchor_gaps(
    edge: LineageEdge,
    expected_run: str,
    allowed_manifests: frozenset[str],
) -> set[str]:
    gaps: set[str] = set()
    if edge.run_id is not None and edge.run_id != expected_run:
        gaps.add(f"edge_run:{edge.source.node_id}")
    if edge.manifest_id is not None and edge.manifest_id not in allowed_manifests:
        gaps.add(f"edge_manifest:{edge.source.node_id}")
    return gaps


def _special_node_gap(
    node: LineageNodeRef,
    expected_run: str,
    allowed_manifests: frozenset[str],
) -> str | None:
    if node.node_type is LineageNodeType.RUN:
        return (
            None
            if _run_node_matches(node, expected_run)
            else f"run_node:{node.node_id}"
        )
    if node.node_type is LineageNodeType.MANIFEST:
        return (
            None
            if _manifest_node_matches(node, allowed_manifests)
            else f"manifest_node:{node.node_id}"
        )
    return None


def _run_node_matches(node: LineageNodeRef, expected_run: str) -> bool:
    return (
        node.node_id == f"run:{expected_run}"
        and str(node.attributes.get("run_id") or "") == expected_run
    )


def _manifest_node_matches(
    node: LineageNodeRef,
    allowed_manifests: frozenset[str],
) -> bool:
    node_manifest = str(node.attributes.get("manifest_id") or "")
    return (
        bool(node_manifest)
        and node_manifest in allowed_manifests
        and node.node_id == f"manifest:{node_manifest}"
    )


__all__ = ["identity_gaps"]
