"""Tests for extraction port contracts."""

from collections.abc import Iterable

import pytest

from bioetl.domain.data import RecordBatch
from bioetl.domain.ports.extraction import (
    BatchAdapterABC,
    ExtractionServiceABC,
    RecordFetcherABC,
    VersionProviderABC,
)


class TestRecordFetcherABC:
    """Tests for RecordFetcherABC contract."""

    def test_is_abstract_class(self) -> None:
        """RecordFetcherABC should not be instantiable directly."""
        with pytest.raises(TypeError, match="abstract"):
            RecordFetcherABC()  # type: ignore[abstract]

    def test_requires_iter_extract_method(self) -> None:
        """Implementations must provide iter_extract method."""

        class IncompleteFetcher(RecordFetcherABC):
            def extract_all(self, entity: str, **filters: object) -> RecordBatch:
                return []

        with pytest.raises(TypeError, match="abstract"):
            IncompleteFetcher()  # type: ignore[abstract]

    def test_requires_extract_all_method(self) -> None:
        """Implementations must provide extract_all method."""

        class IncompleteFetcher(RecordFetcherABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RecordBatch]:
                yield []

        with pytest.raises(TypeError, match="abstract"):
            IncompleteFetcher()  # type: ignore[abstract]

    def test_complete_implementation_instantiates(self) -> None:
        """Complete implementation should be instantiable."""

        class CompleteFetcher(RecordFetcherABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RecordBatch]:
                yield [{"id": "1"}]

            def extract_all(self, entity: str, **filters: object) -> RecordBatch:
                return [{"id": "1"}]

        fetcher = CompleteFetcher()
        assert isinstance(fetcher, RecordFetcherABC)

    def test_iter_extract_returns_generic_dicts(self) -> None:
        """iter_extract should return Iterable[list[dict[str, Any]]]."""

        class TestFetcher(RecordFetcherABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RecordBatch]:
                yield [
                    {"id": "1", "name": "first"},
                    {"id": "2", "name": "second"},
                ]

            def extract_all(self, entity: str, **filters: object) -> RecordBatch:
                return list(self.iter_extract(entity))[0]

        fetcher = TestFetcher()
        batches = list(fetcher.iter_extract("test"))

        assert len(batches) == 1
        assert len(batches[0]) == 2
        assert batches[0][0]["id"] == "1"
        assert batches[0][1]["name"] == "second"

    def test_extract_all_returns_generic_dicts(self) -> None:
        """extract_all should return list[dict[str, Any]]."""

        class TestFetcher(RecordFetcherABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RecordBatch]:
                yield []

            def extract_all(self, entity: str, **filters: object) -> RecordBatch:
                return [
                    {"id": "1", "value": 100},
                    {"id": "2", "value": 200},
                ]

        fetcher = TestFetcher()
        records = fetcher.extract_all("test")

        assert isinstance(records, list)
        assert len(records) == 2
        assert all(isinstance(r, dict) for r in records)


class TestVersionProviderABC:
    """Tests for VersionProviderABC contract."""

    def test_is_abstract_class(self) -> None:
        """VersionProviderABC should not be instantiable directly."""
        with pytest.raises(TypeError, match="abstract"):
            VersionProviderABC()  # type: ignore[abstract]

    def test_requires_get_release_version_method(self) -> None:
        """Implementations must provide get_release_version method."""

        class IncompleteProvider(VersionProviderABC):
            pass

        with pytest.raises(TypeError, match="abstract"):
            IncompleteProvider()  # type: ignore[abstract]

    def test_complete_implementation_instantiates(self) -> None:
        """Complete implementation should be instantiable."""

        class CompleteProvider(VersionProviderABC):
            def get_release_version(self) -> str:
                return "v1.0.0"

        provider = CompleteProvider()
        assert isinstance(provider, VersionProviderABC)
        assert provider.get_release_version() == "v1.0.0"


class TestExtractionServiceABC:
    """Tests for ExtractionServiceABC contract."""

    def test_is_abstract_class(self) -> None:
        """ExtractionServiceABC should not be instantiable directly."""
        with pytest.raises(TypeError, match="abstract"):
            ExtractionServiceABC()  # type: ignore[abstract]

    def test_inherits_from_record_fetcher(self) -> None:
        """ExtractionServiceABC should inherit from RecordFetcherABC."""
        assert issubclass(ExtractionServiceABC, RecordFetcherABC)

    def test_complete_implementation_instantiates(self) -> None:
        """Complete implementation should be instantiable."""

        class CompleteService(ExtractionServiceABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RecordBatch]:
                yield [{"id": "1"}]

            def extract_all(self, entity: str, **filters: object) -> RecordBatch:
                return [{"id": "1"}]

            def get_release_version(self) -> str:
                return "test_v1"

            def request_batch(
                self, entity: str, batch_ids: list[str], filter_key: str
            ) -> dict[str, object]:
                return {"results": []}

            def parse_response(self, raw_response: object) -> RecordBatch:
                return []

            def serialize_records(
                self, entity: str, records: list[object]
            ) -> RecordBatch:
                return []

        service = CompleteService()
        assert isinstance(service, ExtractionServiceABC)
        assert isinstance(service, RecordFetcherABC)

    def test_parse_response_returns_generic_dicts(self) -> None:
        """parse_response should return list[dict[str, Any]]."""

        class TestService(ExtractionServiceABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RecordBatch]:
                yield []

            def extract_all(self, entity: str, **filters: object) -> RecordBatch:
                return []

            def get_release_version(self) -> str:
                return "test"

            def request_batch(
                self, entity: str, batch_ids: list[str], filter_key: str
            ) -> dict[str, object]:
                return {}

            def parse_response(self, raw_response: object) -> RecordBatch:
                if isinstance(raw_response, dict):
                    items = raw_response.get("items", [])
                    if isinstance(items, list):
                        return items
                return []

            def serialize_records(
                self, entity: str, records: list[object]
            ) -> RecordBatch:
                return []

        service = TestService()
        response = {"items": [{"id": "1"}, {"id": "2"}]}
        records = service.parse_response(response)

        assert isinstance(records, list)
        assert len(records) == 2
        assert all(isinstance(r, dict) for r in records)


class TestBatchAdapterABC:
    """Tests for BatchAdapterABC protocol."""

    def test_protocol_accepts_conforming_class(self) -> None:
        """Protocol should accept classes with process_batch method."""

        class ConformingAdapter:
            def process_batch(self, raw_batch: object) -> RecordBatch:
                if isinstance(raw_batch, list):
                    return raw_batch
                return []

        adapter = ConformingAdapter()
        # Protocol duck-typing: should work without explicit inheritance
        assert hasattr(adapter, "process_batch")
        result = adapter.process_batch([{"id": "1"}])
        assert result == [{"id": "1"}]

    def test_protocol_method_signature(self) -> None:
        """Protocol should define correct method signature."""
        # BatchAdapterABC is a Protocol, so we check its structure
        assert hasattr(BatchAdapterABC, "process_batch")


class TestPortsModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_are_importable(self) -> None:
        """All items in __all__ should be importable from the module."""
        from bioetl.domain.ports import extraction

        for name in extraction.__all__:
            assert hasattr(extraction, name), f"{name} not found in module"

    def test_exports_from_package_init(self) -> None:
        """All exports should be available from package init."""
        from bioetl.domain import ports

        # Abstract base classes
        assert hasattr(ports, "RecordFetcherABC")
        assert hasattr(ports, "VersionProviderABC")
        assert hasattr(ports, "ExtractionServiceABC")
        # Protocols
        assert hasattr(ports, "BatchAdapterABC")
