"""Input loading mixin for MergeService."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import polars as pl

from bioetl.application.composite.column_renamer import ColumnRenamerService
from bioetl.application.composite.join_planner_helpers import (
    count_qualified_columns,
    infer_pipeline_from_table,
    infer_silver_table,
    resolve_field_aliases_from_registry,
    table_path_to_name,
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


@dataclass(frozen=True, slots=True)
class _MergeInputLoadSpec:
    """Describes one optional merge input that should be loaded."""

    pipeline: str
    table: str
    role: str


@dataclass(frozen=True, slots=True)
class _LoadedMergeInputsResult:
    """Loaded optional merge inputs plus the source pipelines that succeeded."""

    dataframes: dict[str, pl.DataFrame]
    sources: list[str]


@dataclass(frozen=True, slots=True)
class _PreparedSeedDataframe:
    """Prepared seed dataframe plus derived merge context."""

    seed_df: pl.DataFrame
    records_from_seed: int
    effective_seed_pipeline: str | None


class _MergeInputLoaderMixin:
    """Mixin for loading seed, enricher, and dependency DataFrames."""

    # -- Host-class attributes (set by MergeService.__init__) --
    _config: Any  # Any: host mixin stores injected MergeConfig without importing concrete type here
    _logger: LoggerPort
    _storage: MergedStoragePort
    _delta_reader: DeltaReaderPort | None
    _renamer: ColumnRenamerService

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
        records_from_seed = len(seed_df)
        effective_seed_pipeline = seed_pipeline or infer_pipeline_from_table(seed_table)
        if not effective_seed_pipeline:
            return _PreparedSeedDataframe(
                seed_df=seed_df,
                records_from_seed=records_from_seed,
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
        return _PreparedSeedDataframe(
            seed_df=seed_df,
            records_from_seed=records_from_seed,
            effective_seed_pipeline=effective_seed_pipeline,
        )

    async def _load_enricher_dataframes(
        self,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
    ) -> tuple[dict[str, pl.DataFrame], list[str]]:
        """Load only successful enricher silver tables."""
        load_specs: list[_MergeInputLoadSpec] = []
        for enricher in enrichers:
            result = enrichment_results.get(enricher.pipeline)
            if result is None or not result.is_success:
                continue
            enricher_table = enricher.silver_table or infer_silver_table(
                enricher.pipeline
            )
            load_specs.append(
                _MergeInputLoadSpec(
                    pipeline=enricher.pipeline,
                    table=enricher_table,
                    role="enricher",
                )
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

        load_specs: list[_MergeInputLoadSpec] = []
        for dep in dependencies:
            dep_result = dependency_results.get(dep.pipeline)
            if dep_result is None or not dep_result.is_success or not dep.silver_table:
                continue
            load_specs.append(
                _MergeInputLoadSpec(
                    pipeline=dep.pipeline,
                    table=dep.silver_table,
                    role="dependency",
                )
            )
        loaded_inputs = await self._load_successful_merge_inputs(load_specs)
        return loaded_inputs.dataframes, loaded_inputs.sources

    async def _load_successful_merge_inputs(
        self,
        load_specs: Sequence[_MergeInputLoadSpec],
    ) -> _LoadedMergeInputsResult:
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
        return _LoadedMergeInputsResult(dataframes=loaded_dfs, sources=sources)

    async def _read_silver_table(self, path: str) -> pl.DataFrame:
        """Read a Silver table from DeltaReaderPort or StoragePort fallback."""
        if self._delta_reader is not None:
            arrow_table = await self._delta_reader.read_table(path)
            result = pl.from_arrow(arrow_table)
            if isinstance(result, pl.Series):
                return result.to_frame()
            return result

        table_name = table_path_to_name(path)
        # At runtime _storage is StoragePort (aggregate) which extends SilverStoragePort;
        # MergedStoragePort is declared for mixin compatibility with MergeOutputWriterMixin.
        storage = cast(SilverStoragePort, self._storage)
        records = await storage.read_silver(table_name)
        if not records:
            return pl.DataFrame()
        return pl.DataFrame(records)


__all__ = ["_MergeInputLoaderMixin", "_PreparedSeedDataframe"]
