"""Reproducibility policy assessment helpers for manifest diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants import (
    required_persistence_profile as _required_persistence_profile_module,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.composite_replay import has_composite_replay_bindings
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
    assess_reproducibility_policy,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    resolve_manifest_reproducibility_profile,
)


def _assess_manifest_reproducibility_policy(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
) -> ReproducibilityPolicyAssessment:
    """Return the central reproducibility policy verdict for one manifest."""
    profile = resolve_manifest_reproducibility_profile(manifest)
    return assess_reproducibility_policy(
        source_refs=manifest.source_refs,
        required_persistence_profile=_required_persistence_profile_module._resolve_required_persistence_profile(
            manifest
        ),
        strict_exact_replay_supported=profile.strict_exact_replay_supported
        and (
            not is_composite_execution_context(manifest)
            or has_composite_replay_bindings(manifest)
        ),
        exact_replay_requested=requested_exact_replay,
        resume_requested=resume_requested,
        require_full_snapshot_envelope=False,
        replay_capability=manifest.replay_capability,
        run_type=manifest.run_type,
    )


__all__ = ["_assess_manifest_reproducibility_policy"]
