"""Tests for BaseAlternateIdFallbackHandler."""

from unittest.mock import Mock

import pytest

from bioetl.infrastructure.adapters.common.base_alternate_id_fallback import (
    BaseAlternateIdFallbackHandler,
)


class MockAlternateIdHandler(BaseAlternateIdFallbackHandler):
    """Concrete implementation for testing."""

    def __init__(self, logger):
        super().__init__(logger, provider_prefix="test_provider")
        self.search_calls = []

    async def _search_by_alternate_id(self, alt_id: str):
        self.search_calls.append(alt_id)
        if alt_id == "found_alt_id":
            return {"id": "found_id", "title": "Found Title"}
        return None

    async def _search_by_title(self, title: str):
        return None  # Not used in Phase 2 tests


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def handler(mock_logger):
    return MockAlternateIdHandler(mock_logger)


@pytest.mark.asyncio
async def test_process_missing_by_alternate_id_success(handler, mock_logger):
    """Test successful alternate ID lookup."""
    ids = ["primary_1"]
    found_ids = set()
    alternate_id_mapping = {"primary_1": "found_alt_id"}
    normalize_fn = lambda x: x

    results = []
    async for res in handler.process_missing_by_alternate_id(
        ids, found_ids, alternate_id_mapping, normalize_fn, limit=None, fetched=0
    ):
        results.append(res)

    assert len(results) == 1
    assert results[0]["_lookup_method"] == "alternate_id_fallback"
    assert results[0]["_original_id"] == "primary_1"
    assert results[0]["_alternate_id"] == "found_alt_id"
    assert "primary_1" in found_ids
    assert handler.search_calls == ["found_alt_id"]

    # Verify logging
    mock_logger.info.assert_any_call(
        "test_provider_alternate_id_fallback_success",
        original_id="primary_1",
        alternate_id="found_alt_id",
        found_id="found_id",
    )


@pytest.mark.asyncio
async def test_process_missing_by_alternate_id_not_found(handler, mock_logger):
    """Test alternate ID lookup failure."""
    ids = ["primary_1"]
    found_ids = set()
    alternate_id_mapping = {"primary_1": "missing_alt_id"}
    normalize_fn = lambda x: x

    results = []
    async for res in handler.process_missing_by_alternate_id(
        ids, found_ids, alternate_id_mapping, normalize_fn, limit=None, fetched=0
    ):
        results.append(res)

    assert len(results) == 0
    assert "primary_1" not in found_ids
    assert handler.search_calls == ["missing_alt_id"]

    mock_logger.warning.assert_any_call(
        "test_provider_alternate_id_fallback_not_found",
        id="primary_1",
        alternate_id="missing_alt_id",
    )


@pytest.mark.asyncio
async def test_process_missing_by_alternate_id_skip_found(handler):
    """Test skipping already found IDs."""
    ids = ["primary_1"]
    found_ids = {"primary_1"}
    alternate_id_mapping = {"primary_1": "found_alt_id"}

    results = []
    async for res in handler.process_missing_by_alternate_id(
        ids, found_ids, alternate_id_mapping, lambda x: x, limit=None, fetched=0
    ):
        results.append(res)

    assert len(results) == 0
    assert len(handler.search_calls) == 0


@pytest.mark.asyncio
async def test_process_missing_by_alternate_id_no_mapping(handler, mock_logger):
    """Test behavior when no alternate ID mapping exists."""
    ids = ["primary_1"]
    found_ids = set()
    alternate_id_mapping = {}

    results = []
    async for res in handler.process_missing_by_alternate_id(
        ids, found_ids, alternate_id_mapping, lambda x: x, limit=None, fetched=0
    ):
        results.append(res)

    assert len(results) == 0
    assert len(handler.search_calls) == 0
    mock_logger.debug.assert_any_call(
        "test_provider_no_alternate_id",
        id="primary_1",
    )
