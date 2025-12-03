"""
Базовый класс пайплайна.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING
import pandas as pd

from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.application.pipelines.hooks import PipelineHookABC
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.contracts import WriteResult
from bioetl.infrastructure.output.metadata import (
    build_dry_run_metadata,
    build_run_metadata,
)
from bioetl.domain.validation.service import ValidationService
from bioetl.domain.hashing.hash_calculator import (
    compute_hash_business_key,
    compute_hash_row,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class PipelineBase(ABC):
    """
    Абстрактный базовый класс для всех ETL-пайплайнов.

    Реализует паттерн Template Method для стадий:
    extract → transform → validate → write
    """

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerAdapterABC,
        validation_service: ValidationService,
        output_writer: "UnifiedOutputWriter",
    ) -> None:
        self._config = config
        self._logger = logger.bind(
            entity=config.entity_name,
            provider=config.provider,
        )
        self._validation_service = validation_service
        self._output_writer = output_writer
        self._hooks: list[PipelineHookABC] = []
        self._stage_starts: dict[str, datetime] = {}

    # === Public API ===

    def run(
        self,
        output_path: Path,
        *,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> RunResult:
        """
        Запускает полный цикл ETL-пайплайна.
        """
        context = RunContext(
            entity_name=self._config.entity_name,
            provider=self._config.provider,
            config=self._config.model_dump(),
            dry_run=dry_run,
        )

        self._enrich_context(context)
        self._logger.info("Pipeline started", run_id=context.run_id)
        stages_results: list[StageResult] = []

        try:
            # 1. Extract
            self._notify_stage_start("extract", context)
            df_raw = self.extract(**kwargs)
            stages_results.append(
                self._make_stage_result("extract", len(df_raw))
            )
            self._notify_stage_end("extract", stages_results[-1])

            # 2. Transform
            self._notify_stage_start("transform", context)
            df_transformed = self.transform(df_raw)
            df_transformed = self._add_hash_columns(df_transformed)
            stages_results.append(
                self._make_stage_result("transform", len(df_transformed))
            )
            self._notify_stage_end("transform", stages_results[-1])

            # 3. Validate
            self._notify_stage_start("validate", context)
            df_validated = self.validate(df_transformed)
            stages_results.append(
                self._make_stage_result("validate", len(df_validated))
            )
            self._notify_stage_end("validate", stages_results[-1])

            # 4. Write (skip on dry_run)
            write_result: WriteResult | None = None
            if not dry_run:
                self._notify_stage_start("write", context)
                write_result = self.write(
                    df_validated,
                    output_path,
                    context
                )
                stages_results.append(
                    self._make_stage_result("write", write_result.row_count)
                )
                self._notify_stage_end("write", stages_results[-1])

            # Build metadata
            if write_result:
                meta = build_run_metadata(context, write_result)
            else:
                meta = build_dry_run_metadata(
                    context, len(df_validated)
                )

            return RunResult(
                run_id=context.run_id,
                success=True,
                entity_name=self._config.entity_name,
                row_count=len(df_validated),
                output_path=output_path if not dry_run else None,
                duration_sec=self._calculate_duration(context),
                stages=stages_results,
                errors=[],
                meta=meta,
            )

        except Exception as e:
            self._logger.error("Pipeline failed", error=str(e))
            for hook in self._hooks:
                hook.on_error("pipeline", e)
            raise

    # === Abstract Methods ===

    @abstractmethod
    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """Извлекает данные из источника."""

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Преобразует сырые данные."""

    # === Concrete Methods ===

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Валидирует DataFrame по Pandera-схеме."""
        return self._validation_service.validate(
            df=df,
            entity_name=self._config.entity_name
        )

    def write(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: RunContext,
    ) -> WriteResult:
        """Записывает валидированный DataFrame."""
        return self._output_writer.write_result(
            df=df,
            output_path=output_path,
            entity_name=self._config.entity_name,
            run_context=context,
        )

    # === Hooks ===

    def add_hook(self, hook: PipelineHookABC) -> None:
        """Добавляет хук выполнения."""
        self._hooks.append(hook)

    # === Internal Methods ===

    def _add_hash_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавляет столбцы с хешами строк и бизнес-ключей.
        Использует domain logic: compute_hash_business_key, compute_hash_row.
        """
        if df.empty:
            return df.assign(hash_business_key=None, hash_row=None)

        keys = self._config.hashing.business_key_fields
        
        # Note: This is a row-wise operation which might be slow for very large datasets.
        # Optimization (vectorization) can be done later as permitted by requirements.
        
        def _apply_hashes(row: pd.Series) -> pd.Series:
            # Convert to dict. Note: Timestamps/NaTs need careful handling if not handled by calculator.
            # hash_calculator handles basic types. Pandas NaT/NaN should be handled.
            # We rely on implicit conversion or the calculator's robustness.
            # But `to_dict()` converts NaT to NaTType, NaN to float('nan').
            # `canonical_json_from_record` in calculator handles NaN validation.
            # For safety, we might need to replace NaN with None before dict conversion if that's the policy,
            # but calculator expects 'NaN/Inf' to fail or be handled.
            # The spec says: "Исключить/отлавливать NaN/Inf... если содержат — валидировать/фейлить"
            
            record = row.to_dict()
            
            # 1. Compute Business Key Hash
            bk_hash = compute_hash_business_key(record, keys)
            
            # 2. Insert into record for Row Hash
            record["hash_business_key"] = bk_hash
            
            # 3. Compute Row Hash
            row_hash = compute_hash_row(record)
            
            return pd.Series({"hash_business_key": bk_hash, "hash_row": row_hash})

        hashes = df.apply(_apply_hashes, axis=1)
        
        # Update dataframe with calculated hashes
        # We use assignment to overwrite existing columns (if added by schema enforcement)
        # or append new ones, ensuring no duplicates and preserving order if already present.
        for col in hashes.columns:
            df[col] = hashes[col]
            
        return df

    def _notify_stage_start(self, stage: str, context: RunContext) -> None:
        self._stage_starts[stage] = datetime.now(timezone.utc)
        self._logger.info(f"Stage started: {stage}")
        for hook in self._hooks:
            hook.on_stage_start(stage, context)

    def _notify_stage_end(self, stage: str, result: StageResult) -> None:
        self._logger.info(
            f"Stage finished: {stage}",
            records=result.records_processed
        )
        for hook in self._hooks:
            hook.on_stage_end(stage, result)

    def _make_stage_result(self, stage: str, count: int) -> StageResult:
        start_time = self._stage_starts.get(stage)
        duration = 0.0
        if start_time:
            duration = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds()

        return StageResult(
            stage_name=stage,
            success=True,
            records_processed=count,
            duration_sec=duration,
            errors=[],
        )

    def _calculate_duration(self, context: RunContext) -> float:
        return (
            datetime.now(timezone.utc) - context.started_at
        ).total_seconds()

    def _enrich_context(self, context: RunContext) -> None:
        """
        Хук для обогащения контекста (например, добавления версии релиза).
        """
        pass
