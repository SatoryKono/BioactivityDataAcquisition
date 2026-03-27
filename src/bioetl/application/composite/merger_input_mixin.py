"""Input loading mixin for MergeService."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

import polars as pl

from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.join_planner_helpers import (
    count_qualified_columns,
    infer_pipeline_from_table,
    resolve_field_aliases_from_registry,
)
from bioetl.application.composite.merger_input_runtime import (
    BoundLegacySilverReader,
    LoadedMergeInputsResult,
    MergeInputLoadSpec,
    PreparedSeedDataframe,
    build_dependency_load_specs,
    build_enricher_load_specs,
    build_prepared_seed_dataframe,
    coerce_polars_dataframe,
    to_silver_table_name,
)
from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
from bioetl.domain.composite.result import DependencyResult, EnrichmentResult
from bioetl.domain.exceptions import (
    BioETLError,
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)
from bioetl.domain.ports import (
    DeltaReaderPort,
    LoggerPort,
    MergedStoragePort,
    SilverStoragePort,
)
from bioetl.domain.types import BronzeRecord

_MERGE_READ_ERRORS = (
    StorageError,
    NetworkError,
    CheckpointConflictError,
    DataQualityError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


@runtime_checkable
class _LegacySilverReadable(Protocol):
    """Narrow compatibility protocol for legacy storage-backed silver reads."""

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[BronzeRecord]:
        """Read one Silver table by logical table name."""


_PreparedSeedDataframe = PreparedSeedDataframe


class _MergeInputLoaderMixin:
    """Mixin for loading seed, enricher, and dependency DataFrames."""

    # -- Host-class attributes (set by MergeService.__init__) --
    _config: Any  # Any: host mixin stores injected MergeConfig without importing concrete type here
    _logger: LoggerPort
    _storage: MergedStoragePort
    _delta_reader: DeltaReaderPort | None
    _silver_reader: SilverStoragePort | None
    _renamer: ColumnRenamer

    async def _read_optional_merge_input(
        self,
        *,
        pipeline: str,
        table: str,
        role: str,
    ) -> pl.DataFrame | None:
        """Read optional merge input and degrade to ``None`` on read failures."""
        self._logger.info(
            "reading_merge_input_table",
            role=role,
            **{role: pipeline},
            table=table,
        )
        try:
            return await self._read_silver_table(table)
        except _MERGE_READ_ERRORS as error:
            self._logger.warning(
                "failed_to_read_merge_input_table",
                role=role,
                **{role: pipeline},
                error=str(error),
                error_type=type(error).__name__,
            )
            return None
        except BioETLError as error:
            self._logger.warning(
                "failed_to_read_merge_input_table",
                role=role,
                **{role: pipeline},
                error=str(error),
                error_type=type(error).__name__,
                reason_code="unexpected_bioetl_error",
            )
            return None

    async def _prepare_seed_dataframe(
        self,
        seed_table: str,
        seed_pipeline: str | None,
    ) -> _PreparedSeedDataframe:
        """Read and optionally qualify seed DataFrame."""
        self._logger.info("Reading seed table", table=seed_table)
        seed_df = await self._read_silver_table(seed_table)
        effective_seed_pipeline = seed_pipeline or infer_pipeline_from_table(seed_table)
        if not effective_seed_pipeline:
            return build_prepared_seed_dataframe(
                seed_df=seed_df,
                effective_seed_pipeline=None,
            )
        self._logger.debug(
            "Using seed pipeline for column renaming",
            seed_pipeline=effective_seed_pipeline,
        )
        seed_df = self._renamer.rename_dataframe(
            seed_df,
            effective_seed_pipeline,
            exclude_join_keys=False,
            field_aliases=resolve_field_aliases_from_registry(effective_seed_pipeline),
        )
        self._logger.info(
            "Renamed seed columns to qualified format",
            pipeline=effective_seed_pipeline,
            qualified_count=count_qualified_columns(seed_df.columns),
        )
        return build_prepared_seed_dataframe(
            seed_df=seed_df,
            effective_seed_pipeline=effective_seed_pipeline,
        )

    async def _load_enricher_dataframes(
        self,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
    ) -> tuple[dict[str, pl.DataFrame], list[str]]:
        """Load only successful enricher silver tables."""
        load_specs = build_enricher_load_specs(
            enrichers=enrichers,
            enrichment_results=enrichment_results,
        )
        loaded_inputs = await self._load_successful_merge_inputs(load_specs)
        return loaded_inputs.dataframes, loaded_inputs.sources

    async def _load_dependency_dataframes(
        self,
        dependencies: Sequence[DependencyConfig] | None,
        dependency_results: dict[str, DependencyResult] | None,
    ) -> tuple[dict[str, pl.DataFrame], list[str]]:
        """Load only successful dependency silver tables."""
        if not dependencies or not dependency_results:
            return {}, []

        load_specs = build_dependency_load_specs(
            dependencies=dependencies,
            dependency_results=dependency_results,
        )
        loaded_inputs = await self._load_successful_merge_inputs(load_specs)
        return loaded_inputs.dataframes, loaded_inputs.sources

    async def _load_successful_merge_inputs(
        self,
        load_specs: Sequence[MergeInputLoadSpec],
    ) -> LoadedMergeInputsResult:
        """Load optional merge inputs that already passed success filtering."""
        loaded_dfs: dict[str, pl.DataFrame] = {}
        sources: list[str] = []
        for load_spec in load_specs:
            loaded_df = await self._read_optional_merge_input(
                pipeline=load_spec.pipeline,
                table=load_spec.table,
                role=load_spec.role,
            )
            if loaded_df is None:
                continue
            loaded_dfs[load_spec.pipeline] = loaded_df
            sources.append(load_spec.pipeline)
        return LoadedMergeInputsResult(dataframes=loaded_dfs, sources=sources)

    async def _read_silver_table(self, path: str) -> pl.DataFrame:
        """Read a Silver table using DeltaReaderPort or explicit SilverStoragePort."""
        if self._delta_reader is not None:
            return await self._read_delta_silver_table(self._delta_reader, path)

        records = await self._read_legacy_silver_records(path)
        if not records:
            return pl.DataFrame()
        return pl.DataFrame(records)

    async def _read_delta_silver_table(
        self,
        delta_reader: DeltaReaderPort,
        path: str,
    ) -> pl.DataFrame:
        """Read Silver data through the injected DeltaReaderPort."""
        arrow_table = await delta_reader.read_table(path)
        return coerce_polars_dataframe(pl.from_arrow(arrow_table))

    async def _read_legacy_silver_records(self, path: str) -> list[BronzeRecord]:
        """Read Silver records through the explicit or compatibility reader path."""
        silver_reader = self._resolve_legacy_silver_reader()
        table_name = to_silver_table_name(path)
        return await silver_reader.read_silver(table_name)

    def _resolve_legacy_silver_reader(self) -> _LegacySilverReadable:
        """Resolve the legacy Silver reader or fail on explicit misconfiguration."""
        explicit_silver_reader = self._get_explicit_silver_reader()
        if explicit_silver_reader is not None:
            return explicit_silver_reader

        legacy_storage_reader = self._build_legacy_storage_reader()
        if legacy_storage_reader is not None:
            return legacy_storage_reader

        # Compatibility path:
        # - legacy callers may not define `_silver_reader` at all -> use `_storage`.
        # - if `_silver_reader` exists and is None, treat it as explicit misconfiguration.
        raise RuntimeError(
            "MergeService requires delta_reader or silver_reader for silver reads"
        )

    def _get_explicit_silver_reader(self) -> _LegacySilverReadable | None:
        """Return the explicitly configured SilverStoragePort when present."""
        if "_silver_reader" not in self.__dict__:
            return None
        return self._silver_reader

    def _build_legacy_storage_reader(self) -> _LegacySilverReadable | None:
        """Adapt legacy storage objects exposing ``read_silver`` directly."""
        if "_silver_reader" in self.__dict__:
            return None
        storage_read_silver = getattr(self._storage, "read_silver", None)
        if not callable(storage_read_silver):
            return None
        return BoundLegacySilverReader(storage_read_silver)


__all__ = ["_MergeInputLoaderMixin", "_PreparedSeedDataframe"]
