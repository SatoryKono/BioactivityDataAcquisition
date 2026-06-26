"""Result-finalization helpers for canonical Silver metadata writes."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import timedelta

from deltalake import DeltaTable

from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.finalization_models import (
    _coerce_silver_write_finalization_preparation_request,
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
    return DeltaTable(table_path).version()


async def _prepare_silver_write_finalization_context(
    host: _SilverWriteFinalizationHostProtocol,
    request: _SilverWriteFinalizationPreparationRequest | None = None,
    *args: object,
    perf_counter: Callable[[], float] = time.perf_counter,
    **kwargs: object,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare DQ/version/timing context before Silver metadata persistence."""
    resolved_request = _coerce_silver_write_finalization_preparation_request(
        request,
        args=args,
        kwargs=kwargs,
    )
    dq_metrics = await host._compute_dq_metrics(
        resolved_request.table_name,
        resolved_request.records,
        quarantined_count=resolved_request.quarantined_count or 0,
        validation_errors=resolved_request.validation_errors,
    )
    version_after = await host._get_delta_version(resolved_request.table_path)
    completed_at = resolved_request.started_at + timedelta(
        seconds=perf_counter() - resolved_request.start_perf
    )
    return _PreparedSilverWriteFinalizationContext(
        dq_metrics=dq_metrics,
        version_after=version_after,
        completed_at=completed_at,
    )
