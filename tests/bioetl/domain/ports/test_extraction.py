"""Tests for extraction port contracts and type aliases."""

from collections.abc import Iterable

import pytest

from bioetl.domain.ports.extraction import (
    BatchAdapterABC,
    ExtractionServiceABC,
    RawRecordBatch,
    RawRecordDict,
    RecordFetcherABC,
    VersionProviderABC,
    from_raw_records,
    to_raw_records,
)
from bioetl.domain.record_source import RawRecord


class TestTypeAliases:
    """Tests for type alias compatibility and correctness."""

    def test_raw_record_dict_accepts_dict(self) -> None:
        """RawRecordDict should accept dict[str, Any]."""
        record: RawRecordDict = {"id": "123", "name": "test", "value": 42.5}
        assert isinstance(record, dict)
        assert record["id"] == "123"

    def test_raw_record_batch_accepts_list_of_dicts(self) -> None:
        """RawRecordBatch should accept list of record dicts."""
        batch: RawRecordBatch = [
            {"id": "1", "name": "first"},
            {"id": "2", "name": "second"},
        ]
        assert isinstance(batch, list)
        assert len(batch) == 2
        assert all(isinstance(r, dict) for r in batch)

    def test_type_aliases_are_compatible_with_any_values(self) -> None:
        """Type aliases should allow Any values in dicts."""
        record: RawRecordDict = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "nested": {"deep": {"value": "ok"}},
        }
        assert record["string"] == "value"
        assert record["nested"]["deep"]["value"] == "ok"


class TestRecordFetcherABC:
    """Tests for RecordFetcherABC contract."""

    def test_is_abstract_class(self) -> None:
        """RecordFetcherABC should not be instantiable directly."""
        with pytest.raises(TypeError, match="abstract"):
            RecordFetcherABC()  # type: ignore[abstract]

    def test_requires_iter_extract_method(self) -> None:
        """Implementations must provide iter_extract method."""

        class IncompleteFetcher(RecordFetcherABC):
            def extract_all(self, entity: str, **filters: object) -> RawRecordBatch:
                return []

        with pytest.raises(TypeError, match="abstract"):
            IncompleteFetcher()  # type: ignore[abstract]

    def test_requires_extract_all_method(self) -> None:
        """Implementations must provide extract_all method."""

        class IncompleteFetcher(RecordFetcherABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RawRecordBatch]:
                yield []

        with pytest.raises(TypeError, match="abstract"):
            IncompleteFetcher()  # type: ignore[abstract]

    def test_complete_implementation_instantiates(self) -> None:
        """Complete implementation should be instantiable."""

        class CompleteFetcher(RecordFetcherABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RawRecordBatch]:
                yield [{"id": "1"}]

            def extract_all(self, entity: str, **filters: object) -> RawRecordBatch:
                return [{"id": "1"}]

        fetcher = CompleteFetcher()
        assert isinstance(fetcher, RecordFetcherABC)

    def test_iter_extract_returns_generic_dicts(self) -> None:
        """iter_extract should return Iterable[list[dict[str, Any]]]."""

        class TestFetcher(RecordFetcherABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RawRecordBatch]:
                yield [
                    {"id": "1", "name": "first"},
                    {"id": "2", "name": "second"},
                ]

            def extract_all(self, entity: str, **filters: object) -> RawRecordBatch:
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
            ) -> Iterable[RawRecordBatch]:
                yield []

            def extract_all(self, entity: str, **filters: object) -> RawRecordBatch:
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
            ) -> Iterable[RawRecordBatch]:
                yield [{"id": "1"}]

            def extract_all(self, entity: str, **filters: object) -> RawRecordBatch:
                return [{"id": "1"}]

            def get_release_version(self) -> str:
                return "test_v1"

            def request_batch(
                self, entity: str, batch_ids: list[str], filter_key: str
            ) -> dict[str, object]:
                return {"results": []}

            def parse_response(self, raw_response: object) -> RawRecordBatch:
                return []

        service = CompleteService()
        assert isinstance(service, ExtractionServiceABC)
        assert isinstance(service, RecordFetcherABC)

    def test_parse_response_returns_generic_dicts(self) -> None:
        """parse_response should return list[dict[str, Any]]."""

        class TestService(ExtractionServiceABC):
            def iter_extract(
                self, entity: str, *, chunk_size: int | None = None, **filters: object
            ) -> Iterable[RawRecordBatch]:
                yield []

            def extract_all(self, entity: str, **filters: object) -> RawRecordBatch:
                return []

            def get_release_version(self) -> str:
                return "test"

            def request_batch(
                self, entity: str, batch_ids: list[str], filter_key: str
            ) -> dict[str, object]:
                return {}

            def parse_response(self, raw_response: object) -> RawRecordBatch:
                if isinstance(raw_response, dict):
                    items = raw_response.get("items", [])
                    if isinstance(items, list):
                        return items
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
            def process_batch(self, raw_batch: object) -> RawRecordBatch:
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


class TestBackwardCompatibilityHelpers:
    """Tests for backward compatibility helper functions."""

    def test_to_raw_records_converts_dicts_to_models(self) -> None:
        """to_raw_records should convert dicts to RawRecord models."""
        batch: RawRecordBatch = [
            {"id": "1", "name": "first"},
            {"id": "2", "name": "second"},
        ]

        with pytest.warns(DeprecationWarning, match="to_raw_records is deprecated"):
            records = to_raw_records(batch)

        assert len(records) == 2
        assert all(isinstance(r, RawRecord) for r in records)
        assert records[0].id == "1"  # type: ignore[attr-defined]
        assert records[1].name == "second"  # type: ignore[attr-defined]

    def test_to_raw_records_handles_empty_batch(self) -> None:
        """to_raw_records should handle empty batches."""
        with pytest.warns(DeprecationWarning):
            records = to_raw_records([])

        assert records == []

    def test_to_raw_records_preserves_nested_structures(self) -> None:
        """to_raw_records should preserve nested data structures."""
        batch: RawRecordBatch = [
            {
                "id": "1",
                "nested": {"key": "value"},
                "list": [1, 2, 3],
            }
        ]

        with pytest.warns(DeprecationWarning):
            records = to_raw_records(batch)

        assert records[0].nested == {"key": "value"}  # type: ignore[attr-defined]
        assert records[0].list == [1, 2, 3]  # type: ignore[attr-defined]

    def test_from_raw_records_converts_models_to_dicts(self) -> None:
        """from_raw_records should convert RawRecord models to dicts."""
        records = [
            RawRecord.model_validate({"id": "1", "name": "first"}),
            RawRecord.model_validate({"id": "2", "name": "second"}),
        ]

        with pytest.warns(DeprecationWarning, match="from_raw_records is deprecated"):
            batch = from_raw_records(records)

        assert len(batch) == 2
        assert all(isinstance(r, dict) for r in batch)
        assert batch[0]["id"] == "1"
        assert batch[1]["name"] == "second"

    def test_from_raw_records_handles_empty_list(self) -> None:
        """from_raw_records should handle empty lists."""
        with pytest.warns(DeprecationWarning):
            batch = from_raw_records([])

        assert batch == []

    def test_roundtrip_conversion(self) -> None:
        """Converting dicts -> models -> dicts should preserve data."""
        original_batch: RawRecordBatch = [
            {"id": "1", "value": 100, "nested": {"a": 1}},
            {"id": "2", "value": 200, "nested": {"b": 2}},
        ]

        with pytest.warns(DeprecationWarning):
            records = to_raw_records(original_batch)

        with pytest.warns(DeprecationWarning):
            restored_batch = from_raw_records(records)

        assert len(restored_batch) == len(original_batch)
        for orig, restored in zip(original_batch, restored_batch):
            assert orig["id"] == restored["id"]
            assert orig["value"] == restored["value"]
            assert orig["nested"] == restored["nested"]


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

        # Type aliases
        assert hasattr(ports, "RawRecordDict")
        assert hasattr(ports, "RawRecordBatch")
        # Abstract base classes
        assert hasattr(ports, "RecordFetcherABC")
        assert hasattr(ports, "VersionProviderABC")
        assert hasattr(ports, "ExtractionServiceABC")
        # Protocols
        assert hasattr(ports, "BatchAdapterABC")
        # Backward compatibility helpers
        assert hasattr(ports, "to_raw_records")
        assert hasattr(ports, "from_raw_records")

    def test_type_alias_values_are_correct(self) -> None:
        """Type aliases should have correct underlying types."""
        from bioetl.domain.ports.extraction import RawRecordBatch, RawRecordDict

        # These are TypeAliases, we can verify they work as expected
        test_dict: RawRecordDict = {"key": "value"}
        test_batch: RawRecordBatch = [test_dict]

        assert isinstance(test_dict, dict)
        assert isinstance(test_batch, list)
