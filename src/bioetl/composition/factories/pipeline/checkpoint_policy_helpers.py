"""Helpers for resolving checkpoint compatibility policy in composition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

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
        return cast(CheckpointCompatibilityPolicy, raw_policy)
    if raw_policy is not None:
        logger_port.warning(
            "Unsupported checkpoint compatibility policy in settings; "
            "falling back to soft_fail.",
            pipeline=pipeline.config.pipeline_name,
            policy=raw_policy,
            default=_DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY,
        )
    return _DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY


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
    return requested_policy
