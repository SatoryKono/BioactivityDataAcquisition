"""Tests for internal error handling support functions."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from bioetl.domain.types import ErrorType
from bioetl.infrastructure.adapters.adapter_error_classifier import ErrorCategory
from bioetl.infrastructure.adapters._error_handling_support import (
    AdapterErrorContext,
    build_adapter_error_context,
    emit_error_telemetry,
    extract_retry_after,
    safe_optional_str,
)


class TestBuildAdapterErrorContext:
    def test_builds_correct_context(self) -> None:
        context_dict = {
            "retry_count": 3,
            "circuit_breaker_state": "OPEN",
            "retry_after": 10.5,
            "some_extra": "value",
            "status_code": 500, # reserved, should be stripped from extra
        }

        result = build_adapter_error_context(
            provider="test_provider",
            operation="test_operation",
            context=context_dict,
            error_type=ErrorType.TIMEOUT,
            error_category=ErrorCategory.RECOVERABLE,
            status_code=500,
        )

        assert result.provider == "test_provider"
        assert result.operation == "test_operation"
        assert result.status_code == 500
        assert result.retry_count == 3
        assert result.circuit_breaker_state == "OPEN"
        assert result.error_type == ErrorType.TIMEOUT
        assert result.error_category == ErrorCategory.RECOVERABLE
        assert result.retry_after == 10.5
        assert result.extra == {"some_extra": "value"}

    def test_handles_missing_fields(self) -> None:
        result = build_adapter_error_context(
            provider="test_provider",
            operation="test_operation",
            context={},
            error_type=ErrorType.RATE_LIMIT,
            error_category=ErrorCategory.CRITICAL,
            status_code=None,
        )

        assert result.retry_count == 0
        assert result.circuit_breaker_state is None
        assert result.retry_after is None
        assert result.extra == {}


class TestEmitErrorTelemetry:
    def test_emits_telemetry_with_metrics(self) -> None:
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        error = ValueError("Test error message")

        context = AdapterErrorContext(
            provider="test_provider",
            operation="test_operation",
            status_code=500,
            retry_count=2,
            circuit_breaker_state="HALF_OPEN",
            retry_after=5.0,
            extra={"batch_id": "123"},
        )

        emit_error_telemetry(
            logger=mock_logger,
            metrics=mock_metrics,
            provider="test_provider",
            operation="test_operation",
            error=error,
            error_type=ErrorType.TIMEOUT,
            error_category=ErrorCategory.RECOVERABLE,
            error_context=context,
            status_code=500,
        )

        mock_logger.error.assert_called_once_with(
            "external_api_error",
            provider="test_provider",
            operation="test_operation",
            error_category=ErrorCategory.RECOVERABLE.value,
            error_type=ErrorType.TIMEOUT.value,
            is_critical=ErrorType.TIMEOUT.is_critical(),
            is_recoverable=ErrorType.TIMEOUT.is_recoverable(),
            status_code=500,
            retry_count=2,
            circuit_breaker_state="HALF_OPEN",
            retry_after=5.0,
            error="Test error message",
            error_class="ValueError",
            batch_id="123",
        )

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_adapter_error_taxonomy_total",
            1,
            {
                "provider": "test_provider",
                "operation": "test_operation",
                "error_category": ErrorCategory.RECOVERABLE.value,
                "error_type": ErrorType.TIMEOUT.value,
            },
        )

    def test_handles_none_metrics(self) -> None:
        mock_logger = MagicMock()
        error = ValueError("Test error")
        context = AdapterErrorContext(
            provider="p", operation="o"
        )

        emit_error_telemetry(
            logger=mock_logger,
            metrics=None,
            provider="p",
            operation="o",
            error=error,
            error_type=ErrorType.AUTH_FAILURE,
            error_category=ErrorCategory.CRITICAL,
            error_context=context,
            status_code=None,
        )

        mock_logger.error.assert_called_once()


class TestExtractRetryAfter:
    def test_extracts_valid_float(self) -> None:
        response = httpx.Response(429, headers={"Retry-After": "15.5"})
        assert extract_retry_after(response) == 15.5

    def test_extracts_valid_int(self) -> None:
        response = httpx.Response(429, headers={"Retry-After": "30"})
        assert extract_retry_after(response) == 30.0

    def test_returns_none_if_missing(self) -> None:
        response = httpx.Response(429)
        assert extract_retry_after(response) is None

    def test_returns_default_for_invalid_value(self) -> None:
        # e.g. HTTP date formats which we don't parse yet
        response = httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"})
        assert extract_retry_after(response) == 60.0


class TestSafeOptionalStr:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("hello", "hello"),
            ("  hello  ", "hello"),
            ("", None),
            ("   ", None),
            (None, None),
            (123, None),
            ({"key": "value"}, None),
        ]
    )
    def test_safe_optional_str(self, value: object, expected: str | None) -> None:
        assert safe_optional_str(value) == expected
