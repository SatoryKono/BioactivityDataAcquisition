"""Extracted _refresh_replay_summary_build_policy_assessment for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_types import (
    _ReplayRefreshContext,
)
from bioetl.application.services.control_plane.manifest.diagnostics.source_refs import (
    _build_effective_source_refs,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    assess_reproducibility_policy,
)


def _refresh_replay_summary_build_policy_assessment(
    manifest: RunManifest,
    summary: dict[str, object],
    input_snapshots: list[dict[str, object]],
) -> _ReplayRefreshContext:
    """Build policy assessment from materialized snapshots."""
    source_refs = _build_effective_source_refs(
        manifest=manifest,
        input_snapshots=input_snapshots,
    )
    replay_assessment_seed = cast(
        "dict[str, object]",
        summary.get("replay_capability_assessment", {}),
    )
    strict_exact_replay_supported = bool(
        replay_assessment_seed.get("strict_exact_replay_supported", False)
    )
    requested_exact_replay = bool(summary.get("requested_exact_replay", False))
    resume_requested = bool(manifest.launch_context.get("resume"))
    replay_capability_seed: ReplayCapability | None = None
    if any(source_ref.input_snapshots for source_ref in source_refs):
        replay_capability_seed = ReplayCapability.EXACT_REPLAY_SUPPORTED
    policy_assessment = assess_reproducibility_policy(
        source_refs=source_refs,
        required_persistence_profile=summary.get(
            "required_persistence_profile",
            "degraded_observable",
        ),
        strict_exact_replay_supported=strict_exact_replay_supported,
        exact_replay_requested=requested_exact_replay,
        resume_requested=resume_requested,
        replay_capability=replay_capability_seed,
        run_type=manifest.run_type.value,
        debug_only=False,
        lifecycle_projection_only=False,
    )
    effective_manifest = replace(
        manifest,
        replay_capability=policy_assessment.replay_capability,
        source_refs=source_refs,
    )
    return _ReplayRefreshContext(
        effective_manifest=effective_manifest,
        policy_assessment=policy_assessment,
        input_snapshots=input_snapshots,
        resume_requested=resume_requested,
        requested_exact_replay=requested_exact_replay,
    )
