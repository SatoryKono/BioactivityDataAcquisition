"""Same-path owner tests for Bronze writer pipeline helper module."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.domain.types import RunType
from bioetl.infrastructure.storage.bronze.pipeline_helpers import (
    BronzeWriteArtifacts,
    BronzeWriteRequest,
    build_bronze_write_artifacts,
    prepare_bronze_write,
)


pytestmark = pytest.mark.unit


class _HostStub:
    def __init__(self) -> None:
        self.base_path = Path("test-output/bronze")
        self.save_json = True
        self.validate_json = False
        self.validated_requests: list[BronzeWriteRequest] = []

    def _validate_bronze_request_inputs(self, request: BronzeWriteRequest) -> None:
        self.validated_requests.append(request)

    def _validate_json_records(self, records):
        return records

    def _resolve_bronze_path(
        self,
        provider: str,
        entity: str,
        date_str: str,
        filename: str,
    ) -> str:
        return f"{provider}/{entity}/{date_str}/{filename}"

    def _build_bronze_metadata(
        self,
        run_id,
        run_type,
        effective_ts,
        provider,
        entity,
        batch_id,
    ) -> dict[str, str]:
        return {
            "run_id": str(run_id),
            "run_type": run_type.value,
            "provider": provider,
            "entity": entity,
            "batch_id": str(batch_id),
            "effective_ts": effective_ts.isoformat(),
        }


def test_prepare_bronze_write_materializes_records_and_paths() -> None:
    host = _HostStub()
    request = BronzeWriteRequest(
        records=iter([b'{"id":1}\n', b'{"id":2}\n']),
        provider="chembl",
        entity="activity",
        date=datetime(2026, 3, 19, tzinfo=UTC),
        batch_id="batch-001",
        run_id="run-001",
        run_type=RunType.INCREMENTAL,
        ingestion_ts=datetime(2026, 3, 19, 12, 0, tzinfo=UTC),
    )

    prepared = prepare_bronze_write(host, request)

    assert host.validated_requests == [request]
    assert prepared.date_str == "2026-03-19"
    assert prepared.relative_path.endswith("batch_2026-03-19_batch-001.jsonl.zst")
    assert prepared.full_path == host.base_path / prepared.relative_path
    assert list(prepared.records_iter) == [b'{"id":1}\n', b'{"id":2}\n']
    assert prepared.record_list == [b'{"id":1}\n', b'{"id":2}\n']
    assert prepared.metadata["provider"] == "chembl"


def test_build_bronze_write_artifacts_uses_file_size_and_frozen_dataclass() -> None:
    temp_path = Path(__file__)
    artifacts = build_bronze_write_artifacts(
        full_path=temp_path,
        record_count=2,
        uncompressed_size=128,
    )

    assert isinstance(artifacts, BronzeWriteArtifacts)
    assert artifacts.record_count == 2
    assert artifacts.uncompressed_size == 128
    assert artifacts.compressed_size == temp_path.stat().st_size

    with pytest.raises(FrozenInstanceError):
        artifacts.record_count = 3  # type: ignore[misc]
