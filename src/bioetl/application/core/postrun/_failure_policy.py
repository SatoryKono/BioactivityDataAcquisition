"""Shared strict/warning failure policy helpers for postrun collaborators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class PostrunFailurePolicySpec:
    """Structured log policy for one postrun failure category."""

    event: str
    strict_reason: str
    strict_reason_code: str
    warning_reason: str
    warning_reason_code: str


def is_strict_validation_enabled(runtime: object) -> bool:
    """Return True only when strict validation is explicitly enabled."""
    value = getattr(runtime, "strict_validation", False)
    return bool(value) if isinstance(value, bool) else False


def apply_postrun_failure_policy(
    *,
    logger: LoggerPort,
    runtime: object,
    error: BaseException,
    spec: PostrunFailurePolicySpec,
    extra: dict[str, object] | None = None,
    emit_warning_error_log: bool = False,
) -> bool:
    """Log one postrun failure according to strict/warning mode policy.

    Returns:
        True when the caller should re-raise the exception, False otherwise.
    """
    log_extra = dict(extra or {})

    if is_strict_validation_enabled(runtime):
        logger.error(
            spec.event,
            error=str(error),
            error_type=type(error).__name__,
            reason=spec.strict_reason,
            reason_code=spec.strict_reason_code,
            strict_mode=True,
            **log_extra,
        )
        return True

    warning_kwargs = {
        "error": str(error),
        "error_type": type(error).__name__,
        "reason": spec.warning_reason,
        "reason_code": spec.warning_reason_code,
        "strict_mode": False,
        **log_extra,
    }
    if emit_warning_error_log:
        logger.error(spec.event, **warning_kwargs)
    logger.warning(spec.event, **warning_kwargs)
    return False
