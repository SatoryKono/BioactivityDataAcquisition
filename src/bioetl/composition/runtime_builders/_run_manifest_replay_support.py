"""Replay-policy helpers shared by run-manifest creation support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_policy import (
    assess_reproducibility_policy,
)

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
        ManifestReproducibilityContext,
    )
    from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
        RunManifestCreateRequestInputs,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.control_plane import RunSourceRef
    from bioetl.domain.control_plane.reproducibility_policy import (
        ReproducibilityPolicyAssessment,
    )


class _ManifestLaunchContextBuilder(Protocol):
    def build_launch_context_snapshot(
        self,
        ctx: PipelineRunContext,
        *,
        run_type_value: str,
        execution_context_value: str,
        configured_required_persistence_profile: str | None,
        required_persistence_profile: str,
        required_persistence_profile_opt_down: bool,
        strict_exact_replay_supported: bool,
        reproducibility_family: str,
        replay_family_contract: str,
        strict_replay_runtime_verdict: str,
        replay_support_scope: str,
        replay_support_reason: str,
    ) -> dict[str, object]: ...


def validate_exact_replay_boundary(
    ctx: PipelineRunContext,
    context: ManifestReproducibilityContext,
) -> None:
    """Reject exact replay outside the published support boundary."""
    if not bool(getattr(ctx, "exact_replay", False)):
        return
    if context.strict_exact_replay_supported:
        return
    raise RuntimeError(
        "Pipeline execution is outside the published strict exact-replay "
        "support boundary for this run family"
    )


def build_manifest_launch_context(
    *,
    manifest_support: _ManifestLaunchContextBuilder,
    request_inputs: RunManifestCreateRequestInputs,
    reproducibility_context: ManifestReproducibilityContext,
) -> dict[str, object]:
    """Build the launch-context payload recorded on the run manifest."""
    return manifest_support.build_launch_context_snapshot(
        request_inputs.ctx,
        run_type_value=request_inputs.run_type_value,
        execution_context_value=request_inputs.execution_context_value,
        configured_required_persistence_profile=(
            reproducibility_context.configured_required_persistence_profile
        ),
        required_persistence_profile=reproducibility_context.required_persistence_profile,
        required_persistence_profile_opt_down=(
            reproducibility_context.required_persistence_profile_opt_down
        ),
        strict_exact_replay_supported=(
            reproducibility_context.strict_exact_replay_supported
        ),
        reproducibility_family=reproducibility_context.family,
        replay_family_contract=reproducibility_context.replay_family_contract,
        strict_replay_runtime_verdict=(
            reproducibility_context.strict_replay_runtime_verdict
        ),
        replay_support_scope=reproducibility_context.support_scope,
        replay_support_reason=reproducibility_context.reason,
    )


def build_replay_assessment(
    *,
    request_inputs: RunManifestCreateRequestInputs,
    reproducibility_context: ManifestReproducibilityContext,
    source_refs: tuple[RunSourceRef, ...],
    replay_capability: ReplayCapability,
) -> ReproducibilityPolicyAssessment:
    """Evaluate reproducibility policy for the current manifest request."""
    return assess_reproducibility_policy(
        source_refs=source_refs,
        required_persistence_profile=reproducibility_context.required_persistence_profile,
        strict_exact_replay_supported=(
            reproducibility_context.strict_exact_replay_supported
        ),
        exact_replay_requested=bool(
            getattr(request_inputs.ctx, "exact_replay", False)
        ),
        resume_requested=bool(getattr(request_inputs.ctx, "resume", False)),
        replay_capability=replay_capability,
        run_type=request_inputs.run_type_value,
        debug_only=bool(getattr(request_inputs.inputs.settings, "debug", False)),
    )


def apply_replay_assessment(
    launch_context: dict[str, object],
    replay_assessment: ReproducibilityPolicyAssessment,
) -> None:
    """Persist replay verdict details into the manifest launch context."""
    replay_verdict = replay_assessment.replay_readiness_verdict.value
    launch_context.update(
        {
            "replay_readiness_verdict": replay_verdict,
            "exact_replay_ready": replay_verdict == "exact_replay_ready",
            "replay_blockers": list(replay_assessment.blocking_gaps),
        }
    )
