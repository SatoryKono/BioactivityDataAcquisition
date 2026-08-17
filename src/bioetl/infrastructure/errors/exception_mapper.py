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
type InfrastructureSourceError = (
    OSError | RuntimeError | ValueError | LookupError | AssertionError | BioETLError
)


@dataclass(frozen=True, slots=True)
class DomainErrorMappingInput:
    """Normalized data needed to map infrastructure failures into domain errors."""

    error: InfrastructureSourceError
    provider: str
    error_type: ErrorType
    status_code: int | None = None
    retry_after: float | None = None
    entity: str | None = None
    pipeline: str | None = None
    operation: str | None = None


@dataclass(frozen=True, slots=True)
class InfraErrorDisposition:
    """Infrastructure handling profile resolved from a domain exception."""

    context: DomainExceptionContext
    severity: Literal["critical", "recoverable", "data_quality"]
    retryable: bool


def _decorate_mapped_error[MappedExternalError: ExternalServiceError](
    *,
    error: MappedExternalError,
    reason_code: str,
    payload: DomainErrorMappingInput,
) -> MappedExternalError:
    """Attach standardized reason code, context, and root cause metadata."""
    error.reason_code = reason_code
    error.with_context(
        provider=payload.provider,
        entity=payload.entity,
        pipeline=payload.pipeline,
        operation=payload.operation,
    )
    error.__cause__ = payload.error
    return error


def _raise_critical(
    *,
    message: str,
    reason_code: str,
    payload: DomainErrorMappingInput,
) -> None:
    """Raise critical error with taxonomy reason code and contextual payload."""
    critical = CriticalError(message)
    critical.reason_code = reason_code
    critical.with_context(
        provider=payload.provider,
        entity=payload.entity,
        pipeline=payload.pipeline,
        operation=payload.operation,
    )
    raise critical from payload.error


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
        """Map an HTTP-status-bearing failure to a domain exception.

        Routing: 401/403 → CriticalError (auth), 429 → RateLimitExceededError,
        5xx → ServiceUnavailableError, other → generic ExternalServiceError.

        Args:
            payload: Normalized error input with a non-None status_code.

        Returns:
            Decorated domain exception with reason code and causal chain.

        Raises:
            CriticalError: For authentication failures (401/403).
        """
        message = str(payload.error)
        status_code = payload.status_code
        assert status_code is not None

        if status_code in _AUTH_STATUS_CODES:
            _raise_critical(
                payload=payload,
                message=(
                    f"{payload.provider} authentication failed "
                    f"(HTTP {status_code}): {message}"
                ),
                reason_code="ADAPTER_AUTH_FAILED",
            )

        if status_code == _RATE_LIMIT_STATUS_CODE:
            return self._map_rate_limit_status(
                payload=payload,
                status_code=status_code,
                message=message,
            )

        if status_code >= 500:
            return self._map_server_error_status(
                payload=payload,
                status_code=status_code,
                message=message,
            )

        return self._map_generic_http_error(
            payload=payload,
            status_code=status_code,
            message=message,
        )

    def _map_without_status_code(
        self,
        payload: DomainErrorMappingInput,
    ) -> ExternalServiceError:
        """Map a non-HTTP failure to a domain exception using ErrorType.

        Routing: critical types → CriticalError, RATE_LIMIT → RateLimitExceededError,
        TIMEOUT → ServiceUnavailableError, other → generic ExternalServiceError.

        Args:
            payload: Normalized error input without an HTTP status code.

        Returns:
            Decorated domain exception with reason code and causal chain.

        Raises:
            CriticalError: For error types classified as critical.
        """
        message = str(payload.error)

        if payload.error_type.is_critical():
            _raise_critical(
                message=(
                    f"Critical {payload.provider} error "
                    f"({payload.error_type.value}): {message}"
                ),
                reason_code="ADAPTER_CRITICAL_ERROR",
                payload=payload,
            )

        if payload.error_type == ErrorType.RATE_LIMIT:
            retry_after = payload.retry_after or _DEFAULT_RETRY_AFTER_SECONDS
            self._logger.info(
                "error_wrapped_rate_limit",
                provider=payload.provider,
                error_type=payload.error_type.value,
                retry_after=retry_after,
                original_error=type(payload.error).__name__,
            )
            mapped_rate_limit = RateLimitExceededError(
                message=message,
                service_name=payload.provider,
                retry_after=retry_after,
            )
            return _decorate_mapped_error(
                error=mapped_rate_limit,
                reason_code="ADAPTER_RATE_LIMIT_ERROR",
                payload=payload,
            )

        if payload.error_type == ErrorType.TIMEOUT:
            self._logger.info(
                "error_wrapped_timeout",
                provider=payload.provider,
                error_type=payload.error_type.value,
                retry_after=payload.retry_after,
                original_error=type(payload.error).__name__,
            )
            mapped_timeout = ServiceUnavailableError(
                message=message,
                service_name=payload.provider,
                retry_after=payload.retry_after,
            )
            return _decorate_mapped_error(
                error=mapped_timeout,
                reason_code="ADAPTER_TIMEOUT_ERROR",
                payload=payload,
            )

        from bioetl.infrastructure.observability.logging_helpers import log_debug

        log_debug(
            self._logger,
            (
                f"error_wrapped_generic: provider={payload.provider}, "
                f"error_type={payload.error_type.value}, "
                f"status_code={payload.status_code}, "
                f"retry_after={payload.retry_after}, "
                f"original_error={type(payload.error).__name__}"
            ),
        )
        mapped_external = ExternalServiceError(
            message=message,
            service_name=payload.provider,
            status_code=payload.status_code,
            retry_after=payload.retry_after,
        )
        return _decorate_mapped_error(
            error=mapped_external,
            reason_code="ADAPTER_EXTERNAL_ERROR",
            payload=payload,
        )

    def _map_rate_limit_status(
        self,
        *,
        payload: DomainErrorMappingInput,
        status_code: int,
        message: str,
    ) -> ExternalServiceError:
        """Map HTTP 429 into RateLimitExceededError with retry metadata."""
        retry_after = payload.retry_after or _DEFAULT_RETRY_AFTER_SECONDS
        self._logger.info(
            "http_error_wrapped_rate_limit",
            provider=payload.provider,
            status_code=status_code,
            retry_after=retry_after,
            recovery_action="retry_after_delay",
        )
        mapped_rate_limit = RateLimitExceededError(
            message=message,
            service_name=payload.provider,
            retry_after=retry_after,
        )
        return _decorate_mapped_error(
            error=mapped_rate_limit,
            reason_code="ADAPTER_HTTP_RATE_LIMIT",
            payload=payload,
        )

    def _map_server_error_status(
        self,
        *,
        payload: DomainErrorMappingInput,
        status_code: int,
        message: str,
    ) -> ExternalServiceError:
        """Map HTTP 5xx failures into ServiceUnavailableError."""
        self._logger.info(
            "http_error_wrapped_server_error",
            provider=payload.provider,
            status_code=status_code,
            retry_after=payload.retry_after,
            recovery_action="retry_with_backoff",
        )
        mapped_server_error = ServiceUnavailableError(
            message=message,
            service_name=payload.provider,
            status_code=status_code,
            retry_after=payload.retry_after,
        )
        return _decorate_mapped_error(
            error=mapped_server_error,
            reason_code="ADAPTER_HTTP_SERVER_ERROR",
            payload=payload,
        )

    def _map_generic_http_error(
        self,
        *,
        payload: DomainErrorMappingInput,
        status_code: int,
        message: str,
    ) -> ExternalServiceError:
        """Map non-auth, non-rate-limit, non-5xx HTTP errors generically."""
        from bioetl.infrastructure.observability.logging_helpers import log_debug

        log_debug(
            self._logger,
            (
                f"http_error_wrapped_generic: provider={payload.provider}, "
                f"status_code={status_code}, "
                f"retry_after={payload.retry_after}, "
                "recovery_action=no_retry"
            ),
        )
        mapped_external = ExternalServiceError(
            message=message,
            service_name=payload.provider,
            status_code=status_code,
            retry_after=payload.retry_after,
        )
        return _decorate_mapped_error(
            error=mapped_external,
            reason_code="ADAPTER_HTTP_ERROR",
            payload=payload,
        )
