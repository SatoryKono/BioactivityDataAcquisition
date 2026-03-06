"""Unified mapping layer between infrastructure and domain exceptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.exceptions import (
    BioETLError,
    CriticalError,
    ExternalServiceError,
    RateLimitExceededError,
    RecoverableError,
    ServiceUnavailableError,
    get_domain_exception_context,
)
from bioetl.domain.exceptions.bounded_context import DomainExceptionContext
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import ErrorType

__all__ = [
    "DomainErrorMappingInput",
    "DomainInfraExceptionMapper",
    "InfraErrorDisposition",
]

_AUTH_STATUS_CODES = frozenset({401, 403})
_RATE_LIMIT_STATUS_CODE = 429
_DEFAULT_RETRY_AFTER_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class DomainErrorMappingInput:
    """Normalized data needed to map infrastructure failures into domain errors."""

    error: Exception
    provider: str
    error_type: ErrorType
    status_code: int | None = None
    retry_after: float | None = None


@dataclass(frozen=True, slots=True)
class InfraErrorDisposition:
    """Infrastructure handling profile resolved from a domain exception."""

    context: DomainExceptionContext
    severity: Literal["critical", "recoverable", "data_quality"]
    retryable: bool


class DomainInfraExceptionMapper:
    """Bidirectional mapper: infra failures -> domain errors, domain -> infra profile."""

    def __init__(self, *, logger: LoggerPort) -> None:
        self._logger = logger

    def map_to_domain_error(
        self,
        payload: DomainErrorMappingInput,
    ) -> ExternalServiceError:
        """Map infrastructure-side adapter failure into domain exception taxonomy."""
        if payload.status_code is not None:
            return self._map_with_status_code(payload)
        return self._map_without_status_code(payload)

    def map_domain_to_infra_disposition(
        self,
        error: BioETLError,
    ) -> InfraErrorDisposition:
        """Map domain exception into infra handling profile (retry + severity)."""
        context = get_domain_exception_context(error)
        if isinstance(error, CriticalError):
            return InfraErrorDisposition(
                context=context,
                severity="critical",
                retryable=False,
            )
        if isinstance(error, RecoverableError):
            return InfraErrorDisposition(
                context=context,
                severity="recoverable",
                retryable=True,
            )
        return InfraErrorDisposition(
            context=context,
            severity="data_quality",
            retryable=False,
        )

    def _map_with_status_code(
        self,
        payload: DomainErrorMappingInput,
    ) -> ExternalServiceError:
        message = str(payload.error)
        status_code = payload.status_code
        assert status_code is not None

        if status_code in _AUTH_STATUS_CODES:
            raise CriticalError(
                f"{payload.provider} authentication failed (HTTP {status_code}): {message}"
            ) from payload.error

        if status_code == _RATE_LIMIT_STATUS_CODE:
            retry_after = payload.retry_after or _DEFAULT_RETRY_AFTER_SECONDS
            self._logger.info(
                "http_error_wrapped_rate_limit",
                provider=payload.provider,
                status_code=status_code,
                retry_after=retry_after,
                recovery_action="retry_after_delay",
            )
            return RateLimitExceededError(
                message=message,
                service_name=payload.provider,
                retry_after=retry_after,
            )

        if status_code >= 500:
            self._logger.info(
                "http_error_wrapped_server_error",
                provider=payload.provider,
                status_code=status_code,
                retry_after=payload.retry_after,
                recovery_action="retry_with_backoff",
            )
            return ServiceUnavailableError(
                message=message,
                service_name=payload.provider,
                status_code=status_code,
                retry_after=payload.retry_after,
            )

        self._logger.debug(
            "http_error_wrapped_generic",
            provider=payload.provider,
            status_code=status_code,
            retry_after=payload.retry_after,
            recovery_action="no_retry",
        )
        return ExternalServiceError(
            message=message,
            service_name=payload.provider,
            status_code=status_code,
            retry_after=payload.retry_after,
        )

    def _map_without_status_code(
        self,
        payload: DomainErrorMappingInput,
    ) -> ExternalServiceError:
        message = str(payload.error)

        if payload.error_type.is_critical():
            raise CriticalError(
                f"Critical {payload.provider} error ({payload.error_type.value}): {message}"
            ) from payload.error

        if payload.error_type == ErrorType.RATE_LIMIT:
            retry_after = payload.retry_after or _DEFAULT_RETRY_AFTER_SECONDS
            self._logger.info(
                "error_wrapped_rate_limit",
                provider=payload.provider,
                error_type=payload.error_type.value,
                retry_after=retry_after,
                original_error=type(payload.error).__name__,
            )
            return RateLimitExceededError(
                message=message,
                service_name=payload.provider,
                retry_after=retry_after,
            )

        if payload.error_type == ErrorType.TIMEOUT:
            self._logger.info(
                "error_wrapped_timeout",
                provider=payload.provider,
                error_type=payload.error_type.value,
                retry_after=payload.retry_after,
                original_error=type(payload.error).__name__,
            )
            return ServiceUnavailableError(
                message=message,
                service_name=payload.provider,
                retry_after=payload.retry_after,
            )

        self._logger.debug(
            "error_wrapped_generic",
            provider=payload.provider,
            error_type=payload.error_type.value,
            status_code=payload.status_code,
            retry_after=payload.retry_after,
            original_error=type(payload.error).__name__,
        )
        return ExternalServiceError(
            message=message,
            service_name=payload.provider,
            status_code=payload.status_code,
            retry_after=payload.retry_after,
        )
