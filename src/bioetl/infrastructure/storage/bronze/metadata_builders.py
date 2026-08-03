"""Pure metadata builders for Bronze writer flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from bioetl.domain.models.metadata import BronzeMetadata, SourceMetadata
from bioetl.domain.types import BatchID, JsonDict, RunID, RunType

__all__ = [
    "BronzeLineageMetadataRequest",
    "BronzeMetadataPayloadRequest",
    "build_bronze_lineage_metadata",
    "build_bronze_metadata_payload",
    "build_full_bronze_metadata",
]


@dataclass(frozen=True, slots=True)
class BronzeLineageMetadataRequest:
    """Minimal lineage metadata attached to Bronze raw writes."""

    run_id: RunID
    run_type: RunType
    effective_ts: datetime
    provider: str
    entity: str
    batch_id: BatchID


@dataclass(frozen=True, slots=True)
class BronzeMetadataPayloadRequest:
    """Expanded Bronze metadata payload used by metadata sidecar writes."""

    run_id: RunID
    run_type: RunType
    provider: str
    entity: str
    record_count: int
    compressed_size: int
    output_path: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    source_metadata: SourceMetadata | None


def build_bronze_lineage_metadata(
    request: BronzeLineageMetadataRequest,
) -> dict[str, str]:
    """Build the raw Bronze lineage metadata sidecar dictionary."""
    return {
        "run_id": str(request.run_id),
        "run_type": request.run_type.value,
        "ingestion_ts": request.effective_ts.isoformat(),
        "provider": request.provider,
        "entity": request.entity,
        "batch_id": str(request.batch_id),
    }


def build_bronze_metadata_payload(
    request: BronzeMetadataPayloadRequest,
) -> JsonDict:
    """Build Bronze metadata constructor kwargs for the sidecar model."""
    import platform
    import socket

    from bioetl import __version__ as BIOETL_VERSION
    from bioetl.domain.models.metadata import (
        BaseOutputMetadata,
        BronzeOutputExt,
        EnvironmentMetadata,
        FileOutputMetadata,
        PipelineMetadata,
        RuntimeMetadata,
        RunTypeEnum,
    )
    from bioetl.domain.models.metadata import SourceMetadata as SourceMetadataModel

    run_type_map = {
        RunType.INCREMENTAL: RunTypeEnum.INCREMENTAL,
        RunType.BACKFILL: RunTypeEnum.BACKFILL,
        RunType.REBUILD: RunTypeEnum.REBUILD,
    }
    resolved_source = (
        request.source_metadata
        if request.source_metadata is not None
        else SourceMetadataModel(type="api")
    )
    file_metadata = FileOutputMetadata(
        path=request.output_path,
        size_bytes=request.compressed_size,
        record_count=request.record_count,
    )
    return {
        "runtime": RuntimeMetadata(
            run_id=str(request.run_id),
            run_type=run_type_map.get(request.run_type, RunTypeEnum.INCREMENTAL),
            started_at_utc=request.started_at,
            completed_at_utc=request.completed_at,
            duration_seconds=request.duration_seconds,
        ),
        "pipeline": PipelineMetadata(
            name=f"{request.provider}_{request.entity}",
            provider=request.provider,
            entity=request.entity,
        ),
        "source": cast(Any, resolved_source),  # Any: pydantic narrowing at runtime
        "output": BaseOutputMetadata(
            record_count=request.record_count,
            total_bytes=request.compressed_size,
            write_started_at=request.started_at,
            write_completed_at=request.completed_at,
        ),
        "output_ext": BronzeOutputExt(files=[file_metadata]),
        "environment": EnvironmentMetadata(
            hostname=socket.gethostname(),
            python_version=platform.python_version(),
            bioetl_version=BIOETL_VERSION,
        ),
    }


def build_full_bronze_metadata(
    request: BronzeMetadataPayloadRequest,
) -> BronzeMetadata:
    """Materialize the BronzeMetadata model from a pure request object."""
    return BronzeMetadata(**build_bronze_metadata_payload(request))
