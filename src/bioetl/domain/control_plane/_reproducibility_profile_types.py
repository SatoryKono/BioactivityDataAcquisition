"""Shared reproducibility profile types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReproducibilityExecutionContext = Literal["source", "composite"]
ReplayFamilyContractName = Literal[
    "snapshot_backed_exact_replay",
    "rebuild_only",
]
ReplaySupportState = Literal[
    "exact_replay_supported",
    "rebuild_only",
    "debug_only",
]
StrictReplayRuntimeVerdict = Literal[
    "allowed_with_snapshot_backed_source_refs",
    "blocked_outside_supported_boundary",
]


@dataclass(frozen=True, slots=True)
class ReproducibilityFamilyProfile:
    """Published per-family reproducibility profile."""

    family: str | None
    execution_context: ReproducibilityExecutionContext
    lineage_closure_supported: bool
    strict_exact_replay_supported: bool
    support_state: ReplaySupportState
    strict_replay_runtime_verdict: StrictReplayRuntimeVerdict
    exact_replay_support_boundary: str
    post_capture_replayable_parent_supported: bool
    post_capture_replayable_parent_boundary: str | None
    post_capture_replayable_parent_reason: str
    historical_live_run_upgrade_policy: str
    historical_live_run_upgrade_boundary: str | None
    historical_live_run_upgrade_reason: str
    broader_historical_exact_replay_policy: str
    broader_historical_exact_replay_boundary: str | None
    broader_historical_exact_replay_reason: str
    replay_family_contract: ReplayFamilyContractName
    default_required_persistence_profile: str
    support_scope: str
    reason: str


__all__ = [
    "ReplayFamilyContractName",
    "ReplaySupportState",
    "ReproducibilityExecutionContext",
    "ReproducibilityFamilyProfile",
    "StrictReplayRuntimeVerdict",
]
