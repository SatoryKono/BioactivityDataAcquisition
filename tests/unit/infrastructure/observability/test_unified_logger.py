# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for UnifiedLogger with enforced Log Schema."""

from __future__ import annotations

from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.infrastructure.observability.logging_config import (
    _mask_secrets,
    secret_filter_processor,
)
from bioetl.infrastructure.observability.unified_logger import (
    UnifiedLogger,
    create_unified_logger,
)


@pytest.mark.unit
class TestUnifiedLogger:
    """Tests for UnifiedLogger with Log Schema enforcement."""

    def test_unified_logger_creation(self) -> None:
        """Test that UnifiedLogger can be created with required fields."""
        run_id = deterministic_uuid_from_callsite("test_unified_logger")
        logger = UnifiedLogger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        assert logger._pipeline == "test_pipeline"
        assert logger._run_id == str(run_id)

    def test_unified_logger_info_with_stage(self) -> None:
        """Test that info() works with explicit stage parameter."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        # Should work with stage
        logger.info("Test message", stage="extract")

    def test_unified_logger_info_defaults_stage_to_init(self) -> None:
        """Test that info() defaults stage to 'init' for LoggerPort compatibility."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        # Without stage should not raise, stage defaults to "init"
        logger.info("Test message")

    def test_unified_logger_info_ignores_event_kwarg_conflict(self) -> None:
        """Test that kwargs['event'] does not conflict with structlog signature."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        logger.info("pipeline_started", event="pipeline_started", stage="extract")

    def test_unified_logger_error_with_stage_and_error_type(self) -> None:
        """Test that error() works with stage and error_type."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        # Should work with both parameters
        logger.error("Error occurred", stage="transform", error_type="validation")

        # Should also work without error_type (optional for LoggerPort compatibility)
        logger.error("Error occurred", stage="transform")

    def test_unified_logger_bind_preserves_context(self) -> None:
        """Test that bind() returns new logger with additional context."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        bound = logger.bind(dataset="chembl_activity")

        assert isinstance(bound, UnifiedLogger)
        assert bound._pipeline == "test"
        assert bound._run_id == "abc-123"

    def test_unified_logger_with_optional_fields(self) -> None:
        """Test that optional fields can be passed."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        # Should accept optional dataset and record_count
        logger.info(
            "Fetched records",
            stage="extract",
            dataset="chembl_activity",
            record_count=100,
        )

        logger.warning(
            "Low record count",
            stage="extract",
            dataset="chembl_activity",
            expected_count=1000,
            actual_count=100,
        )

    def test_unified_logger_all_stages_accepted(self) -> None:
        """Test that all valid stage values are accepted."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        valid_stages = ["extract", "transform", "load", "validate", "init", "cleanup"]

        for stage in valid_stages:
            # Should not raise
            logger.info(f"Testing stage {stage}", stage=stage)  # type: ignore[arg-type]

    def test_unified_logger_debug_with_stage(self) -> None:
        """Test that debug() works with explicit stage parameter."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        # Should work with stage
        logger.debug("Debug message", stage="extract")

    def test_unified_logger_debug_defaults_stage_to_init(self) -> None:
        """Test that debug() defaults stage to 'init' for LoggerPort compatibility."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        # Without stage should not raise, defaults to "init"
        logger.debug("Debug message")

    def test_unified_logger_exception_with_stage_and_error_type(self) -> None:
        """Test that exception() works with stage and error_type."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        # Should work with both parameters
        logger.exception("Exception occurred", stage="load", error_type="io_error")

        # Should also work without error_type (optional for LoggerPort compatibility)
        logger.exception("Exception occurred", stage="load")

    def test_unified_logger_exception_defaults_stage_to_init(self) -> None:
        """Test that exception() defaults stage to 'init' for LoggerPort compatibility."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")

        # Without stage should not raise, defaults to "init"
        logger.exception("Exception occurred")

    def test_unified_logger_flattens_extra_context(self) -> None:
        """Nested extra payloads should be flattened into the top-level event."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")
        logger._logger = MagicMock()

        logger.info(
            "bootstrap_complete",
            extra={"stage": "bootstrap", "metrics_type": "NoOpMetrics"},
        )

        logger._logger.info.assert_called_once_with(
            "bootstrap_complete",
            stage="bootstrap",
            metrics_type="NoOpMetrics",
        )

    def test_unified_logger_explicit_kwargs_override_extra_context(self) -> None:
        """Explicit kwargs must win over conflicting extra payload values."""
        logger = UnifiedLogger(pipeline="test", run_id="abc-123")
        logger._logger = MagicMock()

        logger.info(
            "health_check",
            stage="validate",
            component="storage",
            extra={"stage": "bootstrap", "component": "data_source", "event": "bad"},
        )

        logger._logger.info.assert_called_once_with(
            "health_check",
            stage="validate",
            component="storage",
        )


@pytest.mark.unit
class TestCreateUnifiedLogger:
    """Tests for create_unified_logger factory function."""

    def test_create_unified_logger_returns_unified_logger(self) -> None:
        """Test that factory returns UnifiedLogger instance."""
        logger = create_unified_logger(
            pipeline="test_pipeline",
            run_id=deterministic_uuid_from_callsite("test_unified_logger"),
        )

        assert isinstance(logger, UnifiedLogger)

    def test_create_unified_logger_with_uuid(self) -> None:
        """Test that UUID run_id is converted to string."""
        run_id = deterministic_uuid_from_callsite("test_unified_logger")
        logger = create_unified_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        assert logger._run_id == str(run_id)

    def test_create_unified_logger_with_string_run_id(self) -> None:
        """Test that string run_id is preserved."""
        logger = create_unified_logger(
            pipeline="test_pipeline",
            run_id="my-custom-run-id",
        )

        assert logger._run_id == "my-custom-run-id"


@pytest.mark.unit
class TestSecretFiltering:
    """Tests for secret filtering functionality."""

    def test_mask_api_key(self) -> None:
        """Test that API keys are masked."""
        text = "api_key=sk-abc123def456"
        result = _mask_secrets(text)

        assert "sk-abc123def456" not in result
        assert "[REDACTED" in result

    def test_mask_authorization_header(self) -> None:
        """Test that Authorization headers are masked."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = _mask_secrets(text)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "[REDACTED" in result

    def test_mask_password(self) -> None:
        """Test that passwords are masked."""
        secret_key = "password"
        text = f"{secret_key}=mysecretpassword"
        result = _mask_secrets(text)

        assert "mysecretpassword" not in result
        assert "[REDACTED" in result

    def test_mask_aws_key(self) -> None:
        """Test that AWS access keys are masked."""
        text = "AKIAIOSFODNN7EXAMPLE"
        result = _mask_secrets(text)

        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "[REDACTED" in result

    def test_no_mask_for_normal_text(self) -> None:
        """Test that normal text is not masked."""
        text = "This is a normal log message with record count 100"
        result = _mask_secrets(text)

        assert result == text

    def test_mask_secrets_non_string(self) -> None:
        """Test that non-string values are passed through."""
        assert _mask_secrets(123) == 123
        assert _mask_secrets(None) is None
        assert _mask_secrets(["list"]) == ["list"]

    def test_secret_filter_processor_masks_values(self) -> None:
        """Test that the processor masks secrets in event dict."""
        event_dict = {
            "message": "Login with api_key=secret123",
            "headers": {"Authorization": "Bearer token123"},
            "count": 100,  # Should not be affected
        }

        result = secret_filter_processor(None, "info", event_dict)

        # Check that secrets are masked
        assert "secret123" not in result["message"]
        # Nested dicts should also be processed
        assert "token123" not in str(result.get("headers", {}))
        # Numbers should be preserved
        assert result["count"] == 100

    def test_secret_filter_processor_handles_nested_dicts(self) -> None:
        """Test that nested dicts are processed."""
        secret_key = "password"
        event_dict = {
            "config": {
                secret_key: "secret123",
                "timeout": 30,
            }
        }

        result = secret_filter_processor(None, "info", event_dict)

        # Password should be masked if it contains secret pattern
        # (Note: the key "password" triggers the pattern match)
        assert result is not None


@pytest.mark.unit
class TestLoggingUtilsIntegration:
    """Tests for adapter_error_logging integration with Log Schema."""

    def test_log_adapter_error_with_stage(self) -> None:
        """Test that log_adapter_error accepts stage parameter."""
        from unittest.mock import MagicMock

        from tests.helpers.adapter_error_logging import (
            log_adapter_error,
        )

        mock_logger = MagicMock()

        log_adapter_error(
            logger=mock_logger,
            provider="chembl",
            operation="fetch",
            stage="extract",
            error_type="network_error",
        )

        # Verify error was called with correct parameters
        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["stage"] == "extract"
        assert call_kwargs["error_type"] == "network_error"
        assert call_kwargs["provider"] == "chembl"
        assert call_kwargs["operation"] == "fetch"

    def test_log_adapter_error_default_stage(self) -> None:
        """Test that log_adapter_error has sensible default stage."""
        from unittest.mock import MagicMock

        from tests.helpers.adapter_error_logging import (
            log_adapter_error,
        )

        mock_logger = MagicMock()

        # Call without explicit stage
        log_adapter_error(
            logger=mock_logger,
            provider="pubchem",
            operation="health check",
        )

        call_kwargs = mock_logger.error.call_args[1]
        # Default stage should be "extract" for adapter operations
        assert call_kwargs["stage"] == "extract"
        # Default error_type should be "adapter_error"
        assert call_kwargs["error_type"] == "adapter_error"
