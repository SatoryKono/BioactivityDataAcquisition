"""
Pipeline executor that manages state machine for pipeline runs.

This module implements the execution engine for ETL pipelines. It separates
the "how to run" logic from the "what to run" logic in PipelineBase.

Architecture notes:
    - PipelineExecutor implements the State Machine pattern for run lifecycle
    - Uses _RunState dataclass to maintain execution state (immutable context)
    - Delegates actual stage work to the pipeline instance
    - Handles error recovery and result construction

Execution flow:
    1. Initialize: Reset state, build context, bind logger
    2. Extract phase: Run extract → transform → validate in chunks
    3. Write phase: Concatenate validated chunks, write output (if not dry_run)
    4. Finalize: Build metadata, construct RunResult

Error handling:
    - PipelineStageError caught and converted to failed RunResult
    - Stage results recorded even on failure for debugging
    - Error messages propagated to RunResult.errors list

Example::

    executor = PipelineExecutor(runtime_manager, metadata_builder, logger)
    result = executor.execute(pipeline, output_path, dry_run=False)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bioetl.application.pipelines.stage_runtime_manager import StageRuntimeManagerImpl
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
    WriteResult,
)
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.observability import LoggingPortABC

if TYPE_CHECKING:
    from bioetl.application.pipelines.base import PipelineBase


@dataclass
class _RunState:
    """Internal state holder for a single pipeline run execution."""

    context: RunContext
    counters: dict[str, int] = field(default_factory=dict)
    validated_chunks: list[pd.DataFrame] = field(default_factory=list)
    stages_results: list[StageResult] = field(default_factory=list)
    write_result: WriteResult | None = None


class PipelineExecutor:
    """
    Executes pipeline state machine for ETL runs.

    Manages the lifecycle of a pipeline run:
    initialize → extract → transform → validate → write

    Delegates actual stage work to the pipeline instance.
    """

    def __init__(
        self,
        runtime_manager: StageRuntimeManagerImpl,
        metadata_builder: RunMetadataBuilderProtocol,
        logger: LoggingPortABC,
    ) -> None:
        self._runtime_manager = runtime_manager
        self._metadata_builder = metadata_builder
        self._logger = logger

    def execute(
        self,
        pipeline: PipelineBase,
        output_path: Path,
        *,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> RunResult:
        """
        Execute the pipeline state machine.

        Args:
            pipeline: The pipeline instance to execute.
            output_path: Path for output files.
            dry_run: If True, skip write phase.
            **kwargs: Additional arguments passed to extract stage.

        Returns:
            RunResult with execution status and metadata.
        """
        state = self._initialize_run(pipeline, dry_run)

        try:
            self._run_extraction_phase(pipeline, state, dry_run, **kwargs)
            self._record_etl_stages(state)

            if not dry_run:
                result = self._run_write_phase(pipeline, state, output_path)
                if result is not None:
                    return result

            return self._build_success_result(pipeline, state, output_path, dry_run)

        except PipelineStageError as error:
            return self._handle_error(error, state)

    def _initialize_run(self, pipeline: PipelineBase, dry_run: bool) -> _RunState:
        """Initialize runtime state for a new pipeline run."""
        self._runtime_manager.reset()
        hash_service = pipeline.get_hash_service()
        if hasattr(hash_service, "reset_state"):
            hash_service.reset_state()

        context = pipeline.build_context(dry_run)
        self._logger = self._logger.apply_bind(run_id=context.run_id)
        self._runtime_manager.set_logger(self._logger)
        self._logger.info("Pipeline started", run_id=context.run_id)

        return _RunState(
            context=context,
            counters=pipeline.init_stage_counters(),
            validated_chunks=[],
            stages_results=[],
        )

    def _run_extraction_phase(
        self,
        pipeline: PipelineBase,
        state: _RunState,
        dry_run: bool,
        **kwargs: Any,
    ) -> None:
        """Execute extract, transform, and validate stages."""
        self._runtime_manager.notify_stage_start("extract", state.context)
        state.counters, state.validated_chunks = pipeline.process_extract_stage(
            state.context,
            state.counters,
            state.validated_chunks,
            dry_run,
            kwargs,
        )

    def _record_etl_stages(self, state: _RunState) -> None:
        """Record stage results for extract, transform, and validate."""
        for stage_name in ("extract", "transform", "validate"):
            self._append_stage_result(
                state.stages_results,
                stage_name,
                state.counters[f"{stage_name}_count"],
                state.counters[f"{stage_name}_chunks"],
            )

    def _run_write_phase(
        self,
        pipeline: PipelineBase,
        state: _RunState,
        output_path: Path,
    ) -> RunResult | None:
        """Execute write stage; returns RunResult on failure, None on success."""
        state.write_result, state.counters = pipeline.perform_write_stage(
            state.context,
            state.validated_chunks,
            output_path,
            state.counters,
            state.stages_results,
        )
        if state.write_result is None:
            return self._runtime_manager.handle_stage_failure(
                "write", state.stages_results, state.context
            )
        return None

    def _build_success_result(
        self,
        pipeline: PipelineBase,
        state: _RunState,
        output_path: Path,
        dry_run: bool,
    ) -> RunResult:
        """Build and return a successful RunResult."""
        meta = self._build_run_metadata(pipeline, state, dry_run)
        return RunResult(
            run_id=state.context.run_id,
            success=True,
            entity_name=pipeline.config.entity_name,
            row_count=state.counters["validate_count"],
            output_path=output_path if not dry_run else None,
            duration_sec=self._calculate_duration(state.context),
            stages=state.stages_results,
            errors=[],
            meta=meta,
        )

    def _build_run_metadata(
        self,
        pipeline: PipelineBase,
        state: _RunState,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Build metadata for the run result."""
        meta_raw = (
            self._metadata_builder.build_run_metadata(state.context, state.write_result)
            if state.write_result
            else self._metadata_builder.build_dry_run_metadata(
                state.context, state.counters["validate_count"]
            )
        )
        return pipeline.normalize_meta(
            meta_raw, state.context, state.counters["validate_count"], dry_run
        )

    def _handle_error(
        self,
        error: PipelineStageError,
        state: _RunState,
    ) -> RunResult:
        """Handle pipeline error and build failure result."""
        stage_result = self._runtime_manager.make_stage_result(
            error.stage,
            0,
            success=False,
            errors=self._runtime_manager.get_last_error_messages(),
        )
        state.stages_results.append(stage_result)
        self._runtime_manager.notify_stage_end(error.stage, stage_result)
        self._logger.error(
            "Pipeline failed",
            stage=error.stage,
            provider=error.provider,
            entity=error.entity,
            run_id=error.run_id,
            error=str(error.cause) if error.cause else str(error),
        )
        return RunResult(
            run_id=state.context.run_id,
            success=False,
            entity_name=error.entity,
            row_count=0,
            output_path=None,
            duration_sec=self._calculate_duration(state.context),
            stages=state.stages_results,
            errors=self._runtime_manager.get_last_error_messages(),
            meta={},
        )

    def _append_stage_result(
        self,
        stages_results: list[StageResult],
        stage: str,
        count: int,
        chunks: int,
    ) -> None:
        """Append a stage result and notify hooks."""
        stages_results.append(
            self._runtime_manager.make_stage_result(
                stage,
                count,
                chunks=chunks,
            )
        )
        self._runtime_manager.notify_stage_end(stage, stages_results[-1])

    @staticmethod
    def _calculate_duration(context: RunContext) -> float:
        """Calculate elapsed duration since context start."""
        return (datetime.now(timezone.utc) - context.started_at).total_seconds()


__all__ = ["PipelineExecutor"]
