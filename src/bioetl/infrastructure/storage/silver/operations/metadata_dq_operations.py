"""DQ and runtime helper bindings for Silver metadata operations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.operations.metadata_runtime_support import (
    compute_dq_metrics_from_arrow_data,
    persist_silver_metadata,
    resolve_finalization_dq_metrics,
    resolve_flat_structure,
    resolve_manifest_id,
    resolve_transform_steps,
    resolve_transform_version,
    resolve_version_after,
    should_skip_silver_metadata_write,
    write_silver_metadata_file,
)

if TYPE_CHECKING:
    import pyarrow as pa


def get_flat_structure(metadata_ops: object) -> bool:
    """Resolve flat-structure metadata mode from the current host, if any."""
    return resolve_flat_structure(getattr(metadata_ops, "_host", None))


def get_transform_version(metadata_ops: object) -> str | None:
    """Resolve transform version from the current host, if any."""
    return resolve_transform_version(getattr(metadata_ops, "_host", None))


def get_transform_steps(metadata_ops: object) -> tuple[str, ...]:
    """Resolve transform steps from the current host with a stable fallback."""
    return resolve_transform_steps(getattr(metadata_ops, "_host", None))


def resolve_silver_manifest_id(
    metadata_ops: object,
    *,
    records: list[BronzeRecord],
) -> str | None:
    """Resolve control-plane manifest id from records, host, or coordinator."""
    return resolve_manifest_id(metadata_ops, records=records)


async def persist_silver_metadata_operation(
    metadata_ops: object,
    *,
    metadata: SilverMetadata,
    table_name: str,
    table_path: str,
) -> SilverWriteResult | None:
    """Persist metadata using whichever writer signature is available."""
    return await persist_silver_metadata(
        metadata_ops,
        metadata=metadata,
        table_name=table_name,
        table_path=table_path,
    )


async def resolve_finalization_dq_metrics_operation(
    metadata_ops: object,
    *,
    table_name: str,
    records: list[BronzeRecord],
    quarantined_count: int | None = None,
    validation_errors: Sequence[str] | None = None,
) -> BatchDQMetrics:
    """Resolve DQ metrics via host override when present, otherwise compute them."""
    return await resolve_finalization_dq_metrics(
        metadata_ops,
        _table_name=table_name,
        records=records,
        quarantined_count=quarantined_count,
        validation_errors=validation_errors,
    )


async def resolve_version_after_operation(
    metadata_ops: object,
    table_path: str,
) -> int | None:
    """Read Delta version via host helper when available."""
    return await resolve_version_after(metadata_ops, table_path)


async def compute_silver_dq_metrics_operation(
    metadata_ops: object,
    arrow_data: pa.Table,
    *,
    quarantined_count: int | None = None,
    validation_errors: Sequence[str] | None = None,
) -> BatchDQMetrics:
    """Compute data quality metrics for Silver write."""
    return await compute_dq_metrics_from_arrow_data(
        metadata_ops,
        arrow_data,
        quarantined_count=quarantined_count,
        validation_errors=validation_errors,
    )


def should_skip_silver_metadata_write_operation(
    metadata_ops: object,
    *,
    records: list[BronzeRecord],
    table_path: str,
    event_name: str,
) -> bool:
    """Return whether canonical Silver metadata publication should short-circuit."""
    del table_path, event_name
    return should_skip_silver_metadata_write(metadata_ops, records=records)


async def write_silver_metadata_file_operation(
    metadata_ops: object,
    *,
    table_path: str,
    metadata: SilverMetadata,
    table_name: str,
    provider_name: str,
    entity_name: str,
) -> None:
    """Persist one canonical Silver metadata sidecar through the writer port."""
    await write_silver_metadata_file(
        metadata_ops,
        table_path=table_path,
        metadata=metadata,
        table_name=table_name,
        provider_name=provider_name,
        entity_name=entity_name,
    )
