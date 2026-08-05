"""Private runtime helpers for checkpoint admin service operations."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from bioetl.application.services.checkpoint._checkpoint_service_support import (
    _CHECKPOINT_OPERATOR_ERRORS,
)
from bioetl.application.services.checkpoint.checkpoint_models import CheckpointInfo
from bioetl.domain.ports import CheckpointPort, LoggerPort
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.domain.types import JsonDict


class _CheckpointServiceRuntimeHost(Protocol):
    @property
    def checkpoint_port(self) -> CheckpointPort: ...

    @property
    def logger(self) -> LoggerPort: ...

    def _record_operator_metrics(
        self,
        *,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None: ...

    def _checkpoint_info_from_data(
        self,
        *,
        pipeline_name: str,
        checkpoint_data: tuple[RunID, JsonDict],
    ) -> CheckpointInfo: ...


async def list_checkpoints_impl(
    host: _CheckpointServiceRuntimeHost,
    *,
    start_time: float,
) -> list[CheckpointInfo]:
    """List checkpoints and emit bounded observability signals."""
    try:
        pipeline_names = await host.checkpoint_port.list_all()
        checkpoints: list[CheckpointInfo] = []

        for pipeline_name in pipeline_names:
            checkpoint_data = await host.checkpoint_port.load(pipeline_name)
            if checkpoint_data is None:
                checkpoints.append(
                    CheckpointInfo(
                        pipeline_name=pipeline_name,
                        run_id=None,
                        metadata={},
                    )
                )
                continue

            checkpoints.append(
                host._checkpoint_info_from_data(
                    pipeline_name=pipeline_name,
                    checkpoint_data=checkpoint_data,
                )
            )

        host.logger.info(
            "Listed checkpoints",
            checkpoint_count=len(checkpoints),
        )
        host._record_operator_metrics(
            operation="list",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return checkpoints
    except _CHECKPOINT_OPERATOR_ERRORS:
        host._record_operator_metrics(
            operation="list",
            status="failed",
            duration_seconds=perf_counter() - start_time,
        )
        raise


async def get_checkpoint_impl(
    host: _CheckpointServiceRuntimeHost,
    *,
    pipeline_name: str,
    start_time: float,
) -> CheckpointInfo | None:
    """Get a checkpoint and emit bounded observability signals."""
    try:
        checkpoint_data = await host.checkpoint_port.load(pipeline_name)
        if checkpoint_data is None:
            host.logger.debug("Checkpoint not found", pipeline=pipeline_name)
            host._record_operator_metrics(
                operation="get",
                status="missing",
                duration_seconds=perf_counter() - start_time,
            )
            return None

        run_id, _ = checkpoint_data
        host.logger.info(
            "Got checkpoint",
            pipeline=pipeline_name,
            run_id=str(run_id),
        )
        host._record_operator_metrics(
            operation="get",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return host._checkpoint_info_from_data(
            pipeline_name=pipeline_name,
            checkpoint_data=checkpoint_data,
        )
    except _CHECKPOINT_OPERATOR_ERRORS:
        host._record_operator_metrics(
            operation="get",
            status="failed",
            duration_seconds=perf_counter() - start_time,
        )
        raise


async def get_checkpoint_for_run_impl(
    host: _CheckpointServiceRuntimeHost,
    *,
    pipeline_name: str,
    run_id: str,
    start_time: float,
) -> CheckpointInfo | None:
    """Get immutable checkpoint evidence by run_id."""
    try:
        checkpoint_data = await host.checkpoint_port.load_for_run(
            pipeline_name,
            RunID(UUID(run_id)),
        )
        if checkpoint_data is None:
            host.logger.debug(
                "Checkpoint not found for run",
                pipeline=pipeline_name,
                run_id=run_id,
            )
            host._record_operator_metrics(
                operation="get_for_run",
                status="missing",
                duration_seconds=perf_counter() - start_time,
            )
            return None

        host.logger.info(
            "Got checkpoint for run",
            pipeline=pipeline_name,
            run_id=run_id,
        )
        host._record_operator_metrics(
            operation="get_for_run",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return host._checkpoint_info_from_data(
            pipeline_name=pipeline_name,
            checkpoint_data=checkpoint_data,
        )
    except _CHECKPOINT_OPERATOR_ERRORS:
        host._record_operator_metrics(
            operation="get_for_run",
            status="failed",
            duration_seconds=perf_counter() - start_time,
        )
        raise


async def get_checkpoint_for_manifest_id_impl(
    host: _CheckpointServiceRuntimeHost,
    *,
    pipeline_name: str,
    manifest_id: str,
    start_time: float,
) -> CheckpointInfo | None:
    """Get immutable checkpoint evidence by manifest_id."""
    try:
        checkpoint_data = await host.checkpoint_port.load_for_manifest_id(manifest_id)
        if checkpoint_data is None:
            host.logger.debug(
                "Checkpoint not found for manifest",
                pipeline=pipeline_name,
                manifest_id=manifest_id,
            )
            host._record_operator_metrics(
                operation="get_for_manifest_id",
                status="missing",
                duration_seconds=perf_counter() - start_time,
            )
            return None

        host.logger.info(
            "Got checkpoint for manifest",
            pipeline=pipeline_name,
            manifest_id=manifest_id,
        )
        host._record_operator_metrics(
            operation="get_for_manifest_id",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return host._checkpoint_info_from_data(
            pipeline_name=pipeline_name,
            checkpoint_data=checkpoint_data,
        )
    except _CHECKPOINT_OPERATOR_ERRORS:
        host._record_operator_metrics(
            operation="get_for_manifest_id",
            status="failed",
            duration_seconds=perf_counter() - start_time,
        )
        raise


async def delete_checkpoint_impl(
    host: _CheckpointServiceRuntimeHost,
    *,
    pipeline_name: str,
    start_time: float,
) -> bool:
    """Delete a checkpoint and emit bounded observability signals."""
    try:
        existing = await host.checkpoint_port.load(pipeline_name)
        if existing is None:
            host.logger.debug(
                "Checkpoint not found for deletion", pipeline=pipeline_name
            )
            host._record_operator_metrics(
                operation="delete",
                status="missing",
                duration_seconds=perf_counter() - start_time,
            )
            return False

        await host.checkpoint_port.delete(pipeline_name)
        host.logger.info("Deleted checkpoint", pipeline=pipeline_name)
        host._record_operator_metrics(
            operation="delete",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return True
    except _CHECKPOINT_OPERATOR_ERRORS:
        host._record_operator_metrics(
            operation="delete",
            status="failed",
            duration_seconds=perf_counter() - start_time,
        )
        raise
