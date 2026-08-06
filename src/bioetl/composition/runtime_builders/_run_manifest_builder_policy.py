"""Policy and provenance helpers for manifest builder orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._run_manifest_sink_policy import (
    validate_reproducible_sink_modes,
)
from bioetl.composition.services.versioning import (
    CodeRevisionProvenance,
    get_code_revision_provenance,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    assess_reproducibility_policy,
    is_critical_reproducibility_runtime,
    is_degraded_opt_down_eligible,
    normalize_required_persistence_profile,
    resolve_effective_required_persistence_profile,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    resolve_reproducibility_family_profile,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.service import (
        RunManifestCreateSpec,
    )
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.domain.context import PipelineRunContext


@dataclass(frozen=True, slots=True)
class ManifestReproducibilityContext:
    configured_required_persistence_profile: str
    required_persistence_profile: str
    required_persistence_profile_opt_down: bool
    strict_exact_replay_supported: bool
    family: str
    replay_family_contract: str
    strict_replay_runtime_verdict: str
    exact_replay_support_boundary: str
    support_scope: str
    reason: str


def resolve_code_revision_for_manifest(
    *,
    resolved_config_hash: str,
    test_mode: bool,
) -> CodeRevisionProvenance:
    """Return code provenance, with a deterministic test-only fallback."""
    code_revision = get_code_revision_provenance()
    if not test_mode:
        return code_revision
    if (
        code_revision.git_commit is not None
        and str(code_revision.source_revision_state or "").strip().lower() == "clean"
        and code_revision.dependency_lock_hash is not None
    ):
        return code_revision
    # Test-mode manifests use a sealed synthetic revision so strict replay
    # validation remains deterministic even when the developer checkout is dirty.
    # The ``test-`` anchors keep this distinct from verified repository provenance.
    return CodeRevisionProvenance(
        git_commit=f"test-{resolved_config_hash[:12]}",
        source_revision_state="clean",
        dependency_lock_hash=f"sha256:test-lock-{resolved_config_hash[:12]}",
    )


def resolve_manifest_reproducibility_context(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    contract_ref: str,
) -> ManifestReproducibilityContext:
    """Resolve the runtime persistence profile contract for one manifest build."""
    control_plane = getattr(
        getattr(inputs.settings, "pipeline", None), "control_plane", None
    )
    requested_profile = getattr(ctx, "required_persistence_profile", None)
    configured_required_profile = normalize_required_persistence_profile(
        requested_profile
        if requested_profile is not None and str(requested_profile).strip()
        else getattr(
            control_plane,
            "required_persistence_profile",
            DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
        )
    )
    reproducibility_profile = resolve_reproducibility_family_profile(
        provider=provider,
        entity=entity,
        contract_ref=contract_ref,
        execution_context="source",
    )
    critical_runtime = is_critical_reproducibility_runtime(
        runtime_environment=getattr(inputs.settings, "env", None),
        debug_mode=getattr(inputs.settings, "debug", False),
    )
    degraded_opt_down_requested = is_degraded_opt_down_eligible(
        opt_down_requested=bool(
            getattr(ctx, "required_persistence_profile_opt_down", False)
        ),
        configured_required_profile=configured_required_profile,
        exact_replay_requested=bool(getattr(ctx, "exact_replay", False)),
        critical_runtime=critical_runtime,
    )
    required_persistence_profile = resolve_effective_required_persistence_profile(
        configured_required_profile=configured_required_profile,
        family_default_profile=(
            reproducibility_profile.default_required_persistence_profile
        ),
        exact_replay_requested=bool(getattr(ctx, "exact_replay", False)),
        critical_runtime=critical_runtime,
        allow_degraded_opt_down=degraded_opt_down_requested,
    )
    family = reproducibility_profile.family
    if family is None:
        raise RuntimeError(
            f"Reproducibility profile has no family for {provider}.{entity}"
        )
    validate_reproducible_sink_modes(
        yaml_config=inputs.yaml_config,
        strict_replay_requested=bool(getattr(ctx, "exact_replay", False))
        or required_persistence_profile in STRICT_PERSISTENCE_PROFILES,
        replay_capable_family=bool(
            reproducibility_profile.strict_exact_replay_supported
        ),
    )
    return ManifestReproducibilityContext(
        configured_required_persistence_profile=configured_required_profile,
        required_persistence_profile=required_persistence_profile,
        required_persistence_profile_opt_down=(
            degraded_opt_down_requested
            and required_persistence_profile == "degraded_observable"
        ),
        strict_exact_replay_supported=(
            reproducibility_profile.strict_exact_replay_supported
        ),
        family=family,
        replay_family_contract=reproducibility_profile.replay_family_contract,
        strict_replay_runtime_verdict=(
            reproducibility_profile.strict_replay_runtime_verdict
        ),
        exact_replay_support_boundary=(
            reproducibility_profile.exact_replay_support_boundary
        ),
        support_scope=reproducibility_profile.support_scope,
        reason=reproducibility_profile.reason,
    )


def validate_required_runtime_persistence_profile(
    *,
    request: RunManifestCreateSpec,
    required_persistence_profile: str,
    strict_exact_replay_supported: bool,
) -> None:
    """Raise when a strict persistence profile is requested but unsupported."""
    assessment = assess_reproducibility_policy(
        source_refs=request.source_refs,
        required_persistence_profile=required_persistence_profile,
        strict_exact_replay_supported=strict_exact_replay_supported,
        exact_replay_requested=bool(request.launch_context.get("exact_replay")),
        resume_requested=bool(request.launch_context.get("resume")),
        replay_capability=request.replay_capability,
        run_type=request.run_type,
    )
    if not assessment.strict_requirement_requested:
        return
    if "strict_replay_execution_context_support" in assessment.blocking_gaps:
        raise RuntimeError(
            "Pipeline execution is outside the published strict exact-replay "
            "support boundary for this run family"
        )
    if "exact_replay_capability" in assessment.blocking_gaps:
        raise RuntimeError(
            "Pipeline execution cannot satisfy required persistence profile "
            f"'{required_persistence_profile}' because immutable input snapshots "
            "and exact replay capability are not available for this run"
        )


__all__ = [
    "ManifestReproducibilityContext",
    "resolve_code_revision_for_manifest",
    "resolve_manifest_reproducibility_context",
    "validate_required_runtime_persistence_profile",
]
