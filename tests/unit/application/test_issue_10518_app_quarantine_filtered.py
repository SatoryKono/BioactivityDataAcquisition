"""Stream B APP: leftover filtered quarantine operator-error branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.quality._quarantine_service_filtered_mixin import (
    QuarantineServiceFilteredMixin,
)

pytestmark = pytest.mark.unit


class _Host(QuarantineServiceFilteredMixin):
    TRACER_NAME = "test"

    def __init__(self) -> None:
        self.logger = MagicMock()
        self.quarantine_port = SimpleNamespace()
        self.run_manifest_service = None
        self.tracer = None
        self._metrics: list[str] = []

    def _record_operator_metrics(
        self,
        *,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        self._metrics.append(f"{operation}:{status}")

    def _trace_attributes(self, **_k: object) -> dict[str, object]:
        return {}


@pytest.mark.asyncio
async def test_filtered_operator_errors_record_failed() -> None:
    host = _Host()
    host.quarantine_port.list_filtered_records = AsyncMock(
        side_effect=RuntimeError("x")
    )
    host.quarantine_port.get_filtered_record = AsyncMock(side_effect=RuntimeError("x"))
    host.quarantine_port.get_filtered_stats = AsyncMock(side_effect=RuntimeError("x"))
    host.quarantine_port.get_filtered_filter_options = AsyncMock(
        side_effect=RuntimeError("x")
    )
    host.quarantine_port.get_filtered_timeseries = AsyncMock(
        side_effect=RuntimeError("x")
    )
    with pytest.raises(RuntimeError):
        await host.list_filtered_records(pipeline="p")
    with pytest.raises(RuntimeError):
        await host.get_filtered_record(payload_hash="h")
    with pytest.raises(RuntimeError):
        await host.get_filtered_stats(pipeline="p")
    with pytest.raises(RuntimeError):
        await host.get_filtered_filter_options(pipeline="p")
    with pytest.raises(RuntimeError):
        await host.get_filtered_timeseries(pipeline="p")
    assert host._metrics == [
        "filtered_list:failed",
        "filtered_get:failed",
        "filtered_stats:failed",
        "filtered_filter_options:failed",
        "filtered_timeseries:failed",
    ]


@pytest.mark.asyncio
async def test_filtered_get_none_records_not_found() -> None:
    host = _Host()
    host.quarantine_port.get_filtered_record = AsyncMock(return_value=None)
    assert await host.get_filtered_record(payload_hash="missing") is None
    assert "filtered_get:not_found" in host._metrics
