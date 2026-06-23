"""Reproducibility policy assessment helpers for manifest diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.persistence_policy import (
    _resolve_required_persistence_profile,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
    assess_reproducibility_policy,
)


def _assess_manifest_reproducibility_policy(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
    replay_family_contract: dict[str, object],
) -> ReproducibilityPolicyAssessment:
    """Return the central reproducibility policy verdict for one manifest."""
    return assess_reproducibility_policy(
        source_refs=manifest.source_refs,
        required_persistence_profile=_resolve_required_persistence_profile(manifest),
        strict_exact_replay_supported=bool(
            replay_family_contract.get("strict_exact_replay_supported", False)
        ),
        exact_replay_requested=requested_exact_replay,
        resume_requested=resume_requested,
        require_full_snapshot_envelope=False,
        replay_capability=manifest.replay_capability,
        run_type=manifest.run_type,
    )


__all__ = ["_assess_manifest_reproducibility_policy"]
