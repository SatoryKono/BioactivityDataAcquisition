"""Centralized error handling service for BioETL.

This service provides consistent error handling across the application,
including logging, metrics, and error transformation. It acts as a single
point of control for all error handling policies.

REQ-ARCH-013: Application layer should handle errors consistently
REQ-OBS-001: Errors should be logged with full context
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bioetl.domain.exceptions.base_exceptions import (
    BioETLDomainError,
    BioETLIntegrationError,
)
from bioetl.domain.ports import LoggerPort, MetricsPort


class ErrorHandlerService:
    """Centralized error handling service."""

    def __init__(
        self,
        logger: LoggerPort,
        metrics: MetricsPort,
        service_name: str = "bioetl",
    ) -> None:
        """Initialize error handler."""
        self._logger = logger
        self._metrics = metrics
        self._service_name = service_name

    def handle_error(
        self,
        exception: Exception,
        context: dict[
            str,
            Any,  # Any: Generic context data from various sources
        ]
        | None = None,
        reraise: bool = True,
    ) -> None:
        """Handle one exception with logging and metrics."""
        self._log_error(exception, context)
        self._record_error_metrics(exception)
        if reraise:
            raise exception

    def handle_and_transform(
        self,
        exception: Exception,
        transform_func: Callable[[Exception], Exception],
        context: dict[
            str,
            Any,  # Any: Generic context data from various sources
        ]
        | None = None,
        reraise: bool = True,
    ) -> None:
        """Transform an exception, then handle the transformed result."""
        domain_exception = None
        try:
            domain_exception = transform_func(exception)
            self.handle_error(domain_exception, context, reraise=reraise)
        except Exception as transform_error:
            if domain_exception and isinstance(transform_error, type(domain_exception)):
                if reraise:
                    raise transform_error
            else:
                self._logger.error(
                    "Exception transformation failed",
                    original_exception=str(exception),
                    transformation_error=str(transform_error),
                    context=context or {},
                )
                self._log_error(exception, context)
                self._record_error_metrics(exception)
                if reraise:
                    raise exception from transform_error

    def wrap_function(
        self,
        func: Callable[..., Any],  # Any: Generic function that can return any type
        error_transformer: Callable[[Exception], Exception] | None = None,
        **kwargs: Any,  # Any: Generic arguments for wrapped functions
    ) -> Any:  # Any: Generic return type from wrapped functions
        """Wrap one function call with error handling."""
        try:
            return func(**kwargs)
        except Exception as e:
            if error_transformer:
                self.handle_and_transform(
                    e,
                    error_transformer,
                    context={"function": func.__name__},
                    reraise=True,
                )
            else:
                self.handle_error(
                    e,
                    context={"function": func.__name__},
                    reraise=True,
                )

    def _log_error(
        self,
        exception: Exception,
        context: dict[
            str,
            Any,  # Any: Logging context carries heterogeneous scalar payloads from callers.
        ]
        | None = None,
    ) -> None:
        """Log an error with full context."""
        log_context = self._prepare_log_context(exception, context)

        if isinstance(exception, BioETLIntegrationError) and exception.is_retryable:
            self._logger.warning("Retryable integration error occurred", **log_context)
        else:
            self._logger.error("Error occurred", **log_context)

    def _record_error_metrics(
        self,
        exception: Exception,
    ) -> None:
        """Record error metrics."""
        error_type = self._get_error_type(exception)

        # Increment error counter
        self._increment_counter(
            "errors.total",
            1,
            labels={
                "error_type": error_type,
                "service": self._service_name,
            },
        )

        # Record specific error types
        if isinstance(exception, BioETLIntegrationError):
            self._increment_counter(
                "errors.integration",
                1,
                labels={
                    "service": exception.service_name or "unknown",
                    "operation": exception.operation or "unknown",
                },
            )
        elif isinstance(exception, BioETLDomainError):
            self._increment_counter(
                "errors.domain",
                1,
                labels={"service": self._service_name},
            )

    def _increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment metrics via the canonical or legacy counter API."""
        increment_counter = getattr(self._metrics, "increment_counter", None)
        if callable(increment_counter):
            increment_counter(name, value, labels=labels)
            return

        increment = getattr(self._metrics, "increment", None)
        if not callable(increment):
            return

        for kwargs in (
            {"value": float(value), "_tags": labels},
            {"tags": labels},
            {"_tags": labels},
            {},
        ):
            try:
                increment(name, **kwargs)
                return
            except TypeError:
                continue

    def _prepare_log_context(
        self,
        exception: Exception,
        context: dict[
            str,
            Any,  # Any: Generic context data for logging
        ]
        | None = None,
    ) -> dict[
        str,
        Any,  # Any: Prepared log context remains a heterogeneous structured payload.
    ]:
        """Prepare context dictionary for logging."""
        log_context = context or {}

        # Add basic exception information
        log_context.update(
            {
                "error_type": self._get_error_type(exception),
                "error_message": str(exception),
                "service": self._service_name,
            }
        )

        # Add domain exception context if available (without duplicating basic fields)
        if isinstance(exception, BioETLDomainError):
            domain_context = exception.to_dict()
            # Add only the additional context, not the basic fields
            if "context" in domain_context:
                log_context.update(domain_context["context"])

        return log_context

    def _get_error_type(self, exception: Exception) -> str:
        """Get the error type for classification."""
        if isinstance(exception, BioETLIntegrationError):
            return "integration_error"
        elif isinstance(exception, BioETLDomainError):
            return "domain_error"
        else:
            return exception.__class__.__name__

    def create_validation_error(
        self,
        message: str,
        field_name: str,
        invalid_value: Any,  # Any: Generic invalid value from various sources
        context: dict[
            str,
            Any,  # Any: Generic context data for validation errors
        ]
        | None = None,
    ) -> None:
        """Create and handle a validation error."""
        from bioetl.domain.exceptions.base_exceptions import BioETLValidationError

        error = BioETLValidationError(
            message=message,
            field_name=field_name,
            invalid_value=invalid_value,
            context=context or {},
        )
        self.handle_error(error, context, reraise=True)

    def create_config_error(
        self,
        message: str,
        config_key: str,
        context: dict[
            str,
            Any,  # Any: Generic context data for configuration errors
        ]
        | None = None,
    ) -> None:
        """Create and handle a configuration error."""
        from bioetl.domain.exceptions.base_exceptions import BioETLConfigurationError

        error = BioETLConfigurationError(
            message=message,
            config_key=config_key,
            context=context or {},
        )
        self.handle_error(error, context, reraise=True)

    def create_data_quality_error(
        self,
        message: str,
        record_id: str | None = None,
        severity: str = "warning",
        context: dict[
            str,
            Any,  # Any: Generic context data for data quality errors
        ]
        | None = None,
    ) -> None:
        """Create and handle a data quality error."""
        from bioetl.domain.exceptions.base_exceptions import BioETLDataQualityError

        error = BioETLDataQualityError(
            message=message,
            record_id=record_id,
            severity=severity,
            context=context or {},
        )
        self.handle_error(error, context, reraise=True)

    def create_integration_error(
        self,
        message: str,
        service_name: str,
        operation: str,
        is_retryable: bool = True,
        context: dict[
            str,
            Any,  # Any: Generic context data for integration errors
        ]
        | None = None,
    ) -> None:
        """Create and handle an integration error."""
        error = BioETLIntegrationError(
            message=message,
            service_name=service_name,
            operation=operation,
            is_retryable=is_retryable,
            context=context or {},
        )
        self.handle_error(error, context, reraise=True)


ErrorHandler = ErrorHandlerService
