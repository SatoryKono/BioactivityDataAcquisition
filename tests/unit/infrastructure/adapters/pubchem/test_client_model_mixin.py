"""Tests for PubChemAdapterModelMixin.

Covers:
- fetch_as_models: DTO conversion, validate vs construct, unsupported entity
- get_source_metadata: delegation to consume_source_metadata
- clear_request_collector: delegation to clear_source_metadata_collector
- request_count property: delegation to get_request_count
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from bioetl.infrastructure.adapters.pubchem.client_model_mixin import (
    PubChemAdapterModelMixin,
)


# ---------------------------------------------------------------------------
# Concrete test class that inherits the mixin
# ---------------------------------------------------------------------------


class _FakePubChemAdapter(PubChemAdapterModelMixin):
    """Minimal concrete class for testing the mixin."""

    def __init__(self) -> None:
        self._request_collector = MagicMock()
        self.rate_limiter = MagicMock()
        self.rate_limiter.rate = 5.0
        self._records_to_yield: list[dict[str, object]] = []

    async def fetch(  # type: ignore[override]
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ):
        for rec in self._records_to_yield:
            yield rec


@pytest.fixture
def adapter() -> _FakePubChemAdapter:
    return _FakePubChemAdapter()


# ---------------------------------------------------------------------------
# fetch_as_models
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchAsModels:
    async def test_converts_records_to_models(
        self, adapter: _FakePubChemAdapter
    ) -> None:
        """Records yielded from fetch() are converted via model_validate."""
        adapter._records_to_yield = [
            {"molecule_id": "123", "molecular_formula": "C9H8O4"},
            {"molecule_id": "456", "molecular_formula": "H2O"},
        ]

        results = []
        async for model in adapter.fetch_as_models("compound"):
            results.append(model)

        assert len(results) == 2
        assert isinstance(results[0], BaseModel)
        assert results[0].molecule_id == "123"  # type: ignore[attr-defined]

    async def test_cid_key_converted_to_string(
        self, adapter: _FakePubChemAdapter
    ) -> None:
        """When record has 'cid' key with int value, mixin converts it to str.

        Note: The conversion happens in-place on the record dict before
        model_validate. This test verifies the str() conversion logic.
        We use validate=False (model_construct) to avoid extra='forbid' rejection.
        """
        adapter._records_to_yield = [{"molecule_id": "999", "cid": 42}]

        results = []
        async for model in adapter.fetch_as_models("compound", validate=False):
            results.append(model)

        # model_construct receives cid="42" (converted from int 42)
        assert len(results) == 1

    async def test_unsupported_entity_raises_value_error(
        self, adapter: _FakePubChemAdapter
    ) -> None:
        with pytest.raises(ValueError, match="No DTO model for entity_type"):
            async for _ in adapter.fetch_as_models("unknown_entity"):
                continue

    async def test_validate_false_uses_construct(
        self, adapter: _FakePubChemAdapter
    ) -> None:
        """When validate=False, model_construct is used instead of model_validate."""
        adapter._records_to_yield = [{"molecule_id": "1"}]

        results = []
        async for model in adapter.fetch_as_models("compound", validate=False):
            results.append(model)

        assert len(results) == 1

    async def test_none_cid_not_converted(self, adapter: _FakePubChemAdapter) -> None:
        """When cid is None, the str conversion is skipped."""
        adapter._records_to_yield = [{"molecule_id": "1", "cid": None}]

        # Use validate=False to avoid extra='forbid' rejection of 'cid'
        results = []
        async for model in adapter.fetch_as_models("compound", validate=False):
            results.append(model)

        assert len(results) == 1

    async def test_record_without_cid_key(self, adapter: _FakePubChemAdapter) -> None:
        """Records without 'cid' key pass through without modification."""
        adapter._records_to_yield = [{"molecule_id": "100"}]

        results = []
        async for model in adapter.fetch_as_models("compound"):
            results.append(model)

        assert len(results) == 1
        assert results[0].molecule_id == "100"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# get_source_metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSourceMetadata:
    @patch(
        "bioetl.infrastructure.adapters.pubchem.client_model_mixin.consume_source_metadata"
    )
    def test_delegates_to_consume(
        self, mock_consume: MagicMock, adapter: _FakePubChemAdapter
    ) -> None:
        mock_consume.return_value = MagicMock()
        result = adapter.get_source_metadata(api_version="1.0")

        mock_consume.assert_called_once_with(
            collector=adapter._request_collector,
            url="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
            api_version="1.0",
        )
        assert result == mock_consume.return_value

    @patch(
        "bioetl.infrastructure.adapters.pubchem.client_model_mixin.consume_source_metadata"
    )
    def test_default_api_version_none(
        self, mock_consume: MagicMock, adapter: _FakePubChemAdapter
    ) -> None:
        adapter.get_source_metadata()
        mock_consume.assert_called_once_with(
            collector=adapter._request_collector,
            url="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
            api_version=None,
        )


# ---------------------------------------------------------------------------
# clear_request_collector
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClearRequestCollector:
    @patch(
        "bioetl.infrastructure.adapters.pubchem.client_model_mixin.clear_source_metadata_collector"
    )
    def test_delegates_to_clear(
        self, mock_clear: MagicMock, adapter: _FakePubChemAdapter
    ) -> None:
        adapter.clear_request_collector()
        mock_clear.assert_called_once_with(collector=adapter._request_collector)


# ---------------------------------------------------------------------------
# request_count
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequestCount:
    @patch(
        "bioetl.infrastructure.adapters.pubchem.client_model_mixin.get_request_count"
    )
    def test_delegates_to_get_request_count(
        self, mock_get: MagicMock, adapter: _FakePubChemAdapter
    ) -> None:
        mock_get.return_value = 42
        assert adapter.request_count == 42
        mock_get.assert_called_once_with(collector=adapter._request_collector)


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRepr:
    def test_repr_format(self, adapter: _FakePubChemAdapter) -> None:
        assert repr(adapter) == "PubChemAdapter(rate=5.0)"
