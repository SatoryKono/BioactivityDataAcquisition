"""Quarantine HTTP access must fail closed before reading records."""

from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from bioetl.interfaces.http.health_server import HealthServer

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "token,headers,expected",
    [
        (None, {}, 404),
        ("test-only-token", {}, 401),
        ("test-only-token", {"Authorization": "Bearer wrong"}, 401),
        (
            "test-only-token",
            [
                ("Authorization", "Bearer test-only-token"),
                ("authorization", "Bearer test-only-token"),
            ],
            401,
        ),
        ("test-only-token", {"Authorization": "Bearer test-only-token"}, 200),
    ],
)
async def test_detail_auth_precedes_backend_read(token, headers, expected):
    service = MagicMock()
    service.get_filtered_record = AsyncMock(
        return_value={"payload": {"synthetic": True}}
    )
    server = HealthServer(
        host="127.0.0.1",
        port=0,
        quarantine_service=service,
        quarantine_http_token=token,
    )
    await server.start()
    try:
        port = server._server.sockets[0].getsockname()[1]
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.get(
                f"http://127.0.0.1:{port}/ops/quarantine/filtered-record/test?pipeline=audit_test",
                headers=headers,
            )
            assert response.status_code == expected
            health = await client.get(f"http://127.0.0.1:{port}/health/live")
            assert health.status_code == 200
        assert service.get_filtered_record.await_count == (1 if expected == 200 else 0)
    finally:
        await server.stop()
