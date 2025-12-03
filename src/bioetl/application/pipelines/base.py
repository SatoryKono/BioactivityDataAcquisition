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
from bioetl.domain.models import RunContext, RunResult
from bioetl.application.pipelines.stages import StageResult
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.contracts import WriteResult
from bioetl.infrastructure.output.services.metadata_builder import MetadataBuilder
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService

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
        metadata_builder: MetadataBuilder | None = None,
    ) -> None:
        self._config = config
        self._logger = logger.bind(
            entity=config.entity_name,
            provider=config.provider,
        )
        self._validation_service = validation_service
        self._output_writer = output_writer
        self._hash_service = hash_service or HashService()
        self._metadata_builder = metadata_builder or MetadataBuilder()
        self._clients: dict[str, Any] = {}
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
                meta = self._metadata_builder.build(context, write_result)
            else:
                meta = self._metadata_builder.build_dry_run(
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

        finally:
            self._close_clients()

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

    # === Client Management ===

    def register_client(self, name: str, client: Any) -> None:
        """Регистрирует клиент API."""
        self._clients[name] = client

    def add_hook(self, hook: PipelineHookABC) -> None:
        """Добавляет хук выполнения."""
        self._hooks.append(hook)

    # === Internal Methods ===

    def _add_hash_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Добавляет столбцы с хешами строк и бизнес-ключей."""
        keys = self._config.hashing.business_key_fields or self._config.business_key
        return self._hash_service.add_hash_columns(
            df,
            business_key_cols=keys
        )

    def _close_clients(self) -> None:
        for name, client in self._clients.items():
            if hasattr(client, "close"):
                client.close()
                self._logger.debug("Client closed", client=name)

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
