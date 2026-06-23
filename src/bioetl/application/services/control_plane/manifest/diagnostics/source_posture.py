"""Source-posture labels for manifest diagnostics."""

from __future__ import annotations

from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)


def _resolve_source_posture(
    policy_assessment: ReproducibilityPolicyAssessment,
) -> str:
    """Return whether manifested sources are snapshot-backed or live/unknown."""
    snapshot_envelope = policy_assessment.snapshot_envelope
    if snapshot_envelope.full_snapshot_envelope:
        return "immutable_snapshot_envelope"
    if snapshot_envelope.any_input_snapshots:
        return "partial_snapshot_envelope"
    return "live_or_unknown_inputs"


__all__ = ["_resolve_source_posture"]
