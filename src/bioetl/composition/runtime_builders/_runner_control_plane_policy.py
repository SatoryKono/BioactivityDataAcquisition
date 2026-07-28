# pyright: reportArgumentType=false
# Boundary object/payload typing residual at this module.
"""Control-plane policy resolution helpers for runtime runner assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._runner_control_plane_policy_support import (
    _normalize_required_persistence_profile as _normalize_required_persistence_profile_impl,
    requires_artifact_publication_closure as _requires_artifact_publication_closure_impl,
    resolve_required_artifact_lineage_layers as _resolve_required_artifact_lineage_layers,
    validate_artifact_recorder_attachment as _validate_artifact_recorder_attachment,
    validate_manifest_persistence_requirements as _validate_manifest_persistence_requirements,
    validate_required_persistence_profile as _validate_required_persistence_profile,
    validate_strict_data_root_policy as _validate_strict_data_root_policy,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    is_critical_reproducibility_runtime,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

@dataclass(frozen=True, slots=True)
class ResolvedRunnerControlPlanePolicy:
    manifest_enabled: bool
    ledger_enabled: bool
    required_profile: str

def resolve_required_artifact_lineage_layers(
    *,
    yaml_config: object | None,
    skip_gold: bool = False,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return _resolve_required_artifact_lineage_layers(
        yaml_config=yaml_config,
        skip_gold=skip_gold,
    )

def validate_manifest_persistence_requirements(
    *,
    yaml_config: object,
    skip_gold: bool,
    ledger_enabled: bool,
    required_profile: str,
    strict_exact_replay_supported: bool,
) -> None:
    _validate_manifest_persistence_requirements(
        yaml_config=yaml_config,
        skip_gold=skip_gold,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        strict_exact_replay_supported=strict_exact_replay_supported,
    )

def validate_required_persistence_profile(
    *,
    manifest_enabled: bool,
    ledger_enabled: bool,
    required_profile: object,
    execution_label: str,
    exact_replay_execution_context_supported: bool = True,
    composite_resume_rich_replay_supported: bool = True,
    missing_artifact_lineage_layers: tuple[str, ...] = (),
) -> None:
    _validate_required_persistence_profile(
        manifest_enabled=manifest_enabled,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        execution_label=execution_label,
        exact_replay_execution_context_supported=exact_replay_execution_context_supported,
        composite_resume_rich_replay_supported=composite_resume_rich_replay_supported,
        missing_artifact_lineage_layers=missing_artifact_lineage_layers,
    )

def validate_strict_data_root_policy(
    *,
    settings: Settings,
    required_profile: object,
    exact_replay: bool = False,
) -> None:
    _validate_strict_data_root_policy(
        settings=settings,
        required_profile=required_profile,
        exact_replay=exact_replay,
    )

def requires_artifact_publication_closure(required_profile: object) -> bool:
    return _requires_artifact_publication_closure_impl(required_profile)

def validate_artifact_recorder_attachment(
    *,
    required_profile: object,
    candidate_count: int,
    attached_count: int,
    missing_attach_method_count: int,
    failed_count: int,
) -> None:
    _validate_artifact_recorder_attachment(
        required_profile=required_profile,
        candidate_count=candidate_count,
        attached_count=attached_count,
        missing_attach_method_count=missing_attach_method_count,
        failed_count=failed_count,
    )

def resolve_control_plane_flags(
    settings: object,
    *,
    yaml_config: object | None = None,
    skip_gold: bool = False,
    required_profile_override: object | None = None,
    exact_replay: bool = False,
    critical_runtime: bool | None = None,
) -> tuple[bool, bool]:
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    required_profile = getattr(
        control_plane,
        "required_persistence_profile",
        DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    )
    if required_profile_override is not None and str(required_profile_override).strip():
        required_profile = required_profile_override
    critical = (
        is_critical_reproducibility_runtime(
            runtime_environment=getattr(settings, "env", None),
            debug_mode=getattr(settings, "debug", False),
        )
        if critical_runtime is None
        else critical_runtime
    )
    if (exact_replay or critical) and _normalize_required_persistence_profile_impl(
        required_profile
    ) == "degraded_observable":
        required_profile = DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    if not manifest_enabled:
        raise RuntimeError(
            "Pipeline execution requires run manifests; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    _validate_manifest_persistence_requirements(
        yaml_config=yaml_config,
        skip_gold=skip_gold,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        strict_exact_replay_supported=True,
    )
    return True, ledger_enabled

def resolve_runner_control_plane_policy(
    settings: object,
    *,
    yaml_config: object | None = None,
    skip_gold: bool = False,
    required_profile_override: object | None = None,
    exact_replay: bool = False,
) -> ResolvedRunnerControlPlanePolicy:
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    configured_profile = getattr(
        control_plane,
        "required_persistence_profile",
        DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    )
    requested_profile = (
        required_profile_override
        if required_profile_override is not None
        and str(required_profile_override).strip()
        else configured_profile
    )
    critical_runtime = is_critical_reproducibility_runtime(
        runtime_environment=getattr(settings, "env", None),
        debug_mode=getattr(settings, "debug", False),
    )
    if (
        exact_replay or critical_runtime
    ) and _normalize_required_persistence_profile_impl(
        requested_profile
    ) == "degraded_observable":
        requested_profile = DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    required_profile = _normalize_required_persistence_profile_impl(requested_profile)
    manifest_enabled, ledger_enabled = resolve_control_plane_flags(
        settings,
        yaml_config=yaml_config,
        skip_gold=skip_gold,
        exact_replay=exact_replay,
        critical_runtime=critical_runtime,
        required_profile_override=(
            requested_profile if requested_profile != configured_profile else None
        ),
    )
    return ResolvedRunnerControlPlanePolicy(
        manifest_enabled=manifest_enabled,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
    )
