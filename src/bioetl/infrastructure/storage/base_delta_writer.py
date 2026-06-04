"""Base class for Delta Lake writers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import pyarrow as pa
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.base_delta_writer_access import (
    BaseDeltaWriterTableAccessMixin,
)
from bioetl.infrastructure.storage.delta.arrow_converter import (
    ArrowDataConverter,
)
from bioetl.infrastructure.storage.delta.arrow_converter import (
    get_string_fields as _get_string_fields_impl,
)
from bioetl.infrastructure.storage.delta.arrow_converter import (
    serialize_value_for_arrow_schema as _serialize_value_impl,
)
from bioetl.infrastructure.storage.delta.arrow_converter import (
    sort_arrow_table_by_primary_keys as _sort_by_primary_keys_impl,
)
from bioetl.infrastructure.storage.delta.schema_ops import (
    coerce_null_types_for_delta as _coerce_null_types_for_delta_impl,
)
from bioetl.infrastructure.storage.delta.table_ops import (
    clear_delta_tables as _clear_delta_tables_impl,
)
from bioetl.infrastructure.storage.delta.table_ops import (
    get_delta_table_arrow_schema as _get_delta_table_arrow_schema_impl,
)
from bioetl.infrastructure.storage.delta.table_ops import (
    read_delta_records as _read_delta_records_impl,
)
from bioetl.infrastructure.storage.delta.table_ops import (
    resolve_delta_table_path as _resolve_delta_table_path_impl,
)
from bioetl.infrastructure.storage.support.retention import RetentionPolicy

__all__ = ["BaseDeltaWriter", "DeltaTableNotFoundError", "coerce_null_types_for_delta"]

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.ports import LoggerPort


# Any: arbitrary Python value from heterogeneous record fields; returns same or JSON string
def _serialize_value(
    value: Any,  # Any: Arrow field value type varies
    is_string_field: bool,  # Any: Arrow field value type varies
) -> Any:  # Any: input/output type varies
    """Compatibility wrapper delegating schema-aware serialization to Arrow converter."""
    return _serialize_value_impl(value, is_string_field)


def _get_string_fields(schema: pa.Schema) -> set[str]:
    """Compatibility wrapper delegating schema inspection to Arrow converter."""
    return _get_string_fields_impl(schema)


def _read_delta_records(
    table: DeltaTable,
    columns: list[str] | None = None,
) -> list[BronzeRecord]:
    """Read Delta rows into generic record dictionaries."""
    return _read_delta_records_impl(table, columns)


def _load_delta_table(table_path: str) -> DeltaTable:
    """Open a Delta table from its resolved filesystem path."""
    return DeltaTable(table_path)


def _resolve_delta_table_path(
    *,
    base_path: str,
    table_name: str,
    flat_structure: bool,
) -> str:
    """Resolve the filesystem path for a Delta table."""
    return _resolve_delta_table_path_impl(
        base_path=base_path,
        table_name=table_name,
        flat_structure=flat_structure,
    )


def _get_delta_table_arrow_schema(table: DeltaTable) -> pa.Schema:
    """Extract the PyArrow schema from an opened Delta table."""
    return _get_delta_table_arrow_schema_impl(table)


def _clear_delta_tables(
    *,
    base_path: Path,
    table_path: Path | None,
    dry_run: bool,
) -> int:
    """Clear one Delta table or all Delta tables rooted at a base path."""
    return _clear_delta_tables_impl(
        base_path=base_path,
        table_path=table_path,
        dry_run=dry_run,
    )


def coerce_null_types_for_delta(table: pa.Table) -> pa.Table:
    """Coerce Delta-incompatible Null-typed columns to concrete types."""
    return _coerce_null_types_for_delta_impl(table)


class BaseDeltaWriter(BaseDeltaWriterTableAccessMixin):
    """Shared Delta writer infrastructure for Silver and Gold writers."""

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        flat_structure: bool = False,
        arrow_converter: ArrowDataConverter | None = None,
        retention_policy: RetentionPolicy | None = None,
    ) -> None:
        """Initialize base Delta writer."""
        self.base_path = str(base_path).rstrip("/")
        self.logger = logger
        self._flat_structure = flat_structure
        self._arrow_converter = arrow_converter or ArrowDataConverter(logger=logger)
        self._retention_manager = retention_policy or RetentionPolicy(base_path)

    def _resolve_table_path(self, table_name: str) -> str:
        """Resolve the filesystem path for a Delta table."""
        return _resolve_delta_table_path(
            base_path=self.base_path,
            table_name=table_name,
            flat_structure=self._flat_structure,
        )

    def _prepare_arrow_data(
        self,
        records: list[BronzeRecord],
        schema: pa.Schema,
        primary_keys: list[str],
    ) -> pa.Table:
        """Prepare Arrow table from records with schema filtering and sorting."""
        return self._arrow_converter.convert_records_to_arrow_with_schema(
            records,
            schema,
            primary_keys=primary_keys,
        )

    def _sort_by_primary_keys(
        self,
        table: pa.Table,
        primary_keys: list[str],
        schema_names: Sequence[str],
    ) -> pa.Table:
        """Sort Arrow table by primary keys for deterministic writes."""
        return _sort_by_primary_keys_impl(
            table,
            primary_keys,
            schema_names=schema_names,
            logger=self.logger,
        )
