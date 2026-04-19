"""Silver layer storage port."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from bioetl.domain.types import ArrowSchema, BronzeRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.silver_result import SilverWriteResult

if TYPE_CHECKING:
    from datetime import datetime

    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.types import BatchID, RunID, RunType

__all__ = [
    "SilverStoragePort",
    "SilverWriteRequest",
    "coerce_silver_write_request",
]


@dataclass(frozen=True, slots=True)
class SilverWriteRequest:
    """Canonical Silver-write request shared across storage seams."""

    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    schema: ArrowSchema
    mode: Literal["merge", "append", "delete"] = "merge"
    partition_cols: list[str] | None = None
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"
    column_order: list[str] | None = None
    bronze_refs: list[BronzeWriteResult] | None = None
    key_nullability_rules: list[KeyNullabilityRule] | None = None
    run_id: RunID | None = None
    run_type: RunType | None = None
    source_batch_id: BatchID | None = None
    ingestion_ts: datetime | None = None


_SILVER_WRITE_POSITIONAL_FIELDS = (
    "table_name",
    "records",
    "primary_keys",
    "schema",
    "mode",
    "partition_cols",
    "on_schema_mismatch",
    "column_order",
    "bronze_refs",
    "key_nullability_rules",
)
_SILVER_WRITE_REQUIRED_FIELDS = (
    "table_name",
    "records",
    "primary_keys",
    "schema",
)
_SILVER_WRITE_DEFAULTS: dict[str, object] = {
    "mode": "merge",
    "partition_cols": None,
    "on_schema_mismatch": "error",
    "column_order": None,
    "bronze_refs": None,
    "key_nullability_rules": None,
    "run_id": None,
    "run_type": None,
    "source_batch_id": None,
    "ingestion_ts": None,
}
_SILVER_WRITE_ALLOWED_FIELDS = frozenset(
    {*_SILVER_WRITE_POSITIONAL_FIELDS, *tuple(_SILVER_WRITE_DEFAULTS)}
)


def coerce_silver_write_request(
    request: SilverWriteRequest | str | None = None,
    *,
    args: tuple[object, ...] = (),
    kwargs: Mapping[str, object] | None = None,
) -> SilverWriteRequest:
    """Normalize legacy or request-style Silver-write arguments."""
    resolved_kwargs = dict(kwargs or {})
    if isinstance(request, SilverWriteRequest):
        if args or resolved_kwargs:
            raise TypeError(
                "SilverWriteRequest cannot be combined with legacy args/kwargs"
            )
        return request

    legacy_values: list[object] = list(args) if request is None else [request, *args]

    if len(legacy_values) > len(_SILVER_WRITE_POSITIONAL_FIELDS):
        raise TypeError("write_silver() received too many positional arguments")

    for field_name, value in zip(_SILVER_WRITE_POSITIONAL_FIELDS, legacy_values, strict=True):
        if field_name in resolved_kwargs:
            raise TypeError(
                f"write_silver() got multiple values for argument '{field_name}'"
            )
        resolved_kwargs[field_name] = value

    unexpected_fields = sorted(set(resolved_kwargs) - _SILVER_WRITE_ALLOWED_FIELDS)
    if unexpected_fields:
        unexpected = ", ".join(unexpected_fields)
        raise TypeError(f"write_silver() got unexpected keyword arguments: {unexpected}")

    missing_fields = [
        field_name
        for field_name in _SILVER_WRITE_REQUIRED_FIELDS
        if field_name not in resolved_kwargs
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise TypeError(f"write_silver() missing required arguments: {missing}")

    for field_name, default in _SILVER_WRITE_DEFAULTS.items():
        resolved_kwargs.setdefault(field_name, default)

    return SilverWriteRequest(
        table_name=resolved_kwargs["table_name"],  # type: ignore[arg-type]
        records=resolved_kwargs["records"],  # type: ignore[arg-type]
        primary_keys=resolved_kwargs["primary_keys"],  # type: ignore[arg-type]
        schema=resolved_kwargs["schema"],  # type: ignore[arg-type]
        mode=resolved_kwargs["mode"],  # type: ignore[arg-type]
        partition_cols=resolved_kwargs["partition_cols"],  # type: ignore[arg-type]
        on_schema_mismatch=resolved_kwargs["on_schema_mismatch"],  # type: ignore[arg-type]
        column_order=resolved_kwargs["column_order"],  # type: ignore[arg-type]
        bronze_refs=resolved_kwargs["bronze_refs"],  # type: ignore[arg-type]
        key_nullability_rules=resolved_kwargs["key_nullability_rules"],  # type: ignore[arg-type]
        run_id=resolved_kwargs["run_id"],  # type: ignore[arg-type]
        run_type=resolved_kwargs["run_type"],  # type: ignore[arg-type]
        source_batch_id=resolved_kwargs["source_batch_id"],  # type: ignore[arg-type]
        ingestion_ts=resolved_kwargs["ingestion_ts"],  # type: ignore[arg-type]
    )


@runtime_checkable
class SilverStoragePort(Protocol):
    """Port for Silver layer storage operations.

    Covers Silver write (with schema), read-back, and layer clear.
    """

    async def write_silver(
        self,
        request: SilverWriteRequest | str | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverWriteResult | None:
        """Write transformed records to the Silver layer."""
        del request, args, kwargs
        ...

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[
        BronzeRecord
    ]:  # BronzeRecord: read-back Silver records share the same shape
        """Read records from a Silver layer Delta table.

        Args:
            table_name: The name of the table to read (e.g., 'chembl/activity').
            columns: Optional list of columns to select. If None, reads all columns.

        Returns:
            List of dictionaries, where each dictionary represents a record.

        Raises:
            FileNotFoundError: If the table does not exist.
        """
        ...

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table.

        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.
            dry_run: If True, only count what would be deleted.

        Returns:
            Count of cleared items (tables + files).
        """
        ...
