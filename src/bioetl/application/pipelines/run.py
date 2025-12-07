"""Фасад исполнения конвейера."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from bioetl.application.pipelines.extract import ExtractStageProtocol
from bioetl.application.pipelines.stage_runtime_manager import StageRuntimeManagerImpl
from bioetl.application.pipelines.transform import TransformStageProtocol
from bioetl.application.pipelines.validate import ValidateStageProtocol
from bioetl.application.pipelines.write import WriteStageProtocol
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
    WriteResult,
)
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.observability import LoggingPortABC


@dataclass
class StageCountersModel:
    """Accumulated counters for pipeline stages during execution."""

    extract_count: int = 0
    extract_chunks: int = 0
    transform_count: int = 0
    transform_chunks: int = 0
    validate_count: int = 0
    validate_chunks: int = 0
    write_count: int = 0
    write_chunks: int = 0


class PipelineRunnerFacade:
    """Отвечает за оркестрацию стадий пайплайна."""

    def __init__(
        self,
        *,
        logger: LoggingPortABC,
        runtime_manager: StageRuntimeManagerImpl,
        metadata_builder: RunMetadataBuilderProtocol,
        extract_stage: ExtractStageProtocol,
        transform_stage: TransformStageProtocol,
        validate_stage: ValidateStageProtocol,
        write_stage: WriteStageProtocol,
        apply_transformers: Callable[[pd.DataFrame, RunContext], pd.DataFrame],
        context_builder: Callable[[bool], RunContext],
        chunk_iterator_factory: Callable[[RunContext, dict[str, Any]], Any],
        reset_state: Callable[[], None] | None = None,
    ) -> None:
        self._logger = logger
        self._runtime_manager = runtime_manager
        self._metadata_builder = metadata_builder
        self._extract_stage = extract_stage
        self._transform_stage = transform_stage
        self._validate_stage = validate_stage
        self._write_stage = write_stage
        self._apply_transformers = apply_transformers
        self._context_builder = context_builder
        self._chunk_iterator_factory = chunk_iterator_factory
        self._reset_state = reset_state

    def run(
        self, output_path: Path, *, dry_run: bool = False, **kwargs: Any
    ) -> RunResult:
        """Запускает extract → transform → validate → write."""

        self._runtime_manager.reset()
        if self._reset_state:
            self._reset_state()

        context = self._context_builder(dry_run)
        logger = self._logger.apply_bind(run_id=context.run_id)
        self._runtime_manager.set_logger(logger)
        logger.info("Pipeline started", run_id=context.run_id)

        counters = StageCountersModel()
        stages_results: list[StageResult] = []
        validated_chunks: list[pd.DataFrame] = []

        try:
            self._runtime_manager.notify_stage_start("extract", context)
            counters, validated_chunks = self._process_extract_stage(
                context, counters, validated_chunks, dry_run, kwargs
            )

            stages_results.extend(
                [
                    self._runtime_manager.make_stage_result(
                        "extract",
                        counters.extract_count,
                        chunks=counters.extract_chunks,
                    ),
                    self._runtime_manager.make_stage_result(
                        "transform",
                        counters.transform_count,
                        chunks=counters.transform_chunks,
                    ),
                    self._runtime_manager.make_stage_result(
                        "validate",
                        counters.validate_count,
                        chunks=counters.validate_chunks,
                    ),
                ]
            )
            for stage_name, stage_result in zip(
                ("extract", "transform", "validate"), stages_results, strict=True
            ):
                self._runtime_manager.notify_stage_end(stage_name, stage_result)

            write_result: WriteResult | None = None
            if not dry_run:
                write_result, counters, write_stage_result = self._perform_write_stage(
                    context, validated_chunks, output_path, counters
                )
                if write_result is None:
                    return self._runtime_manager.handle_stage_failure(
                        "write",
                        stages_results,
                        context,
                        count=counters.validate_count,
                        chunks=counters.validate_chunks,
                    )
                if write_stage_result:
                    stages_results.append(write_stage_result)

            meta_raw = (
                self._metadata_builder.build_run_metadata(context, write_result)
                if write_result
                else self._metadata_builder.build_dry_run_metadata(
                    context, counters.validate_count
                )
            )
            meta = self._normalize_meta(
                meta_raw, context, counters.validate_count, dry_run
            )

            return RunResult(
                run_id=context.run_id,
                success=True,
                entity_name=context.entity_name,
                row_count=counters.validate_count,
                output_path=output_path if not dry_run else None,
                duration_sec=self._calculate_duration(context),
                stages=stages_results,
                errors=[],
                meta=meta,
            )
        except PipelineStageError as error:
            stage_result = self._runtime_manager.make_stage_result(
                error.stage,
                0,
                success=False,
                errors=self._runtime_manager.get_last_error_messages(),
            )
            stages_results.append(stage_result)
            self._runtime_manager.notify_stage_end(error.stage, stage_result)
            logger.error(
                "Pipeline failed",
                stage=error.stage,
                provider=error.provider,
                entity=error.entity,
                run_id=error.run_id,
                error=str(error.cause) if error.cause else str(error),
            )
            raise

    def _process_extract_stage(
        self,
        context: RunContext,
        counters: StageCountersModel,
        validated_chunks: list[pd.DataFrame],
        dry_run: bool,
        kwargs: dict[str, Any],
    ) -> tuple[StageCountersModel, list[pd.DataFrame]]:
        chunk_iterator = self._chunk_iterator_factory(context, kwargs)
        transform_started = False
        validate_started = False

        def reset_iterator() -> None:
            """Recreate extractor iterator for retry scenarios."""
            nonlocal chunk_iterator
            chunk_iterator = self._chunk_iterator_factory(context, kwargs)

        while True:
            try:
                raw_chunk_obj = self._runtime_manager.execute_stage(
                    "extract",
                    context,
                    lambda: next(chunk_iterator),
                    on_retry=reset_iterator,
                )
            except StopIteration:
                break

            counters.extract_chunks += 1
            if raw_chunk_obj is None:
                raw_chunk = pd.DataFrame()
            elif isinstance(raw_chunk_obj, pd.DataFrame):
                raw_chunk = raw_chunk_obj
            else:
                raise TypeError("Extractor must yield pandas DataFrame chunks.")
            counters.extract_count += len(raw_chunk)

            (
                transform_started,
                counters.transform_chunks,
                counters.transform_count,
                validate_started,
                counters.validate_chunks,
                counters.validate_count,
            ) = self._runtime_manager.process_chunk(
                raw_chunk,
                context,
                transform_started=transform_started,
                transform_chunks=counters.transform_chunks,
                transform_count=counters.transform_count,
                validate_started=validate_started,
                validate_chunks=counters.validate_chunks,
                validate_count=counters.validate_count,
                validated_chunks=validated_chunks,
                dry_run=dry_run,
                transform_fn=lambda frame: self._transform_stage.transform(frame),
                apply_transformers=self._apply_transformers,
                validate_fn=lambda frame: self._validate_stage.validate(frame, context),
            )

        if not transform_started:
            (
                transform_started,
                counters.transform_chunks,
                counters.transform_count,
                validate_started,
                counters.validate_chunks,
                counters.validate_count,
            ) = self._runtime_manager.process_chunk(
                pd.DataFrame(),
                context,
                transform_started=transform_started,
                transform_chunks=counters.transform_chunks,
                transform_count=counters.transform_count,
                validate_started=validate_started,
                validate_chunks=counters.validate_chunks,
                validate_count=counters.validate_count,
                validated_chunks=validated_chunks,
                dry_run=dry_run,
                transform_fn=lambda frame: self._transform_stage.transform(
                    frame, context
                ),
                apply_transformers=self._apply_transformers,
                validate_fn=lambda frame: self._validate_stage.validate(frame, context),
            )

        return counters, validated_chunks

    def _perform_write_stage(
        self,
        context: RunContext,
        validated_chunks: list[pd.DataFrame],
        output_path: Path,
        counters: StageCountersModel,
    ) -> tuple[WriteResult | None, StageCountersModel, StageResult | None]:
        if not self._runtime_manager.get_stage_start("write"):
            self._runtime_manager.notify_stage_start("write", context)

        df_to_write = (
            pd.concat(validated_chunks, ignore_index=True)
            if validated_chunks
            else pd.DataFrame()
        )

        write_result_obj = self._runtime_manager.execute_stage(
            "write",
            context,
            lambda: self._write_stage.write(df_to_write, output_path, context),
        )
        if write_result_obj is None:
            return None, counters, None
        if not isinstance(write_result_obj, WriteResult):
            raise TypeError("Writer must return WriteResult or None.")

        counters.write_count = write_result_obj.row_count
        counters.write_chunks = max(counters.validate_chunks, 1)

        stage_result = self._runtime_manager.make_stage_result(
            "write", write_result_obj.row_count, chunks=counters.write_chunks
        )
        self._runtime_manager.notify_stage_end("write", stage_result)
        return write_result_obj, counters, stage_result

    @staticmethod
    def _normalize_meta(
        meta: dict[str, Any], context: RunContext, row_count: int, dry_run: bool
    ) -> dict[str, Any]:
        if not isinstance(meta, dict):
            raise TypeError("Metadata builder must return a dict.")

        normalized_meta = dict(meta)
        normalized_meta.setdefault("run_id", context.run_id)
        normalized_meta.setdefault("provider", context.provider)
        normalized_meta.setdefault("entity", context.entity_name)
        normalized_meta.setdefault("row_count", row_count)
        if dry_run:
            normalized_meta["dry_run"] = True
        else:
            normalized_meta.setdefault("dry_run", False)

        return normalized_meta

    @staticmethod
    def _calculate_duration(context: RunContext) -> float:
        return (datetime.now(timezone.utc) - context.started_at).total_seconds()


__all__ = ["PipelineRunnerFacade"]
