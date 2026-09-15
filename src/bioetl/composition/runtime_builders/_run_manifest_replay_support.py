"""Replay-policy helpers shared by run-manifest creation support."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._run_manifest_snapshot_resolution import (
    as_runtime_config_mapping,
    coerce_optional_text,
    resolve_replay_parentage_mapping_value,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    build_launch_context_snapshot,
)
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
    request_inputs: RunManifestCreateRequestInputs,
    reproducibility_context: ManifestReproducibilityContext,
) -> dict[str, object]:
    """Build the launch-context payload recorded on the run manifest."""
    snapshot = build_launch_context_snapshot(
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
    snapshot["run_ledger_enabled"] = bool(
        getattr(request_inputs, "ledger_enabled", True)
    )
    return snapshot


def resolve_replay_parentage(
    *,
    ctx: PipelineRunContext,
    runtime_config: object,
) -> tuple[str | None, str | None]:
    """Resolve replay parent identifiers from context or runtime config."""
    runtime_config_mapping = as_runtime_config_mapping(runtime_config)
    return (
        _resolve_replay_id(ctx, "replay_of_run_id", runtime_config_mapping),
        _resolve_replay_id(ctx, "replay_of_manifest_id", runtime_config_mapping),
    )


def _resolve_replay_id(
    ctx: PipelineRunContext,
    attr_name: str,
    runtime_config_mapping: object,
) -> str | None:
    """Resolve one replay identifier from context before runtime config."""
    ctx_value = coerce_optional_text(getattr(ctx, attr_name, None))
    if ctx_value is not None:
        return ctx_value
    keys = (attr_name, f"exact_replay_parent_{attr_name}")
    return resolve_replay_parentage_mapping_value(
        as_runtime_config_mapping(runtime_config_mapping),
        *keys,
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
        exact_replay_requested=bool(getattr(request_inputs.ctx, "exact_replay", False)),
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
