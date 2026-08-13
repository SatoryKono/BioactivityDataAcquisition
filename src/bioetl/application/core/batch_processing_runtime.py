# pyright: reportImportCycles=false
# Import cycle residual (PD4).
# Import cycle residual tracked in allowlist (PD3).
"""Family-local runtime helpers for batch-processing support."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

<<<<<<< Updated upstream
from bioetl.application.core.batch_runtime_failure_policy import (
    OPERATION_ERRORS,
||||||| Stash base
from bioetl.application.core.batch_shared_operation_errors import OPERATION_ERRORS
from bioetl.application.core.batch_pipeline_execution_errors import (
=======
from bioetl.application.core.batch_pipeline_execution_errors import (
>>>>>>> Stashed changes
    PIPELINE_EXECUTION_ERRORS,
<<<<<<< Updated upstream
||||||| Stash base
)
from bioetl.application.core.batch_source_metadata_errors import (
=======
)
from bioetl.application.core.batch_shared_operation_errors import OPERATION_ERRORS
from bioetl.application.core.batch_source_metadata_errors import (
>>>>>>> Stashed changes
    SOURCE_METADATA_ERRORS,
)
from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import BatchID, BronzeRecord

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.batch_tracing import BatchTracingManagerService
    from bioetl.application.core.batch_transformer import (
        BatchTransformer,
        TransformResult,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


@runtime_checkable
class SourceMetadataProtocol(Protocol):
    """Optional data-source capability for typed source metadata."""

    def get_source_metadata(self) -> SourceMetadata | None: ...


def get_source_metadata(
    *,
    data_source: object,
    logger: LoggerPort,
    query_string: str | None,
) -> SourceMetadata | None:
    """Get source metadata and enrich it with query string when available."""
    source_metadata: SourceMetadata | None = None
    if isinstance(data_source, SourceMetadataProtocol):
        try:
            result = data_source.get_source_metadata()
            if isinstance(result, SourceMetadata):
                source_metadata = result
        except SOURCE_METADATA_ERRORS as metadata_error:
            logger.warning(
                "Source metadata collection failed",
                error_type=type(metadata_error).__name__,
                reason="source_metadata_collection_failed",
            )

    if query_string:
        if source_metadata is not None:
            if source_metadata.query_string is None:
                updated_metadata: SourceMetadata = source_metadata.model_copy(
                    update={"query_string": query_string}
                )
                return updated_metadata
            return source_metadata
        return SourceMetadata(type="api", query_string=query_string)

    return source_metadata


async def execute_with_pipeline_failure_policy[ResultT](
    *,
    tracing: BatchTracingManagerService,
    span: Span | None,
    work_coro: Awaitable[ResultT],
) -> ResultT:
    """Finish the batch span consistently across runtime failure cases."""
    try:
        return await work_coro
    except PIPELINE_EXECUTION_ERRORS as error:
        tracing.end_span(span, error)
        raise


async def execute_with_layer_span[ResultT](
    *,
    tracing: BatchTracingManagerService,
    name: str,
    coro: Awaitable[ResultT],
    batch_id: BatchID,
    count: int,
    on_error: Callable[[Exception], None] | None = None,
) -> ResultT:
    """Execute a coroutine wrapped with a per-layer tracing span."""
    span = tracing.start_layer_span(name, batch_id, count)
    try:
        result = await coro
        tracing.end_span(span)
        return result
    except PIPELINE_EXECUTION_ERRORS as error:
        tracing.end_span(span, error)
        if on_error is not None:
            on_error(error)
        raise


async def execute_transform_with_span(
    *,
    tracing: BatchTracingManagerService,
    transformer: BatchTransformer,
    records: list[BronzeRecord],
    batch_id: BatchID,
    start_index: int,
) -> TransformResult:
    """Execute transform stage and attach output metrics to the span."""
    span = tracing.start_layer_span(
        "transform",
        batch_id,
        len(records),
        input_count=True,
    )
    try:
        result = await _run_transform_batch(
            transformer=transformer,
            records=records,
            batch_id=batch_id,
            start_index=start_index,
        )
        tracing.set_transform_result(
            span,
            silver_count=len(result.silver_records),
            gold_count=len(result.gold_records),
            quarantined_count=result.quarantined_count,
        )
        tracing.end_span(span)
        return result
    except PIPELINE_EXECUTION_ERRORS as error:
        tracing.end_span(span, error)
        raise


async def _run_transform_batch(
    *,
    transformer: BatchTransformer,
    records: list[BronzeRecord],
    batch_id: BatchID,
    start_index: int,
) -> TransformResult:
    """Execute one transformer batch with the canonical call signature."""
    return await transformer.transform_batch(
        records,
        batch_id,
        start_index=start_index,
    )


def build_bronze_refs(
    bronze_result: object,
) -> list[BronzeWriteResult] | None:
    """Normalize Bronze write output into writer-compatible references."""
    typed_bronze_result = cast("BronzeWriteResult | None", bronze_result)
    return [typed_bronze_result] if typed_bronze_result else None


__all__ = [
    "OPERATION_ERRORS",
    "SourceMetadataProtocol",
    "build_bronze_refs",
    "execute_transform_with_span",
    "execute_with_layer_span",
    "execute_with_pipeline_failure_policy",
    "get_source_metadata",
]
