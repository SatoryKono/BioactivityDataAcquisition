# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Output-writing helpers extracted from MergeIOMixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.exceptions import DataQualityError

if TYPE_CHECKING:
    from datetime import datetime

    import polars as pl

    from bioetl.domain.composite import MergeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import LoggerPort, MergedStoragePort


class _MergeOutputHostProtocol(Protocol):
    """Internal dependencies initialized by MergeService."""

    _config: MergeConfig
    _logger: LoggerPort
    _storage: MergedStoragePort
    _field_group_registry: FieldGroupRegistry | None
    _gold_schema: object | None


class MergeOutputWriterMixin:
    """Mixin for persisting merged Silver/Gold outputs."""

    @staticmethod
    def _path_to_table_name(path: str) -> str:
        """Convert a full path to a table name by stripping layer prefix."""
        normalized = path.replace("\\", "/")
        for layer in ("silver/", "gold/", "bronze/"):
            if layer in normalized:
                idx = normalized.find(layer)
                return normalized[idx + len(layer) :]
        return path

    def _coerce_null_columns(
        self, df: pl.DataFrame
    ) -> pl.DataFrame:
        """Coerce Null-typed columns to String for Delta Lake compatibility."""
        host = cast("_MergeOutputHostProtocol", cast(object, self))
        import polars as pl
        import polars.selectors as cs

        # Extract columns only to log the names without looping over dataframe columns in Python
        null_cols = df.select(cs.by_dtype(pl.Null)).columns
        if null_cols:
            host._logger.debug("Coercing null columns to String", columns=null_cols)
            df = df.with_columns(cs.by_dtype(pl.Null).cast(pl.String))
        return df

    async def _write_merged_silver(
        self,
        df: pl.DataFrame,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged data to Silver layer via MergedStoragePort.

        Args:
            df: Merged DataFrame to persist; Null-typed columns are coerced to String first.
            completed_at: Optional deterministic metadata timestamp routed into
                merged Silver sidecar/control-plane metadata.
            run_id: Optional composite run identifier attached to the write for lineage.
            sources_used: Optional list of pipeline names that contributed to the merge,
                attached to the write for provenance tracking.
        """
        host = cast("_MergeOutputHostProtocol", cast(object, self))
        df = self._coerce_null_columns(df)

        table_name = self._path_to_table_name(host._config.output_silver_path)
        records = df.to_dicts()
        await host._storage.write_silver_merged(
            table_name,
            records,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=True,
        )

    async def _write_merged_gold(
        self,
        df: pl.DataFrame,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged data to Gold layer via MergedStoragePort.

        Args:
            df: Merged DataFrame to persist; trash columns and Null-typed columns
                are removed or coerced before writing.
            run_id: Optional composite run identifier attached to the write for lineage.
            sources_used: Optional list of pipeline names that contributed to the merge,
                attached to the write for provenance tracking.
        """
        host = cast("_MergeOutputHostProtocol", cast(object, self))
        if host._field_group_registry is not None:
            trash_cols = host._field_group_registry.get_trash_columns(df.columns)
            if trash_cols:
                host._logger.info(
                    "Filtering trash columns from Gold output",
                    trash_count=len(trash_cols),
                    trash_columns=trash_cols[:10],
                )
                df = df.drop(trash_cols)

        df = self._coerce_null_columns(df)
        table_name = self._path_to_table_name(host._config.output_gold_path)
        if host._gold_schema is None:
            raise DataQualityError(
                "Composite Gold write requires a registered strict schema: "
                f"table_name={table_name}"
            )
        records = df.to_dicts()
        await host._storage.write_gold_merged(
            table_name,
            records,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=True,
            schema=host._gold_schema,
        )


__all__ = ["MergeOutputWriterMixin"]
