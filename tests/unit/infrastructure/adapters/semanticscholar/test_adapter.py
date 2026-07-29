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
# tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py
"""Unit tests for Semantic Scholar Adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from tests.helpers.adapter_runtime import (
    build_http_adapter_runtime_bundle,
    build_http_adapter_runtime_kwargs,
)

pytestmark = pytest.mark.unit

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1038/s41586-024-07487-w"


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client."""
    client = MagicMock()
    client.get_once = AsyncMock()
    client.post = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def adapter(
    mock_http_client: MagicMock, mock_logger: MagicMock
) -> SemanticScholarAdapter:
    """Create an adapter instance."""
    return SemanticScholarAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        api_key="test-api-key",
        batch_size=10,
        **build_http_adapter_runtime_kwargs(
            "semanticscholar",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


class TestSemanticScholarAdapter:
    """Tests for SemanticScholarAdapter."""

    def test_scholar_adapter__base_collaborators__767a5e2e(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Dataclass adapter should delegate shared base initialization."""
        error_handler = MagicMock()
        metrics = MagicMock()
        adapter_metrics = AdapterMetricsRecorder(metrics, "semanticscholar")
        request_collector = APIRequestCollector()
        runtime_bundle = build_http_adapter_runtime_bundle(
            "semanticscholar",
            logger=mock_logger,
        )

        adapter = SemanticScholarAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=metrics,
            error_handler=error_handler,
            adapter_metrics=adapter_metrics,
            request_collector=request_collector,
            fallback_fetch_service=runtime_bundle.fallback_fetch_service,
        )

        assert adapter._http_client is mock_http_client
        assert adapter._logger is mock_logger
        assert adapter._metrics is metrics
        assert adapter._error_handler is error_handler
        assert adapter._adapter_metrics is adapter_metrics
        assert adapter._request_collector is request_collector

    def test_scholar_adapter__provider_name__cc77e4ec(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test provider name is set correctly."""
        assert adapter.provider_name == "semanticscholar"

    def test_build_headers_with_api_key(self, adapter: SemanticScholarAdapter) -> None:
        """Test headers include API key when provided."""
        headers = adapter._build_headers()

        assert headers["x-api-key"] == "test-api-key"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_build_headers_without_api_key(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test headers when no API key is provided."""
        adapter = SemanticScholarAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            **build_http_adapter_runtime_kwargs(
                "semanticscholar",
                logger=mock_logger,
                include_fallback_service=True,
            ),
        )

        headers = adapter._build_headers()

        assert "x-api-key" not in headers

    def test_normalize_doi_no_prefix(self, adapter: SemanticScholarAdapter) -> None:
        """Test DOI normalization without prefix."""
        result = adapter._normalize_doi("10.1038/s41586-024-07487-w")
        assert result == "10.1038/s41586-024-07487-w"

    def test_normalize_doi_https_prefix(self, adapter: SemanticScholarAdapter) -> None:
        """Test DOI normalization with https prefix."""
        result = adapter._normalize_doi("https://doi.org/10.1038/s41586-024-07487-w")
        assert result == "10.1038/s41586-024-07487-w"

    def test_normalize_doi_http_prefix(self, adapter: SemanticScholarAdapter) -> None:
        """Test DOI normalization with http prefix."""
        result = adapter._normalize_doi(LEGACY_HTTP_DOI)
        assert result == "10.1038/s41586-024-07487-w"

    def test_normalize_doi_lowercase_prefix(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test DOI normalization with lowercase doi: prefix."""
        result = adapter._normalize_doi("doi:10.1038/s41586-024-07487-w")
        assert result == "10.1038/s41586-024-07487-w"

    def test_normalize_doi_uppercase_prefix(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test DOI normalization with uppercase DOI: prefix."""
        result = adapter._normalize_doi("DOI:10.1038/s41586-024-07487-w")
        assert result == "10.1038/s41586-024-07487-w"


class TestFetchFiltered:
    """Tests for fetch_filtered method."""

    @pytest.mark.asyncio
    async def test_fetch_filtered_batch(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
    ) -> None:
        """Test batch DOI resolution."""
        # Mock response with two records
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"paperId": "a" * 40, "title": "Paper 1"},
            {"paperId": "b" * 40, "title": "Paper 2"},
        ]
        mock_http_client.post.return_value = mock_response

        results = []
        async for record in adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["10.1038/paper1", "10.1016/paper2"],
            filter_field="doi",
        ):
            results.append(record)

        assert len(results) == 2
        assert results[0]["paperId"] == "a" * 40
        assert results[1]["paperId"] == "b" * 40

    @pytest.mark.asyncio
    async def test_fetch_filtered_skips_null(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
    ) -> None:
        """Test that null results are skipped."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"paperId": "a" * 40, "title": "Paper 1"},
            None,  # Not found
            {"paperId": "c" * 40, "title": "Paper 3"},
        ]
        mock_http_client.post.return_value = mock_response

        results = []
        async for record in adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["doi1", "doi2", "doi3"],
            filter_field="doi",
        ):
            results.append(record)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_adapter_fetch_filtered__respects_limit__90302f40(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
    ) -> None:
        """Test that limit is respected."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"paperId": "a" * 40},
            {"paperId": "b" * 40},
            {"paperId": "c" * 40},
        ]
        mock_http_client.post.return_value = mock_response

        results = []
        async for record in adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["doi1", "doi2", "doi3"],
            filter_field="doi",
            limit=2,
        ):
            results.append(record)

        assert len(results) == 2


class TestFetchFilteredWithFallback:
    """Tests for fetch_filtered_with_fallback method."""

    @pytest.mark.asyncio
    async def test_fallback_for_not_found(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
    ) -> None:
        """Test fallback to title search when DOI returns null."""
        # First call - batch DOI lookup with one null
        batch_response = MagicMock()
        batch_response.json.return_value = [
            {"paperId": "a" * 40, "title": "Found by DOI"},
            None,  # Not found by DOI
        ]

        # Second call - title search (title must match fallback_mapping value)
        search_response = MagicMock()
        search_response.json.return_value = {
            "data": [{"paperId": "b" * 40, "title": "Title 2"}]  # Matches fallback
        }

        mock_http_client.post.return_value = batch_response
        mock_http_client.get_once.return_value = search_response

        fallback_mapping = {
            "doi1": "Title 1",
            "doi2": "Title 2",
        }

        results = []
        async for record in adapter.fetch_filtered_with_fallback(
            entity_type="publication",
            filter_ids=["doi1", "doi2"],
            filter_field="doi",
            fallback_mapping=fallback_mapping,
        ):
            results.append(record)

        assert len(results) == 2
        assert results[0]["_lookup_method"] == "doi"
        assert results[1]["_lookup_method"] == "title_fallback"

    @pytest.mark.asyncio
    async def test_title_only_entries(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
    ) -> None:
        """Test handling of empty DOI entries (title-only)."""
        # Search response must return title matching fallback_mapping value
        search_response = MagicMock()
        search_response.json.return_value = {
            "data": [
                {"paperId": "c" * 40, "title": "Title Only Paper"}
            ]  # Matches fallback
        }
        mock_http_client.get_once.return_value = search_response

        # Empty batch response for no valid DOIs
        batch_response = MagicMock()
        batch_response.json.return_value = []
        mock_http_client.post.return_value = batch_response

        fallback_mapping = {
            "": "Title Only Paper",
        }

        results = []
        async for record in adapter.fetch_filtered_with_fallback(
            entity_type="publication",
            filter_ids=[""],  # Empty DOI
            filter_field="doi",
            fallback_mapping=fallback_mapping,
        ):
            results.append(record)

        assert len(results) == 1
        assert results[0]["_lookup_method"] == "title_only"


class TestHealthCheck:
    """Tests for health check."""

    @pytest.mark.asyncio
    async def test_adapter_health_check__health_check_healthy__88d14468(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
    ) -> None:
        """Test healthy status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http_client.get_once.return_value = mock_response

        status = await adapter.health_check()

        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_adapter_health_check__check_unhealthy__18013daa(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
    ) -> None:
        """Test unhealthy status on error."""
        mock_http_client.get_once.side_effect = RuntimeError("Network error")

        status = await adapter.health_check()

        assert status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_adapter_health_check__on_slow_response__8a6f5d36(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Slow health probes should degrade the provider status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http_client.get_once.return_value = mock_response

        import bioetl.infrastructure.adapters.semanticscholar.health_metadata_mixin as health_module

        call_count = [0]

        def _mock_monotonic() -> float:
            call_count[0] += 1
            return 0.0 if call_count[0] == 1 else 6.0

        monkeypatch.setattr(health_module.time, "monotonic", _mock_monotonic)

        status = await adapter._probe_health()

        assert status == HealthStatus.DEGRADED
        mock_http_client.get_once.assert_awaited_once()


class TestFetchMultiFiltered:
    """Tests for fetch_multi_filtered method."""

    @pytest.mark.asyncio
    async def test_not_implemented(self, adapter: SemanticScholarAdapter) -> None:
        """Test that multi-field filtering raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            async for _ in adapter.fetch_multi_filtered(
                entity_type="publication",
                filters={"doi": ["doi1"], "pmid": ["12345"]},
            ):
                continue


class TestFetch:
    """Tests for basic fetch method."""

    @pytest.mark.asyncio
    async def test_fetch_delegates_to_filtered(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
    ) -> None:
        """Test that fetch with filter_ids delegates to fetch_filtered."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"paperId": "a" * 40}]
        mock_http_client.post.return_value = mock_response

        results = []
        async for record in adapter.fetch(
            entity_type="publication",
            filter_ids=["doi1"],
            filter_field="doi",
        ):
            results.append(record)

        assert len(results) == 1
        mock_http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_search(
        self,
        adapter: SemanticScholarAdapter,
        mock_http_client: MagicMock,
    ) -> None:
        """Test search-based fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"paperId": "a" * 40}],
            "next": None,
        }
        mock_http_client.get_once.return_value = mock_response

        results = []
        async for record in adapter.fetch(
            entity_type="publication",
            query="gene editing",
            limit=1,
        ):
            results.append(record)

        assert len(results) == 1
        mock_http_client.get_once.assert_called_once()

    @pytest.mark.asyncio
    async def test_adapter_fetch__invalid_entity_type__31f77600(
        self,
        adapter: SemanticScholarAdapter,
    ) -> None:
        """Test that invalid entity type raises ValueError."""
        with pytest.raises(ValueError, match=r"publication.*paper"):
            async for _ in adapter.fetch(
                entity_type="invalid",
                query="test",
            ):
                continue
