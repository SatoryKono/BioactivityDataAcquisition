"""Centralized error handling service for BioETL.

This service provides consistent error handling across the application,
including logging, metrics, and error transformation. It acts as a single
point of control for all error handling policies.

REQ-ARCH-013: Application layer should handle errors consistently
REQ-OBS-001: Errors should be logged with full context
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Type

from bioetl.domain.exceptions.base_exceptions import (
    BioETLDomainError,
    BioETLIntegrationError,
)
from bioetl.domain.ports import LoggerPort, MetricsPort


class ErrorHandler:
    """Centralized error handling service.

    This service provides consistent error handling, logging, and metrics
    collection across the entire application.
    """

    def __init__(
        self,
        logger: LoggerPort,
        metrics: MetricsPort,
        service_name: str = "bioetl",
    ) -> None:
        """Initialize error handler.

        Args:
            logger: Logger port for structured logging
            metrics: Metrics port for error metrics
            service_name: Name of the service for context
        """
        self._logger = logger
        self._metrics = metrics
        self._service_name = service_name

    def handle_error(
        self,
        exception: Exception,
        context: Dict[
            str,
            Any,  # Any: Generic context data from various sources
        ]
        | None = None,
        reraise: bool = True,
    ) -> None:
        """Handle an exception with logging and metrics.

        Args:
            exception: The exception to handle
            context: Additional context for logging
            reraise: Whether to re-raise the exception after handling

        Raises:
            The original exception if reraise=True
        """
        # Log the error
        self._log_error(exception, context)

        # Record metrics
        self._record_error_metrics(exception)

        # Re-raise if requested
        if reraise:
            raise exception

    def handle_and_transform(
        self,
        exception: Exception,
        transform_func: Callable[[Exception], Exception],
        context: Dict[
            str,
            Any,  # Any: Generic context data from various sources
        ]
        | None = None,
        reraise: bool = True,
    ) -> None:
        """Handle an exception and transform it to a domain exception.

        Args:
            exception: The original exception
            transform_func: Function to transform exception to domain exception
            context: Additional context for logging
            reraise: Whether to re-raise the transformed exception

        Raises:
            The transformed exception if reraise=True
        """
        domain_exception = None
        try:
            # Transform the exception
            domain_exception = transform_func(exception)

            # Handle the transformed exception
            # Note: handle_error will re-raise the domain_exception if reraise=True
            self.handle_error(domain_exception, context, reraise=reraise)

        except Exception as transform_error:
            # Only catch actual transformation errors, not the transformed exception itself
            if domain_exception and isinstance(transform_error, type(domain_exception)):
                # This is the transformed exception being raised as expected
                if reraise:
                    raise transform_error
            else:
                # If transformation fails, log the failure and handle the original exception
                self._logger.error(
                    "Exception transformation failed",
                    original_exception=str(exception),
                    transformation_error=str(transform_error),
                    context=context or {},
                )
                # Log the original exception but don't re-raise to avoid infinite recursion
                self._log_error(exception, context)
                self._record_error_metrics(exception)
                if reraise:
                    raise exception

    def wrap_function(
        self,
        func: Callable[..., Any],  # Any: Generic function that can return any type
        error_transformer: Optional[Callable[[Exception], Exception]] = None,
        **kwargs: Any,  # Any: Generic arguments for wrapped functions
    ) -> Any:  # Any: Generic return type from wrapped functions
        """Wrap a function call with error handling.

        Args:
            func: Function to wrap
            error_transformer: Optional function to transform exceptions
            **kwargs: Arguments to pass to the function

        Returns:
            Result of the function call

        Raises:
            Transformed exception if error_transformer is provided
            Original exception otherwise
        """
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
        context: Dict[
            str,
            Any,  # Any: Logging context carries heterogeneous scalar payloads from callers.
        ] = None,
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
        self._metrics.increment(
            "errors.total",
            tags={
                "error_type": error_type,
                "service": self._service_name,
            },
        )

        # Record specific error types
        if isinstance(exception, BioETLIntegrationError):
            self._metrics.increment(
                "errors.integration",
                tags={
                    "service": exception.service_name or "unknown",
                    "operation": exception.operation or "unknown",
                },
            )
        elif isinstance(exception, BioETLDomainError):
            self._metrics.increment(
                "errors.domain",
                tags={"service": self._service_name},
            )

    def _prepare_log_context(
        self,
        exception: Exception,
        context: Dict[
            str,
            Any,  # Any: Generic context data for logging
        ]
        | None = None,
    ) -> Dict[
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
        context: Dict[
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
            context=context,
        )
        self.handle_error(error, context, reraise=True)

    def create_config_error(
        self,
        message: str,
        config_key: str,
        context: Dict[
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
            context=context,
        )
        self.handle_error(error, context, reraise=True)

    def create_data_quality_error(
        self,
        message: str,
        record_id: str | None = None,
        severity: str = "warning",
        context: Dict[
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
            context=context,
        )
        self.handle_error(error, context, reraise=True)

    def create_integration_error(
        self,
        message: str,
        service_name: str,
        operation: str,
        is_retryable: bool = True,
        context: Dict[
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
            context=context,
        )
        self.handle_error(error, context, reraise=True)
