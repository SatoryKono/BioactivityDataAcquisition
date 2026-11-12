"""Every quarantine HTTP reader shares the forensic request budget."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from bioetl.interfaces.http.health_server import HealthServer
from bioetl.interfaces.http._health_server_quarantine_routing import (
    dispatch_quarantine_request,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suffix",
    [
        "filtered-records",
        "filtered-stats",
        "filter-options",
        "filtered-timeseries",
        "filtered-record/hash",
    ],
)
async def test_saturated_capacity_rejects_without_backend_read(suffix):
    service = MagicMock()
    service.list_filtered_records = AsyncMock()
    service.get_filtered_record = AsyncMock()
    service.get_filtered_stats = AsyncMock()
    service.get_filtered_timeseries = AsyncMock()
    service.get_filtered_filter_options = AsyncMock()
    server = HealthServer(quarantine_service=service)
    server._forensic_endpoint_limiter = asyncio.Semaphore(0)
    server._send_payload_response = AsyncMock()
    await dispatch_quarantine_request(
        server,
        writer=MagicMock(),
        path="/ops/quarantine/" + suffix,
        query={"pipeline": "audit"},
    )
    assert server._send_payload_response.await_args.args[1] == 503
    assert all(
        getattr(service, name).await_count == 0
        for name in [
            "list_filtered_records",
            "get_filtered_record",
            "get_filtered_stats",
            "get_filtered_timeseries",
            "get_filtered_filter_options",
        ]
    )
