"""Unit tests for OpenAlexAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.exceptions import CriticalError, OpenAlexApiError, RateLimitError
from bioetl.domain.types import ErrorType, HealthStatus
from bioetl.infrastructure.adapters.openalex.client import (
    OPENALEX_MAX_FILTER_IDS,
    OpenAlexAdapter,
)


@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    return client


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    return OpenAlexAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        mailto="test@example.com",
    )


@pytest.mark.asyncio
async def test_fetch_works(adapter, mock_http_client):
    """Test fetching work records."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "id": "https://openalex.org/W2741809807",
                "title": "Test Paper",
                "doi": "https://doi.org/10.1234/test",
            }
        ],
        "meta": {"next_cursor": None},
    }
    mock_http_client.get.return_value = mock_response

    records = []
    async for record in adapter.fetch("works"):
        records.append(record)

    assert len(records) == 1
    assert records[0]["openalex_id"] == "W2741809807"
    assert records[0]["doi"] == "10.1234/test"
    mock_http_client.get.assert_called()


@pytest.mark.asyncio
async def test_fetch_pagination(adapter, mock_http_client):
    """Test cursor-based pagination."""
    # First page
    resp1 = MagicMock()
    resp1.json.return_value = {
        "results": [{"id": "https://openalex.org/W1", "title": "Paper 1"}],
        "meta": {"next_cursor": "cursor123"},
    }
    # Second page
    resp2 = MagicMock()
    resp2.json.return_value = {
        "results": [{"id": "https://openalex.org/W2", "title": "Paper 2"}],
        "meta": {"next_cursor": None},
    }

    mock_http_client.get.side_effect = [resp1, resp2]

    records = []
    async for record in adapter.fetch("works"):
        records.append(record)

    assert len(records) == 2
    assert records[0]["openalex_id"] == "W1"
    assert records[1]["openalex_id"] == "W2"
    assert mock_http_client.get.call_count == 2

    # Verify cursor was passed in second call
    second_call_params = mock_http_client.get.call_args_list[1][1]["params"]
    assert second_call_params["cursor"] == "cursor123"


@pytest.mark.asyncio
async def test_fetch_with_limit(adapter, mock_http_client):
    """Test fetch respects limit."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"id": "https://openalex.org/W1", "title": "Paper 1"},
            {"id": "https://openalex.org/W2", "title": "Paper 2"},
            {"id": "https://openalex.org/W3", "title": "Paper 3"},
        ],
        "meta": {"next_cursor": "more"},
    }
    mock_http_client.get.return_value = mock_response

    records = []
    async for record in adapter.fetch("works", limit=2):
        records.append(record)

    assert len(records) == 2


@pytest.mark.asyncio
async def test_fetch_error(adapter, mock_http_client):
    """Test API error handling."""
    mock_http_client.get.side_effect = Exception("API Error")

    with pytest.raises(OpenAlexApiError):
        async for _ in adapter.fetch("works"):
            pass

    assert adapter._consecutive_errors == 1


@pytest.mark.asyncio
async def test_fetch_filtered_by_doi(adapter, mock_http_client):
    """Test filtered fetch by DOI."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1234/a"},
            {"id": "https://openalex.org/W2", "doi": "https://doi.org/10.1234/b"},
        ],
        "meta": {"next_cursor": None},
    }
    mock_http_client.get.return_value = mock_response

    records = []
    async for record in adapter.fetch_filtered(
        entity_type="works",
        filter_ids=["10.1234/a", "10.1234/b"],
        filter_field="doi",
    ):
        records.append(record)

    assert len(records) == 2

    # Verify filter parameter was set
    call_params = mock_http_client.get.call_args[1]["params"]
    assert "filter" in call_params
    assert "doi:" in call_params["filter"]


@pytest.mark.asyncio
async def test_health_check_healthy(adapter, mock_http_client):
    """Test healthy health check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"id": "W1"}], "meta": {}}
    mock_http_client.get.return_value = mock_response

    status = await adapter.health_check()
    assert status == HealthStatus.HEALTHY
    assert adapter._consecutive_errors == 0


@pytest.mark.asyncio
async def test_health_check_unhealthy(adapter, mock_http_client):
    """Test unhealthy health check."""
    mock_http_client.get.side_effect = Exception("Down")

    # Degraded first
    status = await adapter.health_check()
    assert status == HealthStatus.DEGRADED

    # Still degraded
    status = await adapter.health_check()
    assert status == HealthStatus.DEGRADED

    # Unhealthy after 3 errors
    status = await adapter.health_check()
    assert status == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_context_manager(adapter, mock_http_client):
    """Test async context manager."""
    async with adapter as a:
        assert a is adapter
        mock_http_client.__aenter__.assert_called_once()
    mock_http_client.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_mailto_included_in_params(adapter, mock_http_client):
    """Test that mailto is included in API params."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [],
        "meta": {"next_cursor": None},
    }
    mock_http_client.get.return_value = mock_response

    async for _ in adapter.fetch("works"):
        pass

    call_params = mock_http_client.get.call_args[1]["params"]
    assert call_params["mailto"] == "test@example.com"


@pytest.mark.unit
class TestOpenAlexAdapterAbstractReconstruction:
    """Tests for abstract inverted index reconstruction."""

    @pytest.mark.asyncio
    async def test_abstract_reconstructed(self, mock_http_client, mock_logger):
        """Test abstract is reconstructed from inverted index."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "title": "Test Paper",
                    "abstract_inverted_index": {
                        "This": [0],
                        "is": [1],
                        "a": [2],
                        "test": [3, 5],
                        "abstract": [4],
                    },
                }
            ],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch("works"):
            records.append(record)

        assert len(records) == 1
        assert records[0]["abstract"] == "This is a test abstract test"

    @pytest.mark.asyncio
    async def test_no_abstract_when_missing(self, mock_http_client, mock_logger):
        """Test no abstract field when inverted index is missing."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "title": "Test Paper",
                }
            ],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch("works"):
            records.append(record)

        assert len(records) == 1
        assert records[0].get("abstract") is None


@pytest.mark.unit
class TestOpenAlexAdapterWorkTransformation:
    """Tests for work record transformation."""

    @pytest.mark.asyncio
    async def test_author_extraction(self, mock_http_client, mock_logger):
        """Test author names are extracted."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "authorships": [
                        {"author": {"display_name": "John Doe"}, "institutions": []},
                        {"author": {"display_name": "Jane Smith"}, "institutions": []},
                    ],
                }
            ],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch("works"):
            records.append(record)

        assert records[0]["authors"] == ["John Doe", "Jane Smith"]

    @pytest.mark.asyncio
    async def test_institution_extraction(self, mock_http_client, mock_logger):
        """Test institution names are extracted and deduplicated."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "authorships": [
                        {
                            "author": {"display_name": "John Doe"},
                            "institutions": [{"display_name": "MIT"}],
                        },
                        {
                            "author": {"display_name": "Jane Smith"},
                            "institutions": [
                                {"display_name": "MIT"},
                                {"display_name": "Harvard"},
                            ],
                        },
                    ],
                }
            ],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch("works"):
            records.append(record)

        institutions = records[0]["institutions"]
        assert len(institutions) == 2
        assert "MIT" in institutions
        assert "Harvard" in institutions

    @pytest.mark.asyncio
    async def test_doi_normalization(self, mock_http_client, mock_logger):
        """Test DOI prefix is stripped."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.1234/test.123",
                }
            ],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch("works"):
            records.append(record)

        assert records[0]["doi"] == "10.1234/test.123"

    @pytest.mark.asyncio
    async def test_pmid_extraction(self, mock_http_client, mock_logger):
        """Test PMID is extracted from ids."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/12345678"},
                }
            ],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch("works"):
            records.append(record)

        assert records[0]["pmid"] == "12345678"

    @pytest.mark.asyncio
    async def test_journal_extraction(self, mock_http_client, mock_logger):
        """Test journal name is extracted from primary_location."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "primary_location": {
                        "source": {"display_name": "Nature"}
                    },
                }
            ],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch("works"):
            records.append(record)

        assert records[0]["journal"] == "Nature"

    @pytest.mark.asyncio
    async def test_work_type_mapping(self, mock_http_client, mock_logger):
        """Test work type is mapped to doc_type."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": "https://openalex.org/W1", "type": "article"},
            ],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch("works"):
            records.append(record)

        assert records[0]["doc_type"] == "PUBLICATION"

    @pytest.mark.asyncio
    async def test_open_access_extraction(self, mock_http_client, mock_logger):
        """Test open access status is extracted."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "open_access": {"is_oa": True},
                },
            ],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch("works"):
            records.append(record)

        assert records[0]["is_open_access"] is True


@pytest.mark.unit
class TestOpenAlexAdapterErrorClassification:
    """Tests for error classification and handling."""

    @pytest.mark.asyncio
    async def test_error_classification_logged(
        self, adapter, mock_http_client, mock_logger
    ):
        """Test that error type is classified and logged."""
        mock_http_client.get.side_effect = RateLimitError("openalex", 60.0)

        with pytest.raises(OpenAlexApiError):
            async for _ in adapter.fetch("works"):
                pass

        mock_logger.error.assert_called()
        call_kwargs = mock_logger.error.call_args.kwargs
        assert call_kwargs["error_type"] == ErrorType.RATE_LIMIT.value
        assert call_kwargs["is_recoverable"] is True

    @pytest.mark.asyncio
    async def test_error_counts_tracked(self, adapter, mock_http_client):
        """Test that error counts are tracked by type."""
        mock_http_client.get.side_effect = RateLimitError("openalex", 60.0)

        for _ in range(3):
            with pytest.raises(OpenAlexApiError):
                async for _ in adapter.fetch("works"):
                    pass

        stats = adapter.get_error_stats()
        assert stats["total_errors"] == 3
        assert stats["consecutive_errors"] == 3
        assert ErrorType.RATE_LIMIT.value in stats["error_counts_by_type"]

    @pytest.mark.asyncio
    async def test_reset_error_counters(self, adapter, mock_http_client):
        """Test error counter reset."""
        mock_http_client.get.side_effect = Exception("Error")

        with pytest.raises(OpenAlexApiError):
            async for _ in adapter.fetch("works"):
                pass

        assert adapter._total_errors == 1

        adapter.reset_error_counters()

        assert adapter._total_errors == 0
        assert adapter._consecutive_errors == 0
        assert adapter._cached_health == HealthStatus.HEALTHY


@pytest.mark.unit
class TestOpenAlexAdapterHealthAwareBatchSize:
    """Tests for health-aware batch size adjustment."""

    @pytest.mark.asyncio
    async def test_healthy_uses_full_per_page(self, mock_http_client, mock_logger):
        """Test that HEALTHY status uses full per_page."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            per_page=200,
        )

        effective = adapter._get_effective_per_page()
        assert effective == 200

    @pytest.mark.asyncio
    async def test_degraded_halves_per_page(self, mock_http_client, mock_logger):
        """Test that DEGRADED status halves per_page."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            per_page=200,
        )
        adapter._cached_health = HealthStatus.DEGRADED
        adapter._consecutive_errors = 1

        effective = adapter._get_effective_per_page()
        assert effective == 100

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args.kwargs
        assert call_kwargs["original_per_page"] == 200
        assert call_kwargs["effective_per_page"] == 100

    @pytest.mark.asyncio
    async def test_degraded_respects_minimum_per_page(
        self, mock_http_client, mock_logger
    ):
        """Test that DEGRADED status respects minimum per_page of 25."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            per_page=40,
        )
        adapter._cached_health = HealthStatus.DEGRADED
        adapter._consecutive_errors = 1

        effective = adapter._get_effective_per_page()
        assert effective == 25

    @pytest.mark.asyncio
    async def test_unhealthy_raises_critical_error(self, mock_http_client, mock_logger):
        """Test that UNHEALTHY status raises CriticalError."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            per_page=200,
        )
        adapter._cached_health = HealthStatus.UNHEALTHY
        adapter._consecutive_errors = 3
        adapter._total_errors = 5

        with pytest.raises(CriticalError) as exc_info:
            adapter._get_effective_per_page()

        assert "UNHEALTHY" in str(exc_info.value)
        assert "3" in str(exc_info.value)


@pytest.mark.unit
class TestOpenAlexAdapterFilterString:
    """Tests for filter string building."""

    def test_build_filter_string_doi(self, mock_http_client, mock_logger):
        """Test filter string for DOI."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        filter_str = adapter._build_filter_string(
            ["10.1234/a", "10.1234/b"], "doi"
        )

        assert filter_str == "doi:10.1234/a|10.1234/b"

    def test_build_filter_string_openalex_id(self, mock_http_client, mock_logger):
        """Test filter string for OpenAlex ID."""
        adapter = OpenAlexAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        filter_str = adapter._build_filter_string(
            ["W1", "W2"], "openalex_id"
        )

        assert filter_str == "ids.openalex:W1|W2"

    def test_max_filter_ids_constant(self):
        """Test max filter IDs constant is set correctly."""
        assert OPENALEX_MAX_FILTER_IDS == 50


@pytest.mark.unit
class TestOpenAlexAdapterHealthTransitions:
    """Tests for health status transitions and logging."""

    @pytest.mark.asyncio
    async def test_health_transition_logged(
        self, adapter, mock_http_client, mock_logger
    ):
        """Test that health transitions are logged."""
        mock_http_client.get.side_effect = Exception("Error")

        with pytest.raises(OpenAlexApiError):
            async for _ in adapter.fetch("works"):
                pass

        info_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call.args and call.args[0] == "openalex_health_transition"
        ]
        assert len(info_calls) == 1
        kwargs = info_calls[0].kwargs
        assert kwargs["previous_status"] == "HEALTHY"
        assert kwargs["current_status"] == "DEGRADED"

    @pytest.mark.asyncio
    async def test_consecutive_errors_reset_on_success(self, adapter, mock_http_client):
        """Test that consecutive errors reset after successful fetch."""
        # First: simulate error
        mock_http_client.get.side_effect = Exception("Error")
        with pytest.raises(OpenAlexApiError):
            async for _ in adapter.fetch("works"):
                pass

        assert adapter._consecutive_errors == 1

        # Second: successful fetch resets counter
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"id": "https://openalex.org/W1"}],
            "meta": {"next_cursor": None},
        }
        mock_http_client.get.side_effect = None
        mock_http_client.get.return_value = mock_response

        async for _ in adapter.fetch("works"):
            pass

        assert adapter._consecutive_errors == 0
