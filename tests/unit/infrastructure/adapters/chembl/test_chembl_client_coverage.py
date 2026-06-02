"""Additional coverage tests for ChemblAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.entities.chembl import (
    ActivityRecord,
    ChemblPublicationRecord,
    CompoundLinkRecord,
    PublicationSimilarityRecord,
    TissueRecord,
)
from bioetl.domain.exceptions import ExternalServiceError, RetryExhaustedError
from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters.chembl import ChemblAdapter


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.circuit_breaker = MagicMock()
    client.circuit_breaker.get_state.return_value = CircuitBreakerState.CLOSED
    client.circuit_breaker.get_failure_count.return_value = 0
    return client


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    return ChemblAdapter(http_client=mock_http_client, logger=mock_logger)


@pytest.mark.asyncio
async def test_fetch_as_models_valid(adapter, mock_http_client):
    """Test fetching as validated models."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "activities": [
            {
                "activity_id": "1",
                "assay_id": "CHEMBL123",
                "molecule_id": "CHEMBL456",
                "pchembl_value": "7.5",
                "standard_type": "IC50",
                "standard_value": "30.0",
                "standard_units": "nM",
                "target_id": "CHEMBL789",
            }
        ],
        "page_meta": {"next": None},
    }
    mock_http_client.get.return_value = mock_response

    models = []
    async for model in adapter.fetch_as_models("activity", validate=True):
        models.append(model)

    assert len(models) == 1
    assert isinstance(models[0], ActivityRecord)
    assert models[0].activity_id == "1"


@pytest.mark.asyncio
async def test_fetch_as_models_invalid_type(adapter):
    """Test fetch_as_models with unsupported entity type."""
    with pytest.raises(ValueError):
        async for _ in adapter.fetch_as_models("unsupported_type"):
            continue


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("entity_type", "record", "expected_type"),
    (
        (
            "publication",
            {
                "publication_id": "CHEMBL1234567",
                "title": "Deterministic publication alias coverage",
            },
            ChemblPublicationRecord,
        ),
        (
            "tissue",
            {
                "tissue_id": "CHEMBL-T1",
                "pref_name": "Liver",
                "bto_id": "BTO:0000759",
            },
            TissueRecord,
        ),
        (
            "compound_record",
            {
                "record_id": 10,
                "molecule_id": "CHEMBL25",
                "publication_id": "CHEMBL1123456",
                "src_id": 1,
            },
            CompoundLinkRecord,
        ),
        (
            "publication_similarity",
            {
                "sim_id": 99,
                "doc_1": 100,
                "doc_2": 200,
                "tid_tani": 0.75,
                "mol_tani": 0.25,
            },
            PublicationSimilarityRecord,
        ),
    ),
)
async def test_fetch_as_models_supports_newly_registered_chembl_dtos(
    adapter,
    mock_http_client,
    entity_type,
    record,
    expected_type,
):
    plural_key_by_entity = {
        "publication": "documents",
        "tissue": "tissues",
        "compound_record": "compound_records",
        "publication_similarity": "document_similarities",
    }
    mock_response = MagicMock()
    mock_response.json.return_value = {
        plural_key_by_entity[entity_type]: [record],
        "page_meta": {"next": None},
    }
    mock_http_client.get.return_value = mock_response

    models = []
    async for model in adapter.fetch_as_models(entity_type, validate=True):
        models.append(model)

    assert len(models) == 1
    assert isinstance(models[0], expected_type)


@pytest.mark.asyncio
async def test_chembl_client_coverage__get_entity_count__6ef0e846(
    adapter, mock_http_client
):
    """Test getting total entity count."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"page_meta": {"total_count": 12345}}
    mock_http_client.get.return_value = mock_response

    count = await adapter.get_entity_count("activity")
    assert count == 12345
    mock_http_client.get.assert_called_with(
        "https://www.ebi.ac.uk/chembl/api/data/activity",
        params={"limit": 1, "format": "json"},
    )


@pytest.mark.asyncio
async def test_fetch_single_record_direct_success(adapter, mock_http_client):
    """Test successful fallback to direct endpoint."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"target_id": "CHEMBL123"}
    mock_http_client.get.return_value = mock_response

    result = await adapter._fetch_single_record_direct("target", "CHEMBL123")

    assert result is not None
    assert result["target_id"] == "CHEMBL123"
    mock_http_client.get.assert_called_with(
        "https://www.ebi.ac.uk/chembl/api/data/target/CHEMBL123",
        params={"format": "json"},
    )


@pytest.mark.asyncio
async def test_fetch_single_record_direct_failure(adapter, mock_http_client):
    """Test failed fallback to direct endpoint."""
    mock_http_client.get.side_effect = Exception("API Error")

    result = await adapter._fetch_single_record_direct("target", "CHEMBL123")

    assert result is None
    adapter.logger.warning.assert_called()


@pytest.mark.asyncio
async def test_retry_with_split_batches(adapter, mock_http_client):
    """Test batch splitting logic on failure."""

    # Mock _fetch_batch_with_reduction to avoid complex recursion logic
    # We just want to see if it splits
    async def empty_async_gen(*args, **kwargs):
        for record in ():
            yield record

    adapter._fetch_batch_with_reduction = MagicMock(side_effect=empty_async_gen)

    id_batch = ["1", "2", "3", "4"]
    error = RetryExhaustedError("Fail", attempts=3)
    seen_ids = set()

    gen = adapter._retry_with_split_batches(
        "target", id_batch, "id", None, seen_ids, "id", error
    )

    async for _ in gen:
        continue

    # Should call twice with split batches
    assert adapter._fetch_batch_with_reduction.call_count == 2
    args_list = adapter._fetch_batch_with_reduction.call_args_list
    assert args_list[0][0][1] == ["1", "2"]  # First half
    assert args_list[1][0][1] == ["3", "4"]  # Second half


def test_mark_record_as_seen_supports_composite_keys(adapter) -> None:
    seen_ids: set[str] = set()

    first = adapter._mark_record_as_seen(
        {"left_id": "A", "right_id": "B"},
        seen_ids,
        "left_id",
        ("left_id", "right_id"),
    )
    duplicate = adapter._mark_record_as_seen(
        {"left_id": "A", "right_id": "B"},
        seen_ids,
        "left_id",
        ("left_id", "right_id"),
    )

    assert first is True
    assert duplicate is False
    assert seen_ids == {"A|B"}


@pytest.mark.asyncio
async def test_is_retry_exhausted_error(adapter):
    """Test error type checking."""
    e1 = RetryExhaustedError("Fail", attempts=3)
    assert adapter._is_retry_exhausted_error(e1) is True

    e2 = ExternalServiceError("Wrapper")
    e2.__cause__ = e1
    assert adapter._is_retry_exhausted_error(e2) is True

    e3 = ValueError("Other")
    assert adapter._is_retry_exhausted_error(e3) is False


@pytest.mark.asyncio
async def test_reset_circuit_breaker(adapter, mock_http_client):
    """Test circuit breaker reset."""
    adapter.reset_circuit_breaker()
    mock_http_client.circuit_breaker.reset.assert_called_once()
    adapter.logger.info.assert_called_with(
        "chembl_circuit_breaker_reset", provider="chembl"
    )
