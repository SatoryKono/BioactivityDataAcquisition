from collections.abc import Iterable
from typing import cast

from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.record_source import ApiRecordSource, InMemoryRecordSource, RawRecord


class _DummyExtractionService:
    def __init__(self) -> None:
        self.called_with: dict[str, str] | None = None

    def extract_all(
        self, entity: str, **filters: str
    ) -> list[RawRecord]:  # type: ignore[override]
        record_batches = list(self.iter_extract(entity, **filters))
        flattened: list[RawRecord] = []
        for batch in record_batches:
            flattened.extend(batch)
        return flattened

    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: str
    ) -> Iterable[list[RawRecord]]:  # type: ignore[override]
        self.called_with = {"entity": entity, **filters, "chunk_size": chunk_size}
        records = [
            {"id": "1", "name": "alpha"},
            {"id": "2", "name": "beta"},
        ]
        if chunk_size is None or chunk_size <= 0:
            yield records
            return

        for start in range(0, len(records), chunk_size):
            yield records[start : start + chunk_size]

    def get_release_version(self) -> str:  # pragma: no cover
        return "v1"

    def request_batch(
        self, entity: str, batch_ids: list[str], filter_key: str
    ):  # pragma: no cover
        raise NotImplementedError

    def parse_response(self, raw_response):  # pragma: no cover
        raise NotImplementedError

    def serialize_records(
        self, entity: str, records: list[dict[str, str]]
    ):  # pragma: no cover
        raise NotImplementedError


def test_in_memory_record_source_iterates_stably() -> None:
    records: list[RawRecord] = [
        cast(RawRecord, {"id": "1", "value": "a"}),
        cast(RawRecord, {"id": "2", "value": "b"}),
    ]
    source = InMemoryRecordSource(records)

    first_pass = list(source.iter_records())
    second_pass = list(source.iter_records())

    assert len(first_pass) == len(second_pass) == 1
    assert first_pass[0] == records
    assert second_pass[0] == records


def test_api_record_source_returns_serialized_records() -> None:
    extraction = _DummyExtractionService()
    source = ApiRecordSource(
        extraction_service=cast(ExtractionServiceABC, extraction),
        entity="activity",
        filters={"limit": 1},
    )

    records = list(source.iter_records())

    assert extraction.called_with == {
        "entity": "activity",
        "limit": 1,
        "chunk_size": None,
    }
    assert len(records) == 1
    expected_records = [
        {"id": "1", "name": "alpha"},
        {"id": "2", "name": "beta"},
    ]
    assert records[0] == expected_records
