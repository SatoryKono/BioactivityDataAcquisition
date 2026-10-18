"""Preparation helpers for Bronze writer orchestration."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, cast

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import BatchID, JsonDict, RunID, RunType

__all__ = [
    "BronzeWriteArtifacts",
    "BronzeWritePostwriteContext",
    "BronzeWritePrepared",
    "BronzeWriteRequest",
    "build_bronze_write_artifacts",
    "prepare_bronze_write",
]


@dataclass(frozen=True, slots=True)
class BronzeWriteRequest:
    """Normalized request carried through one Bronze write pipeline."""

    records: Iterator[bytes]
    provider: str
    entity: str
    date: datetime
    batch_id: BatchID
    run_id: RunID
    run_type: RunType
    ingestion_ts: datetime
    source_metadata: SourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class BronzeWritePrepared:
    """Prepared context used by Bronze write orchestration phases."""

    records_iter: Iterator[bytes]
    record_list: list[bytes]
    date_str: str
    relative_path: str
    metadata: JsonDict
    full_path: Path
    meta_path: Path


@dataclass(frozen=True, slots=True)
class BronzeWriteArtifacts:
    """Measured write output produced before post-write side effects."""

    record_count: int
    uncompressed_size: int
    compressed_size: int


@dataclass(frozen=True, slots=True)
class BronzeWritePostwriteContext:
    """All data needed by Bronze post-write side effects."""

    request: BronzeWriteRequest
    prepared: BronzeWritePrepared
    write_artifacts: BronzeWriteArtifacts
    duration: float


class _BronzeWritePreparationHostProtocol(Protocol):
    """Typed host contract for Bronze pre-write validation and path building."""

    base_path: Path
    save_json: bool
    validate_json: bool

    def _validate_bronze_request_inputs(self, request: BronzeWriteRequest) -> None: ...

    def _validate_json_records(self, records: Iterator[bytes]) -> Iterator[bytes]: ...

    def _resolve_bronze_path(
        self,
        provider: str,
        entity: str,
        date_str: str,
        filename: str,
    ) -> str: ...

    def _build_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        effective_ts: datetime,
        provider: str,
        entity: str,
        batch_id: BatchID,
    ) -> dict[str, str]: ...


def prepare_bronze_write(
    host: _BronzeWritePreparationHostProtocol,
    request: BronzeWriteRequest,
) -> BronzeWritePrepared:
    """Validate inputs and build the prepared Bronze write context."""
    host._validate_bronze_request_inputs(request)

    validated_records = iter(request.records)
    if host.validate_json:
        validated_records = host._validate_json_records(validated_records)

    date_str = request.date.strftime("%Y-%m-%d")
    filename = f"batch_{date_str}_{request.batch_id}.jsonl.zst"
    relative_path = host._resolve_bronze_path(
        request.provider,
        request.entity,
        date_str,
        filename,
    )
    metadata = host._build_bronze_metadata(
        request.run_id,
        request.run_type,
        request.ingestion_ts,
        request.provider,
        request.entity,
        request.batch_id,
    )
    if host.save_json:
        record_list = list(validated_records)
        records_iter = iter(record_list)
    else:
        record_list = cast(list[bytes], [])
        records_iter = validated_records

    full_path = host.base_path / relative_path
    return BronzeWritePrepared(
        records_iter=records_iter,
        record_list=record_list,
        date_str=date_str,
        relative_path=relative_path,
        metadata=metadata,
        full_path=full_path,
        meta_path=full_path.with_suffix(".zst.meta.json"),
    )


def build_bronze_write_artifacts(
    *,
    full_path: Path,
    record_count: int,
    uncompressed_size: int,
) -> BronzeWriteArtifacts:
    """Build the measured Bronze write artifact payload."""
    return BronzeWriteArtifacts(
        record_count=record_count,
        uncompressed_size=uncompressed_size,
        compressed_size=full_path.stat().st_size,
    )
