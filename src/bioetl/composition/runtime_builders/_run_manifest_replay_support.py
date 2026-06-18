"""Private replay helpers for run-manifest creation orchestration."""

from __future__ import annotations

from collections.abc import Mapping

import bioetl.composition.runtime_builders.run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec,
)
from bioetl.composition.runtime_builders._run_manifest_attr_support import (
    read_attr as _read_attr,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    assess_reproducibility_policy,
)


def _validate_exact_replay_boundary(ctx: object, context: object) -> None:
    if not bool(_read_attr(ctx, "exact_replay", False)):
        return
    if bool(_read_attr(context, "strict_exact_replay_supported", False)):
        return
    raise RuntimeError(
        "Pipeline execution is outside the published strict exact-replay "
        "support boundary for this run family"
    )


def _build_manifest_launch_context(
    *,
    request_inputs: object,
    reproducibility_context: object,
) -> dict[str, object]:
    return _manifest_support.build_launch_context_snapshot(
        _read_attr(request_inputs, "ctx"),
        run_type_value=_read_attr(request_inputs, "run_type_value"),
        execution_context_value=_read_attr(request_inputs, "execution_context_value"),
        configured_required_persistence_profile=_read_attr(
            reproducibility_context, "configured_required_persistence_profile"
        ),
        required_persistence_profile=_read_attr(
            reproducibility_context, "required_persistence_profile"
        ),
        required_persistence_profile_opt_down=bool(
            _read_attr(
                reproducibility_context,
                "required_persistence_profile_opt_down",
                False,
            )
        ),
        strict_exact_replay_supported=_read_attr(
            reproducibility_context, "strict_exact_replay_supported"
        ),
        reproducibility_family=_read_attr(reproducibility_context, "family"),
        replay_family_contract=_read_attr(
            reproducibility_context, "replay_family_contract"
        ),
        strict_replay_runtime_verdict=_read_attr(
            reproducibility_context, "strict_replay_runtime_verdict"
        ),
        replay_support_scope=_read_attr(reproducibility_context, "support_scope"),
        replay_support_reason=_read_attr(reproducibility_context, "reason"),
    )


def _build_replay_assessment(
    *,
    request_inputs: object,
    reproducibility_context: object,
    source_refs: tuple[object, ...],
    replay_capability: ReplayCapability,
) -> object:
    return assess_reproducibility_policy(
        source_refs=source_refs,
        required_persistence_profile=_read_attr(
            reproducibility_context, "required_persistence_profile"
        ),
        strict_exact_replay_supported=_read_attr(
            reproducibility_context, "strict_exact_replay_supported"
        ),
        exact_replay_requested=bool(
            _read_attr(_read_attr(request_inputs, "ctx"), "exact_replay", False)
        ),
        resume_requested=bool(
            _read_attr(_read_attr(request_inputs, "ctx"), "resume", False)
        ),
        replay_capability=replay_capability,
        run_type=_read_attr(request_inputs, "run_type_value"),
        debug_only=bool(
            _read_attr(
                _read_attr(_read_attr(request_inputs, "inputs"), "settings"),
                "debug",
                False,
            )
        ),
    )


def _apply_replay_assessment(
    launch_context: dict[str, object],
    replay_assessment: object,
) -> None:
    replay_verdict = _read_attr(replay_assessment, "replay_readiness_verdict").value
    launch_context.update(
        {
            "replay_readiness_verdict": replay_verdict,
            "exact_replay_ready": replay_verdict == "exact_replay_ready",
            "replay_blockers": list(_read_attr(replay_assessment, "blocking_gaps")),
        }
    )


def emit_replay_reconstructability_metric(
    *,
    request: RunManifestCreateSpec,
    strict_exact_replay_supported: bool,
    metrics: object,
) -> None:
    """Emit replay reconstructability metrics for one manifest request."""
    increment_counter = _read_attr(metrics, "increment_counter", None)
    if not callable(increment_counter):
        return
    set_gauge = _read_attr(metrics, "set_gauge", None)
    launch_context = request.launch_context
    strict_replay_requested = bool(
        launch_context.get("exact_replay", False)
        if isinstance(launch_context, Mapping)
        else _read_attr(launch_context, "exact_replay", False)
    )
    required_persistence_profile = str(
        (
            launch_context.get("required_persistence_profile")
            if isinstance(launch_context, Mapping)
            else _read_attr(launch_context, "required_persistence_profile")
        )
        or DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )
    strict_requirement = (
        strict_replay_requested
        or required_persistence_profile in STRICT_PERSISTENCE_PROFILES
    )
    status = "reconstructable"
    if strict_requirement and (
        not strict_exact_replay_supported
        or request.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        status = "not_reconstructable"
    raw_run_type = _read_attr(request.run_type, "value", request.run_type)
    run_type = str(raw_run_type or "unknown").strip().lower().replace(" ", "_")
    bounded_run_type = run_type or "unknown"
    increment_counter(
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
    if callable(set_gauge):
        set_gauge(
            "bioetl_replay_lag_seconds",
            value=0.0,
            labels={**replay_labels, "status": lag_status},
        )
    if status == "not_reconstructable":
        increment_counter(
            "bioetl_replay_drift_events_total",
            value=1,
            labels={
                **replay_labels,
                "drift_type": "strict_replay_not_reconstructable",
                "status": "detected",
            },
        )
