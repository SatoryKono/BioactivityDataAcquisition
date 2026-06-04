"""Tests for CrossRef client observability helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.crossref.client_observability_helpers import (
    build_crossref_source_metadata,
    clear_crossref_request_collector,
    get_crossref_request_count,
    probe_crossref_health,
)

pytestmark = pytest.mark.unit


class TestBuildCrossrefSourceMetadata:
    """Tests for build_crossref_source_metadata."""

    @pytest.fixture
    def mock_request_collector(self):
        collector = MagicMock()
        collector.to_source_metadata = MagicMock(
            return_value=SourceMetadata(
                source_type="api",
                url="https://api.crossref.org",
                api_version="v1",
            )
        )
        collector.request_count = 42
        collector.clear = MagicMock()
        return collector

    def test_build_crossref_source_metadata_returns_metadata(self, mock_request_collector):
        """Test build_crossref_source_metadata returns SourceMetadata."""
        metadata = build_crossref_source_metadata(
            request_collector=mock_request_collector,
            api_base="https://api.crossref.org",
            api_version="v1",
        )

        assert isinstance(metadata, SourceMetadata)
        assert metadata.url == "https://api.crossref.org"
        assert metadata.api_version == "v1"

    def test_build_crossref_source_metadata_consumes_collector(self, mock_request_collector):
        """Test build_crossref_source_metadata consumes collector data."""
        build_crossref_source_metadata(
            request_collector=mock_request_collector,
            api_base="https://api.crossref.org",
        )

        mock_request_collector.to_source_metadata.assert_called_once_with(
            source_type="api",
            url="https://api.crossref.org",
            api_version=None,
            query_string=None,
        )
        mock_request_collector.clear.assert_called_once()


class TestClearCrossrefRequestCollector:
    """Tests for clear_crossref_request_collector."""

    @pytest.fixture
    def mock_request_collector(self):
        collector = MagicMock()
        collector.clear = MagicMock()
        return collector

    def test_clear_crossref_request_collector_clears_collector(self, mock_request_collector):
        """Test clear_crossref_request_collector clears collector."""
        clear_crossref_request_collector(request_collector=mock_request_collector)

        mock_request_collector.clear.assert_called_once()


class TestGetCrossrefRequestCount:
    """Tests for get_crossref_request_count."""

    @pytest.fixture
    def mock_request_collector(self):
        collector = MagicMock()
        collector.request_count = 42
        return collector

    def test_get_crossref_request_count_returns_count(self, mock_request_collector):
        """Test get_crossref_request_count returns request count."""
        count = get_crossref_request_count(request_collector=mock_request_collector)

        assert count == 42


class TestProbeCrossrefHealth:
    """Tests for probe_crossref_health."""

    @pytest.fixture
    def mock_http_client(self):
        client = MagicMock()
        client.get_once = AsyncMock()
        return client

    @pytest.fixture
    def mock_query_builder(self):
        builder = MagicMock()
        builder.build_health_probe_url = MagicMock(return_value="https://api.crossref.org/works")
        builder.build_health_probe_params = MagicMock(return_value={"test": "param"})
        return builder

    @pytest.fixture
    def mock_response_mapper(self):
        mapper = MagicMock()
        return mapper

    @pytest.fixture
    def mock_adapter_metrics(self):
        metrics = MagicMock()
        metrics.measure_request = MagicMock()
        return metrics

    @pytest.fixture
    def mock_logger(self):
        logger = MagicMock()
        logger.warning = MagicMock()
        return logger

    @pytest.mark.asyncio
    async def test_probe_crossref_health_success(
        self,
        mock_http_client,
        mock_query_builder,
        mock_response_mapper,
        mock_adapter_metrics,
        mock_logger,
    ):
        """Test probe_crossref_health returns healthy status on success."""
        # Configure successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http_client.get_once.return_value = mock_response

        mock_mapping = MagicMock()
        mock_mapping.status = HealthStatus.HEALTHY
        mock_mapping.event_name = None
        mock_response_mapper.map_health_probe = MagicMock(return_value=mock_mapping)

        result = await probe_crossref_health(
            http_client=mock_http_client,
            query_builder=mock_query_builder,
            response_mapper=mock_response_mapper,
            adapter_metrics=mock_adapter_metrics,
            headers_provider=lambda: {"User-Agent": "test"},
            logger=mock_logger,
            health_errors=(ConnectionError, TimeoutError),
        )

        assert result == HealthStatus.HEALTHY
        mock_query_builder.build_health_probe_url.assert_called_once()
        mock_query_builder.build_health_probe_params.assert_called_once()
        mock_response_mapper.map_health_probe.assert_called_once_with(
            status_code=200,
            elapsed_seconds=pytest.approx(0.0, abs=1.0),
        )

    @pytest.mark.asyncio
    async def test_probe_crossref_health_slow_warning(
        self,
        mock_http_client,
        mock_query_builder,
        mock_response_mapper,
        mock_adapter_metrics,
        mock_logger,
    ):
        """Test probe_crossref_health logs warning for slow response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http_client.get_once.return_value = mock_response

        mock_mapping = MagicMock()
        mock_mapping.status = HealthStatus.HEALTHY
        mock_mapping.event_name = "crossref_health_check_slow"
        mock_response_mapper.map_health_probe = MagicMock(return_value=mock_mapping)

        result = await probe_crossref_health(
            http_client=mock_http_client,
            query_builder=mock_query_builder,
            response_mapper=mock_response_mapper,
            adapter_metrics=mock_adapter_metrics,
            headers_provider=lambda: {"User-Agent": "test"},
            logger=mock_logger,
            health_errors=(ConnectionError, TimeoutError),
        )

        assert result == HealthStatus.HEALTHY
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert warning_call.args[0] == "crossref_health_check_slow"
        assert "elapsed_seconds" in warning_call.kwargs

    @pytest.mark.asyncio
    async def test_probe_crossref_health_unhealthy_status(
        self,
        mock_http_client,
        mock_query_builder,
        mock_response_mapper,
        mock_adapter_metrics,
        mock_logger,
    ):
        """Test probe_crossref_health returns unhealthy status."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_http_client.get_once.return_value = mock_response

        mock_mapping = MagicMock()
        mock_mapping.status = HealthStatus.UNHEALTHY
        mock_mapping.event_name = "crossref_health_check_failed"
        mock_response_mapper.map_health_probe = MagicMock(return_value=mock_mapping)

        result = await probe_crossref_health(
            http_client=mock_http_client,
            query_builder=mock_query_builder,
            response_mapper=mock_response_mapper,
            adapter_metrics=mock_adapter_metrics,
            headers_provider=lambda: {"User-Agent": "test"},
            logger=mock_logger,
            health_errors=(ConnectionError, TimeoutError),
        )

        assert result == HealthStatus.UNHEALTHY
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert warning_call.args[0] == "crossref_health_check_failed"

    @pytest.mark.asyncio
    async def test_probe_crossref_health_raises_on_error(
        self,
        mock_http_client,
        mock_query_builder,
        mock_response_mapper,
        mock_adapter_metrics,
        mock_logger,
    ):
        """Test probe_crossref_health raises on network error."""
        mock_http_client.get_once = AsyncMock(side_effect=ConnectionError("Network error"))

        with pytest.raises(ConnectionError):
            await probe_crossref_health(
                http_client=mock_http_client,
                query_builder=mock_query_builder,
                response_mapper=mock_response_mapper,
                adapter_metrics=mock_adapter_metrics,
                headers_provider=lambda: {"User-Agent": "test"},
                logger=mock_logger,
                health_errors=(ConnectionError, TimeoutError),
            )

        mock_logger.warning.assert_called_once_with(
            "crossref_health_check_failed",
            error="Network error",
        )
