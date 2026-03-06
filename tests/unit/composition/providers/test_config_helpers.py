"""Unit tests for _config_helpers — generic HTTP data source creator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestCreateHttpDataSource:
    """Tests for _create_http_data_source generic helper."""

    @patch(
        "bioetl.composition.providers._config_helpers._wrap_with_filter",
    )
    @patch(
        "bioetl.composition.factories.adapter_helpers_factory.AdapterHelpersFactory",
    )
    @patch(
        "bioetl.composition.providers.factory_loader.get_http_client_factory",
    )
    def test_assembles_adapter_with_helpers_and_wraps(
        self,
        mock_get_http_factory: MagicMock,
        mock_helpers_factory_cls: MagicMock,
        mock_wrap: MagicMock,
    ) -> None:
        from bioetl.composition.providers._config_helpers import (
            _create_http_data_source,
        )

        # Setup HTTP client factory
        mock_http_factory = MagicMock()
        mock_get_http_factory.return_value = mock_http_factory
        mock_http_client = MagicMock(name="http_client")
        mock_http_factory.create_for_provider.return_value = mock_http_client

        # Setup helper services
        mock_helpers = MagicMock()
        mock_helpers.as_injection_kwargs.return_value = {
            "error_handler": MagicMock(),
            "adapter_metrics": MagicMock(),
        }
        mock_helpers_factory_cls.create_http_helpers.return_value = mock_helpers

        # Setup adapter factory
        mock_adapter = MagicMock(name="adapter")
        adapter_factory = MagicMock(return_value=mock_adapter)

        mock_wrapped = MagicMock(name="wrapped")
        mock_wrap.return_value = mock_wrapped

        settings = MagicMock()
        logger = MagicMock()
        metrics = MagicMock()

        result = _create_http_data_source(
            provider="test_provider",
            settings=settings,
            logger=logger,
            filter_config=None,
            metrics=metrics,
            pipeline_name="test_pipeline",
            adapter_factory=adapter_factory,
            extra_kwargs={"custom_param": "value"},
        )

        # Verify HTTP client created for provider
        mock_http_factory.create_for_provider.assert_called_once_with(
            "test_provider", settings, metrics=metrics
        )

        # Verify helpers created
        mock_helpers_factory_cls.create_http_helpers.assert_called_once_with(
            provider="test_provider", logger=logger, metrics=metrics
        )

        # Verify adapter factory called with merged kwargs
        call_kwargs = adapter_factory.call_args.kwargs
        assert call_kwargs["http_client"] is mock_http_client
        assert call_kwargs["logger"] is logger
        assert call_kwargs["metrics"] is metrics
        assert call_kwargs["custom_param"] == "value"
        assert "error_handler" in call_kwargs

        # Verify wrap with filter
        mock_wrap.assert_called_once_with(
            mock_adapter, None, logger, metrics, "test_pipeline"
        )
        assert result is mock_wrapped
