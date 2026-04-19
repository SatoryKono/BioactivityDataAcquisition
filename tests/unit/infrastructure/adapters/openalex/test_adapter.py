"""Unit tests for OpenAlex adapter.

Tests the OpenAlexAdapter class with mocked HTTP client.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
from bioetl.infrastructure.adapters.openalex.client import _create_openalex_adapter
from bioetl.infrastructure.adapters.openalex.client_runtime_helpers import (
    OpenAlexRuntimeServicesRequest,
    build_openalex_runtime_services_from_request,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.helpers.adapter_runtime import (
    build_http_adapter_runtime_bundle,
    build_http_adapter_runtime_kwargs,
)

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1038/test"


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client."""
    client = MagicMock()
    client.get = AsyncMock()
    client.get_once = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.fixture
def logger() -> NoOpLogger:
    """Create a NoOp logger for testing."""
    return NoOpLogger()


@pytest.fixture
def adapter(
    mock_http_client: MagicMock,
    logger: NoOpLogger,
) -> OpenAlexAdapter:
    """Create an adapter instance for testing."""
    return OpenAlexAdapter(
        http_client=mock_http_client,
        logger=logger,
        mailto="test@example.com",
        batch_size=10,
        **build_http_adapter_runtime_kwargs(
            "openalex",
            logger=logger,
            include_fallback_service=True,
        ),
    )


class TestOpenAlexAdapter:
    """Tests for OpenAlexAdapter."""

    def test_adapter_initialization(
        self,
        mock_http_client: MagicMock,
        logger: NoOpLogger,
    ) -> None:
        """Should initialize adapter with required parameters."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=logger,
            mailto="test@example.com",
            **build_http_adapter_runtime_kwargs(
                "openalex",
                logger=logger,
                include_fallback_service=True,
            ),
        )
        assert adapter.provider_name == "openalex"
        assert adapter.mailto == "test@example.com"
        assert adapter.batch_size == 50  # Default

    def test_post_init_preserves_injected_base_collaborators(
        self, mock_http_client: MagicMock, logger: NoOpLogger
    ) -> None:
        """Dataclass adapter should delegate shared base initialization."""
        error_handler = MagicMock()
        metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(metrics, "openalex")
        request_collector = APIRequestCollector()
        runtime_bundle = build_http_adapter_runtime_bundle("openalex", logger=logger)

        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=logger,
            mailto="test@example.com",
            metrics=metrics,
            error_handler=error_handler,
            adapter_metrics=adapter_metrics,
            request_collector=request_collector,
            fallback_fetch_service=runtime_bundle.fallback_fetch_service,
        )

        assert adapter._http_client is mock_http_client
        assert adapter._logger is logger
        assert adapter._metrics is metrics
        assert adapter._error_handler is error_handler
        assert adapter._adapter_metrics is adapter_metrics
        assert adapter._request_collector is request_collector

    def test_post_init_preserves_injected_openalex_runtime_collaborators(
        self,
        mock_http_client: MagicMock,
        logger: NoOpLogger,
    ) -> None:
        """Injected OpenAlex runtime collaborators should survive post-init wiring."""
        query_executor = MagicMock()
        response_mapper = MagicMock()
        cursor_flow = MagicMock()
        fallback_handler = MagicMock()
        fallback_orchestrator = MagicMock()
        runtime_bundle = build_http_adapter_runtime_bundle(
            "openalex",
            logger=logger,
        )

        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=logger,
            mailto="test@example.com",
            dependency_context=runtime_bundle.dependency_context,
            fallback_fetch_service=runtime_bundle.fallback_fetch_service,
            openalex_query_executor=query_executor,
            openalex_response_mapper=response_mapper,
            openalex_cursor_flow=cursor_flow,
            title_fallback_handler=fallback_handler,
            openalex_fallback_orchestrator=fallback_orchestrator,
        )

        assert adapter._query_executor is query_executor
        assert adapter._response_mapper is response_mapper
        assert adapter._cursor_flow is cursor_flow
        assert adapter._fallback_handler is fallback_handler
        assert adapter._fallback_orchestrator is fallback_orchestrator

    def test_runtime_services_request_preserves_injected_collaborators(
        self,
        mock_http_client: MagicMock,
        logger: NoOpLogger,
    ) -> None:
        """Request-style runtime assembly should preserve injected seams."""
        query_executor = MagicMock()
        response_mapper = MagicMock()
        cursor_flow = MagicMock()
        fallback_handler = MagicMock()
        fallback_orchestrator = MagicMock()
        runtime_bundle = build_http_adapter_runtime_bundle(
            "openalex",
            logger=logger,
        )
        adapter_metrics = AdapterMetricsRecorder(MagicMock(), "openalex")
        request_collector = APIRequestCollector()

        request = OpenAlexRuntimeServicesRequest(
            fallback_fetch_service=runtime_bundle.fallback_fetch_service,
            openalex_query_executor=query_executor,
            openalex_response_mapper=response_mapper,
            openalex_cursor_flow=cursor_flow,
            title_fallback_handler=fallback_handler,
            openalex_fallback_orchestrator=fallback_orchestrator,
            http_client=mock_http_client,
            adapter_metrics=adapter_metrics,
            request_collector=request_collector,
            headers_provider=lambda: {"Accept": "application/json"},
            api_base="https://api.openalex.org",
            mailto="test@example.com",
            batch_size=10,
            title_search_cache_size=128,
            normalize_doi=lambda doi: doi.lower(),
            escape_title_for_search=lambda title: title.replace(" ", "+"),
            extract_record_id=lambda record: record.get("doi"),
            search_by_title=AsyncMock(),
            logger=logger,
            runtime_errors=(RuntimeError,),
        )

        runtime_services = build_openalex_runtime_services_from_request(request)

        assert (
            runtime_services.fallback_fetch_service
            is runtime_bundle.fallback_fetch_service
        )
        assert runtime_services.query_executor is query_executor
        assert runtime_services.response_mapper is response_mapper
        assert runtime_services.cursor_flow is cursor_flow
        assert runtime_services.fallback_handler is fallback_handler
        assert runtime_services.fallback_orchestrator is fallback_orchestrator

    def test_adapter_provider_name(self, adapter: OpenAlexAdapter) -> None:
        """Should return correct provider name."""
        assert adapter.provider_name == "openalex"

    def test_build_headers(self, adapter: OpenAlexAdapter) -> None:
        """Should build headers with mailto in User-Agent."""
        headers = adapter._build_headers()
        assert "User-Agent" in headers
        assert "test@example.com" in headers["User-Agent"]
        assert headers["Accept"] == "application/json"

    def test_build_base_params(self, adapter: OpenAlexAdapter) -> None:
        """Should include mailto in base params."""
        params = adapter._build_base_params()
        assert params["mailto"] == "test@example.com"


class TestNormalizeDoi:
    """Tests for DOI normalization."""

    def test_normalize_doi_https_url(self) -> None:
        """Should normalize https://doi.org/ URL."""
        result = OpenAlexAdapter._normalize_doi("https://doi.org/10.1038/test")
        assert result == "10.1038/test"

    def test_normalize_doi_http_url(self) -> None:
        """Should normalize a legacy HTTP DOI URL."""
        result = OpenAlexAdapter._normalize_doi(LEGACY_HTTP_DOI)
        assert result == "10.1038/test"

    def test_normalize_doi_prefix(self) -> None:
        """Should normalize doi: prefix."""
        result = OpenAlexAdapter._normalize_doi("doi:10.1038/test")
        assert result == "10.1038/test"

    def test_normalize_doi_bare(self) -> None:
        """Should return bare DOI unchanged."""
        result = OpenAlexAdapter._normalize_doi("10.1038/test")
        assert result == "10.1038/test"

    def test_normalize_doi_empty(self) -> None:
        """Should return None for empty string."""
        result = OpenAlexAdapter._normalize_doi("")
        assert result is None


class TestEscapeTitleForSearch:
    """Tests for title escaping."""

    def test_escape_title_basic(self) -> None:
        """Should escape title for search."""
        result = OpenAlexAdapter._escape_title_for_search("Machine learning")
        assert result == "Machine+learning"

    def test_escape_title_special_chars(self) -> None:
        """Should remove special characters."""
        result = OpenAlexAdapter._escape_title_for_search(
            "Test: A Study | Part 1, Part 2"
        )
        assert ":" not in result
        assert "|" not in result
        assert "," not in result

    def test_escape_title_multiple_spaces(self) -> None:
        """Should handle multiple spaces."""
        result = OpenAlexAdapter._escape_title_for_search("A   B   C")
        assert result == "A+B+C"


class TestExtractDoiFromRecord:
    """Tests for DOI extraction from records."""

    def test_extract_doi_from_url(self) -> None:
        """Should extract DOI from record URL."""
        record = {"doi": "https://doi.org/10.1038/TEST123"}
        result = OpenAlexAdapter._extract_doi_from_record(record)
        assert result == "10.1038/test123"  # Lowercase

    def test_extract_doi_bare(self) -> None:
        """Should handle bare DOI."""
        record = {"doi": "10.1016/j.test.2024"}
        result = OpenAlexAdapter._extract_doi_from_record(record)
        assert result == "10.1016/j.test.2024"

    def test_extract_doi_none(self) -> None:
        """Should return None for missing DOI."""
        record = {"doi": None}
        result = OpenAlexAdapter._extract_doi_from_record(record)
        assert result is None

    def test_extract_doi_empty(self) -> None:
        """Should return None for empty DOI."""
        record = {"doi": ""}
        result = OpenAlexAdapter._extract_doi_from_record(record)
        assert result is None


class TestFetchFiltered:
    """Tests for fetch_filtered method."""

    @pytest.mark.asyncio
    async def test_fetch_filtered_invalid_entity_type(
        self, adapter: OpenAlexAdapter
    ) -> None:
        """Should raise ValueError for invalid entity type."""
        with pytest.raises(ValueError, match="supports 'work' or 'publication'"):
            async for _ in adapter.fetch_filtered(
                "invalid_type", ["10.1038/test"], "doi"
            ):
                pass

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_dois(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should fetch works by DOIs."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W123",
                    "doi": "https://doi.org/10.1038/test1",
                },
                {
                    "id": "https://openalex.org/W456",
                    "doi": "https://doi.org/10.1038/test2",
                },
            ]
        }
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch_filtered(
            "publication", ["10.1038/test1", "10.1038/test2"], "doi"
        ):
            results.append(work)

        assert len(results) == 2
        mock_http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_filtered_respects_limit(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should respect limit parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"id": f"https://openalex.org/W{i}"} for i in range(10)]
        }
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch_filtered(
            "publication", [f"10.1038/test{i}" for i in range(20)], "doi", limit=3
        ):
            results.append(work)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_fetch_filtered_by_title(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should fetch works by title search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W123",
                    "title": "Machine Learning in Drug Discovery",
                    "doi": "https://doi.org/10.1038/test1",
                }
            ]
        }
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch_filtered(
            "publication",
            ["Machine Learning in Drug Discovery"],
            "title",
        ):
            results.append(work)

        assert len(results) == 1
        assert results[0]["_lookup_method"] == "title"
        assert results[0]["_search_title"] == "Machine Learning in Drug Discovery"
        mock_http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_filtered_by_title_uses_cache_for_duplicate_queries(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should reuse title-search results for repeated titles."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W123",
                    "title": "Machine Learning in Drug Discovery",
                }
            ]
        }
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch_filtered(
            "publication",
            [
                "Machine Learning in Drug Discovery",
                "Machine Learning in Drug Discovery",
            ],
            "title",
        ):
            results.append(work)

        assert len(results) == 2
        assert mock_http_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_filtered_by_title_respects_limit(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should respect limit when searching by title."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"id": "https://openalex.org/W1", "title": "Test"}]
        }
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch_filtered(
            "publication",
            ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
            "title",
            limit=2,
        ):
            results.append(work)

        assert len(results) == 2
        # Should have made only 2 requests (rate limited)
        assert mock_http_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_filtered_by_title_skips_empty(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should skip empty titles."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"id": "https://openalex.org/W1", "title": "Test"}]
        }
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch_filtered(
            "publication",
            ["", "  ", "Valid Title"],
            "title",
        ):
            results.append(work)

        assert len(results) == 1
        # Should have made only 1 request (empty titles skipped)
        assert mock_http_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_filtered_unsupported_field_returns_empty(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should return empty for unsupported filter fields."""
        results = []
        async for work in adapter.fetch_filtered(
            "publication",
            ["some_value"],
            "unsupported_field",
        ):
            results.append(work)

        assert len(results) == 0
        # Should not have made any HTTP requests
        mock_http_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_filtered_by_title_no_results(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should handle title search with no results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch_filtered(
            "publication",
            ["Nonexistent Publication Title"],
            "title",
        ):
            results.append(work)

        assert len(results) == 0
        mock_http_client.get.assert_called_once()


class TestFetchFilteredWithFallback:
    """Tests for fetch_filtered_with_fallback method."""

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_unsupported_field_returns_empty(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should return empty for unsupported filter fields in fallback mode."""
        results = []
        async for work in adapter.fetch_filtered_with_fallback(
            "publication",
            ["some_value"],
            "unsupported_field",  # Not "doi"
            fallback_mapping={"some_value": "Some Title"},
        ):
            results.append(work)

        assert len(results) == 0
        # Should not have made any HTTP requests
        mock_http_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_invalid_entity_type(
        self, adapter: OpenAlexAdapter
    ) -> None:
        """Should raise ValueError for invalid entity type."""
        with pytest.raises(ValueError, match="supports 'work'/'publication'"):
            async for _ in adapter.fetch_filtered_with_fallback(
                "invalid_type",
                ["10.1038/test"],
                "doi",
                fallback_mapping={},
            ):
                pass


class TestFetchMultiFiltered:
    """Tests for fetch_multi_filtered method."""

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_not_supported(
        self, adapter: OpenAlexAdapter
    ) -> None:
        """Should raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            async for _ in adapter.fetch_multi_filtered(
                "publication", {"doi": ["test"]}
            ):
                pass


class TestFetch:
    """Tests for fetch method."""

    @pytest.mark.asyncio
    async def test_fetch_with_filter_ids_delegates(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should delegate to fetch_filtered when filter_ids provided."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": "W123"}]}
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch(
            "publication", filter_ids=["10.1038/test"], filter_field="doi"
        ):
            results.append(work)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fetch_with_filter_ids_defaults_filter_field_to_doi(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should default fetch(filter_ids=...) to DOI routing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": "W123"}]}
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch("publication", filter_ids=["10.1038/test"]):
            results.append(work)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fetch_with_filter_ids_defaults_to_doi(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should default filter_field to DOI when filter_ids are provided."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"id": "W123"}]}
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch(
            "publication",
            filter_ids=["10.1038/test"],
        ):
            results.append(work)

        assert len(results) == 1
        mock_http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_invalid_entity_type(self, adapter: OpenAlexAdapter) -> None:
        """Should raise ValueError for invalid entity type."""
        with pytest.raises(ValueError, match="supports 'work' or 'publication'"):
            async for _ in adapter.fetch("invalid", query="test"):
                pass

    @pytest.mark.asyncio
    async def test_fetch_requires_query_or_filter_ids(
        self, adapter: OpenAlexAdapter
    ) -> None:
        """Should raise ValueError when neither query nor filter_ids provided."""
        with pytest.raises(ValueError, match="requires either filter_ids"):
            async for _ in adapter.fetch("publication"):
                pass


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should return HEALTHY for successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http_client.get_once.return_value = mock_response

        result = await adapter._probe_health()

        assert result == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_degraded_on_transient_error(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should return DEGRADED for transient non-200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_http_client.get_once.return_value = mock_response

        result = await adapter._probe_health()

        assert result == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_auth_error(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should return UNHEALTHY for auth-related response codes."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_http_client.get_once.return_value = mock_response

        result = await adapter._probe_health()

        assert result == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_degraded_on_slow_response(
        self,
        adapter: OpenAlexAdapter,
        mock_http_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should return DEGRADED when the health probe exceeds the slow threshold."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http_client.get_once.return_value = mock_response

        import bioetl.infrastructure.adapters.openalex.health_probe as health_probe_module

        call_count = [0]

        def _mock_monotonic() -> float:
            call_count[0] += 1
            return 0.0 if call_count[0] == 1 else 6.0

        monkeypatch.setattr(health_probe_module.time, "monotonic", _mock_monotonic)

        result = await adapter._probe_health()

        assert result == HealthStatus.DEGRADED


class TestCreateOpenAlexAdapter:
    """Tests for _create_openalex_adapter factory function."""

    def test_create_adapter_with_all_params(
        self, mock_http_client: MagicMock, logger: NoOpLogger
    ) -> None:
        """Should create adapter with all parameters."""
        adapter = _create_openalex_adapter(
            http_client=mock_http_client,
            logger=logger,
            settings=None,
            mailto="test@example.com",
            batch_size=25,
            **build_http_adapter_runtime_kwargs(
                "openalex",
                logger=logger,
                include_fallback_service=True,
            ),
        )

        assert adapter.mailto == "test@example.com"
        assert adapter.batch_size == 25

    def test_create_adapter_requires_mailto(
        self, mock_http_client: MagicMock, logger: NoOpLogger
    ) -> None:
        """Should raise ValueError when mailto not provided."""
        with pytest.raises(ValueError, match="requires mailto"):
            _create_openalex_adapter(
                http_client=mock_http_client,
                logger=logger,
                settings=None,
                **build_http_adapter_runtime_kwargs(
                    "openalex",
                    logger=logger,
                    include_fallback_service=True,
                ),
            )

    def test_create_adapter_requires_http_client(self, logger: NoOpLogger) -> None:
        """Should raise ValueError when http_client not provided."""
        with pytest.raises(ValueError, match="requires http_client"):
            _create_openalex_adapter(
                http_client=None,
                logger=logger,
                settings=None,
                mailto="test@example.com",
                **build_http_adapter_runtime_kwargs(
                    "openalex",
                    logger=logger,
                    include_fallback_service=True,
                ),
            )

    def test_create_adapter_requires_logger(self, mock_http_client: MagicMock) -> None:
        """Should raise ValueError when logger not provided."""
        with pytest.raises(ValueError, match="requires logger"):
            _create_openalex_adapter(
                http_client=mock_http_client,
                logger=None,
                settings=None,
                mailto="test@example.com",
                **build_http_adapter_runtime_kwargs(
                    "openalex",
                    logger=NoOpLogger(),
                    include_fallback_service=True,
                ),
            )
