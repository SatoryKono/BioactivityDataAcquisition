"""Shared internal types for artifact lifecycle planning."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["_ProtectedRefs"]


@dataclass(frozen=True, slots=True)
class _ProtectedRefs:
    """Resolved reference sets that block lifecycle deletion."""

    manifest_ids: frozenset[str]
    run_ids: frozenset[str]
    input_snapshot_ids: frozenset[str]
    effective_config_artifact_ids: frozenset[str]
    lineage_fragment_ids: frozenset[str]
    evidence_floor_manifest_ids: frozenset[str]
    evidence_floor_run_ids: frozenset[str]
    evidence_floor_input_snapshot_ids: frozenset[str]
    evidence_floor_effective_config_artifact_ids: frozenset[str]
    evidence_floor_lineage_fragment_ids: frozenset[str]
