"""Control-plane assembly phase for runtime runner construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.composition.observability import (
    bind_manifest_logger_context as _bind_manifest_logger_context,
)
from bioetl.composition.runtime_builders._runner_control_plane_policy import (
    resolve_required_artifact_lineage_layers,
    resolve_runner_control_plane_policy as _resolve_runner_control_plane_policy,
    validate_required_persistence_profile,
)
from bioetl.composition.runtime_builders._runner_control_plane_data_root_policy import (
    validate_strict_data_root_policy as _validate_strict_data_root_policy,
)
from bioetl.composition.runtime_builders._context_field_binding import (
    bind_context_fields,
)
from bioetl.composition.runtime_builders.control_plane import (
    attach_manifest_id,
    create_run_manifest_with_effective_config,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    is_degraded_observable_profile_requested,
)

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.runner_inputs import (
        RunnerInputs as _RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext

__all__ = [
    "ControlPlaneSetupResult",
    "assemble_runner_control_plane",
    "resolve_required_artifact_lineage_layers",
    "validate_required_persistence_profile",
]


@dataclass(frozen=True, slots=True)
class ControlPlaneSetupResult:
    """Resolved control-plane collaborators for runtime runner assembly."""

    ctx: PipelineRunContext
    inputs: _RunnerInputs
    run_ledger_service: RunLedgerService | None
    required_profile: str


def _log_effective_required_persistence_profile(
    *,
    inputs: _RunnerInputs,
    configured_profile: str,
    effective_profile: str,
    manifest_enabled: bool,
    ledger_enabled: bool,
    exact_replay: bool,
) -> None:
    """Emit the canonical effective persistence profile after policy resolution."""
    observability = getattr(inputs, "observability", None)
    logger = getattr(observability, "logger", None)
    log_info = getattr(logger, "info", None)
    if not callable(log_info):
        return
    log_info(
        "control_plane_profile_resolved",
        stage="bootstrap",
        configured_required_persistence_profile=configured_profile,
        required_persistence_profile=effective_profile,
        run_manifest_enabled=manifest_enabled,
        run_ledger_enabled=ledger_enabled,
        exact_replay=exact_replay,
    )


def _bind_required_persistence_profile(
    ctx: PipelineRunContext,
    *,
    required_profile: str,
    opt_down_requested: bool,
) -> PipelineRunContext:
    """Return a context carrying the resolved persistence-profile policy."""
    return bind_context_fields(
        ctx,
        updates={
            "required_persistence_profile": required_profile,
            "required_persistence_profile_opt_down": opt_down_requested,
        },
        unsupported_message=(
            "PipelineRunContext must support persistence-profile attachment"
        ),
    )


def assemble_runner_control_plane(
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> ControlPlaneSetupResult:
    """Resolve manifest/ledger policy and attach control-plane identity anchors."""
    degraded_profile_opt_down_requested = is_degraded_observable_profile_requested(
        getattr(ctx, "required_persistence_profile", None)
    )
    control_plane_policy = _resolve_runner_control_plane_policy(
        inputs.settings,
        yaml_config=inputs.yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
        required_profile_override=getattr(ctx, "required_persistence_profile", None),
        exact_replay=bool(getattr(ctx, "exact_replay", False)),
    )
    _validate_strict_data_root_policy(
        settings=inputs.settings,
        required_profile=control_plane_policy.required_profile,
        exact_replay=bool(getattr(ctx, "exact_replay", False)),
    )
    ctx = _bind_required_persistence_profile(
        ctx,
        required_profile=control_plane_policy.required_profile,
        opt_down_requested=degraded_profile_opt_down_requested,
    )
    run_ledger_service: RunLedgerService | None = None

    effective_required_profile = control_plane_policy.required_profile
    if control_plane_policy.manifest_enabled:
        control_plane_refs, run_ledger_service = (
            create_run_manifest_with_effective_config(
                ctx=ctx,
                inputs=inputs,
                ledger_enabled=control_plane_policy.ledger_enabled,
            )
        )
        ctx = attach_manifest_id(
            ctx,
            control_plane_refs=control_plane_refs,
        )
        inputs = _bind_manifest_logger_context(
            inputs,
            control_plane_refs.manifest_id,
        )
        effective_required_profile = (
            control_plane_refs.required_persistence_profile
            or control_plane_policy.required_profile
        )
    _log_effective_required_persistence_profile(
        inputs=inputs,
        configured_profile=control_plane_policy.required_profile,
        effective_profile=effective_required_profile,
        manifest_enabled=control_plane_policy.manifest_enabled,
        ledger_enabled=control_plane_policy.ledger_enabled,
        exact_replay=bool(getattr(ctx, "exact_replay", False)),
    )

    return ControlPlaneSetupResult(
        ctx=ctx,
        inputs=inputs,
        run_ledger_service=run_ledger_service,
        required_profile=effective_required_profile,
    )
