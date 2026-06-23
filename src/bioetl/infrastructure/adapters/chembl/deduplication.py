"""Utility functions and helpers for ChEMBL adapter."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.common.deduplication import (
    compute_composite_dedup_key,
)
from bioetl.infrastructure.adapters.common.deduplication import (
    is_duplicate_record as is_duplicate_record_shared,
)

__all__ = [
    "compute_composite_key",
    "is_duplicate_record",
    "is_duplicate_record_composite",
]


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder


def compute_composite_key(
    record: JsonDict,  # Any: untyped API JSON record
    pk_fields: tuple[str, ...],
) -> str:
    """Compute composite key string from multiple fields."""
    return compute_composite_dedup_key(record, pk_fields)


def is_duplicate_record_composite(
    record: JsonDict,  # Any: untyped API JSON record
    pk_fields: tuple[str, ...],
    seen_keys: set[str],
    entity_type: str,
    logger: LoggerPort,
    metrics: AdapterMetricsRecorder,
) -> bool:
    """Check if record is duplicate using composite key.

    Args:
        record: Record dictionary.
        pk_fields: Tuple of field names forming the composite key.
        seen_keys: Set of already seen composite keys.
        entity_type: Entity type for logging.
        logger: Logger port.
        metrics: Adapter metrics.

    Returns:
        True if record is a duplicate.
    """
    return is_duplicate_record_shared(
        record=record,
        seen_keys=seen_keys,
        primary_field=pk_fields[0],
        composite_fields=pk_fields,
        composite_key_builder=compute_composite_key,
        entity_type=entity_type,
        logger=logger,
        metrics=metrics,
    )


def is_duplicate_record(
    record: JsonDict,  # Any: untyped API JSON record
    pk_field: str,
    seen_ids: set[str],
    entity_type: str,
    logger: LoggerPort,
    metrics: AdapterMetricsRecorder,
) -> bool:
    """Check if record is duplicate and add to seen set if not.

    Args:
        record: Single data record.
        pk_field: Pk field.
        seen_ids: Collection of seen identifiers.
        entity_type: Entity type identifier.
        logger: Logger instance.
        metrics: Metrics collector instance.

    Returns:
        True if the condition is met, False otherwise.
    """
    return is_duplicate_record_shared(
        record=record,
        seen_keys=seen_ids,
        primary_field=pk_field,
        entity_type=entity_type,
        logger=logger,
        metrics=metrics,
    )
