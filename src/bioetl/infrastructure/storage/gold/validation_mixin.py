"""Validation helpers for GoldWriter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Protocol

from bioetl.domain.medallion import GoldWriteMode

if TYPE_CHECKING:
    from datetime import datetime

    from pandera.polars import DataFrameSchema

    from bioetl.domain.types import GoldRecord, ScdConfig


class _RunInExecutorHost(Protocol):
    """Host contract for mixins that rely on executor offloading."""

    def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> Awaitable[object]:
        """Execute callable in executor context."""
        ...


class GoldWriterValidationMixin:
    """Mixin with mode/record/schema validation helpers for Gold writes."""

    def _validate_write_mode(self, mode: str) -> GoldWriteMode:
        """Validate and return the write mode enum.

        Returns:
            GoldWriteMode enum value corresponding to the given mode string.
        """
        try:
            return GoldWriteMode(mode)
        except ValueError:
            valid_modes = [m.value for m in GoldWriteMode]
            raise ValueError(
                f"Invalid Gold write mode '{mode}'. Allowed: {valid_modes}"
            ) from None

    def _validate_records(self, records: list[GoldRecord]) -> None:
        """Validate that records list is not empty."""
        if not records:
            raise ValueError("No records to write")

    def _validate_scd2_requirements(
        self,
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
    ) -> None:
        """Validate SCD2-specific requirements."""
        if mode != GoldWriteMode.SCD2:
            return

        if scd_config is None:
            raise ValueError("scd_config required for SCD Type 2 mode")
        if scd_config.scd_type != 2:
            raise ValueError("scd_config.type must be 2 for SCD Type 2 mode")
        if not scd_config.business_keys:
            raise ValueError("scd_config.business_key required for SCD Type 2 mode")
        if ingestion_ts is None:
            raise ValueError(
                "ingestion_ts required for SCD Type 2 mode "
                "(timestamp must come from application layer per ADR-014)"
            )

    def _validate_schema_strict(self, schema: DataFrameSchema) -> None:
        """Validate that schema has strict=True."""
        is_strict = getattr(schema, "strict", False) or getattr(
            getattr(schema, "Config", None), "strict", False
        )
        if not is_strict:
            raise ValueError("Gold layer requires strict=True schema validation")

    async def _validate_records_against_schema(
        self: _RunInExecutorHost,
        records: list[GoldRecord],
        schema: DataFrameSchema,
    ) -> None:
        """Validate records against Pandera schema."""
        import pandas as pd
        import pandera.errors

        df = pd.DataFrame(records)
        try:
            schema_any: Any = schema  # Any: Pandera model class
            await self._run_in_executor(lambda: schema_any.validate(df, lazy=False))
        except pandera.errors.SchemaError as exc:
            raise ValueError(f"Schema validation failed: {exc}") from exc


__all__ = ["GoldWriterValidationMixin"]
