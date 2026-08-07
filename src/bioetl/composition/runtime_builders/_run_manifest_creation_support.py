"""Private helpers for run-manifest creation orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import bioetl.composition.runtime_builders.run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.manifest import RunManifestCreateSpec
from bioetl.composition.runtime_builders._run_manifest_attr_support import (
    read_attr as _read_attr,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
    RunManifestCreateRequestInputs,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
    assemble_manifest_create_spec as _assemble_manifest_create_spec,
    build_manifest_source_refs as _build_manifest_source_refs,
    create_ledger_service as _create_ledger_service,
)
from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    resolve_code_revision_for_manifest,
    validate_required_runtime_persistence_profile,
)
from bioetl.composition.runtime_builders._run_manifest_replay_support import (
    apply_replay_assessment as _apply_replay_assessment,
    build_manifest_launch_context as _build_manifest_launch_context,
    build_replay_assessment as _build_replay_assessment,
    validate_exact_replay_boundary as _validate_exact_replay_boundary,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.ports import MetricsPort

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger import (
        RunLedgerService as Ledger,
    )
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.domain.context import PipelineRunContext as Context


def build_manifest_create_request(
    request_inputs: RunManifestCreateRequestInputs,
) -> RunManifestCreateSpec:
    """Build the canonical RunManifest create request."""
    ctx = request_inputs.ctx
    inputs = request_inputs.inputs
    reproducibility_context = request_inputs.reproducibility_context
    _validate_exact_replay_boundary(ctx, reproducibility_context)
    source_refs = _build_manifest_source_refs(
        manifest_support=_manifest_support,
        ctx=ctx,
        inputs=inputs,
        provider=request_inputs.provider,
        entity=request_inputs.entity,
        required_persistence_profile=(
            reproducibility_context.required_persistence_profile
        ),
    )
    replay_of_run_id, replay_of_manifest_id = (
        _manifest_support.resolve_replay_parentage(
            ctx=ctx,
            runtime_config=inputs.runtime_config,
        )
    )
    replay_capability = _manifest_support.resolve_replay_capability(
        source_refs=source_refs,
        resume_requested=bool(_read_attr(ctx, "resume", False)),
    )
    launch_context = _build_manifest_launch_context(
        manifest_support=_manifest_support,
        request_inputs=request_inputs,
        reproducibility_context=reproducibility_context,
    )
    replay_assessment = _build_replay_assessment(
        request_inputs=request_inputs,
        reproducibility_context=reproducibility_context,
        source_refs=source_refs,
        replay_capability=replay_capability,
    )
    _apply_replay_assessment(launch_context, replay_assessment)
    request = _assemble_manifest_create_spec(
        request_inputs=request_inputs,
        source_refs=source_refs,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        code_revision=resolve_code_revision_for_manifest(
            resolved_config_hash=request_inputs.resolved_config_hash,
            test_mode=bool(_read_attr(inputs.settings, "test_mode", False)),
        ),
        replay_capability=replay_capability,
        launch_context=launch_context,
    )
    validate_required_runtime_persistence_profile(
        request=request,
        required_persistence_profile=(
            reproducibility_context.required_persistence_profile
        ),
        strict_exact_replay_supported=(
            reproducibility_context.strict_exact_replay_supported
        ),
    )
    return request


def _launch_context_value(
    launch_context: object, key: str, default: object = None
) -> object:
    if isinstance(launch_context, Mapping):
        return launch_context.get(key, default)
    return _read_attr(launch_context, key, default)


def _resolve_replay_reconstructability_status(
    *,
    request: RunManifestCreateSpec,
    strict_exact_replay_supported: bool,
    strict_requirement: bool,
    precomputed: Mapping[str, object] | None,
) -> tuple[str, bool]:
    """Return (status, effective_strict_requirement)."""
    if precomputed is not None:
        strict_requirement = bool(
            precomputed.get("strict_requirement_requested", strict_requirement)
        )
        assessment_capability = precomputed.get("replay_capability")
        capability_value = (
            assessment_capability
            if isinstance(assessment_capability, str)
            else request.replay_capability.value
        )
        supported = bool(
            precomputed.get(
                "strict_exact_replay_supported", strict_exact_replay_supported
            )
        )
        not_ok = strict_requirement and (
            not supported
            or capability_value != ReplayCapability.EXACT_REPLAY_SUPPORTED.value
        )
        return (
            "not_reconstructable" if not_ok else "reconstructable",
            strict_requirement,
        )
    not_ok = strict_requirement and (
        not strict_exact_replay_supported
        or request.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    )
    return ("not_reconstructable" if not_ok else "reconstructable", strict_requirement)


def emit_replay_reconstructability_metric(
    *,
    request: RunManifestCreateSpec,
    strict_exact_replay_supported: bool,
    metrics: MetricsPort | None,
) -> None:
    """Emit replay reconstructability metrics for one manifest request."""
    if metrics is None:
        return

    launch_context = request.launch_context
    strict_replay_requested = bool(
        _launch_context_value(launch_context, "exact_replay", False)
    )
    required_persistence_profile = str(
        _launch_context_value(launch_context, "required_persistence_profile")
        or DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )
    # Prefer assessment already attached
    # do not recompute reproducibility d
    precomputed_raw = _launch_context_value(
        launch_context, "reproducibility_policy_assessment"
    )
    precomputed = precomputed_raw if isinstance(precomputed_raw, Mapping) else None
    strict_requirement = (
        strict_replay_requested
        or required_persistence_profile in STRICT_PERSISTENCE_PROFILES
    )
    status, strict_requirement = _resolve_replay_reconstructability_status(
        request=request,
        strict_exact_replay_supported=strict_exact_replay_supported,
        strict_requirement=strict_requirement,
        precomputed=precomputed,
    )
    raw_run_type = _read_attr(request.run_type, "value", request.run_type)
    run_type = str(raw_run_type or "unknown").strip().lower().replace(" ", "_")
    bounded_run_type = run_type or "unknown"
    metrics.increment_counter(
        "bioetl_replay_reconstructability_events_total",
        value=1,
        labels={
            "pipeline": request.pipeline_name,
            "replay_capability": request.replay_capability.value,
            "strict_requirement": "true" if strict_requirement else "false",
            "status": status,
        },
    )
    lag_status = "not_requested"
    if status == "not_reconstructable":
        lag_status = "blocked"
    elif strict_replay_requested:
        lag_status = "ready"
    replay_labels = {
        "pipeline": request.pipeline_name,
        "run_type": bounded_run_type,
        "replay_capability": request.replay_capability.value,
    }
    lag_seconds = _resolve_replay_lag_seconds(
        launch_context=launch_context,
        lag_status=lag_status,
    )
    if lag_seconds is not None:
        metrics.set_gauge(
            "bioetl_replay_lag_seconds",
            value=float(lag_seconds),
            labels={**replay_labels, "status": lag_status},
        )

    if status == "not_reconstructable":
        metrics.increment_counter(
            "bioetl_replay_drift_events_total",
            value=1,
            labels={
                **replay_labels,
                "drift_type": "strict_replay_not_reconstructable",
                "status": "detected",
            },
        )


def _resolve_replay_lag_seconds(
    *,
    launch_context: object,
    lag_status: str,
) -> float | None:
    from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
        resolve_replay_lag_seconds as _resolve,
    )

    return _resolve(
        launch_context=launch_context,
        lag_status=lag_status,
        read_attr=_read_attr,
    )


def create_ledger_service(inputs: RunnerInputs, ctx: Context) -> Ledger | None:
    """Keep the public ownership seam local to this support module."""
    return _create_ledger_service(inputs, ctx)
