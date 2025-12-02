from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

from bioetl.config.models import PipelineConfig
from bioetl.core.contracts import PipelineHookABC, StageResult
from bioetl.core.models import RunContext, RunResult
from bioetl.logging.contracts import LoggerAdapterABC
from bioetl.output.contracts import WriteResult
from bioetl.output.unified_writer import UnifiedOutputWriter
from bioetl.transform.contracts import HasherABC
from bioetl.transform.impl.hasher import HasherImpl
from bioetl.validation.service import ValidationService


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
        output_writer: UnifiedOutputWriter,
    ) -> None:
        self._config = config
        self._logger = logger.bind(
            entity=config.entity_name,
            provider=config.provider,
        )
        self._validation_service = validation_service
        self._output_writer = output_writer
        self._clients: dict[str, Any] = {}
        self._hooks: list[PipelineHookABC] = []
    
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
        
        self._logger.info("Pipeline started", run_id=context.run_id)
        stages_results: list[StageResult] = []
        
        try:
            # 1. Extract
            self._notify_stage_start("extract", context)
            df_raw = self.extract(**kwargs)
            stages_results.append(self._make_stage_result("extract", len(df_raw)))
            self._notify_stage_end("extract", stages_results[-1])
            
            # 2. Transform
            self._notify_stage_start("transform", context)
            df_transformed = self.transform(df_raw)
            df_transformed = self._add_hash_columns(df_transformed)
            stages_results.append(self._make_stage_result("transform", len(df_transformed)))
            self._notify_stage_end("transform", stages_results[-1])
            
            # 3. Validate
            self._notify_stage_start("validate", context)
            df_validated = self.validate(df_transformed)
            stages_results.append(self._make_stage_result("validate", len(df_validated)))
            self._notify_stage_end("validate", stages_results[-1])
            
            # 4. Write (skip on dry_run)
            if not dry_run:
                self._notify_stage_start("write", context)
                write_result = self.write(df_validated, output_path, context)
                stages_results.append(self._make_stage_result("write", write_result.row_count))
                self._notify_stage_end("write", stages_results[-1])
            
            return RunResult(
                run_id=context.run_id,
                success=True,
                entity_name=self._config.entity_name,
                row_count=len(df_validated),
                output_path=output_path if not dry_run else None,
                duration_sec=self._calculate_duration(context),
                stages=stages_results,
                errors=[],
                meta=self._build_meta(context, df_validated),
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
        return self._validation_service.validate(df, self._config.entity_name)
    
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
        self._clients[name] = client
    
    def add_hook(self, hook: PipelineHookABC) -> None:
        self._hooks.append(hook)
    
    # === Internal Methods ===
    
    def _get_hasher(self) -> HasherABC:
        return HasherImpl()
        
    def _add_hash_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        hasher = self._get_hasher()
        df = df.copy()
        df["hash_row"] = hasher.hash_columns(df, df.columns.tolist())
        
        business_key_cols = self._config.business_key
        if business_key_cols:
            # Ensure columns exist before hashing
            cols_to_hash = [c for c in business_key_cols if c in df.columns]
            if cols_to_hash:
                df["hash_business_key"] = hasher.hash_columns(df, cols_to_hash)
        
        return df
    
    def _close_clients(self) -> None:
        for name, client in self._clients.items():
            if hasattr(client, "close"):
                client.close()
                self._logger.debug("Client closed", client=name)

    def _notify_stage_start(self, stage: str, context: RunContext) -> None:
        self._logger.info(f"Stage started: {stage}")
        for hook in self._hooks:
            hook.on_stage_start(stage, context)

    def _notify_stage_end(self, stage: str, result: StageResult) -> None:
        self._logger.info(f"Stage finished: {stage}", records=result.records_processed)
        for hook in self._hooks:
            hook.on_stage_end(stage, result)

    def _make_stage_result(self, stage: str, count: int) -> StageResult:
        return StageResult(
            stage_name=stage,
            success=True,
            records_processed=count,
            duration_sec=0.0, # TODO: measure duration
            errors=[],
        )

    def _calculate_duration(self, context: RunContext) -> float:
        return (datetime.now(timezone.utc).replace(tzinfo=None) - context.started_at).total_seconds()

    def _build_meta(self, context: RunContext, df: pd.DataFrame) -> dict[str, Any]:
        return {
            "run_id": context.run_id,
            "entity": self._config.entity_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "row_count": len(df),
        }

