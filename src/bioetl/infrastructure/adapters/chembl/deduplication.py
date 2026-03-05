"""Utility functions and helpers for ChEMBL adapter."""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = [
    "compute_composite_key",
    "is_duplicate_record",
    "is_duplicate_record_composite",
]


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics


def compute_composite_key(
    record: JsonDict,  # Any: untyped API JSON record
    pk_fields: tuple[str, ...],
) -> str:
    """Compute composite key string from multiple fields.

    Args:
        record: Record dictionary.
        pk_fields: Tuple of field names forming the composite key.

    Returns:
        Serialized composite key string (fields joined with '|').
    """
    parts = []
    for pk_field in pk_fields:
        value = record.get(pk_field, "")
        # Normalize to string and handle None
        parts.append(str(value) if value is not None else "")
    return "|".join(parts)


def is_duplicate_record_composite(
    record: JsonDict,  # Any: untyped API JSON record
    pk_fields: tuple[str, ...],
    seen_keys: set[str],
    entity_type: str,
    logger: LoggerPort,
    metrics: AdapterMetrics,
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
    comp_key = compute_composite_key(record, pk_fields)
    # Skip records with empty composite key (missing required fields)
    if not comp_key or comp_key == "|".join([""] * len(pk_fields)):
        return False
    if comp_key in seen_keys:
        logger.debug(
            "skipping_duplicate_record",
            entity_type=entity_type,
            pk_fields=pk_fields,
            composite_key=comp_key,
        )
        metrics.record_dropped_duplicates(entity_type)
        return True
    seen_keys.add(comp_key)
    return False


def is_duplicate_record(
    record: JsonDict,  # Any: untyped API JSON record
    pk_field: str,
    seen_ids: set[str],
    entity_type: str,
    logger: LoggerPort,
    metrics: AdapterMetrics,
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
    record_id = str(record.get(pk_field, ""))
    if not record_id:
        return False
    if record_id in seen_ids:
        logger.debug(
            "skipping_duplicate_record",
            entity_type=entity_type,
            pk_field=pk_field,
            record_id=record_id,
        )
        metrics.record_dropped_duplicates(entity_type)
        return True
    seen_ids.add(record_id)
    return False
