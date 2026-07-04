"""Result-finalization helpers for canonical Silver metadata writes."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import timedelta

from deltalake import DeltaTable

from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.delta.table_ops import (
    normalize_delta_filesystem_path,
)
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_operation_protocols import (
    _SilverWriteFinalizationHostProtocol,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverWriteFinalizationContext,
)

__all__ = [
    "_build_silver_write_result",
    "_prepare_silver_write_finalization_context",
    "_read_delta_version",
]


def _build_silver_write_result(
    *, table_name: str, table_path: str, version_after: int | None, records_count: int
) -> SilverWriteResult | None:
    return (
        None
        if version_after is None
        else SilverWriteResult(table_name, table_path, version_after, records_count)
    )


def _read_delta_version(table_path: str) -> int:
    """Read the current Delta table version synchronously."""
    return DeltaTable(normalize_delta_filesystem_path(table_path)).version()


async def _prepare_silver_write_finalization_context(
    host: _SilverWriteFinalizationHostProtocol,
    request: _SilverWriteFinalizationPreparationRequest,
    *,
    perf_counter: Callable[[], float] = time.perf_counter,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare DQ/version/timing context before Silver metadata persistence."""
    dq_metrics = await host._compute_dq_metrics(
        request.table_name,
        request.records,
        quarantined_count=request.quarantined_count or 0,
        validation_errors=request.validation_errors,
    )
    version_after = await host._get_delta_version(request.table_path)
    completed_at = request.started_at + timedelta(
        seconds=perf_counter() - request.start_perf
    )
    return _PreparedSilverWriteFinalizationContext(
        dq_metrics=dq_metrics,
        version_after=version_after,
        completed_at=completed_at,
    )
