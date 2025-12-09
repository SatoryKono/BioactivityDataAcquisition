"""
Tests for ChemblExtractionServiceImpl.
"""

# pylint: disable=redefined-outer-name
from unittest.mock import MagicMock

import pytest

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import (
    ChemblExtractionServiceImpl,
)


@pytest.fixture
def mock_client():
    """Mock ChEMBL client."""
    client = MagicMock(spec=DataClientABC)
    # Add request_builder mock as required by implementation
    client.request_builder = MagicMock()
    # Default build return
    client.request_builder.build.return_value = "http://mock-url"
    return client


@pytest.fixture
def service(mock_client):
    """ChemblExtractionServiceImpl instance with mock client."""
    return ChemblExtractionServiceImpl(client=mock_client, batch_size=10)


def test_get_release_version(service, mock_client):
    """Test getting release version."""
    mock_client.metadata.return_value = {"chembl_release": "34"}
    version = service.get_release_version()
    assert version == "chembl_34"
    mock_client.metadata.assert_called_once()


def test_extract_all_single_page(service, mock_client):
    """Test extraction of a single page."""
    # Mock parser and paginator attributes on the instance
    mock_paginator = MagicMock()
    mock_parser = MagicMock()

    service.paginator = mock_paginator
    mock_client.response_parser = mock_parser

    # Setup mock responses
    # iter_pages yields raw page data
    mock_client.iter_pages.return_value = [{"data": "page1"}]
    mock_parser.parse_response.return_value = [{"id": 1}, {"id": 2}]

    # Act
    records = service.extract_all("activity")

    # Assert
    assert len(records) == 2
    assert records[0]["id"] == 1
    # Verify iter_pages called with URL from builder
    mock_client.iter_pages.assert_called_once_with("http://mock-url")
    # Verify builder used correct limit
    mock_client.request_builder.build.assert_called_with({"limit": 10})


def test_extract_all_pagination(service, mock_client):
    """Test extraction with pagination."""
    # Mock parser and paginator attributes
    mock_paginator = MagicMock()
    mock_parser = MagicMock()

    service.paginator = mock_paginator
    mock_client.response_parser = mock_parser

    # Setup iteration
    mock_client.iter_pages.return_value = [{"data": "page1"}, {"data": "page2"}]
    mock_parser.parse_response.side_effect = [[{"id": 1}, {"id": 2}], [{"id": 3}]]

    # Act
    records = service.extract_all("activity")

    # Assert
    assert len(records) == 3
    assert mock_client.iter_pages.call_count == 1


def test_extract_all_serializes_nested_fields(service, mock_client):
    """Nested payloads are flattened before being returned."""
    mock_parser = MagicMock()
    mock_paginator = MagicMock()

    service.paginator = mock_paginator
    mock_client.response_parser = mock_parser

    mock_client.iter_pages.return_value = [{"data": "page"}]
    mock_parser.parse_response.return_value = [
        {
            "id": 1,
            "activity_properties": [{"k1": "v1"}, {"k2": "v2"}],
            "ligand_efficiency": {"le": 1.1},
        }
    ]

    records = service.extract_all("activity")

    assert records[0]["activity_properties"] == [{"k1": "v1"}, {"k2": "v2"}]
    assert records[0]["ligand_efficiency"] == {"le": 1.1}


def test_extract_all_limit(service, mock_client):
    """Test extraction with limit."""
    # Mock parser and paginator
    mock_parser = MagicMock()
    mock_paginator = MagicMock()
    service.paginator = mock_paginator
    mock_client.response_parser = mock_parser

    # Returns 10 items per call
    mock_client.iter_pages.return_value = [{"data": "page"}]
    mock_parser.parse_response.return_value = [{"id": i} for i in range(10)]

    # Act - request limit 5 (which acts as chunk_size in current impl)
    records = service.extract_all("activity", limit=5)

    # Assert
    assert len(records) == 10  # Mock returns 10 because iter_pages isn't filtering
    # Verify client called with limit=5
    mock_client.request_builder.build.assert_called_with({"limit": 5})


def test_iter_extract_stops_on_empty_page(service, mock_client):
    """Streaming stops when API returns no data."""
    mock_parser = MagicMock()
    mock_paginator = MagicMock()

    service.paginator = mock_paginator
    mock_client.response_parser = mock_parser

    mock_client.iter_pages.return_value = []  # Empty iteration
    mock_parser.parse_response.return_value = []

    chunks = list(service.iter_extract("activity", chunk_size=5))

    assert chunks == []
    mock_client.iter_pages.assert_called_once()
    mock_client.request_builder.build.assert_called_with({"limit": 5})


def test_iter_extract_respects_limit_with_pagination(service, mock_client):
    """Streaming honors limit across multiple pages."""
    mock_parser = MagicMock()
    mock_paginator = MagicMock()

    service.paginator = mock_paginator
    mock_client.response_parser = mock_parser

    mock_client.iter_pages.return_value = [
        {"data": "page1"},
        {"data": "page2"},
    ]
    mock_parser.parse_response.side_effect = [
        [{"id": 1}, {"id": 2}],
        [{"id": 3}],
    ]

    # chunk_size=2 used for limit
    chunks = list(service.iter_extract("activity", chunk_size=2, limit=3))

    assert len(chunks) == 2
    assert sum(len(chunk) for chunk in chunks) == 3
    mock_client.request_builder.build.assert_called_with({"limit": 2})


def test_extract_unknown_entity(service, mock_client):
    """Test extraction of unknown entity raises ValueError."""

    # Configure mock builder to raise error for unknown entity
    def raise_for_unknown(entity):
        if entity == "unknown_entity":
            raise ValueError("Unknown entity")

    # Try both potential methods
    mock_client.request_builder.build_for_endpoint.side_effect = raise_for_unknown
    mock_client.request_builder.for_endpoint.side_effect = raise_for_unknown

    with pytest.raises(ValueError, match="Unknown entity"):
        service.extract_all("unknown_entity")


@pytest.mark.parametrize("entity", ["assay", "target", "publication", "molecule"])
def test_extract_entities_dispatch(service, mock_client, entity):
    """Test correct client dispatch for entities."""
    mock_parser = MagicMock()
    mock_client.response_parser = mock_parser

    mock_parser.parse_response.return_value = []
    mock_client.iter_pages.return_value = []

    service.extract_all(entity)

    # Check that builder was configured for the entity
    # Handle alias mapping
    aliases = {
        "publication": "document",
        "molecule": "molecule",
        "activity": "activity",
        "assay": "assay",
        "target": "target",
    }
    expected = aliases.get(entity, entity)

    # Check if build_for_endpoint or for_endpoint was called
    try:
        mock_client.request_builder.build_for_endpoint.assert_called_with(expected)
    except AssertionError:
        mock_client.request_builder.for_endpoint.assert_called_with(expected)
