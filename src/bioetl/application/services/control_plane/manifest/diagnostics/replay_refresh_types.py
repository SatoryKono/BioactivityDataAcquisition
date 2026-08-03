"""Dataclasses for replay refresh diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)


@dataclass(frozen=True, slots=True)
class _ReplayRefreshContext:
    """Replay-refresh inputs reused after snapshot materialization."""

    effective_manifest: RunManifest
    policy_assessment: ReproducibilityPolicyAssessment
    input_snapshots: list[dict[str, object]]
    resume_requested: bool
    requested_exact_replay: bool


@dataclass(frozen=True, slots=True)
class _ReplayRefreshProjection:
    """Replay-field projection built after materialized snapshot refresh."""

    replay_payload: dict[str, object]
    exact_replay_eligible: bool
    replay_mode: str
    continuation_mode: str


@dataclass(frozen=True, slots=True)
class _ReplayRefreshSummaryUpdate:
    """All replay-summary updates derived after snapshot materialization."""

    payload: dict[str, object]


__all__ = [
    "_ReplayRefreshContext",
    "_ReplayRefreshProjection",
    "_ReplayRefreshSummaryUpdate",
]
