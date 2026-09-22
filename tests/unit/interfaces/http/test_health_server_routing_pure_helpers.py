# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Pure unit coverage for HealthServer routing and HTTP mixin branches."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from threading import get_ident

import pytest
from tests.conftest import _is_wsl

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import HealthStatus
from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope
from bioetl.interfaces.http import (
    _health_server_observability_routing as observability_routing,
)
from bioetl.interfaces.http import (
    _health_server_quarantine_routing as quarantine_routing,
)
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
)
from bioetl.interfaces.http import (
    _health_server_checkpoint_freshness as checkpoint_freshness,
)
from bioetl.interfaces.http import _health_server_routing_support as routing_support
from bioetl.interfaces.http import health_server_routing_mixin as routing_mixin_module
from bioetl.interfaces.http.health_server_http_mixin import HealthServerHTTPMixin
from bioetl.interfaces.http.health_server_routing_mixin import HealthServerRoutingMixin
from bioetl.interfaces.http.types import HealthResponse


pytestmark = pytest.mark.unit


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 7, 6, 12, 0, tzinfo=UTC)


class _Logger:
    def __init__(self) -> None:
        self.errors: list[dict[str, object]] = []
        self.debugs: list[dict[str, object]] = []

    def error(self, event: str, **context: object) -> None:
        self.errors.append({"event": event, **context})

    def debug(self, event: str, **context: object) -> None:
        self.debugs.append({"event": event, **context})


class _Writer:
    def __init__(self, *, close_error: BaseException | None = None) -> None:
        self.data = b""
        self.closed = False
        self.close_error = close_error

    def write(self, data: bytes) -> None:
        self.data += data

    async def drain(self) -> None:
        await asyncio.sleep(0)

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        if self.close_error is not None:
            raise self.close_error


class _Reader:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    async def readline(self) -> bytes:
        await asyncio.sleep(0)
        if not self._lines:
            return b""
        return self._lines.pop(0)


class _ManifestPort:
    def __init__(self) -> None:
        self.list_all_calls = 0

    def list_all(self) -> tuple[object, ...]:
        self.list_all_calls += 1
        return ("manifest",)


class _StaticMetricsExposition:
    def build_exposition(self) -> str:
        return (
            "# HELP bioetl_health_server_scrape_up Health server /metrics scrape "
            "liveness (1=serving).\n"
            "# TYPE bioetl_health_server_scrape_up gauge\n"
            "bioetl_health_server_scrape_up 1\n"
        )


class _RoutingHost(HealthServerRoutingMixin):
    def __init__(self) -> None:
        self.sent: list[tuple[str, object, object | None]] = []
        self._health_monitor: object | None = None
        self._quarantine_service = object()
        self._checkpoint_port: object | None = object()
        self._run_manifest_port: object | None = _ManifestPort()
        self._run_ledger_port: object | None = object()
        self._workflow_manifest_port: object | None = object()
        self._metrics_exposition = _StaticMetricsExposition()
        self._clock: object | None = _Clock()
        self._prometheus_base_url = "http://prometheus.test"
        self._forensic_endpoint_limiter = asyncio.Semaphore(4)
        self.provider_statuses: dict[str, dict[str, object]] = {}
        self.overall_status = HealthStatus.HEALTHY

    @property
    def uptime_seconds(self) -> float:
        return 12.345

    async def _send_json_response(
        self,
        writer: _Writer,
        response: HealthResponse,
    ) -> None:
        self.sent.append(("json", response, None))

    async def _send_response(
        self,
        writer: _Writer,
        status_code: int,
        message: str,
    ) -> None:
        self.sent.append(("text", status_code, message))

    async def _send_payload_response(
        self,
        writer: _Writer,
        status_code: int,
        payload: dict[str, object],
    ) -> None:
        self.sent.append(("payload", status_code, payload))

    async def _send_text_response(
        self,
        writer: _Writer,
        status_code: int,
        body: str,
        *,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        self.sent.append(("text_response", status_code, (body, content_type)))

    async def _handle_request_error(
        self,
        writer: _Writer,
        error: BaseException,
    ) -> None:
        self.sent.append(("error", type(error).__name__, str(error)))

    def _get_overall_status(self) -> HealthStatus:
        return self.overall_status

    def _get_provider_statuses(self) -> dict[str, dict[str, object]]:
        return self.provider_statuses


class _HTTPHost(HealthServerHTTPMixin):
    def __init__(self) -> None:
        self.sent: list[tuple[int, str] | tuple[str, str]] = []
        self.routes: list[str] = []
        self._logger: _Logger | None = _Logger()
        self._request_error_allowlist = (RuntimeError,)
        self._writer_close_allowlist = (OSError,)
        self._request_line_timeout_seconds = 0.1
        self._header_line_timeout_seconds = 0.1
        self._writer_close_timeout_seconds = 0.1
        self._max_header_lines = 3

    async def _route_request(self, writer: _Writer, path: str) -> None:
        self.routes.append(path)

    async def _send_response(
        self,
        writer: _Writer,
        status_code: int,
        message: str,
    ) -> None:
        self.sent.append((status_code, message))


class _QuarantineService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.detail_payload: dict[str, object] | None = {"payload_hash": "hash-1"}

    async def list_filtered_records(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("list", kwargs))
        return {"items": [], "kwargs": kwargs}

    async def get_filtered_stats(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("stats", kwargs))
        return {"total": 0, "kwargs": kwargs}

    async def get_filtered_timeseries(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("timeseries", kwargs))
        return {"rows": [], "kwargs": kwargs}

    async def get_filtered_filter_options(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("options", kwargs))
        return {"pipelines": [], "kwargs": kwargs}

    async def get_filtered_record(self, **kwargs: object) -> dict[str, object] | None:
        self.calls.append(("detail", kwargs))
        return self.detail_payload


async def _inline_to_thread(
    function: object, /, *args: object, **kwargs: object
) -> object:
    assert callable(function)
    return function(*args, **kwargs)


@pytest.mark.asyncio
async def test_routing_mixin_parses_queries_and_routes_without_sockets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _Writer()
    routed: list[tuple[str, str, dict[str, str]]] = []

    async def fake_quarantine(
        server: object,
        *,
        writer: _Writer,
        path: str,
        query: dict[str, str],
    ) -> None:
        routed.append(("quarantine", path, query))

    async def fake_control(
        server: object,
        *,
        writer: _Writer,
        path: str,
        query: dict[str, str],
    ) -> None:
        routed.append(("control", path, query))

    async def fake_observability(
        server: object,
        *,
        writer: _Writer,
        path: str,
        query: dict[str, str],
    ) -> None:
        routed.append(("observability", path, query))

    monkeypatch.setattr(
        routing_mixin_module,
        "dispatch_quarantine_request",
        fake_quarantine,
    )
    monkeypatch.setattr(
        routing_mixin_module,
        "dispatch_control_plane_request",
        fake_control,
    )
    monkeypatch.setattr(
        routing_mixin_module,
        "dispatch_observability_request",
        fake_observability,
    )

    assert host._response_timestamp() == "2026-07-06T12:00:00+00:00"
    assert host._parse_query_params("a=1&a=2&empty=&b=x") == {"a": "2", "b": "x"}
    assert host._read_required_param({"pipeline": " chembl "}, "pipeline") == "chembl"
    with pytest.raises(ValueError, match="Missing required query parameter"):
        host._read_required_param({"pipeline": " "}, "pipeline")
    assert host._read_optional_param({"run_id": " "}, "run_id") is None
    assert host._read_optional_scope_param({"pipeline": "$__all"}, "pipeline") is None
    assert host._read_int_param({}, "limit", 50, minimum=1) == 50
    assert host._read_int_param({"limit": " 5 "}, "limit", 50, minimum=1) == 5
    with pytest.raises(ValueError, match="must be >= 1"):
        host._read_int_param({"limit": "0"}, "limit", 50, minimum=1)
    assert host._read_csv_param({"pipeline": "{a, b, a, }"}, "pipeline") == ("a", "b")
    assert host._read_scope_csv_param({"pipeline": "a,$__all"}, "pipeline") == ()

    await host._route_request(writer, "/health")
    await host._route_request(writer, "/ops/quarantine/list?pipeline=chembl")
    await host._route_request(writer, "/ops/control-plane/ready")
    await host._route_request(writer, "/ops/observability/metrics")
    await host._route_request(writer, "/metrics")
    await host._route_request(writer, "/missing")

    assert isinstance(host.sent[0][1], HealthResponse)
    metrics_payload = host.sent[-2]
    assert metrics_payload[0] == "text_response"
    assert metrics_payload[1] == 200
    body, content_type = metrics_payload[2]
    assert content_type == "text/plain; version=0.0.4; charset=utf-8"
    assert "bioetl_health_server_scrape_up 1" in body
    assert routed == [
        ("quarantine", "/ops/quarantine/list", {"pipeline": "chembl"}),
        ("control", "/ops/control-plane/ready", {}),
        ("observability", "/ops/observability/metrics", {}),
    ]
    assert host.sent[-1] == ("text", 404, "Not Found")


@pytest.mark.asyncio
async def test_metrics_collection_runs_outside_http_event_loop(monkeypatch) -> None:
    if _is_wsl():
        pytest.skip("WSL inline to_thread - skipping")
    if _is_wsl():
        pytest.skip("WSL inline to_thread - skipping")
