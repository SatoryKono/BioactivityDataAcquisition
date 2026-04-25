"""Checkpoint service for administrative operations (Application layer).

Provides high-level checkpoint management for CLI and other interfaces.
Uses CheckpointPort for actual persistence operations.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

__all__ = ["CheckpointInfo", "CheckpointService"]


from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.application.observability.span_attribute_values import (
    coerce_span_attribute_value,
)
from bioetl.application.observability.span_helpers import traced_async_operation
from bioetl.application.services._checkpoint_service_support import (
    _CHECKPOINT_OPERATOR_DURATION_METRIC,
    _CHECKPOINT_OPERATOR_ERRORS,
    _CHECKPOINT_OPERATOR_OPERATIONS_METRIC,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import CheckpointPort, LoggerPort, MetricsPort, TracingPort
from bioetl.domain.types import JsonDict


@dataclass(frozen=True, slots=True)
class CheckpointInfo:
    """Information about a checkpoint.

    Attributes:
        pipeline_name: Name of the pipeline.
        run_id: Run ID that created this checkpoint.
        metadata: Checkpoint metadata (records_processed, etc.).
    """

    pipeline_name: str
    run_id: str | None
    metadata: JsonDict  # Any: checkpoint metadata values are heterogeneous


@dataclass
class CheckpointService:
    """Service for administrative checkpoint operations.

    Provides high-level operations for checkpoint management
    used by CLI and other interfaces. Wraps CheckpointPort
    for Application-layer abstraction.

    Attributes:
        checkpoint_port: Port for checkpoint persistence.
        logger: Structured logger for observability.

    Example:
        >>> service = CheckpointService(checkpoint_port=port, logger=logger)
        >>> checkpoints = await service.list_checkpoints()
        >>> for cp in checkpoints:
        ...     logger.info("checkpoint", pipeline=cp.pipeline_name, metadata=cp.metadata)
    """

    checkpoint_port: CheckpointPort
    logger: LoggerPort
    metrics: MetricsPort | None = None
    tracer: TracingPort | None = None
    TRACER_NAME = "bioetl.checkpoint_admin"

    def _trace_attributes(
        self,
        *,
        operation: str,
        pipeline: str | None = None,
        **extra: object,
    ) -> dict[str, object]:
        """Build bounded trace attributes for checkpoint admin operations."""
        attributes: dict[str, object] = {
            "bioetl.component": "checkpoint_service",
            "bioetl.operation": operation,
        }
        if pipeline is not None:
            attributes["bioetl.pipeline"] = pipeline
        attributes.update(extra)
        return attributes

    @staticmethod
    def _set_trace_result(
        span: Span,
        *,
        success: bool,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        """Attach bounded result attributes to a checkpoint admin span."""
        span.set_attribute("bioetl.success", success)
        for key, value in (extra or {}).items():
            span.set_attribute(key, _coerce_span_attribute_value(value))

    def _record_operator_metrics(
        self,
        *,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """Record bounded metrics for checkpoint admin operations."""
        if self.metrics is None:
            return
        labels = {"operation": operation, "status": status}
        self.metrics.increment_counter(
            _CHECKPOINT_OPERATOR_OPERATIONS_METRIC,
            1,
            labels=labels,
        )
        self.metrics.observe_histogram(
            _CHECKPOINT_OPERATOR_DURATION_METRIC,
            duration_seconds,
            labels=labels,
        )

    async def list_checkpoints(self) -> list[CheckpointInfo]:
        """List all checkpoints across all pipelines.

        Returns:
            List of CheckpointInfo with pipeline names and metadata.
        """
        self.logger.debug("Listing all checkpoints")
        start_time = perf_counter()
        if self.tracer is None:
            return await self._list_checkpoints_impl(start_time=start_time)
        async with traced_async_operation(
            self.tracer,
            "checkpoint.list",
            self._trace_attributes(operation="list"),
            tracer_name=self.TRACER_NAME,
        ) as span:
            checkpoints = await self._list_checkpoints_impl(start_time=start_time)
            self._set_trace_result(
                span,
                success=True,
                extra={"bioetl.checkpoint_count": len(checkpoints)},
            )
            return checkpoints

    async def _list_checkpoints_impl(
        self,
        *,
        start_time: float,
    ) -> list[CheckpointInfo]:
        """List checkpoints and emit bounded observability signals."""
        try:
            pipeline_names = await self.checkpoint_port.list_all()
            checkpoints: list[CheckpointInfo] = []

            for pipeline_name in pipeline_names:
                checkpoint_data = await self.checkpoint_port.load(pipeline_name)
                if checkpoint_data:
                    run_id, metadata = checkpoint_data
                    checkpoints.append(
                        CheckpointInfo(
                            pipeline_name=pipeline_name,
                            run_id=str(run_id),
                            metadata=metadata,
                        )
                    )
                else:
                    checkpoints.append(
                        CheckpointInfo(
                            pipeline_name=pipeline_name,
                            run_id=None,
                            metadata={},
                        )
                    )

            self.logger.info(
                "Listed checkpoints",
                checkpoint_count=len(checkpoints),
            )
            self._record_operator_metrics(
                operation="list",
                status="success",
                duration_seconds=perf_counter() - start_time,
            )
            return checkpoints
        except _CHECKPOINT_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="list",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

    async def get_checkpoint(self, pipeline_name: str) -> CheckpointInfo | None:
        """Get checkpoint for a specific pipeline.

        Args:
            pipeline_name: Name of the pipeline.

        Returns:
            CheckpointInfo if checkpoint exists, None otherwise.
        """
        self.logger.debug("Getting checkpoint", pipeline=pipeline_name)
        start_time = perf_counter()
        if self.tracer is None:
            return await self._get_checkpoint_impl(
                pipeline_name=pipeline_name,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "checkpoint.get",
            self._trace_attributes(operation="get", pipeline=pipeline_name),
            tracer_name=self.TRACER_NAME,
        ) as span:
            checkpoint = await self._get_checkpoint_impl(
                pipeline_name=pipeline_name,
                start_time=start_time,
            )
            self._set_trace_result(
                span,
                success=True,
                extra={"bioetl.checkpoint_found": checkpoint is not None},
            )
            return checkpoint

    async def _get_checkpoint_impl(
        self,
        *,
        pipeline_name: str,
        start_time: float,
    ) -> CheckpointInfo | None:
        """Get a checkpoint and emit bounded observability signals."""
        try:
            checkpoint_data = await self.checkpoint_port.load(pipeline_name)
            if checkpoint_data is None:
                self.logger.debug("Checkpoint not found", pipeline=pipeline_name)
                self._record_operator_metrics(
                    operation="get",
                    status="missing",
                    duration_seconds=perf_counter() - start_time,
                )
                return None

            run_id, metadata = checkpoint_data
            self.logger.info(
                "Got checkpoint",
                pipeline=pipeline_name,
                run_id=str(run_id),
            )
            self._record_operator_metrics(
                operation="get",
                status="success",
                duration_seconds=perf_counter() - start_time,
            )
            return CheckpointInfo(
                pipeline_name=pipeline_name,
                run_id=str(run_id),
                metadata=metadata,
            )
        except _CHECKPOINT_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="get",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

    async def delete_checkpoint(self, pipeline_name: str) -> bool:
        """Delete checkpoint for a specific pipeline.

        Args:
            pipeline_name: Name of the pipeline.

        Returns:
            True if checkpoint was deleted, False if it didn't exist.
        """
        self.logger.debug("Deleting checkpoint", pipeline=pipeline_name)
        start_time = perf_counter()
        if self.tracer is None:
            return await self._delete_checkpoint_impl(
                pipeline_name=pipeline_name,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "checkpoint.delete",
            self._trace_attributes(operation="delete", pipeline=pipeline_name),
            tracer_name=self.TRACER_NAME,
        ) as span:
            deleted = await self._delete_checkpoint_impl(
                pipeline_name=pipeline_name,
                start_time=start_time,
            )
            self._set_trace_result(
                span,
                success=True,
                extra={"bioetl.checkpoint_deleted": deleted},
            )
            return deleted

    async def _delete_checkpoint_impl(
        self,
        *,
        pipeline_name: str,
        start_time: float,
    ) -> bool:
        """Delete a checkpoint and emit bounded observability signals."""
        try:
            existing = await self.checkpoint_port.load(pipeline_name)
            if existing is None:
                self.logger.debug(
                    "Checkpoint not found for deletion", pipeline=pipeline_name
                )
                self._record_operator_metrics(
                    operation="delete",
                    status="missing",
                    duration_seconds=perf_counter() - start_time,
                )
                return False

            await self.checkpoint_port.delete(pipeline_name)
            self.logger.info("Deleted checkpoint", pipeline=pipeline_name)
            self._record_operator_metrics(
                operation="delete",
                status="success",
                duration_seconds=perf_counter() - start_time,
            )
            return True
        except _CHECKPOINT_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="delete",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.checkpoint_port.aclose()
