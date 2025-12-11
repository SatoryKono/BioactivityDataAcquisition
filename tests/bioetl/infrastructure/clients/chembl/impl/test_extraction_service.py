"""Tests for ChemblExtractionServiceImpl."""

from unittest.mock import Mock

from bioetl.application.services import FilterEnrichmentService
from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC
from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import (
    ChemblExtractionServiceImpl,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)


def _mock_logger() -> LoggingPortABC:
    """Create mock logger for tests."""
    return Mock(spec=LoggingPortABC)


def test_filter_enricher_uses_provider():
    """Test that filter enricher uses field provider to populate fields."""
    mock_provider = Mock(spec=DefaultFieldProviderABC)
    mock_provider.get_default_fields.return_value = ["col1", "col2"]

    enricher = FilterEnrichmentService(mock_provider)

    # entity="assay", no fields provided
    filters: dict[str, object] = {}
    result = enricher.enrich_filters("assay", filters)

    assert result["fields"] == "col1,col2"
    mock_provider.get_default_fields.assert_called_with("assay")


def test_filter_enricher_skips_if_fields_present():
    """Test that enricher is ignored if fields are already present."""
    mock_provider = Mock(spec=DefaultFieldProviderABC)

    enricher = FilterEnrichmentService(mock_provider)

    filters: dict[str, object] = {"fields": "custom"}
    result = enricher.enrich_filters("assay", filters)

    assert result["fields"] == "custom"
    mock_provider.get_default_fields.assert_not_called()


def test_filter_enricher_no_provider():
    """Test fallback when no provider is configured."""
    enricher = FilterEnrichmentService(field_provider=None)

    filters: dict[str, object] = {}
    result = enricher.enrich_filters("assay", filters)

    assert "fields" not in result


def test_extraction_service_uses_filter_enricher():
    """Test that extraction service delegates to filter enricher."""
    client = Mock(spec=DataClientABC)
    client.provider = "chembl"

    mock_enricher = Mock(spec=FilterEnricherABC)
    mock_enricher.enrich_filters.return_value = {"fields": "enriched", "limit": 100}

    service = ChemblExtractionServiceImpl(
        client, logger=_mock_logger(), filter_enricher=mock_enricher
    )

    # Test _enrich_filters delegation
    result = service._enrich_filters("assay", {"limit": 100})

    mock_enricher.enrich_filters.assert_called_once_with("assay", {"limit": 100})
    assert result == {"fields": "enriched", "limit": 100}


def test_extraction_service_no_enricher():
    """Test extraction service without enricher passes filters through."""
    client = Mock(spec=DataClientABC)
    client.provider = "chembl"

    service = ChemblExtractionServiceImpl(
        client, logger=_mock_logger(), filter_enricher=None
    )

    filters: dict[str, object] = {"limit": 100}
    result = service._enrich_filters("assay", filters)

    assert result == {"limit": 100}


# =============================================================================
# Generic Parser Tests
# =============================================================================


def test_service_uses_default_generic_parser():
    """Test that service defaults to ChemblGenericResponseParser."""
    client = Mock(spec=DataClientABC)

    service = ChemblExtractionServiceImpl(client, logger=_mock_logger())

    assert isinstance(service._parser, ChemblGenericResponseParser)


def test_service_accepts_injected_parser():
    """Test that parser can be injected via DI."""
    client = Mock(spec=DataClientABC)
    mock_parser = Mock(spec=ResponseParserPortABC)

    service = ChemblExtractionServiceImpl(
        client, logger=_mock_logger(), parser=mock_parser
    )

    assert service._parser is mock_parser


def test_parse_response_returns_list_of_dicts():
    """Test that parse_response returns list[dict], not typed models."""
    client = Mock(spec=DataClientABC)
    service = ChemblExtractionServiceImpl(client, logger=_mock_logger())

    raw_response = {
        "activities": [
            {"activity_id": "1", "value": 10.5},
            {"activity_id": "2", "value": 20.0},
        ]
    }

    result = service.parse_response(raw_response)

    # Should return list of plain dicts
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(r, dict) for r in result)
    # Verify data is preserved
    assert result[0]["activity_id"] == "1"
    assert result[1]["value"] == 20.0


def test_parse_response_with_non_dict_returns_empty_list():
    """Test parse_response gracefully handles non-dict input."""
    client = Mock(spec=DataClientABC)
    service = ChemblExtractionServiceImpl(client, logger=_mock_logger())

    # Non-dict input should return empty list
    assert service.parse_response(None) == []
    assert service.parse_response("string") == []
    assert service.parse_response([1, 2, 3]) == []


def test_parse_response_delegates_to_parser():
    """Test that parse_response delegates to injected parser."""
    client = Mock(spec=DataClientABC)
    mock_parser = Mock(spec=ResponseParserPortABC)
    mock_parser.parse_to_records.return_value = [{"id": "parsed"}]

    service = ChemblExtractionServiceImpl(
        client, logger=_mock_logger(), parser=mock_parser
    )

    raw_response = {"data": [{"id": "raw"}]}
    result = service.parse_response(raw_response)

    mock_parser.parse_to_records.assert_called_once_with(raw_response)
    assert result == [{"id": "parsed"}]


def test_extract_all_returns_list_of_dicts():
    """Test that extract_all returns list[dict[str, Any]]."""
    client = Mock(spec=DataClientABC)
    client.provider = "chembl"

    # Create mock request builder
    mock_builder = Mock()
    mock_builder.build.return_value = "http://test.com/api"
    client.request_builder = mock_builder

    # Mock iter_pages to return raw response
    client.iter_pages.return_value = [{"activities": [{"id": "1"}, {"id": "2"}]}]

    service = ChemblExtractionServiceImpl(client, logger=_mock_logger())

    result = service.extract_all("activity")

    # Should return list of dicts
    assert isinstance(result, list)
    assert all(isinstance(r, dict) for r in result)
    assert len(result) == 2


def test_iter_extract_yields_batches_of_dicts():
    """Test that iter_extract yields batches of raw dicts."""
    client = Mock(spec=DataClientABC)
    client.provider = "chembl"

    mock_builder = Mock()
    mock_builder.build.return_value = "http://test.com/api"
    client.request_builder = mock_builder

    # Simulate two pages
    client.iter_pages.return_value = [
        {"molecules": [{"chembl_id": "CHEMBL1"}]},
        {"molecules": [{"chembl_id": "CHEMBL2"}]},
    ]

    service = ChemblExtractionServiceImpl(client, logger=_mock_logger())

    batches = list(service.iter_extract("molecule"))

    assert len(batches) == 2
    # Each batch is a list of dicts
    assert all(isinstance(batch, list) for batch in batches)
    assert all(isinstance(record, dict) for batch in batches for record in batch)
    # Verify data preserved
    assert batches[0][0]["chembl_id"] == "CHEMBL1"
    assert batches[1][0]["chembl_id"] == "CHEMBL2"
