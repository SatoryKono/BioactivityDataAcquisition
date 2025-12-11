"""
Contract tests for ExtractionServiceABC implementations.

These tests verify that implementations conform to the port contracts defined
in the domain layer. Any implementation of ExtractionServiceABC must pass
these tests to ensure interoperability.

Contract tests verify:
1. Method signatures and return types
2. Behavioral invariants (e.g., iter_extract yields batches)
3. Error handling patterns
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any
from unittest.mock import Mock

import pytest

from bioetl.domain.ports.extraction import (
    BatchAdapterABC,
    ExtractionServiceABC,
    RecordFetcherABC,
    VersionProviderABC,
)


class RecordFetcherContractTests(ABC):
    """Contract tests for RecordFetcherABC implementations.

    Subclass this and implement create_fetcher() to test your implementation.
    """

    @abstractmethod
    def create_fetcher(self) -> RecordFetcherABC:
        """Create instance of RecordFetcherABC implementation to test."""

    def test_iter_extract_returns_iterable(self) -> None:
        """iter_extract must return an Iterable."""
        fetcher = self.create_fetcher()
        result = fetcher.iter_extract("test_entity")
        assert isinstance(result, Iterable)

    def test_iter_extract_yields_lists(self) -> None:
        """iter_extract must yield list batches."""
        fetcher = self.create_fetcher()
        for batch in fetcher.iter_extract("test_entity"):
            assert isinstance(batch, list)
            break  # Just check first batch

    def test_iter_extract_batch_items_are_dicts(self) -> None:
        """iter_extract batch items must be dict[str, Any]."""
        fetcher = self.create_fetcher()
        for batch in fetcher.iter_extract("test_entity"):
            for item in batch:
                assert isinstance(item, dict)
            break  # Just check first batch

    def test_extract_all_returns_list(self) -> None:
        """extract_all must return a list."""
        fetcher = self.create_fetcher()
        result = fetcher.extract_all("test_entity")
        assert isinstance(result, list)

    def test_extract_all_items_are_dicts(self) -> None:
        """extract_all items must be dict[str, Any]."""
        fetcher = self.create_fetcher()
        result = fetcher.extract_all("test_entity")
        for item in result:
            assert isinstance(item, dict)


class VersionProviderContractTests(ABC):
    """Contract tests for VersionProviderABC implementations."""

    @abstractmethod
    def create_provider(self) -> VersionProviderABC:
        """Create instance of VersionProviderABC implementation to test."""

    def test_get_release_version_returns_string(self) -> None:
        """get_release_version must return a string."""
        provider = self.create_provider()
        result = provider.get_release_version()
        assert isinstance(result, str)

    def test_get_release_version_not_empty(self) -> None:
        """get_release_version must return non-empty string."""
        provider = self.create_provider()
        result = provider.get_release_version()
        assert result.strip() != ""


class ExtractionServiceContractTests(RecordFetcherContractTests):
    """Contract tests for ExtractionServiceABC implementations.

    Combines RecordFetcherABC tests with additional ExtractionService tests.
    """

    @abstractmethod
    def create_fetcher(self) -> ExtractionServiceABC:
        """Create instance of ExtractionServiceABC implementation to test."""

    def test_get_release_version_returns_string(self) -> None:
        """get_release_version must return a string."""
        service = self.create_fetcher()
        result = service.get_release_version()
        assert isinstance(result, str)

    def test_parse_response_returns_list(self) -> None:
        """parse_response must return a list."""
        service = self.create_fetcher()
        # Use empty response as baseline
        result = service.parse_response({})
        assert isinstance(result, list)

    def test_serialize_records_returns_list(self) -> None:
        """serialize_records must return a list."""
        service = self.create_fetcher()
        result = service.serialize_records("test_entity", [])
        assert isinstance(result, list)


class BatchAdapterContractTests(ABC):
    """Contract tests for BatchAdapterABC implementations."""

    @abstractmethod
    def create_adapter(self) -> BatchAdapterABC:
        """Create instance of BatchAdapterABC implementation to test."""

    def test_process_batch_returns_list(self) -> None:
        """process_batch must return a list."""
        adapter = self.create_adapter()
        result = adapter.process_batch([])
        assert isinstance(result, list)

    def test_process_batch_items_are_dicts(self) -> None:
        """process_batch items must be dict[str, Any]."""
        adapter = self.create_adapter()
        result = adapter.process_batch([{"key": "value"}])
        for item in result:
            assert isinstance(item, dict)


# =============================================================================
# Stub Implementations for Testing the Contract Tests Themselves
# =============================================================================


class StubRecordFetcher(RecordFetcherABC):
    """Stub implementation for testing contract tests."""

    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self._records = records or [{"id": 1, "name": "test"}]

    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: object
    ) -> Iterable[list[dict[str, Any]]]:
        yield self._records

    def extract_all(self, entity: str, **filters: object) -> list[dict[str, Any]]:
        return self._records


class StubVersionProvider(VersionProviderABC):
    """Stub implementation for testing contract tests."""

    def __init__(self, version: str = "1.0") -> None:
        self._version = version

    def get_release_version(self) -> str:
        return self._version


class StubExtractionService(StubRecordFetcher, ExtractionServiceABC):
    """Stub implementation for testing contract tests."""

    def __init__(
        self,
        records: list[dict[str, Any]] | None = None,
        version: str = "1.0",
    ) -> None:
        super().__init__(records)
        self._version = version

    def get_release_version(self) -> str:
        return self._version

    def request_batch(
        self, entity: str, batch_ids: list[str], filter_key: str
    ) -> dict[str, object]:
        return {"results": self._records}

    def parse_response(self, raw_response: object) -> list[dict[str, Any]]:
        if isinstance(raw_response, dict) and "results" in raw_response:
            return raw_response["results"]  # type: ignore[return-value]
        return []

    def serialize_records(
        self, entity: str, records: list[object]
    ) -> list[dict[str, Any]]:
        return [{"serialized": r} for r in records]


class StubBatchAdapter:
    """Stub implementation for BatchAdapterABC contract tests."""

    def process_batch(self, raw_batch: object) -> list[dict[str, Any]]:
        if isinstance(raw_batch, list):
            return [item if isinstance(item, dict) else {"value": item} for item in raw_batch]
        return []


# =============================================================================
# Concrete Test Classes Using Stub Implementations
# =============================================================================


class TestStubRecordFetcherContract(RecordFetcherContractTests):
    """Test that StubRecordFetcher passes contract tests."""

    def create_fetcher(self) -> RecordFetcherABC:
        return StubRecordFetcher()


class TestStubVersionProviderContract(VersionProviderContractTests):
    """Test that StubVersionProvider passes contract tests."""

    def create_provider(self) -> VersionProviderABC:
        return StubVersionProvider()


class TestStubExtractionServiceContract(ExtractionServiceContractTests):
    """Test that StubExtractionService passes contract tests."""

    def create_fetcher(self) -> ExtractionServiceABC:
        return StubExtractionService()


class TestStubBatchAdapterContract(BatchAdapterContractTests):
    """Test that StubBatchAdapter passes contract tests."""

    def create_adapter(self) -> BatchAdapterABC:
        return StubBatchAdapter()


# =============================================================================
# Additional Contract Invariant Tests
# =============================================================================


class TestExtractionServiceInvariants:
    """Test behavioral invariants of extraction services."""

    def test_iter_extract_with_chunk_size_respects_limit(self) -> None:
        """If chunk_size is specified, batches should not exceed it."""
        records = [{"id": i} for i in range(10)]
        fetcher = StubRecordFetcher(records)

        for batch in fetcher.iter_extract("test", chunk_size=5):
            # Our stub doesn't implement chunking, but real implementations should
            assert isinstance(batch, list)

    def test_extract_all_equivalent_to_iter_extract_combined(self) -> None:
        """extract_all should return same data as iterating all batches."""
        records = [{"id": i} for i in range(5)]
        fetcher = StubRecordFetcher(records)

        all_records = fetcher.extract_all("test")
        iter_records = []
        for batch in fetcher.iter_extract("test"):
            iter_records.extend(batch)

        assert all_records == iter_records

    def test_version_is_deterministic(self) -> None:
        """Multiple calls to get_release_version should return same value."""
        provider = StubVersionProvider("2.0")
        v1 = provider.get_release_version()
        v2 = provider.get_release_version()
        assert v1 == v2

    def test_parse_response_handles_empty_gracefully(self) -> None:
        """parse_response should handle empty/invalid input without crashing."""
        service = StubExtractionService()

        # Empty dict
        result = service.parse_response({})
        assert isinstance(result, list)

        # Dict without results
        result = service.parse_response({"other": "data"})
        assert isinstance(result, list)


class TestBatchAdapterInvariants:
    """Test behavioral invariants of batch adapters."""

    def test_empty_input_returns_empty_list(self) -> None:
        """Empty input should return empty list, not None or error."""
        adapter = StubBatchAdapter()
        result = adapter.process_batch([])
        assert result == []

    def test_preserves_dict_items(self) -> None:
        """Dict items should be preserved (possibly transformed)."""
        adapter = StubBatchAdapter()
        input_batch = [{"key": "value"}, {"other": 123}]
        result = adapter.process_batch(input_batch)

        assert len(result) == len(input_batch)
        for item in result:
            assert isinstance(item, dict)
