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
"""Tests for runtime observability bootstrap entrypoints."""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest


pytestmark = pytest.mark.unit


def test_runtime_observability_import_does_not_load_heavy_adapters() -> None:
    """Importing the runtime entrypoint must keep optional adapters lazy."""
    module_name = "bioetl.composition.bootstrap.runtime.observability"
    heavy_modules = {
        "bioetl.infrastructure.observability.anomaly",
        "bioetl.infrastructure.observability.prometheus_metrics",
        "bioetl.infrastructure.observability.tracing",
        "bioetl.infrastructure.observability.unified_logger",
    }
    saved_modules = {
        name: sys.modules.pop(name, None) for name in (module_name, *heavy_modules)
    }

    try:
        importlib.import_module(module_name)

        loaded_heavy_modules = sorted(
            name for name in heavy_modules if name in sys.modules
        )
        assert loaded_heavy_modules == []
    finally:
        sys.modules.pop(module_name, None)
        for name, module in saved_modules.items():
            if module is not None:
                sys.modules[name] = module


@pytest.mark.unit
class TestBootstrapLoggerPort:
    """Tests for bootstrap_logger runtime entrypoint."""

    @patch(
        "bioetl.composition.bootstrap.runtime.logger_bootstrap._default_logger_factory"
    )
    def test_bootstrap_logger_delegates_to_unified_logger(
        self,
        mock_logger_factory: MagicMock,
    ) -> None:
        """bootstrap_logger should pass runtime metadata to UnifiedLogger."""
        from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger

        run_id = deterministic_uuid_from_callsite("test_observability_entrypoints")
        expected_logger = MagicMock()
        mock_logger_factory.return_value = expected_logger

        logger = bootstrap_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            log_level="INFO",
        )

        assert logger is expected_logger
        mock_logger_factory.assert_called_once_with("test_pipeline", run_id, "INFO")


@pytest.mark.unit
class TestMaybeStartMetricsServer:
    """Tests for maybe_start_metrics_server runtime entrypoint."""

    @patch(
        "bioetl.composition.bootstrap.runtime.metrics_bootstrap.create_metrics_service"
    )
    def test_passes_config_params(
        self,
        mock_bootstrap_metrics_service: MagicMock,
    ) -> None:
        """Runtime wrapper should pass settings through to server startup."""
        from bioetl.composition.bootstrap.runtime.observability import (
            maybe_start_metrics_server,
        )

        settings = MagicMock()
        settings.metrics_port = 9090
        settings.metrics_addr = "0.0.0.0"
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 5
        settings.observability.metrics_retry_delay = 2.0

        mock_service = MagicMock()
        mock_service.start.return_value = MagicMock(success=True)
        mock_bootstrap_metrics_service.return_value = mock_service

        result = maybe_start_metrics_server(settings)

        assert result is True
        mock_service.start.assert_called_once_with(
            port=9090,
            addr="0.0.0.0",
            fail_fast=False,
            retry_count=5,
            retry_delay=2.0,
        )

    @patch(
        "bioetl.composition.bootstrap.runtime.metrics_bootstrap.create_metrics_service"
    )
    def test_fail_fast_true_raises_error(
        self,
        mock_bootstrap_metrics_service: MagicMock,
    ) -> None:
        """Fail-fast mode should propagate MetricsServerError to callers."""
        from bioetl.composition.bootstrap.runtime.observability import (
            maybe_start_metrics_server,
        )
        from bioetl.composition.observability_api import MetricsServerError

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = True
        settings.observability.metrics_retry_count = 3
        settings.observability.metrics_retry_delay = 1.0

        mock_service = MagicMock()
        mock_service.start.side_effect = MetricsServerError(
            port=8000,
            reason="port_in_use",
        )
        mock_bootstrap_metrics_service.return_value = mock_service

        with pytest.raises(MetricsServerError) as exc_info:
            maybe_start_metrics_server(settings)

        assert exc_info.value.port == 8000
        assert exc_info.value.reason == "port_in_use"

    @patch(
        "bioetl.composition.bootstrap.runtime.metrics_bootstrap.create_metrics_service"
    )
    def test_fail_fast_false_propagates_error(
        self,
        mock_bootstrap_metrics_service: MagicMock,
    ) -> None:
        """Unexpected startup errors should still bubble up to entrypoints."""
        from bioetl.composition.bootstrap.runtime.observability import (
            maybe_start_metrics_server,
        )

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 3
        settings.observability.metrics_retry_delay = 1.0

        mock_service = MagicMock()
        mock_service.start.side_effect = Exception("Random failure")
        mock_bootstrap_metrics_service.return_value = mock_service

        with pytest.raises(Exception, match="Random failure"):
            maybe_start_metrics_server(settings)

    def test_disabled_metrics_returns_false(self) -> None:
        """Disabled metrics should short-circuit without server startup."""
        from bioetl.composition.bootstrap.runtime.observability import (
            maybe_start_metrics_server,
        )

        settings = MagicMock()
        settings.observability.metrics_enabled = False

        result = maybe_start_metrics_server(settings)

        assert result is False

    def test_disabled_metrics_server_returns_false(self) -> None:
        """Disabled metrics server should short-circuit without startup."""
        from bioetl.composition.bootstrap.runtime.observability import (
            maybe_start_metrics_server,
        )

        settings = MagicMock()
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = False

        result = maybe_start_metrics_server(settings)

        assert result is False
