"""Lineage closure, identity, and cycle validation helpers."""

from __future__ import annotations

from collections.abc import Iterable

from bioetl.application.services.control_plane.evidence.models import EvidenceCheck
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.lineage import LineageGraphFragment, LineageNodeType


def build_lineage_checks(
    *,
    manifest: RunManifest,
    fragments: tuple[LineageGraphFragment, ...],
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> tuple[EvidenceCheck, ...]:
    """Validate the persisted lineage graph for one manifested run."""
    if not fragments:
        required_profile = _required_profile(manifest)
        return (
            EvidenceCheck(
                "closure",
                "ERROR" if required_profile in {"replay_ready", "forensic_grade"} else "UNKNOWN",
                "lineage_fragments_missing",
                "No persisted lineage fragments resolved for the selected run.",
            ),
            EvidenceCheck(
                "identity_consistency",
                "UNKNOWN",
                "lineage_identity_not_observable",
                "Lineage identity cannot be validated without persisted fragments.",
            ),
            EvidenceCheck(
                "cycle_detection",
                "UNKNOWN",
                "lineage_cycle_not_observable",
                "Cycle detection cannot run without persisted fragments.",
            ),
            _persistence_profile_check(manifest, fragments),
        )

    node_ids = {node.node_id for fragment in fragments for node in fragment.nodes}
    missing_edge_nodes = sorted(
        {
            node_id
            for fragment in fragments
            for edge in fragment.edges
            for node_id in (edge.source.node_id, edge.target.node_id)
            if node_id not in node_ids
        }
    )
    stored_ids = {
        identifier
        for fragment in fragments
        for identifier in (fragment.fragment_id, fragment.stored_fragment_id)
        if identifier
    }
    missing_ledger_fragments = sorted(
        {
            entry.lineage_fragment_id
            for entry in ledger_entries
            if entry.lineage_fragment_id
            and entry.lineage_fragment_id not in stored_ids
        }
    )
    closure_gaps = [
        *(f"node:{node_id}" for node_id in missing_edge_nodes),
        *(f"fragment:{fragment_id}" for fragment_id in missing_ledger_fragments),
    ]
    identity_gaps = _identity_gaps(manifest=manifest, fragments=fragments)
    cycle_nodes = _cycle_nodes(fragments)
    return (
        _gap_check(
            check="closure",
            gaps=closure_gaps,
            ok_reason="lineage_closure_complete",
            error_reason="lineage_closure_gap",
            ok_detail="Every edge endpoint and ledger lineage reference resolves.",
            error_prefix="Unresolved lineage references: ",
        ),
        _gap_check(
            check="identity_consistency",
            gaps=identity_gaps,
            ok_reason="lineage_identity_consistent",
            error_reason="lineage_identity_mismatch",
            ok_detail="Fragment, edge, run-node, and manifest-node identities match.",
            error_prefix="Lineage identity mismatches: ",
        ),
        _gap_check(
            check="cycle_detection",
            gaps=cycle_nodes,
            ok_reason="lineage_graph_acyclic",
            error_reason="lineage_cycle_detected",
            ok_detail="No directed cycle was detected in the selected lineage graph.",
            error_prefix="Directed cycle includes nodes: ",
        ),
        _persistence_profile_check(manifest, fragments),
    )


def _identity_gaps(
    *, manifest: RunManifest, fragments: tuple[LineageGraphFragment, ...]
) -> list[str]:
    expected_run = str(manifest.run_id)
    expected_manifest = manifest.manifest_id
    gaps: set[str] = set()
    for fragment in fragments:
        fragment_key = fragment.stored_fragment_id or fragment.fragment_id
        if fragment.run_id != expected_run:
            gaps.add(f"fragment_run:{fragment_key}")
        if fragment.manifest_id != expected_manifest:
            gaps.add(f"fragment_manifest:{fragment_key}")
        for edge in fragment.edges:
            if edge.run_id is not None and edge.run_id != expected_run:
                gaps.add(f"edge_run:{edge.source.node_id}")
            if edge.manifest_id is not None and edge.manifest_id != expected_manifest:
                gaps.add(f"edge_manifest:{edge.source.node_id}")
        for node in fragment.nodes:
            if node.node_type is LineageNodeType.RUN:
                if node.node_id != f"run:{expected_run}" or str(
                    node.attributes.get("run_id") or ""
                ) != expected_run:
                    gaps.add(f"run_node:{node.node_id}")
            if node.node_type is LineageNodeType.MANIFEST:
                if node.node_id != f"manifest:{expected_manifest}" or str(
                    node.attributes.get("manifest_id") or ""
                ) != expected_manifest:
                    gaps.add(f"manifest_node:{node.node_id}")
    return sorted(gaps)


def _cycle_nodes(fragments: tuple[LineageGraphFragment, ...]) -> list[str]:
    adjacency: dict[str, set[str]] = {}
    for fragment in fragments:
        for edge in fragment.edges:
            adjacency.setdefault(edge.source.node_id, set()).add(edge.target.node_id)
            adjacency.setdefault(edge.target.node_id, set())

    visiting: set[str] = set()
    visited: set[str] = set()
    cycle: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            cycle.add(node_id)
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        found = False
        for target_id in sorted(adjacency.get(node_id, ())):
            if visit(target_id):
                cycle.update({node_id, target_id})
                found = True
        visiting.remove(node_id)
        visited.add(node_id)
        return found

    for candidate in sorted(adjacency):
        visit(candidate)
    return sorted(cycle)


def _gap_check(
    *,
    check: str,
    gaps: Iterable[str],
    ok_reason: str,
    error_reason: str,
    ok_detail: str,
    error_prefix: str,
) -> EvidenceCheck:
    items = tuple(gaps)
    if not items:
        return EvidenceCheck(check, "OK", ok_reason, ok_detail)
    return EvidenceCheck(
        check,
        "ERROR",
        error_reason,
        error_prefix + ", ".join(items[:12]),
    )


def _required_profile(manifest: RunManifest) -> str:
    return str(
        manifest.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    ).strip()


def _persistence_profile_check(
    manifest: RunManifest,
    fragments: tuple[LineageGraphFragment, ...],
) -> EvidenceCheck:
    required_profile = _required_profile(manifest)
    if fragments:
        return EvidenceCheck(
            "persistence_profile",
            "OK",
            "lineage_persistence_profile_observed",
            f"Persisted lineage evidence is present for {required_profile}.",
        )
    if required_profile in {"replay_ready", "forensic_grade"}:
        return EvidenceCheck(
            "persistence_profile",
            "ERROR",
            "lineage_persistence_profile_unsatisfied",
            f"{required_profile} requires persisted lineage evidence.",
        )
    return EvidenceCheck(
        "persistence_profile",
        "WARNING",
        "lineage_persistence_profile_degraded",
        "degraded_observable permits a run without persisted lineage closure.",
    )


__all__ = ["build_lineage_checks"]
