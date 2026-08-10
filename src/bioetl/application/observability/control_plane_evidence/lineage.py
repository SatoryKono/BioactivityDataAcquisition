"""Lineage closure, identity, and cycle validation helpers."""

from __future__ import annotations

from collections.abc import Iterable

from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
)
from bioetl.application.observability.control_plane_evidence.lineage_closure import (
    closure_gaps,
)
from bioetl.application.observability.control_plane_evidence.lineage_graph_validation import (
    cycle_nodes,
)
from bioetl.application.observability.control_plane_evidence.lineage_identity import (
    identity_gaps,
)
from bioetl.application.observability.control_plane_evidence.persistence_profile import (
    resolve_persistence_profile,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.lineage import LineageGraphFragment


def build_lineage_checks(
    *,
    manifest: RunManifest,
    fragments: tuple[LineageGraphFragment, ...],
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> tuple[EvidenceCheckResult, ...]:
    """Validate the persisted lineage graph for one manifested run."""
    if not fragments:
        return _missing_fragment_checks(manifest)

    closure = closure_gaps(fragments, ledger_entries)
    identities = identity_gaps(manifest=manifest, fragments=fragments)
    cycles = cycle_nodes(fragments)
    return (
        _gap_check(
            check="closure",
            gaps=closure,
            ok_reason="lineage_closure_complete",
            error_reason="lineage_closure_gap",
            ok_detail="Every edge endpoint and ledger lineage reference resolves.",
            error_prefix="Unresolved lineage references: ",
        ),
        _gap_check(
            check="identity_consistency",
            gaps=identities,
            ok_reason="lineage_identity_consistent",
            error_reason="lineage_identity_mismatch",
            ok_detail="Fragment, edge, run-node, and manifest-node identities match.",
            error_prefix="Lineage identity mismatches: ",
        ),
        _gap_check(
            check="cycle_detection",
            gaps=cycles,
            ok_reason="lineage_graph_acyclic",
            error_reason="lineage_cycle_detected",
            ok_detail="No directed cycle was detected in the selected lineage graph.",
            error_prefix="Directed cycle includes nodes: ",
        ),
        _persistence_profile_check(
            manifest,
            fragments,
            validation_complete=not (closure or identities or cycles),
        ),
    )


def _missing_fragment_checks(
    manifest: RunManifest,
) -> tuple[EvidenceCheckResult, ...]:
    required_profile, profile_valid = resolve_persistence_profile(manifest)
    lineage_required = not profile_valid or required_profile == "forensic_grade"
    return (
        EvidenceCheckResult(
            "closure",
            "ERROR" if lineage_required else "UNKNOWN",
            "lineage_fragments_missing",
            "No persisted lineage fragments resolved for the selected run.",
        ),
        EvidenceCheckResult(
            "identity_consistency",
            "UNKNOWN",
            "lineage_identity_not_observable",
            "Lineage identity cannot be validated without persisted fragments.",
        ),
        EvidenceCheckResult(
            "cycle_detection",
            "UNKNOWN",
            "lineage_cycle_not_observable",
            "Cycle detection cannot run without persisted fragments.",
        ),
        _persistence_profile_check(manifest, (), validation_complete=False),
    )


def _gap_check(
    *,
    check: str,
    gaps: Iterable[str],
    ok_reason: str,
    error_reason: str,
    ok_detail: str,
    error_prefix: str,
) -> EvidenceCheckResult:
    items = tuple(gaps)
    if not items:
        return EvidenceCheckResult(check, "OK", ok_reason, ok_detail)
    return EvidenceCheckResult(
        check,
        "ERROR",
        error_reason,
        error_prefix + ", ".join(items[:12]),
    )


def _persistence_profile_check(
    manifest: RunManifest,
    fragments: tuple[LineageGraphFragment, ...],
    *,
    validation_complete: bool,
) -> EvidenceCheckResult:
    required_profile, profile_valid = resolve_persistence_profile(manifest)
    if not profile_valid:
        return EvidenceCheckResult(
            "persistence_profile",
            "ERROR",
            "lineage_persistence_profile_unsupported",
            "Lineage validation rejects an unsupported persistence profile.",
        )
    if fragments and validation_complete:
        return EvidenceCheckResult(
            "persistence_profile",
            "OK",
            "lineage_persistence_profile_observed",
            f"Persisted lineage evidence is present for {required_profile}.",
        )
    if required_profile == "forensic_grade":
        return EvidenceCheckResult(
            "persistence_profile",
            "ERROR",
            "lineage_persistence_profile_unsatisfied",
            f"{required_profile} requires complete persisted lineage evidence.",
        )
    return EvidenceCheckResult(
        "persistence_profile",
        "WARNING",
        "lineage_persistence_profile_degraded",
        f"{required_profile} permits a run without persisted forensic lineage.",
    )


__all__ = ["build_lineage_checks"]
