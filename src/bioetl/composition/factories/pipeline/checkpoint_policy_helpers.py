"""Helpers for resolving checkpoint compatibility policy in composition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from bioetl.domain.control_plane.reproducibility_policy import STRICT_PERSISTENCE_PROFILES

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.domain.ports import LoggerPort

CheckpointCompatibilityPolicy = Literal[
    "observe", "legacy_observe", "soft_fail", "hard_fail"
]
_DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY: CheckpointCompatibilityPolicy = "soft_fail"
_ALLOWED_CHECKPOINT_COMPATIBILITY_POLICIES: tuple[
    CheckpointCompatibilityPolicy, ...
] = (
    "observe",
    "legacy_observe",
    "soft_fail",
    "hard_fail",
)


def _resolve_requested_checkpoint_compatibility_policy(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> CheckpointCompatibilityPolicy:
    """Resolve the operator-selected policy before strict replay coercion."""
    settings = getattr(pipeline, "settings", None)
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    raw_policy = getattr(control_plane, "checkpoint_compatibility_policy", None)
    if (
        isinstance(raw_policy, str)
        and raw_policy in _ALLOWED_CHECKPOINT_COMPATIBILITY_POLICIES
    ):
        return raw_policy
    if raw_policy is not None:
        logger_port.warning(
            "Unsupported checkpoint compatibility policy in settings; "
            "falling back to soft_fail.",
            pipeline=pipeline.config.pipeline_name,
            policy=raw_policy,
            default=_DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY,
        )
    return _DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY


def _resolve_required_persistence_profile(
    *,
    pipeline: BasePipeline,
) -> str:
    """Resolve the declared minimum persistence profile for this runtime."""
    settings = getattr(pipeline, "settings", None)
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    raw_profile = getattr(control_plane, "required_persistence_profile", None)
    if isinstance(raw_profile, str) and raw_profile:
        return raw_profile
    return "degraded_observable"


def resolve_checkpoint_compatibility_policy(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> CheckpointCompatibilityPolicy:
    """Resolve compatibility policy from pipeline runtime settings."""
    requested_policy = _resolve_requested_checkpoint_compatibility_policy(
        pipeline=pipeline,
        logger_port=logger_port,
    )
    required_persistence_profile = _resolve_required_persistence_profile(
        pipeline=pipeline,
    )
    runtime = getattr(pipeline, "runtime", None)
    exact_replay = bool(getattr(runtime, "exact_replay", False))
    if exact_replay and requested_policy != "hard_fail":
        logger_port.warning(
            "Exact replay requires hard_fail checkpoint compatibility policy; "
            "coercing requested policy.",
            pipeline=pipeline.config.pipeline_name,
            exact_replay=True,
            requested_policy=requested_policy,
            applied_policy="hard_fail",
        )
        return "hard_fail"
    if (
        required_persistence_profile in STRICT_PERSISTENCE_PROFILES
        and requested_policy in {"observe", "legacy_observe"}
    ):
        logger_port.warning(
            "Required persistence profile enforces at least soft_fail "
            "checkpoint compatibility policy; coercing requested policy.",
            pipeline=pipeline.config.pipeline_name,
            required_persistence_profile=required_persistence_profile,
            requested_policy=requested_policy,
            applied_policy="soft_fail",
        )
        return "soft_fail"
    return requested_policy
