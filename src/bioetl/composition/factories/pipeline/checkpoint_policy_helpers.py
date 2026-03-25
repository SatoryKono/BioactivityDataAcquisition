"""Helpers for resolving checkpoint compatibility policy in composition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.domain.ports import LoggerPort

CheckpointCompatibilityPolicy = Literal["observe", "soft_fail", "hard_fail"]
_DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY: CheckpointCompatibilityPolicy = "soft_fail"
_ALLOWED_CHECKPOINT_COMPATIBILITY_POLICIES: tuple[CheckpointCompatibilityPolicy, ...] = (
    "observe",
    "soft_fail",
    "hard_fail",
)


def resolve_checkpoint_compatibility_policy(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> CheckpointCompatibilityPolicy:
    """Resolve compatibility policy from pipeline runtime settings."""
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
            extra={
                "pipeline": pipeline.config.pipeline_name,
                "policy": raw_policy,
                "default": _DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY,
            },
        )
    return _DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY
