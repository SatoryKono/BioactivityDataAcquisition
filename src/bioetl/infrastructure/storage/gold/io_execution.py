"""Execution helpers for Gold merged writes."""

from __future__ import annotations

from time import perf_counter
from typing import cast

from bioetl.infrastructure.observability.metrics import (
    GOLD_VALIDATION_FAILURES_TOTAL,
    GOLD_WRITE_ATTEMPTS_TOTAL,
    GOLD_WRITE_DURATION_SECONDS,
    GOLD_WRITE_OUTCOMES_TOTAL,
)
from bioetl.infrastructure.storage.gold.io_helpers import (
    load_gold_writer_module as _load_gold_writer_module,
)
from bioetl.infrastructure.storage.gold.io_metrics import (
    _gold_merged_metric_labels,
    _gold_merged_validation_metric_labels,
)
from bioetl.infrastructure.storage.gold.io_preparation import (
    _GoldMergedWriteRequest,
    _PreparedGoldMergedWrite,
)
from bioetl.infrastructure.storage.gold.io_protocols import (
    _GoldMergedMetadataWriterProtocol,
    _GoldMergedWriteHostProtocol,
)

__all__ = [
    "_complete_gold_merged_write",
    "_execute_gold_merged_write",
    "_export_gold_merged_csv",
    "_write_gold_merged_delta",
    "_write_gold_merged_sidecar",
]


async def _write_gold_merged_delta(
    host: _GoldMergedWriteHostProtocol,
    prepared: _PreparedGoldMergedWrite,
) -> None:
    """Persist merged Gold table to Delta."""
    module = _load_gold_writer_module()
    await host._run_in_executor(
        lambda: module.write_deltalake(
            prepared.table_path,
            prepared.arrow_table,
            mode="overwrite",
            schema_mode="overwrite",
        )
    )


async def _export_gold_merged_csv(
    host: _GoldMergedWriteHostProtocol,
    prepared: _PreparedGoldMergedWrite,
) -> None:
    """Export merged Gold table to CSV when exporter is configured."""
    if host.csv_exporter:
        await host.csv_exporter.export(
            prepared.request.table_name,
            prepared.arrow_table,
            append=False,
        )


async def _write_gold_merged_sidecar(
    host: _GoldMergedWriteHostProtocol,
    prepared: _PreparedGoldMergedWrite,
) -> None:
    """Write merged Gold metadata sidecar after data write completes."""
    metadata_writer = cast(_GoldMergedMetadataWriterProtocol, host)
    await metadata_writer._write_gold_merged_metadata(
        table_path=prepared.table_path,
        table_name=prepared.request.table_name,
        records=prepared.request.records,
        completed_at=prepared.request.completed_at,
        run_id=prepared.request.run_id,
        schema=prepared.request.schema,
    )


async def _complete_gold_merged_write(
    host: _GoldMergedWriteHostProtocol,
    prepared: _PreparedGoldMergedWrite,
) -> None:
    """Run Delta write plus post-write side effects for merged Gold."""
    await _write_gold_merged_delta(host, prepared)
    await _export_gold_merged_csv(host, prepared)
    await _write_gold_merged_sidecar(host, prepared)


async def _execute_gold_merged_write(
    host: _GoldMergedWriteHostProtocol,
    request: _GoldMergedWriteRequest,
) -> None:
    """Prepare, log, and execute one merged Gold write request."""
    from bioetl.infrastructure.storage.gold.io_preparation import (
        _log_prepared_gold_merged_write,
        _prepare_gold_merged_write,
    )

    started_at = perf_counter()
    terminal_status = "failure"
    GOLD_WRITE_ATTEMPTS_TOTAL.labels(
        **_gold_merged_metric_labels(request.table_name)
    ).inc()
    try:
        prepared = await _prepare_gold_merged_write(host, request)
        _log_prepared_gold_merged_write(host, prepared)
        await _complete_gold_merged_write(host, prepared)
        terminal_status = "success"
    except ValueError as error:
        terminal_status = "validation_failure"
        GOLD_VALIDATION_FAILURES_TOTAL.labels(
            **_gold_merged_validation_metric_labels(request.table_name, error)
        ).inc()
        raise
    finally:
        GOLD_WRITE_OUTCOMES_TOTAL.labels(
            **_gold_merged_metric_labels(
                request.table_name,
                status=terminal_status,
            )
        ).inc()
        GOLD_WRITE_DURATION_SECONDS.labels(
            **_gold_merged_metric_labels(
                request.table_name,
                status=terminal_status,
            )
        ).observe(perf_counter() - started_at)
