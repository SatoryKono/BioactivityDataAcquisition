"""Tests for centralized error handler.

This module tests the ErrorHandler service and its integration with
logging and metrics ports.
"""

from __future__ import annotations


import pytest

from bioetl.application.services.error_handler import ErrorHandler
from bioetl.domain.exceptions.base_exceptions import (
    BioETLDomainError,
    BioETLIntegrationError,
    BioETLValidationError,
    BioETLConfigurationError,
    BioETLDataQualityError,
)


class MockLoggerPort:
    """Mock implementation of LoggerPort for testing."""

    def __init__(self) -> None:
        self.logs = []

    def error(self, message: str | None = None, **kwargs: dict) -> None:
        # Handle both styles: error("msg") and error(message="msg", ...)
        actual_message = message or kwargs.get("message", "")
        # Remove 'message' from kwargs to avoid duplication
        log_kwargs = {k: v for k, v in kwargs.items() if k != "message"}
        self.logs.append(("ERROR", actual_message, log_kwargs))

    def warning(self, message: str | None = None, **kwargs: dict) -> None:
        # Handle both styles: warning("msg") and warning(message="msg", ...)
        actual_message = message or kwargs.get("message", "")
        # Remove 'message' from kwargs to avoid duplication
        log_kwargs = {k: v for k, v in kwargs.items() if k != "message"}
        self.logs.append(("WARNING", actual_message, log_kwargs))

    def info(self, message: str | None = None, **kwargs: dict) -> None:
        # Handle both styles: info("msg") and info(message="msg", ...)
        actual_message = message or kwargs.get("message", "")
        # Remove 'message' from kwargs to avoid duplication
        log_kwargs = {k: v for k, v in kwargs.items() if k != "message"}
        self.logs.append(("INFO", actual_message, log_kwargs))


class MockMetricsPort:
    """Mock implementation of MetricsPort for testing."""

    def __init__(self) -> None:
        self.metrics = []

    def increment(self, metric_name: str, tags: dict | None = None) -> None:
        self.metrics.append((metric_name, tags or {}))


class TestErrorHandlerInitialization:
    """Test error handler initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default service name."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()

        handler = ErrorHandler(logger, metrics)

        assert handler._service_name == "bioetl"
        assert handler._logger is logger
        assert handler._metrics is metrics

    def test_init_with_custom_service_name(self) -> None:
        """Test initialization with custom service name."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()

        handler = ErrorHandler(logger, metrics, service_name="test-service")

        assert handler._service_name == "test-service"


class TestErrorHandlerBasicFunctionality:
    """Test basic error handling functionality."""

    def test_handle_error_with_reraise(self) -> None:
        """Test error handling with re-raise."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        with pytest.raises(ValueError):
            handler.handle_error(ValueError("Test error"), reraise=True)

        # Verify logging and metrics
        assert len(logger.logs) == 1
        assert len(metrics.metrics) == 1  # Only total for non-domain errors

    def test_handle_error_without_reraise(self) -> None:
        """Test error handling without re-raise."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        # Should not raise
        handler.handle_error(ValueError("Test error"), reraise=False)

        # Verify logging and metrics
        assert len(logger.logs) == 1
        assert len(metrics.metrics) == 1  # Only total for non-domain errors

    def test_handle_error_with_context(self) -> None:
        """Test error handling with additional context."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        with pytest.raises(ValueError):
            handler.handle_error(
                ValueError("Test error"),
                context={"user_id": "123", "operation": "update"},
                reraise=True,
            )

        # Verify context is included in logs
        assert len(logger.logs) == 1
        _, log_context = logger.logs[0][1], logger.logs[0][2]
        assert log_context["user_id"] == "123"
        assert log_context["operation"] == "update"


class TestErrorHandlerDomainExceptions:
    """Test handling of domain-specific exceptions."""

    def test_handle_domain_error(self) -> None:
        """Test handling of domain errors."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        error = BioETLDomainError(
            message="Test domain error", context={"field": "value"}
        )

        with pytest.raises(BioETLDomainError):
            handler.handle_error(error, reraise=True)

        # Verify domain error metrics
        metric_names = [m[0] for m in metrics.metrics]
        assert "errors.domain" in metric_names

    def test_handle_integration_error(self) -> None:
        """Test handling of integration errors."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        error = BioETLIntegrationError(
            message="Service unavailable",
            service_name="api-service",
            operation="fetch",
            is_retryable=True,
        )

        with pytest.raises(BioETLIntegrationError):
            handler.handle_error(error, reraise=True)

        # Verify integration error metrics
        metric_names = [m[0] for m in metrics.metrics]
        assert "errors.integration" in metric_names

    def test_retryable_integration_error_logs_warning(self) -> None:
        """Test that retryable integration errors log as warning."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        error = BioETLIntegrationError(
            message="Service unavailable",
            service_name="api-service",
            operation="fetch",
            is_retryable=True,
        )

        with pytest.raises(BioETLIntegrationError):
            handler.handle_error(error, reraise=True)

        # Verify warning level logging
        assert logger.logs[0][0] == "WARNING"


class TestErrorHandlerTransformations:
    """Test error transformation functionality."""

    def test_handle_and_transform_success(self) -> None:
        """Test successful error transformation."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        def transform_func(exc: Exception) -> BioETLDomainError:
            return BioETLDomainError(
                message="Transformed error", context={"original": str(exc)}
            )

        with pytest.raises(BioETLDomainError) as exc_info:
            handler.handle_and_transform(
                ValueError("Original error"), transform_func, reraise=True
            )

        assert "Transformed error" in str(exc_info.value)

    def test_handle_and_transform_failure(self) -> None:
        """Test error transformation failure falls back to original error."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        def failing_transform_func(exc: Exception) -> BioETLDomainError:
            raise RuntimeError("Transformation failed")

        with pytest.raises(ValueError):  # Original error should be raised
            handler.handle_and_transform(
                ValueError("Original error"), failing_transform_func, reraise=True
            )

        # Verify transformation error was logged
        transformation_logs = [
            log for log in logger.logs if "transformation failed" in log[1].lower()
        ]
        assert len(transformation_logs) == 1


class TestErrorHandlerConvenienceMethods:
    """Test convenience methods for creating specific error types."""

    def test_create_validation_error(self) -> None:
        """Test validation error creation."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        with pytest.raises(BioETLValidationError) as exc_info:
            handler.create_validation_error(
                message="Invalid email",
                field_name="email",
                invalid_value="invalid@example",
                context={"pattern": "^\\S+@\\S+\\.\\S+$"},
            )

        error = exc_info.value
        assert error.field_name == "email"
        assert error.invalid_value == "invalid@example"

    def test_create_config_error(self) -> None:
        """Test configuration error creation."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        with pytest.raises(BioETLConfigurationError) as exc_info:
            handler.create_config_error(
                message="Missing API key",
                config_key="api.key",
                context={"env": "production"},
            )

        error = exc_info.value
        assert error.config_key == "api.key"

    def test_create_data_quality_error(self) -> None:
        """Test data quality error creation."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        with pytest.raises(BioETLDataQualityError) as exc_info:
            handler.create_data_quality_error(
                message="Invalid data format",
                record_id="record-123",
                severity="error",
                context={"field": "age", "value": -5},
            )

        error = exc_info.value
        assert error.record_id == "record-123"
        assert error.severity == "error"

    def test_create_integration_error(self) -> None:
        """Test integration error creation."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        with pytest.raises(BioETLIntegrationError) as exc_info:
            handler.create_integration_error(
                message="API timeout",
                service_name="external-api",
                operation="fetch_data",
                is_retryable=True,
                context={"timeout": 30},
            )

        error = exc_info.value
        assert error.service_name == "external-api"
        assert error.operation == "fetch_data"
        assert error.is_retryable is True


class TestErrorHandlerFunctionWrapping:
    """Test function wrapping functionality."""

    def test_wrap_function_success(self) -> None:
        """Test successful function wrapping."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        def test_func(x: int) -> int:
            return x * 2

        result = handler.wrap_function(test_func, x=5)
        assert result == 10
        assert len(logger.logs) == 0  # No errors

    def test_wrap_function_with_error(self) -> None:
        """Test function wrapping with error."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        def failing_func() -> None:
            raise ValueError("Function failed")

        with pytest.raises(ValueError):
            handler.wrap_function(failing_func)

        # Verify error was handled
        assert len(logger.logs) == 1
        assert len(metrics.metrics) == 1  # Only total for non-domain errors

    def test_wrap_function_with_transform(self) -> None:
        """Test function wrapping with error transformation."""
        logger = MockLoggerPort()
        metrics = MockMetricsPort()
        handler = ErrorHandler(logger, metrics)

        def failing_func() -> None:
            raise ValueError("Original error")

        def transform_func(exc: Exception) -> BioETLDomainError:
            return BioETLDomainError(
                message="Transformed function error", context={"original": str(exc)}
            )

        with pytest.raises(BioETLDomainError) as exc_info:
            handler.wrap_function(failing_func, error_transformer=transform_func)

        assert "Transformed function error" in str(exc_info.value)
