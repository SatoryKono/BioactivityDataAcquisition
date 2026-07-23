"""Pure unit coverage for HealthServer routing and HTTP mixin branches."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.interfaces.http import (
    _health_server_observability_routing as observability_routing,
)
from bioetl.interfaces.http import (
    _health_server_quarantine_routing as quarantine_routing,
)
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
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


class _RoutingHost(HealthServerRoutingMixin):
    def __init__(self) -> None:
        self.sent: list[tuple[str, object, object | None]] = []
        self._health_monitor: object | None = None
        self._quarantine_service = object()
        self._checkpoint_port: object | None = object()
        self._run_manifest_port: object | None = _ManifestPort()
        self._run_ledger_port: object | None = object()
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
    assert host.sent[-2] == (
        "text_response",
        200,
        (
            "# BioETL health server scrape endpoint\n",
            "text/plain; version=0.0.4; charset=utf-8",
        ),
    )
    assert routed == [
        ("quarantine", "/ops/quarantine/list", {"pipeline": "chembl"}),
        ("control", "/ops/control-plane/ready", {}),
        ("observability", "/ops/observability/metrics", {}),
    ]
    assert host.sent[-1] == ("text", 404, "Not Found")


@pytest.mark.asyncio
async def test_routing_mixin_health_handlers_cover_monitor_states() -> None:
    host = _RoutingHost()

    health = await host._handle_health()
    assert health.status == "healthy"
    assert health.checks["server"]["uptime_seconds"] == 12.35

    ready_without_monitor = await host._handle_readiness()
    assert ready_without_monitor.status == "healthy"
    assert ready_without_monitor.checks == {"message": "No health monitor configured"}
    providers_without_monitor = await host._handle_providers()
    assert providers_without_monitor.checks == {
        "message": "No health monitor configured"
    }

    host._health_monitor = object()
    host.provider_statuses = {
        "chembl": {"status": "healthy"},
        "pubchem": {"status": "unhealthy"},
    }
    ready_unhealthy = await host._handle_readiness()
    assert ready_unhealthy.status == "unhealthy"
    host.provider_statuses = {"chembl": {"status": "healthy"}}
    ready_healthy = await host._handle_readiness()
    assert ready_healthy.status == "healthy"
    host.overall_status = HealthStatus.DEGRADED
    providers = await host._handle_providers()
    assert providers.status == "degraded"
    health_with_monitor = await host._handle_health()
    assert "providers" in health_with_monitor.checks


@pytest.mark.asyncio
async def test_routing_support_dispatches_control_plane_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _Writer()

    host._run_manifest_port = None
    await routing_support.dispatch_control_plane_request(
        host,
        writer=writer,
        path="/ops/control-plane/ready",
        query={},
    )
    assert host.sent[-1] == (
        "text",
        503,
        "Control-plane selector catalog unavailable",
    )

    host._run_manifest_port = _ManifestPort()
    host._data_root = "/audit-root"
    await routing_support.dispatch_control_plane_request(
        host,
        writer=writer,
        path="/ops/control-plane/ready",
        query={},
    )
    assert host.sent[-1] == (
        "payload",
        200,
        {
            "run_manifest_port": True,
            "run_ledger_port": True,
            "workflow_manifest_port": False,
            "checkpoint_port": True,
            "data_root": "/audit-root",
        },
    )

    async def fake_identity_table(*_args: object, **_kwargs: object) -> None:
        host.sent.append(("identity_table", None, None))

    async def fake_identity_evidence(*_args: object, **_kwargs: object) -> None:
        host.sent.append(("identity_evidence", None, None))

    monkeypatch.setattr(
        routing_support,
        "handle_control_plane_identity_table",
        fake_identity_table,
    )
    monkeypatch.setattr(
        routing_support,
        "handle_control_plane_identity_evidence",
        fake_identity_evidence,
    )

    await routing_support.dispatch_control_plane_request(
        host,
        writer=writer,
        path="/ops/control-plane/identity-table",
        query={},
    )
    await routing_support.dispatch_control_plane_request(
        host,
        writer=writer,
        path="/ops/control-plane/identity-evidence",
        query={},
    )
    await routing_support.dispatch_control_plane_request(
        host,
        writer=writer,
        path="/ops/control-plane/missing",
        query={},
    )
    await routing_support.dispatch_control_plane_request(
        host,
        writer=writer,
        path="/ops/control-plane/filter-options",
        query={},
    )

    assert ("identity_table", None, None) in host.sent
    assert ("identity_evidence", None, None) in host.sent
    assert host.sent[-2] == ("text", 404, "Not Found")
    assert host.sent[-1] == (
        "text",
        400,
        "Missing required query parameter: pipeline",
    )


@pytest.mark.asyncio
async def test_routing_support_filter_options_and_selector_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _Writer()
    monkeypatch.setattr(routing_support.asyncio, "to_thread", _inline_to_thread)

    def fake_filter_payload(**kwargs: object) -> dict[str, object]:
        return {"items": ["-", "run-2"], "kwargs": kwargs}

    def fake_context_payload(**kwargs: object) -> dict[str, object]:
        return {"context_kwargs": kwargs}

    monkeypatch.setattr(
        routing_support,
        "build_selector_filter_options_payload",
        fake_filter_payload,
    )
    monkeypatch.setattr(
        routing_support,
        "build_selector_context_payload",
        fake_context_payload,
    )

    await routing_support.handle_control_plane_filter_options(
        host,
        writer,
        {
            "pipeline": "chembl_activity",
            "workflow": "wf-a",
            "run_type": "incremental",
            "run_status": "success",
            "exact_run_only": "yes",
            "fallback_value": "run-fallback",
        },
    )
    payload = host.sent[-1][2]
    assert isinstance(payload, dict)
    assert payload["run_ids"] == ["run-2"]
    assert payload["kwargs"]["requested_pipeline"] == "chembl_activity"
    assert payload["kwargs"]["exact_run_only"] is True
    assert routing_support._read_truthy_query_param({}, "exact_run_only") is False
    assert (
        routing_support._read_truthy_query_param(
            {"exact_run_only": " false "},
            "exact_run_only",
        )
        is False
    )

    await routing_support.handle_control_plane_filter_options(
        host,
        writer,
        {
            "dimension": "pipeline",
            "pipeline": "$__all",
            "response_shape": "list",
        },
    )
    list_payload = host.sent[-1][2]
    assert isinstance(list_payload, dict)
    assert "run_ids" not in list_payload
    assert list_payload["kwargs"]["requested_pipeline"] == "$__all"

    await routing_support.handle_control_plane_selector_context(
        host,
        writer,
        {"pipeline": "chembl_activity", "run_id": "-"},
    )
    context_payload = host.sent[-1][2]
    assert isinstance(context_payload, dict)
    assert context_payload["context_kwargs"]["selected_run_id"] is None


@pytest.mark.asyncio
async def test_routing_support_checkpoint_freshness_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _Writer()
    monkeypatch.setattr(routing_support.asyncio, "to_thread", _inline_to_thread)
    host._checkpoint_port = None

    await routing_support.handle_control_plane_checkpoint_freshness(
        host,
        writer,
        {"pipeline": "chembl_activity"},
    )
    assert host.sent[-1][1] == 200
    assert host.sent[-1][2]["evidence_source"] == "checkpoint_port_missing"

    host._checkpoint_port = object()
    scope = SimpleNamespace(
        requested_pipeline="chembl_activity",
        resolved_manifest=None,
        resolved_via="selected_run_id",
    )
    monkeypatch.setattr(
        routing_support,
        "resolve_control_plane_identity_scope",
        lambda *_args, **_kwargs: scope,
    )

    for evidence, expected_source in (
        ((None, "scope", None, True), "aggregate_scope_requires_exact_pipeline"),
        ((None, "missing", "manifest-1", False), "missing"),
        (
            (("run-1", {"manifest_id": "manifest-2"}), "metadata", None, False),
            "metadata",
        ),
        (
            (
                ("run-1", {"checkpoint_saved_at_epoch_seconds": 1_786_000_000}),
                "checkpoint",
                "manifest-3",
                False,
            ),
            "checkpoint",
        ),
    ):

        async def fake_load_checkpoint_freshness_evidence(
            *_args: object,
            _evidence: object = evidence,
            **_kwargs: object,
        ) -> object:
            return _evidence

        monkeypatch.setattr(
            routing_support,
            "load_checkpoint_freshness_evidence",
            fake_load_checkpoint_freshness_evidence,
        )
        await routing_support.handle_control_plane_checkpoint_freshness(
            host,
            writer,
            {"pipeline": "chembl_activity"},
        )
        assert host.sent[-1][1] == 200
        assert host.sent[-1][2]["evidence_source"] == expected_source

    resolved_scope = SimpleNamespace(
        requested_pipeline="ignored",
        resolved_manifest=SimpleNamespace(pipeline_name="pubchem_compound"),
        resolved_via="latest_manifest",
    )
    assert routing_support._resolved_scope_pipeline(scope) == "chembl_activity"
    assert (
        routing_support._resolved_scope_pipeline(resolved_scope) == "pubchem_compound"
    )


@pytest.mark.asyncio
async def test_quarantine_routing_dispatches_filtered_explorer_branches() -> None:
    host = _RoutingHost()
    writer = _Writer()

    host._quarantine_service = None
    await quarantine_routing.dispatch_quarantine_request(
        host,
        writer=writer,
        path="/ops/quarantine/filtered-records",
        query={"pipeline": "chembl_activity"},
    )
    assert host.sent[-1] == (
        "payload",
        503,
        {
            "contract": "forensic_endpoint_error_v1",
            "status": "unavailable",
            "endpoint": "filtered-records",
            "reason": "backend_unavailable",
            "retryable": True,
        },
    )

    service = _QuarantineService()
    host._quarantine_service = service
    common_query = {
        "pipeline": "chembl_activity",
        "run_type": "incremental",
        "reason_code": "missing",
        "field": "canonical_smiles",
        "run_id": "run-1",
        "payload_hash": "hash-1",
        "from": "2026-07-06T00:00:00Z",
        "to": "2026-07-06T01:00:00Z",
    }
    await quarantine_routing.dispatch_quarantine_request(
        host,
        writer=writer,
        path="/ops/quarantine/filtered-records",
        query={**common_query, "limit": "5", "offset": "2", "sort": "ingestion_ts_asc"},
    )
    assert service.calls[-1] == (
        "list",
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "reason_code": "missing",
            "field": "canonical_smiles",
            "run_id": "run-1",
            "payload_hash": "hash-1",
            "from_ts": "2026-07-06T00:00:00Z",
            "to_ts": "2026-07-06T01:00:00Z",
            "limit": 5,
            "offset": 2,
            "sort": "ingestion_ts_asc",
        },
    )

    for path, expected_call in (
        ("/ops/quarantine/filtered-stats", "stats"),
        ("/ops/quarantine/filtered-timeseries", "timeseries"),
        ("/ops/quarantine/filter-options", "options"),
    ):
        await quarantine_routing.dispatch_quarantine_request(
            host,
            writer=writer,
            path=path,
            query=common_query,
        )
        assert service.calls[-1][0] == expected_call
        assert host.sent[-1][0] == "payload"
        assert host.sent[-1][1] == 200

    assert service.calls[-2][1]["bucket"] == "1h"
    await quarantine_routing.dispatch_quarantine_request(
        host,
        writer=writer,
        path="/ops/quarantine/filtered-timeseries",
        query={**common_query, "bucket": "1d"},
    )
    assert service.calls[-1][1]["bucket"] == "1d"

    await quarantine_routing.dispatch_quarantine_request(
        host,
        writer=writer,
        path="/ops/quarantine/filtered-record/hash%201",
        query={"pipeline": "chembl_activity"},
    )
    assert service.calls[-1] == (
        "detail",
        {"payload_hash": "hash 1", "pipeline": "chembl_activity"},
    )
    assert host.sent[-1] == ("payload", 200, {"payload_hash": "hash-1"})

    service.detail_payload = None
    await quarantine_routing.dispatch_quarantine_request(
        host,
        writer=writer,
        path="/ops/quarantine/filtered-record/hash-2",
        query={"pipeline": "chembl_activity"},
    )
    assert host.sent[-1] == ("text", 404, "Not Found")

    await quarantine_routing.dispatch_quarantine_request(
        host,
        writer=writer,
        path="/ops/quarantine/filtered-record/",
        query={"pipeline": "chembl_activity"},
    )
    assert host.sent[-1] == ("text", 400, "Missing payload_hash in path")
    await quarantine_routing.dispatch_quarantine_request(
        host,
        writer=writer,
        path="/ops/quarantine/missing",
        query={"pipeline": "chembl_activity"},
    )
    assert host.sent[-1] == ("text", 404, "Not Found")
    await quarantine_routing.dispatch_quarantine_request(
        host,
        writer=writer,
        path="/ops/quarantine/filtered-stats",
        query={},
    )
    assert host.sent[-1] == (
        "text",
        400,
        "Missing required query parameter: pipeline",
    )


@pytest.mark.asyncio
async def test_filtered_stats_deadline_returns_typed_504(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    host._quarantine_service = _QuarantineService()
    writer = _Writer()

    async def deadline(**_kwargs: object) -> object:
        raise ForensicEndpointUnavailable(
            reason="deadline_exceeded",
            status_code=504,
        )

    monkeypatch.setattr(
        quarantine_routing,
        "run_bounded_forensic_operation",
        deadline,
    )

    await quarantine_routing.dispatch_quarantine_request(
        host,
        writer=writer,
        path="/ops/quarantine/filtered-stats",
        query={"pipeline": "chembl_activity"},
    )

    assert host.sent[-1] == (
        "payload",
        504,
        {
            "contract": "forensic_endpoint_error_v1",
            "status": "unavailable",
            "endpoint": "filtered-stats",
            "reason": "deadline_exceeded",
            "retryable": True,
        },
    )


@pytest.mark.asyncio
async def test_processed_records_distinguishes_empty_and_backend_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _Writer()
    empty_payload = {"contract": "processed_records_table_v1", "rows": []}
    monkeypatch.setattr(
        observability_routing,
        "build_processed_records_table_payload_from_prometheus",
        lambda **_kwargs: empty_payload,
    )

    await observability_routing.dispatch_observability_request(
        host,
        writer=writer,
        path="/ops/observability/processed-records",
        query={"pipeline": "chembl_activity"},
    )
    assert host.sent[-1] == ("payload", 200, empty_payload)

    def unavailable(**_kwargs: object) -> dict[str, object]:
        raise RuntimeError("Prometheus unavailable")

    monkeypatch.setattr(
        observability_routing,
        "build_processed_records_table_payload_from_prometheus",
        unavailable,
    )
    await observability_routing.dispatch_observability_request(
        host,
        writer=writer,
        path="/ops/observability/processed-records",
        query={"pipeline": "chembl_activity"},
    )
    assert host.sent[-1] == (
        "payload",
        503,
        {
            "contract": "forensic_endpoint_error_v1",
            "status": "unavailable",
            "endpoint": "processed-records",
            "reason": "backend_unavailable",
            "retryable": True,
        },
    )


@pytest.mark.asyncio
async def test_pipeline_run_report_route_returns_versioned_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _Writer()
    payload = {"schema_version": "pipeline_run_report_v1", "identity": {}}
    monkeypatch.setattr(
        observability_routing,
        "load_pipeline_run_report_payload",
        lambda **_kwargs: payload,
    )

    await observability_routing.dispatch_observability_request(
        host,
        writer=writer,
        path="/ops/observability/pipeline-run-report",
        query={"pipeline": "chembl_activity", "run_id": "run-1"},
    )

    assert host.sent[-1] == ("payload", 200, payload)


@pytest.mark.asyncio
async def test_pipeline_run_report_route_requires_pipeline_selector() -> None:
    host = _RoutingHost()
    writer = _Writer()

    await observability_routing.dispatch_observability_request(
        host,
        writer=writer,
        path="/ops/observability/pipeline-run-report",
        query={"run_id": "run-1"},
    )

    assert host.sent[-1] == (
        "text",
        400,
        "Missing required query parameter: pipeline",
    )


@pytest.mark.asyncio
async def test_http_mixin_processes_requests_responses_and_close_errors() -> None:
    host = _HTTPHost()
    writer = _Writer()

    assert host._parse_request_line(b"GET /health HTTP/1.1\r\n") == ("GET", "/health")
    assert host._parse_request_line(b"GET\r\n") == (None, None)

    await host._process_request(_Reader([]), writer)
    await host._process_request(_Reader([b"BAD\r\n"]), writer)
    await host._process_request(
        _Reader([b"POST /health HTTP/1.1\r\n", b"\r\n"]), writer
    )
    await host._process_request(_Reader([b"GET /health HTTP/1.1\r\n", b"\r\n"]), writer)
    assert host.sent == [(400, "Bad Request"), (405, "Method Not Allowed")]
    assert host.routes == ["/health"]

    with pytest.raises(ValueError, match="Too many request headers"):
        await host._consume_headers(
            _Reader(
                [
                    b"Header-1: value\r\n",
                    b"Header-2: value\r\n",
                    b"Header-3: value\r\n",
                ]
            )
        )

    await host._handle_request_error(writer, RuntimeError("boom"))
    assert host.sent[-1] == (500, "Internal Server Error")
    assert host._logger is not None
    assert host._logger.errors[-1]["reason_code"] == "HEALTH_REQUEST_PROCESSING_FAILED"

    timeout_writer = _Writer(close_error=TimeoutError("slow close"))
    await host._close_writer(timeout_writer)
    assert host._logger.debugs[-1]["reason_code"] == "HEALTH_WRITER_CLOSE_TIMEOUT"
    os_error_writer = _Writer(close_error=OSError("closed"))
    await host._close_writer(os_error_writer)
    assert host._logger.debugs[-1]["reason_code"] == "HEALTH_WRITER_CLOSE_FAILED"


@pytest.mark.asyncio
async def test_http_mixin_serializes_payload_responses() -> None:
    host = HealthServerHTTPMixin()
    writer = _Writer()

    await host._send_json_response(
        writer,
        HealthResponse(status="unhealthy", timestamp="2026-07-06T00:00:00Z"),
    )
    assert writer.data.startswith(b"HTTP/1.1 503 Service Unavailable")

    writer = _Writer()
    await host._send_payload_response(writer, 299, {"ok": True})
    assert writer.data.startswith(b"HTTP/1.1 299 OK")
    assert b'"ok": true' in writer.data

    writer = _Writer()
    await host._send_response(writer, 404, "Not Found")
    assert writer.data.startswith(b"HTTP/1.1 404 Not Found")
    assert b'"error": "Not Found"' in writer.data


@pytest.mark.asyncio
async def test_http_mixin_serializes_text_responses() -> None:
    host = HealthServerHTTPMixin()
    writer = _Writer()

    await host._send_text_response(
        writer,
        200,
        "# scrape endpoint\n",
        content_type="text/plain; version=0.0.4; charset=utf-8",
    )

    assert writer.data.startswith(b"HTTP/1.1 200 OK")
    assert b"Content-Type: text/plain; version=0.0.4; charset=utf-8" in writer.data
    assert writer.data.endswith(b"# scrape endpoint\n")
