"""Runtime helpers for Silver metadata operations."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any, Protocol, cast

import orjson

from bioetl.domain.behavior.dq_metrics_calculator import (
    DQMetricsInput,
)
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    LoggerPort,
)
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.metadata.builder_base import _parse_table_name

if TYPE_CHECKING:
    import pyarrow as pa


class _SilverMetadataWriterProtocol(Protocol):
    """Structural protocol for canonical Silver metadata operations host."""

    _host: object | None
    _logger: LoggerPort
    _metadata_coordinator: object | None
    _metadata_writer: object | None
    _dq_calculator: object | None

    async def compute_dq_metrics(
        self,
        arrow_data: pa.Table,
        *,
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics: ...

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None: ...


_GetDeltaVersion = Callable[[str], Awaitable[int | None]]


def _normalize_record_value_for_dq_metrics(value: object) -> object:
    """Normalize heterogeneous record values for DQ metric tabularization."""
    if isinstance(value, (dict, list, tuple)):
        return orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode("utf-8")
    return value


def _normalize_records_for_dq_metrics(
    records: list[BronzeRecord],
) -> list[BronzeRecord]:
    """Normalize record payloads before temporary DQ metrics conversion."""
    return [
        {
            key: _normalize_record_value_for_dq_metrics(value)
            for key, value in record.items()
        }
        for record in records
    ]


def resolve_flat_structure(host: object | None) -> bool:
    """Resolve flat-structure metadata mode from the current host, if any."""
    return bool(getattr(host, "_flat_structure", False))


def resolve_transform_version(host: object | None) -> str | None:
    """Resolve transform version from the current host, if any."""
    value = getattr(host, "_transform_version", None)
    return str(value) if value is not None else None


def resolve_transform_steps(host: object | None) -> tuple[str, ...]:
    """Resolve transform steps from the current host with a stable fallback."""
    value = getattr(host, "_transform_steps", ())
    if isinstance(value, tuple):
        return tuple(str(step) for step in value)
    if isinstance(value, list):
        return tuple(str(step) for step in value)
    return ()


def best_effort_log(logger: LoggerPort, level: str, message: str) -> None:
    """Log when the logger exposes the requested level method."""
    log_method = getattr(logger, level, None)
    if callable(log_method):
        log_method(message)


def resolve_manifest_id(
    metadata_ops: _SilverMetadataWriterProtocol,
    *,
    records: list[BronzeRecord],
) -> str | None:
    """Resolve control-plane manifest id from records, host, or coordinator."""
    if records and records[0].get("_manifest_id") is not None:
        return str(records[0]["_manifest_id"])

    host_manifest_id = getattr(metadata_ops._host, "manifest_id", None)
    if host_manifest_id is not None:
        return str(host_manifest_id)

    coordinator = metadata_ops._metadata_coordinator
    coordinator_context = getattr(coordinator, "run_context", None)
    coordinator_manifest_id = getattr(coordinator_context, "manifest_id", None)
    if coordinator_manifest_id is not None:
        return str(coordinator_manifest_id)

    best_effort_log(
        metadata_ops._logger,
        "debug",
        "Silver metadata manifest_id is unavailable",
    )
    return None


async def persist_silver_metadata(
    metadata_ops: _SilverMetadataWriterProtocol,
    *,
    metadata: SilverMetadata,
    table_name: str,
    table_path: str,
) -> SilverWriteResult | None:
    """Persist metadata using whichever writer signature is available."""
    provider_name, entity_name = _parse_table_name(table_name)
    await metadata_ops._write_silver_metadata_file(
        table_path=table_path,
        metadata=metadata,
        table_name=table_name,
        provider_name=provider_name,
        entity_name=entity_name,
    )
    return None


async def resolve_finalization_dq_metrics(
    metadata_ops: _SilverMetadataWriterProtocol,
    *,
    _table_name: str,
    records: list[BronzeRecord],
    quarantined_count: int | None = None,
    validation_errors: Sequence[str] | None = None,
) -> BatchDQMetrics:
    """Resolve DQ metrics through canonical metadata operations."""
    best_effort_log(
        metadata_ops._logger,
        "debug",
        f"Resolving finalization DQ metrics for table {_table_name}",
    )
    import pyarrow as pa

    normalized_records = _normalize_records_for_dq_metrics(records)
    arrow_data = (
        pa.Table.from_pylist(normalized_records) if normalized_records else pa.table({})
    )
    return await metadata_ops.compute_dq_metrics(
        arrow_data=arrow_data,
        quarantined_count=quarantined_count,
        validation_errors=validation_errors,
    )


async def resolve_version_after(
    metadata_ops: _SilverMetadataWriterProtocol, table_path: str
) -> int | None:
    """Read Delta version via host helper when available."""
    if metadata_ops._host is not None and hasattr(
        metadata_ops._host, "_get_delta_version"
    ):
        get_delta_version = cast(
            _GetDeltaVersion,
            metadata_ops._host._get_delta_version,
        )
        return await get_delta_version(table_path)
    return 0


async def compute_dq_metrics_from_arrow_data(
    metadata_ops: _SilverMetadataWriterProtocol,
    arrow_data: pa.Table,
    *,
    quarantined_count: int | None = None,
    validation_errors: Sequence[str] | None = None,
) -> BatchDQMetrics:
    """Compute data quality metrics for Silver write."""
    if metadata_ops._dq_calculator is None:
        best_effort_log(
            metadata_ops._logger,
            "warning",
            "DQ calculator missing; returning empty BatchDQMetrics",
        )
        return BatchDQMetrics()

    records_dict = (
        [dict(record) for record in arrow_data.to_pylist()] if arrow_data else []
    )
    existing_schema_fields = set(arrow_data.column_names) if arrow_data else set()

    dq_input = DQMetricsInput(
        records=records_dict,
        existing_schema_fields=existing_schema_fields,
        quarantined_count=quarantined_count or 0,
        validation_errors=(
            list(validation_errors) if validation_errors is not None else None
        ),
    )
    return metadata_ops._dq_calculator.calculate(dq_input)


def should_skip_silver_metadata_write(
    metadata_ops: _SilverMetadataWriterProtocol,
    *,
    records: list[BronzeRecord],
) -> bool:
    """Return whether canonical Silver metadata publication should short-circuit."""
    if not records:
        return True
    if isinstance(metadata_ops._metadata_writer, NoOpMetadataWriter):
        return True
    if metadata_ops._metadata_coordinator is None:
        raise RuntimeError(
            "MetadataCoordinator with create_silver_metadata_bundle is required "
            "for Silver metadata publication"
        )
    return False


async def write_silver_metadata_file(
    metadata_ops: _SilverMetadataWriterProtocol,
    *,
    table_path: str,
    metadata: SilverMetadata,
    table_name: str,
    provider_name: str,
    entity_name: str,
) -> None:
    """Persist one canonical Silver metadata sidecar through the writer port."""
    if metadata_ops._metadata_writer is None:
        best_effort_log(
            metadata_ops._logger,
            "info",
            "Skipping Silver metadata persistence: metadata writer missing",
        )
        return

    write_silver_metadata = metadata_ops._metadata_writer.write_silver_metadata
    parameters = inspect.signature(write_silver_metadata).parameters
    accepts_var_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )

    kwargs: dict[str, Any] = {  # Any: dynamic metadata writer kwargs
        "metadata": metadata
    }  # Any: dynamic metadata writer kwargs
    if "base_path" in parameters or accepts_var_kwargs:
        kwargs["base_path"] = table_path
    elif "table_path" in parameters:
        kwargs["table_path"] = table_path
    else:
        legacy_write = cast(  # Any: legacy signature compatibility
            Any,  # Any: legacy signature compatibility
            write_silver_metadata,
        )
        await legacy_write(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=metadata_ops._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )
        return

    if "table_name" in parameters or accepts_var_kwargs:
        kwargs["table_name"] = table_name
    if "flat_structure" in parameters or accepts_var_kwargs:
        kwargs["flat_structure"] = metadata_ops._flat_structure
    if "provider" in parameters or accepts_var_kwargs:
        kwargs["provider"] = provider_name
    if "entity" in parameters or accepts_var_kwargs:
        kwargs["entity"] = entity_name

    await write_silver_metadata(**kwargs)
