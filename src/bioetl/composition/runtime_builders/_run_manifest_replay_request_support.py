"""Replay-request helper logic for run-manifest creation."""

from __future__ import annotations

from bioetl.composition.runtime_builders._run_manifest_attr_support import (
    read_attr as _read_attr,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_policy import (
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
    manifest_support: object,
    request_inputs: object,
    reproducibility_context: object,
) -> dict[str, object]:
    return manifest_support.build_launch_context_snapshot(
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
