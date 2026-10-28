"""Schema drift detection and policy operations for Silver layer.

Extracted from ``silver_writer_validation_operations`` to localise the
schema-evolution axis: field diff, drift classification, and policy
enforcement are isolated here so that changes to drift handling do not
ripple through the wider validation / Arrow-preparation pipeline.
"""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

import pyarrow as pa

from bioetl.domain.constants import NONDETERMINISTIC_PERSISTED_FIELDS
from bioetl.domain.exceptions import SchemaEvolutionError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import BronzeRecord
    from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo

__all__ = [
    "_SchemaDriftHostProtocol",
    "_SilverSchemaDriftDiff",
    "_build_schema_drift_info",
    "_build_silver_schema_drift_diff",
    "_check_schema_drift",
    "_detect_schema_drift",
    "_diff_schema_fields",
]


@dataclass(frozen=True, slots=True)
class _SilverSchemaDriftDiff:
    """Normalized schema drift field sets for one Silver batch."""

    new_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    changed_fields: tuple[tuple[str, str, str], ...]


class _SchemaDriftHostProtocol(Protocol):
    """Minimal host contract for schema drift helpers."""

    logger: LoggerPort

    def _get_table_schema(self, table_name: str) -> Awaitable[pa.Schema | None]: ...


# ---------------------------------------------------------------------------
# Pure helpers (no host dependency)
# ---------------------------------------------------------------------------


def _diff_schema_fields(
    existing_schema: pa.Schema | None,
    records: list[BronzeRecord],
) -> tuple[set[str], set[str]] | None:
    """Return incoming-only and existing-only fields for one Silver batch."""
    if existing_schema is None or not records:
        return None

    incoming_fields = {
        field_name
        for field_name in records[0]
        if field_name not in NONDETERMINISTIC_PERSISTED_FIELDS
    }
    existing_fields = {
        field_name
        for field_name in existing_schema.names
        if field_name not in NONDETERMINISTIC_PERSISTED_FIELDS
    }
    return incoming_fields - existing_fields, existing_fields - incoming_fields


def _diff_schema_types(
    existing_schema: pa.Schema | None,
    records: list[BronzeRecord],
) -> tuple[tuple[str, str, str], ...]:
    """Return incompatible types inferred from persisted incoming values."""
    if existing_schema is None or not records:
        return ()
    incoming_schema = pa.Table.from_pylist(records).schema
    incoming_fields = {
        field.name: field
        for field in incoming_schema
        if field.name not in NONDETERMINISTIC_PERSISTED_FIELDS
    }
    changes = []
    for existing_field in existing_schema:
        incoming_field = incoming_fields.get(existing_field.name)
        if incoming_field is None or pa.types.is_null(incoming_field.type):
            continue
        if not existing_field.type.equals(incoming_field.type):
            changes.append(
                (
                    existing_field.name,
                    str(existing_field.type),
                    str(incoming_field.type),
                )
            )
    return tuple(sorted(changes))


def _build_silver_schema_drift_diff(
    existing_schema: pa.Schema | None,
    records: list[BronzeRecord],
) -> _SilverSchemaDriftDiff | None:
    """Build a normalized Silver schema drift diff from existing and incoming data."""
    diff = _diff_schema_fields(existing_schema, records)
    if diff is None:
        return None

    new_fields, missing_fields = diff
    changed_fields = _diff_schema_types(existing_schema, records)
    if not new_fields and not missing_fields and not changed_fields:
        return None

    return _SilverSchemaDriftDiff(
        new_fields=tuple(sorted(new_fields)),
        missing_fields=tuple(sorted(missing_fields)),
        changed_fields=changed_fields,
    )


def _build_schema_drift_info(
    diff: _SilverSchemaDriftDiff,
) -> SchemaDriftInfo:
    """Build SchemaDriftInfo from a normalized field diff."""
    from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo

    critical_missing = [
        field for field in diff.missing_fields if not field.startswith("_")
    ]
    status: Literal["info", "warn", "critical"]
    if critical_missing:
        status = "critical"
    elif len(diff.new_fields) > 3:
        status = "warn"
    else:
        status = "info"

    return SchemaDriftInfo(
        status=status,
        new_fields=diff.new_fields,
        missing_fields=diff.missing_fields,
    )


# ---------------------------------------------------------------------------
# Async host-dependent operations
# ---------------------------------------------------------------------------


async def _check_schema_drift(
    host: _SchemaDriftHostProtocol,
    table_name: str,
    records: list[BronzeRecord],
    on_schema_mismatch: Literal["error", "evolve", "ignore"],
) -> None:
    """Check schema drift and handle according to configured policy."""
    existing_schema = await host._get_table_schema(table_name)
    diff = _build_silver_schema_drift_diff(existing_schema, records)
    if diff is None:
        return

    host.logger.warning(
        "Schema drift detected",
        table=table_name,
        new_fields=list(diff.new_fields) if diff.new_fields else None,
        removed_fields=list(diff.missing_fields) if diff.missing_fields else None,
        changed_fields=list(diff.changed_fields) if diff.changed_fields else None,
        action=on_schema_mismatch,
    )

    if diff.changed_fields:
        raise SchemaEvolutionError(
            table=table_name,
            changed_fields={
                name: (existing, incoming)
                for name, existing, incoming in diff.changed_fields
            },
        )

    if on_schema_mismatch == "error":
        raise SchemaEvolutionError(
            table=table_name,
            new_fields=set(diff.new_fields),
            removed_fields=set(diff.missing_fields),
        )


async def _detect_schema_drift(
    host: _SchemaDriftHostProtocol,
    table_name: str,
    records: list[BronzeRecord],
) -> SchemaDriftInfo | None:
    """Detect schema drift between existing table and incoming records."""
    existing_schema = await host._get_table_schema(table_name)
    diff = _build_silver_schema_drift_diff(existing_schema, records)
    if diff is None:
        return None
    return _build_schema_drift_info(diff)
