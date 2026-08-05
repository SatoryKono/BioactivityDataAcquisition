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
from bioetl.application.observability.tracing_operation_helpers import (
    traced_async_operation,
)
from bioetl.application.services.checkpoint._checkpoint_service_runtime import (
    delete_checkpoint_impl,
    get_checkpoint_for_manifest_id_impl,
    get_checkpoint_for_run_impl,
    get_checkpoint_impl,
    list_checkpoints_impl,
)
from bioetl.application.services.checkpoint._checkpoint_service_support import (
    _CHECKPOINT_OPERATOR_DURATION_METRIC,
    _CHECKPOINT_OPERATOR_OPERATIONS_METRIC,
)
from bioetl.application.services.checkpoint.checkpoint_models import CheckpointInfo
from bioetl.domain.types import JsonDict, RunID

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import CheckpointPort, LoggerPort, MetricsPort, TracingPort

CHECKPOINT_FOUND_ATTR = "bioetl.checkpoint_found"


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
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        """Attach bounded result attributes to a checkpoint admin span."""
        span.set_attribute("bioetl.success", success)
        for key, value in (attributes or {}).items():
            span.set_attribute(key, coerce_span_attribute_value(value))

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

    @staticmethod
    def _checkpoint_info_from_data(
        *,
        pipeline_name: str,
        checkpoint_data: tuple[RunID, JsonDict],
    ) -> CheckpointInfo:
        run_id, metadata = checkpoint_data
        return CheckpointInfo(
            pipeline_name=pipeline_name,
            run_id=str(run_id),
            metadata=metadata,
        )

    async def list_checkpoints(self) -> list[CheckpointInfo]:
        """List all checkpoints across all pipelines.

        Returns:
            List of CheckpointInfo with pipeline names and metadata.
        """
        self.logger.debug("Listing all checkpoints")
        start_time = perf_counter()
        if self.tracer is None:
            return await list_checkpoints_impl(self, start_time=start_time)
        async with traced_async_operation(
            self.tracer,
            "checkpoint.list",
            self._trace_attributes(operation="list"),
            tracer_name=self.TRACER_NAME,
        ) as span:
            checkpoints = await list_checkpoints_impl(self, start_time=start_time)
            self._set_trace_result(
                span,
                success=True,
                attributes={"bioetl.checkpoint_count": len(checkpoints)},
            )
            return checkpoints

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
            return await get_checkpoint_impl(
                self,
                pipeline_name=pipeline_name,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "checkpoint.get",
            self._trace_attributes(operation="get", pipeline=pipeline_name),
            tracer_name=self.TRACER_NAME,
        ) as span:
            checkpoint = await get_checkpoint_impl(
                self,
                pipeline_name=pipeline_name,
                start_time=start_time,
            )
            self._set_trace_result(
                span,
                success=True,
                attributes={CHECKPOINT_FOUND_ATTR: checkpoint is not None},
            )
            return checkpoint

    async def get_checkpoint_for_run(
        self,
        pipeline_name: str,
        run_id: str,
    ) -> CheckpointInfo | None:
        """Get immutable checkpoint evidence for one specific run occurrence."""
        self.logger.debug(
            "Getting checkpoint for run",
            pipeline=pipeline_name,
            run_id=run_id,
        )
        start_time = perf_counter()
        if self.tracer is None:
            return await get_checkpoint_for_run_impl(
                self,
                pipeline_name=pipeline_name,
                run_id=run_id,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "checkpoint.get_for_run",
            self._trace_attributes(
                operation="get_for_run",
                pipeline=pipeline_name,
                **{"bioetl.run_id": run_id},
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            checkpoint = await get_checkpoint_for_run_impl(
                self,
                pipeline_name=pipeline_name,
                run_id=run_id,
                start_time=start_time,
            )
            self._set_trace_result(
                span,
                success=True,
                attributes={CHECKPOINT_FOUND_ATTR: checkpoint is not None},
            )
            return checkpoint

    async def get_checkpoint_for_manifest_id(
        self,
        pipeline_name: str,
        manifest_id: str,
    ) -> CheckpointInfo | None:
        """Get immutable checkpoint evidence for one specific manifest_id."""
        self.logger.debug(
            "Getting checkpoint for manifest",
            pipeline=pipeline_name,
            manifest_id=manifest_id,
        )
        start_time = perf_counter()
        if self.tracer is None:
            return await get_checkpoint_for_manifest_id_impl(
                self,
                pipeline_name=pipeline_name,
                manifest_id=manifest_id,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "checkpoint.get_for_manifest_id",
            self._trace_attributes(
                operation="get_for_manifest_id",
                pipeline=pipeline_name,
                **{"bioetl.manifest_id": manifest_id},
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            checkpoint = await get_checkpoint_for_manifest_id_impl(
                self,
                pipeline_name=pipeline_name,
                manifest_id=manifest_id,
                start_time=start_time,
            )
            self._set_trace_result(
                span,
                success=True,
                attributes={CHECKPOINT_FOUND_ATTR: checkpoint is not None},
            )
            return checkpoint

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
            return await delete_checkpoint_impl(
                self,
                pipeline_name=pipeline_name,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "checkpoint.delete",
            self._trace_attributes(operation="delete", pipeline=pipeline_name),
            tracer_name=self.TRACER_NAME,
        ) as span:
            deleted = await delete_checkpoint_impl(
                self,
                pipeline_name=pipeline_name,
                start_time=start_time,
            )
            self._set_trace_result(
                span,
                success=True,
                attributes={"bioetl.checkpoint_deleted": deleted},
            )
            return deleted

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.checkpoint_port.aclose()
