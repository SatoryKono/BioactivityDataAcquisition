"""
Tests for ChemblExtractionService.
"""
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.clients.chembl.contracts import ChemblDataClientABC
from bioetl.application.pipelines.chembl.extraction import ChemblExtractionService


@pytest.fixture
def mock_client():
    """Mock ChEMBL client."""
    return MagicMock(spec=ChemblDataClientABC)


@pytest.fixture
def service(mock_client):
    """ChemblExtractionService instance with mock client."""
    return ChemblExtractionService(client=mock_client, batch_size=10)


def test_get_release_version(service, mock_client):
    """Test getting release version."""
    mock_client.metadata.return_value = {"chembl_release": "chembl_34"}
    version = service.get_release_version()
    assert version == "chembl_34"
    mock_client.metadata.assert_called_once()


def test_extract_all_single_page(service, mock_client):
    """Test extraction of a single page."""
    # Mock parser and paginator attributes on the instance
    mock_paginator = MagicMock()
    mock_parser = MagicMock()

    service.paginator = mock_paginator
    service.parser = mock_parser

    # Setup mock responses
    mock_client.request_activity.return_value = {"data": "page1"}
    mock_parser.parse.return_value = [{"id": 1}, {"id": 2}]
    mock_paginator.has_more.return_value = False

    # Act
    df = service.extract_all("activity")

    # Assert
    assert len(df) == 2
    assert df.iloc[0]["id"] == 1
    mock_client.request_activity.assert_called_with(offset=0, limit=10)


def test_extract_all_pagination(service, mock_client):
    """Test extraction with pagination."""
    # Mock parser and paginator attributes
    mock_paginator = MagicMock()
    mock_parser = MagicMock()

    service.paginator = mock_paginator
    service.parser = mock_parser

    # Setup iteration
    # Call 1: returns 2 items, has_more=True
    # Call 2: returns 1 item, has_more=False

    mock_client.request_activity.side_effect = [
        {"data": "page1"},
        {"data": "page2"}
    ]
    mock_parser.parse.side_effect = [
        [{"id": 1}, {"id": 2}],
        [{"id": 3}]
    ]
    mock_paginator.has_more.side_effect = [True, False]

    # Act
    df = service.extract_all("activity")

    # Assert
    assert len(df) == 3
    assert mock_client.request_activity.call_count == 2
    # Check call args
    calls = mock_client.request_activity.call_args_list
    assert calls[0].kwargs["offset"] == 0
    assert calls[1].kwargs["offset"] == 10


def test_extract_all_limit(service, mock_client):
    """Test extraction with limit."""
    # Mock parser
    mock_parser = MagicMock()
    service.parser = mock_parser

    # Returns 10 items per call
    mock_parser.parse.return_value = [{"id": i} for i in range(10)]

    # Act - request limit 5
    df = service.extract_all("activity", limit=5)

    # Assert
    assert len(df) == 5
    # Should call client with limit=5
    mock_client.request_activity.assert_called_with(offset=0, limit=5)


def test_extract_unknown_entity(service):
    """Test extraction of unknown entity raises ValueError."""
    with pytest.raises(ValueError, match="Unknown entity"):
        service.extract_all("unknown_entity")


@pytest.mark.parametrize("entity,method", [
    ("assay", "request_assay"),
    ("target", "request_target"),
    ("document", "request_document"),
    ("testitem", "request_molecule"),
])
def test_extract_entities_dispatch(service, mock_client, entity, method):
    """Test correct client method dispatch for entities."""
    # Mock parser - paginator not strictly needed as we return empty list
    mock_parser = MagicMock()
    service.parser = mock_parser
    
    mock_parser.parse.return_value = []

    service.extract_all(entity)

    # Check corresponding method called
    getattr(mock_client, method).assert_called_once()

