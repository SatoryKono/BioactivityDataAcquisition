"""
Базовый класс пайплайна.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING
import pandas as pd

from bioetl.application.pipelines.hooks import PipelineHookABC
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.contracts import WriteResult
from bioetl.infrastructure.output.metadata import (
    build_dry_run_metadata,
    build_run_metadata,
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
        hash_service: HashService | None = None,
    ) -> None:
        self._config = config
        self._logger = logger.bind(
            entity=config.entity_name,
            provider=config.provider,
        )
        self._validation_service = validation_service
        self._output_writer = output_writer
        self._hash_service = hash_service or HashService()
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
            df_raw = self._run_stage(
                stage="extract",
                context=context,
                action=lambda: self.extract(**kwargs),
            )
            stages_results.append(
                self._make_stage_result("extract", len(df_raw))
            )
            self._notify_stage_end("extract", stages_results[-1])

            df_transformed = self._run_stage(
                stage="transform",
                context=context,
                action=lambda: self.transform(df_raw),
            )
            df_transformed = self._add_hash_columns(df_transformed)
            df_transformed = self._add_index_column(df_transformed)
            df_transformed = self._add_database_version_column(
                df_transformed, self.get_version()
            )
            df_transformed = self._add_fulldate_column(df_transformed)
            stages_results.append(
                self._make_stage_result("transform", len(df_transformed))
            )
            self._notify_stage_end("transform", stages_results[-1])

            df_validated = self._run_stage(
                stage="validate",
                context=context,
                action=lambda: self.validate(df_transformed),
            )
            stages_results.append(
                self._make_stage_result("validate", len(df_validated))
            )
            self._notify_stage_end("validate", stages_results[-1])

            write_result: WriteResult | None = None
            if not dry_run:
                write_result = self._run_stage(
                    stage="write",
                    context=context,
                    action=lambda: self.write(
                        df_validated,
                        output_path,
                        context,
                    ),
                )
                if write_result is None:
                    raise RuntimeError("Write stage returned None")

                stages_results.append(
                    self._make_stage_result("write", write_result.row_count)
                )
                self._notify_stage_end("write", stages_results[-1])

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
        except PipelineStageError as error:
            self._logger.error(
                "Pipeline failed",
                stage=error.stage,
                provider=error.provider,
                entity=error.entity,
                run_id=error.run_id,
                error=str(error.cause) if error.cause else str(error),
            )
            # Hooks are already notified in _run_stage
            raise

    # === Abstract Methods ===

    def get_database_version(self) -> str | None:
        """
        Возвращает версию базы данных источника.
        Может быть переопределено в наследниках.
        """
        return None

    @abstractmethod
    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """Извлекает данные из источника."""

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Преобразует сырые данные."""

    # === Concrete Methods ===

    def get_version(self) -> str:
        """Возвращает версию источника данных. По умолчанию 'unknown'."""
        return "unknown"

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
        Использует HashService.
        """
        if df.empty:
            return df.assign(hash_business_key=None, hash_row=None)

        keys = self._config.hashing.business_key_fields
        return self._hash_service.add_hash_columns(df, business_key_cols=keys)

    def _add_index_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавляет столбцы с индексами строк.
        Использует HashService.
        """
        return self._hash_service.add_index_column(df)

    def _add_database_version_column(
        self, df: pd.DataFrame, database_version: str
    ) -> pd.DataFrame:
        """
        Добавляет столбцы с версией базы данных.
        Использует HashService.
        """
        return self._hash_service.add_database_version_column(
            df, database_version
        )

    def _add_fulldate_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавляет столбцы с датой и временем извлечения.
        Использует HashService.
        """
        return self._hash_service.add_fulldate_column(df)

    def _notify_stage_start(self, stage: str, context: RunContext) -> None:
        self._stage_starts[stage] = datetime.now(timezone.utc)
        self._logger.info(
            f"Stage started: {stage}",
            provider=context.provider,
            entity=context.entity_name,
            run_id=context.run_id,
        )
        for hook in self._hooks:
            hook.on_stage_start(stage, context)

    def _notify_stage_end(self, stage: str, result: StageResult) -> None:
        self._logger.info(
            f"Stage finished: {stage}",
            records=result.records_processed,
            provider=self._config.provider,
            entity=self._config.entity_name,
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

    def _run_stage(
        self,
        stage: str,
        context: RunContext,
        action: Callable[[], Any],
        *,
        attempt: int = 1,
    ) -> Any:
        self._notify_stage_start(stage, context)
        try:
            return action()
        except Exception as exc:
            error = PipelineStageError(
                provider=self._config.provider,
                entity=self._config.entity_name,
                stage=stage,
                attempt=attempt,
                run_id=context.run_id,
                cause=exc,
            )
            self._logger.error(
                "Stage failed",
                stage=stage,
                provider=self._config.provider,
                entity=self._config.entity_name,
                run_id=context.run_id,
                error=str(exc),
            )
            for hook in self._hooks:
                hook.on_error(stage, error)
            raise error from exc

    def _enrich_context(self, context: RunContext) -> None:
        """
        Хук для обогащения контекста (например, добавления версии релиза).
        """
