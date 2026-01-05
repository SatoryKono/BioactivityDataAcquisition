"""Unit tests for OpenAlex adapter.

Tests the OpenAlexAdapter class with mocked HTTP client.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.openalex.client import (
    OpenAlexAdapter,
    _create_openalex_adapter,
)


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
def adapter(mock_http_client: MagicMock, logger: NoOpLogger) -> OpenAlexAdapter:
    """Create an adapter instance for testing."""
    return OpenAlexAdapter(
        http_client=mock_http_client,
        logger=logger,
        mailto="test@example.com",
        batch_size=10,
    )


class TestOpenAlexAdapter:
    """Tests for OpenAlexAdapter."""

    def test_adapter_initialization(
        self, mock_http_client: MagicMock, logger: NoOpLogger
    ) -> None:
        """Should initialize adapter with required parameters."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=logger,
            mailto="test@example.com",
        )
        assert adapter.provider_name == "openalex"
        assert adapter.mailto == "test@example.com"
        assert adapter.batch_size == 50  # Default

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
        """Should normalize http://doi.org/ URL."""
        result = OpenAlexAdapter._normalize_doi("http://doi.org/10.1038/test")
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
                {"id": "https://openalex.org/W123", "doi": "https://doi.org/10.1038/test1"},
                {"id": "https://openalex.org/W456", "doi": "https://doi.org/10.1038/test2"},
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
            "results": [
                {"id": f"https://openalex.org/W{i}"} for i in range(10)
            ]
        }
        mock_http_client.get.return_value = mock_response

        results = []
        async for work in adapter.fetch_filtered(
            "publication", [f"10.1038/test{i}" for i in range(20)], "doi", limit=3
        ):
            results.append(work)

        assert len(results) == 3


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
    async def test_fetch_invalid_entity_type(
        self, adapter: OpenAlexAdapter
    ) -> None:
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
    async def test_health_check_unhealthy_on_error(
        self, adapter: OpenAlexAdapter, mock_http_client: MagicMock
    ) -> None:
        """Should return UNHEALTHY for non-200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_http_client.get_once.return_value = mock_response

        result = await adapter._probe_health()

        assert result == HealthStatus.UNHEALTHY


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
            )

    def test_create_adapter_requires_http_client(
        self, logger: NoOpLogger
    ) -> None:
        """Should raise ValueError when http_client not provided."""
        with pytest.raises(ValueError, match="requires http_client"):
            _create_openalex_adapter(
                http_client=None,
                logger=logger,
                settings=None,
                mailto="test@example.com",
            )

    def test_create_adapter_requires_logger(
        self, mock_http_client: MagicMock
    ) -> None:
        """Should raise ValueError when logger not provided."""
        with pytest.raises(ValueError, match="requires logger"):
            _create_openalex_adapter(
                http_client=mock_http_client,
                logger=None,
                settings=None,
                mailto="test@example.com",
            )
