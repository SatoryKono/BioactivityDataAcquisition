"""Stage processing utilities for ETL pipelines.

This module provides the StageProcessor class that handles the execution
of individual ETL stages (extract, transform, validate, write).

Extracted from PipelineBase to reduce class size and improve separation
of concerns. StageProcessor handles the "how" of stage execution while
PipelineBase handles the "what" (template method pattern).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterator, cast

import pandas as pd

from bioetl.application.pipelines.stage_runtime_manager import StageRuntimeManagerImpl
from bioetl.domain.clients.base.output.contracts import WriteResult
from bioetl.domain.models import RunContext, StageResult

if TYPE_CHECKING:
    pass


class StageProcessor:
    """Handles execution of ETL stages.

    Encapsulates the logic for processing extract, transform, validate,
    and write stages, delegating runtime management to StageRuntimeManagerImpl.
    """

    def __init__(
        self,
        runtime_manager: StageRuntimeManagerImpl,
    ) -> None:
        """Initialize stage processor.

        Args:
            runtime_manager: Manager for stage execution and hooks.
        """
        self._runtime_manager = runtime_manager

    def init_stage_counters(self) -> dict[str, int]:
        """Initialize counters for all stages.

        Returns:
            Dictionary with zero counters for each stage.
        """
        return {
            "extract_count": 0,
            "extract_chunks": 0,
            "transform_count": 0,
            "transform_chunks": 0,
            "validate_count": 0,
            "validate_chunks": 0,
            "export_count": 0,
            "export_chunks": 0,
        }

    def process_extract_stage(
        self,
        context: RunContext,
        counters: dict[str, int],
        validated_chunks: list[pd.DataFrame],
        dry_run: bool,
        kwargs: dict[str, Any],
        *,
        extract_fn: Callable[..., Any],
        transform_fn: Callable[[pd.DataFrame], pd.DataFrame],
        apply_transformers: Callable[[pd.DataFrame, RunContext], pd.DataFrame],
        validate_fn: Callable[[pd.DataFrame], pd.DataFrame],
        normalize_extract_result: Callable[[Any], Iterator[pd.DataFrame]],
    ) -> tuple[dict[str, int], list[pd.DataFrame]]:
        """Process extract stage with transform and validate.

        Args:
            context: Run context.
            counters: Stage counters to update.
            validated_chunks: List to accumulate validated chunks.
            dry_run: Whether this is a dry run.
            kwargs: Additional arguments for extract function.
            extract_fn: Function to call for extraction.
            transform_fn: Function for transformation.
            apply_transformers: Function to apply post-transformers.
            validate_fn: Function for validation.
            normalize_extract_result: Function to normalize extract results.

        Returns:
            Tuple of (updated counters, validated chunks).
        """
        chunk_iterator: Iterator[pd.DataFrame] | None = None
        transform_started = False
        validate_started = False

        def reset_iterator() -> None:
            """Recreate extractor iterator for retries."""
            nonlocal chunk_iterator
            extract_result = self._runtime_manager.execute_stage(
                "extract",
                context,
                lambda: extract_fn(**kwargs),
            )
            chunk_iterator = normalize_extract_result(extract_result)

        reset_iterator()
        while True:
            try:
                raw_chunk_obj = self._runtime_manager.execute_stage(
                    "extract",
                    context,
                    lambda: next(cast(Iterator[pd.DataFrame], chunk_iterator)),
                    on_retry=reset_iterator,
                )
            except StopIteration:
                break

            counters["extract_chunks"] += 1
            if raw_chunk_obj is None:
                raw_chunk: pd.DataFrame = pd.DataFrame()
            elif isinstance(raw_chunk_obj, pd.DataFrame):
                raw_chunk = raw_chunk_obj
            else:
                raise TypeError("Extractor must yield pandas DataFrame chunks.")
            counters["extract_count"] += len(raw_chunk)

            (
                transform_started,
                counters["transform_chunks"],
                counters["transform_count"],
                validate_started,
                counters["validate_chunks"],
                counters["validate_count"],
            ) = self._runtime_manager.process_chunk(
                raw_chunk,
                context,
                transform_started=transform_started,
                transform_chunks=counters["transform_chunks"],
                transform_count=counters["transform_count"],
                validate_started=validate_started,
                validate_chunks=counters["validate_chunks"],
                validate_count=counters["validate_count"],
                validated_chunks=validated_chunks,
                dry_run=dry_run,
                transform_fn=transform_fn,
                apply_transformers=apply_transformers,
                validate_fn=validate_fn,
            )

        # Ensure transform is started even if no data
        if not transform_started:
            (
                transform_started,
                counters["transform_chunks"],
                counters["transform_count"],
                validate_started,
                counters["validate_chunks"],
                counters["validate_count"],
            ) = self._runtime_manager.process_chunk(
                pd.DataFrame(),
                context,
                transform_started=transform_started,
                transform_chunks=counters["transform_chunks"],
                transform_count=counters["transform_count"],
                validate_started=validate_started,
                validate_chunks=counters["validate_chunks"],
                validate_count=counters["validate_count"],
                validated_chunks=validated_chunks,
                dry_run=dry_run,
                transform_fn=transform_fn,
                apply_transformers=apply_transformers,
                validate_fn=validate_fn,
            )

        return counters, validated_chunks

    def perform_write_stage(
        self,
        context: RunContext,
        validated_chunks: list[pd.DataFrame],
        output_path: Path,
        counters: dict[str, int],
        stages_results: list[StageResult],
        *,
        write_fn: Callable[[pd.DataFrame, Path, RunContext], WriteResult],
    ) -> tuple[WriteResult | None, dict[str, int]]:
        """Perform write stage.

        Args:
            context: Run context.
            validated_chunks: Validated data chunks.
            output_path: Output file path.
            counters: Stage counters to update.
            stages_results: List to append stage results.
            write_fn: Function to perform the actual write.

        Returns:
            Tuple of (write result or None, updated counters).
        """
        if not self._runtime_manager.get_stage_start("export"):
            self._runtime_manager.notify_stage_start("export", context)

        df_to_write = (
            pd.concat(validated_chunks, ignore_index=True)
            if validated_chunks
            else pd.DataFrame()
        )

        write_result_obj = self._runtime_manager.execute_stage(
            "export",
            context,
            lambda: write_fn(df_to_write, output_path, context),
        )
        if write_result_obj is None:
            return None, counters
        if not isinstance(write_result_obj, WriteResult):
            raise TypeError("Writer must return WriteResult or None.")
        write_result = write_result_obj

        counters["export_count"] = write_result.row_count
        counters["export_chunks"] = max(counters["validate_chunks"], 1)

        self._append_stage_result(
            stages_results,
            "export",
            write_result.row_count,
            counters["export_chunks"],
        )
        return write_result, counters

    def _append_stage_result(
        self,
        stages_results: list[StageResult],
        stage: str,
        count: int,
        chunks: int,
    ) -> None:
        """Append stage result and notify hooks.

        Args:
            stages_results: List to append to.
            stage: Stage name.
            count: Record count.
            chunks: Chunk count.
        """
        stages_results.append(
            self._runtime_manager.make_stage_result(
                stage,
                count,
                chunks=chunks,
            )
        )
        self._runtime_manager.notify_stage_end(stage, stages_results[-1])


__all__ = ["StageProcessor"]
