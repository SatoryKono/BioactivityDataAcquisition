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
    log_fields: dict[str, object] | None = None,
    emit_warning_error_log: bool = False,
) -> bool:
    """Log one postrun failure according to strict/warning mode policy.

    Returns:
        True when the caller should re-raise the exception, False otherwise.
    """
    log_extra = dict(log_fields or {})

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


def apply_postrun_failure_policy_or_raise(
    *,
    logger: LoggerPort,
    runtime: object,
    error: BaseException,
    spec: PostrunFailurePolicySpec,
    log_fields: dict[str, object] | None = None,
    emit_warning_error_log: bool = False,
) -> None:
    """Apply warning/strict policy and re-raise when strict mode demands it."""
    should_raise = apply_postrun_failure_policy(
        logger=logger,
        runtime=runtime,
        error=error,
        spec=spec,
        log_fields=log_fields,
        emit_warning_error_log=emit_warning_error_log,
    )
    if should_raise:
        raise error


class PostrunStrictValidationMixin:
    """Compatibility mixin for postrun collaborators exposing strict mode check."""

    if TYPE_CHECKING:
        _runtime: object

    def _is_strict_validation_enabled(self) -> bool:
        """Compatibility wrapper around shared strict-mode evaluation."""
        return is_strict_validation_enabled(self._runtime)


class PostrunFailureHandlingMixin(PostrunStrictValidationMixin):
    """Shared allowlisted failure handling for postrun collaborators."""

    if TYPE_CHECKING:
        _logger: LoggerPort
        _FAILURE_POLICY: PostrunFailurePolicySpec

    def _handle_allowlisted_failure(
        self,
        error: BaseException,
        *,
        log_fields: dict[str, object] | None = None,
        emit_warning_error_log: bool = False,
    ) -> None:
        """Apply postrun warning/strict policy using instance-held collaborators."""
        apply_postrun_failure_policy_or_raise(
            logger=self._logger,
            runtime=self._runtime,
            error=error,
            spec=self._FAILURE_POLICY,
            log_fields=log_fields,
            emit_warning_error_log=emit_warning_error_log,
        )
