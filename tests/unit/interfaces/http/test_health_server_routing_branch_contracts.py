"""Socket-free branch contracts for HealthServer helper routing."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import cast

import pytest

from bioetl.interfaces.http import (
    _health_server_observability_routing as observability_routing,
)
from bioetl.interfaces.http import _health_server_routing_support as routing_support
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
)


pytestmark = pytest.mark.unit


class _Writer:
    """Identity-only writer; response fakes never touch a socket."""


class _ObservabilityHost:
    def __init__(self) -> None:
        self.sent: list[tuple[str, int, object]] = []
        self._forensic_endpoint_limiter = asyncio.Semaphore(1)
        self._prometheus_base_url = "http://prometheus.test"
        self._run_ledger_port: object | None = None

    @staticmethod
    def _read_required_param(query: dict[str, str], name: str) -> str:
        value = query.get(name, "").strip()
        if not value:
            raise ValueError(f"Missing required query parameter: {name}")
        return value

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None:
        value = query.get(name, "").strip()
        return value or None

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


class _ListPort:
    def __init__(self, items: tuple[object, ...] = ()) -> None:
        self.items = items
        self.calls = 0

    def list_all(self) -> tuple[object, ...]:
        self.calls += 1
        return self.items


class _RoutingHost(_ObservabilityHost):
    def __init__(self) -> None:
        super().__init__()
        self._control_plane_evidence_service: object | None = None
        self._checkpoint_port: object | None = object()
        self._run_manifest_port: object | None = _ListPort()
        self._workflow_manifest_port: object | None = None
        self._data_root: str | None = None
        self._runtime_source_id: str | None = None

    @staticmethod
    def _is_all_scope_token(value: str | None) -> bool:
        return value in {"all", "$__all"}

    def _read_int_param(
        self,
        query: dict[str, str],
        name: str,
        default: int,
        *,
        minimum: int,
    ) -> int:
        value = int(query.get(name, default))
        if value < minimum:
            raise ValueError(f"{name} must be >= {minimum}")
        return value

    @classmethod
    def _read_scope_csv_param(
        cls,
        query: dict[str, str],
        name: str,
    ) -> tuple[str, ...]:
        value = cls._read_optional_param(query, name)
        if value is None or cls._is_all_scope_token(value):
            return ()
        return tuple(item.strip() for item in value.split(",") if item.strip())


async def _inline_to_thread(
    function: Callable[..., object],
    /,
    *args: object,
    **kwargs: object,
) -> object:
    return function(*args, **kwargs)


async def _run_operation_directly(
    *,
    limiter: asyncio.Semaphore,
    operation_factory: Callable[[], Awaitable[object]],
) -> object:
    del limiter
    return await operation_factory()


def _writer() -> asyncio.StreamWriter:
    return cast("asyncio.StreamWriter", _Writer())


@pytest.mark.asyncio
async def test_observability_dispatch_routes_every_endpoint_and_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _ObservabilityHost()
    writer = _writer()
    calls: list[tuple[str, dict[str, str]]] = []
    route_map = {
        "/ops/observability/processed-records": "handle_processed_records_table",
        "/ops/observability/pipeline-run-report": "handle_pipeline_run_report",
        "/ops/observability/workflow-run-report": "handle_workflow_run_report",
        "/ops/observability/pipeline-run-reports": ("handle_pipeline_run_reports_list"),
        "/ops/observability/workflow-run-reports": ("handle_workflow_run_reports_list"),
    }

    for path, handler_name in route_map.items():

        async def record_call(
            _host: object,
            _writer: object,
            query: dict[str, str],
            *,
            route: str = path,
        ) -> None:
            calls.append((route, query))

        monkeypatch.setattr(observability_routing, handler_name, record_call)

    for path in route_map:
        await observability_routing.dispatch_observability_request(
            host,
            writer=writer,
            path=path,
            query={"request": path},
        )

    await observability_routing.dispatch_observability_request(
        host,
        writer=writer,
        path="/ops/observability/not-a-route",
        query={},
    )

    assert calls == [(path, {"request": path}) for path in route_map]
    assert host.sent[-1] == ("text", 404, "Not Found")


@pytest.mark.asyncio
async def test_observability_dispatch_maps_value_and_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _ObservabilityHost()

    async def invalid_request(*_args: object, **_kwargs: object) -> None:
        raise ValueError("bad selector")

    monkeypatch.setattr(
        observability_routing,
        "handle_processed_records_table",
        invalid_request,
    )
    await observability_routing.dispatch_observability_request(
        host,
        writer=_writer(),
        path="/ops/observability/processed-records",
        query={},
    )
    assert host.sent[-1] == ("text", 400, "bad selector")

    async def unavailable(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("report backend unavailable")

    monkeypatch.setattr(
        observability_routing,
        "handle_processed_records_table",
        unavailable,
    )
    await observability_routing.dispatch_observability_request(
        host,
        writer=_writer(),
        path="/ops/observability/processed-records",
        query={},
    )
    assert host.sent[-1] == ("text", 502, "report backend unavailable")


@pytest.mark.asyncio
async def test_pipeline_run_report_returns_unresolved_and_missing_shells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _ObservabilityHost()
    writer = _writer()

    await observability_routing.handle_pipeline_run_report(
        host,
        writer,
        {"run_id": "-", "pipeline": "chembl_activity"},
    )
    assert host.sent[-1][1:] == (
        200,
        {
            "status": "unresolved_scope",
            "message": "run_id not selected; pick a run from Inspect Recent Runs",
            "run_id": "-",
            "pipeline": "chembl_activity",
            "funnel": [],
            "reasons_top_n": [],
            "reconciliation": [],
            "artifacts": [],
            "layers": [],
            "failure": [],
            "stage_timings": [],
            "identity_rows": [],
            "schema_version": "pipeline_run_report_v1",
        },
    )

    monkeypatch.setattr(observability_routing.asyncio, "to_thread", _inline_to_thread)
    monkeypatch.setattr(
        observability_routing,
        "run_bounded_forensic_operation",
        _run_operation_directly,
    )
    monkeypatch.setattr(
        observability_routing,
        "load_pipeline_run_report_payload",
        lambda **_kwargs: None,
    )
    await observability_routing.handle_pipeline_run_report(
        host,
        writer,
        {"run_id": "run-404", "pipeline": "chembl_activity"},
    )
    payload = host.sent[-1][2]
    assert isinstance(payload, dict)
    assert host.sent[-1][1] == 200
    assert payload["status"] == "not_found"
    assert payload["run_id"] == "run-404"
    assert payload["identity_rows"] == []


@pytest.mark.asyncio
async def test_workflow_report_handles_found_and_missing_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _ObservabilityHost()
    writer = _writer()
    monkeypatch.setattr(observability_routing.asyncio, "to_thread", _inline_to_thread)
    monkeypatch.setattr(
        observability_routing,
        "run_bounded_forensic_operation",
        _run_operation_directly,
    )
    monkeypatch.setattr(
        observability_routing,
        "load_workflow_run_report_payload",
        lambda **_kwargs: None,
    )

    query = {"workflow_run_id": "wf-run-404", "workflow": "nightly"}
    await observability_routing.handle_workflow_run_report(host, writer, query)
    assert host.sent[-1] == (
        "payload",
        404,
        {
            "status": "not_found",
            "message": "workflow run report not found",
            "workflow_run_id": "wf-run-404",
            "workflow": "nightly",
        },
    )

    expected = {"schema_version": "workflow_run_report_v1", "steps": []}
    monkeypatch.setattr(
        observability_routing,
        "load_workflow_run_report_payload",
        lambda **_kwargs: expected,
    )
    await observability_routing.handle_workflow_run_report(host, writer, query)
    assert host.sent[-1] == ("payload", 200, expected)


@pytest.mark.asyncio
async def test_report_lists_bound_limits_and_reject_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _ObservabilityHost()
    writer = _writer()
    calls: list[tuple[str, str | None, int]] = []
    monkeypatch.setattr(observability_routing.asyncio, "to_thread", _inline_to_thread)

    async def unexpected_bounded_operation(**_kwargs: object) -> object:
        raise AssertionError("report list endpoints must bypass the forensic limiter")

    monkeypatch.setattr(
        observability_routing,
        "run_bounded_forensic_operation",
        unexpected_bounded_operation,
    )

    def list_pipeline(*, pipeline_name: str | None, limit: int) -> dict[str, object]:
        calls.append(("pipeline", pipeline_name, limit))
        return {"items": []}

    def list_workflow(*, workflow_name: str | None, limit: int) -> dict[str, object]:
        calls.append(("workflow", workflow_name, limit))
        return {"items": []}

    monkeypatch.setattr(
        observability_routing,
        "list_pipeline_run_report_payloads",
        list_pipeline,
    )
    monkeypatch.setattr(
        observability_routing,
        "list_workflow_run_report_payloads",
        list_workflow,
    )

    await observability_routing.handle_pipeline_run_reports_list(
        host,
        writer,
        {"pipeline": "chembl_activity", "limit": "0"},
    )
    await observability_routing.handle_workflow_run_reports_list(
        host,
        writer,
        {"workflow": "nightly", "limit": "101"},
    )
    assert calls == [
        ("pipeline", "chembl_activity", 1),
        ("workflow", "nightly", 100),
    ]

    for path in (
        "/ops/observability/pipeline-run-reports",
        "/ops/observability/workflow-run-reports",
    ):
        await observability_routing.dispatch_observability_request(
            host,
            writer=writer,
            path=path,
            query={"limit": "many"},
        )
        assert host.sent[-1] == ("text", 400, "limit must be an integer")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "query", "endpoint"),
    [
        (
            "/ops/observability/processed-records",
            {"pipeline": "chembl_activity"},
            "processed-records",
        ),
        (
            "/ops/observability/pipeline-run-report",
            {"pipeline": "chembl_activity", "run_id": "run-1"},
            "pipeline-run-report",
        ),
        (
            "/ops/observability/workflow-run-report",
            {"workflow": "nightly", "workflow_run_id": "wf-run-1"},
            "workflow-run-report",
        ),
    ],
)
async def test_observability_endpoints_return_bounded_failure_contract(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    query: dict[str, str],
    endpoint: str,
) -> None:
    host = _ObservabilityHost()

    async def capacity_exhausted(**_kwargs: object) -> object:
        raise ForensicEndpointUnavailable(
            reason="capacity_exhausted",
            status_code=503,
        )

    monkeypatch.setattr(
        observability_routing,
        "run_bounded_forensic_operation",
        capacity_exhausted,
    )
    await observability_routing.dispatch_observability_request(
        host,
        writer=_writer(),
        path=path,
        query=query,
    )
    assert host.sent[-1] == (
        "payload",
        503,
        {
            "contract": "forensic_endpoint_error_v1",
            "status": "unavailable",
            "endpoint": endpoint,
            "reason": "capacity_exhausted",
            "retryable": True,
        },
    )


@pytest.mark.asyncio
async def test_processed_records_prefers_exact_run_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _ObservabilityHost()
    writer = _writer()
    seen: dict[str, object] = {}
    run_id = "00000000-0000-0000-0000-000000000001"

    class _Ledger:
        @staticmethod
        def list_entries_by_run_id(run_id: object) -> list[object]:
            seen["run_id"] = run_id
            return ["entry-a", "entry-b"]

    def build_from_ledger(**kwargs: object) -> dict[str, object]:
        seen.update(kwargs)
        return {"contract": "processed_records_table_v1", "rows": [1]}

    host._run_ledger_port = _Ledger()
    monkeypatch.setattr(observability_routing.asyncio, "to_thread", _inline_to_thread)
    monkeypatch.setattr(
        observability_routing,
        "run_bounded_forensic_operation",
        _run_operation_directly,
    )
    monkeypatch.setattr(
        observability_routing,
        "build_processed_records_table_payload_from_ledger",
        build_from_ledger,
    )

    await observability_routing.handle_processed_records_table(
        host,
        writer,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "run_id": run_id,
        },
    )

    assert str(seen["run_id"]) == run_id
    assert seen["ledger_entries"] == ("entry-a", "entry-b")
    assert seen["pipeline"] == "chembl_activity"
    assert seen["run_type"] == "incremental"
    assert host.sent[-1] == (
        "payload",
        200,
        {"contract": "processed_records_table_v1", "rows": [1]},
    )


@pytest.mark.asyncio
async def test_control_plane_dispatch_fails_closed_for_missing_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _writer()

    async def not_evidence(*_args: object, **_kwargs: object) -> bool:
        return False

    monkeypatch.setattr(
        routing_support,
        "dispatch_control_plane_evidence_request",
        not_evidence,
    )
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

    async def invalid_evidence(*_args: object, **_kwargs: object) -> bool:
        raise ValueError("invalid evidence scope")

    monkeypatch.setattr(
        routing_support,
        "dispatch_control_plane_evidence_request",
        invalid_evidence,
    )
    await routing_support.dispatch_control_plane_request(
        host,
        writer=writer,
        path="/ops/control-plane/manifest-validation",
        query={},
    )
    assert host.sent[-1] == ("text", 400, "invalid evidence scope")

    async def unavailable_evidence(*_args: object, **_kwargs: object) -> bool:
        raise RuntimeError("control-plane evidence service is unavailable")

    monkeypatch.setattr(
        routing_support,
        "dispatch_control_plane_evidence_request",
        unavailable_evidence,
    )
    await routing_support.dispatch_control_plane_request(
        host,
        writer=writer,
        path="/ops/control-plane/manifest-validation",
        query={},
    )
    assert host.sent[-1] == (
        "text",
        503,
        "control-plane evidence service is unavailable",
    )


@pytest.mark.asyncio
async def test_control_plane_ops_dispatch_maps_runtime_errors_to_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _writer()

    async def not_evidence(*_args: object, **_kwargs: object) -> bool:
        return False

    async def boom(*_args: object, **_kwargs: object) -> bool:
        raise OSError("selector catalog offline")

    monkeypatch.setattr(
        routing_support,
        "dispatch_control_plane_evidence_request",
        not_evidence,
    )
    monkeypatch.setattr(routing_support, "_dispatch_ops_endpoints", boom)
    await routing_support.dispatch_control_plane_request(
        host,
        writer=writer,
        path="/ops/control-plane/ready",
        query={},
    )
    assert host.sent[-1] == ("text", 503, "selector catalog offline")


@pytest.mark.asyncio
async def test_control_plane_ops_dispatch_delegates_every_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _writer()
    calls: list[tuple[str, dict[str, str]]] = []
    route_map = {
        "/ops/control-plane/ready": "handle_control_plane_ready",
        "/ops/control-plane/filter-options": "handle_control_plane_filter_options",
        "/ops/control-plane/selector-context": (
            "handle_control_plane_selector_context"
        ),
        "/ops/control-plane/identity-table": "handle_control_plane_identity_table",
        "/ops/control-plane/identity-evidence": (
            "handle_control_plane_identity_evidence"
        ),
        "/ops/control-plane/checkpoint-freshness": (
            "handle_control_plane_checkpoint_freshness"
        ),
    }

    for path, handler_name in route_map.items():

        async def record_call(
            _host: object,
            _writer: object,
            query: dict[str, str] | None = None,
            *,
            route: str = path,
        ) -> None:
            calls.append((route, query or {}))

        monkeypatch.setattr(routing_support, handler_name, record_call)

    for path in route_map:
        handled = await routing_support._dispatch_ops_endpoints(
            host,
            writer,
            path,
            {"request": path},
        )
        assert handled is True

    assert (
        await routing_support._dispatch_ops_endpoints(
            host,
            writer,
            "/ops/control-plane/not-a-route",
            {},
        )
        is False
    )
    assert calls == [
        (path, {} if path == "/ops/control-plane/ready" else {"request": path})
        for path in route_map
    ]


@pytest.mark.asyncio
async def test_routing_helpers_cover_non_list_and_workflow_port_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert routing_support._string_payload_items({"items": []}) == ()

    workflow_port = _ListPort(("workflow-a", "workflow-b"))
    host = _RoutingHost()
    host._workflow_manifest_port = workflow_port
    monkeypatch.setattr(routing_support.asyncio, "to_thread", _inline_to_thread)

    manifests = await routing_support._list_workflow_manifests(host)

    assert manifests == ("workflow-a", "workflow-b")
    assert workflow_port.calls == 1


@pytest.mark.asyncio
async def test_control_plane_ready_reports_missing_catalog_without_scanning() -> None:
    host = _RoutingHost()
    host._run_manifest_port = None

    await routing_support.handle_control_plane_ready(host, _writer())

    response_type, status_code, payload = host.sent[-1]
    assert response_type == "payload"
    assert status_code == 503
    assert isinstance(payload, dict)
    assert payload["run_manifest_port"] is False
