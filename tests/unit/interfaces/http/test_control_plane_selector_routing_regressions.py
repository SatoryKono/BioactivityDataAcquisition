"""Socket-free regressions for selector filtering and health-server routing."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest

from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.interfaces.http import _control_plane_selector_filters as selector_filters
from bioetl.interfaces.http import health_server_routing_mixin as routing_module
from bioetl.interfaces.http import report_root_config
from bioetl.interfaces.http._control_plane_selector_records import SelectorRecord
from bioetl.interfaces.http.health_server_routing_mixin import HealthServerRoutingMixin
from bioetl.interfaces.http.types import HealthResponse

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunManifest


pytestmark = pytest.mark.unit


def _record(
    suffix: str,
    *,
    workflow_candidates: tuple[str, ...],
    pipeline: str,
    run_type: str,
    run_status: str,
    completed_offset: int,
) -> SelectorRecord:
    completed_at = datetime(2026, 8, 10, 12, 0, tzinfo=UTC) + timedelta(
        minutes=completed_offset
    )
    return SelectorRecord(
        manifest=cast("RunManifest", object()),
        workflow=workflow_candidates[0],
        workflow_candidates=workflow_candidates,
        pipeline=pipeline,
        run_type=run_type,
        run_id=f"run-{suffix}",
        provider=pipeline.split("_", 1)[0],
        entity=pipeline.split("_", 1)[-1],
        manifest_id=f"manifest-{suffix}",
        started_at=completed_at,
        started_at_source="test",
        completed_at=completed_at,
        completed_at_source="test",
        run_status=run_status,
        terminal_event_type=None,
    )


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 8, 10, 12, 30, tzinfo=UTC)


class _MetricsExposition:
    @staticmethod
    def build_exposition() -> str:
        return "bioetl_health_server_scrape_up 1\n"


class _RoutingHost(HealthServerRoutingMixin):
    def __init__(self) -> None:
        self._clock = _Clock()
        self._health_monitor: object | None = None
        self._metrics_exposition = _MetricsExposition()
        self.provider_statuses: dict[str, JsonDict] = {}
        self.overall_status = HealthStatus.HEALTHY
        self.sent: list[tuple[str, int | HealthResponse, object | None]] = []

    @property
    def uptime_seconds(self) -> float:
        return 12.345

    async def _send_json_response(
        self,
        writer: asyncio.StreamWriter,
        response: HealthResponse,
    ) -> None:
        self.sent.append(("json", response, None))

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None:
        self.sent.append(("text", status_code, message))

    async def _send_text_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        body: str,
        *,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        self.sent.append(("text_body", status_code, (body, content_type)))

    def _get_overall_status(self) -> HealthStatus:
        return self.overall_status

    def _get_provider_statuses(self) -> dict[str, JsonDict]:
        return self.provider_statuses


def _writer() -> asyncio.StreamWriter:
    return cast("asyncio.StreamWriter", object())


def test_selector_filters_distinguish_all_scope_and_explicit_selection() -> None:
    first = _record(
        "1",
        workflow_candidates=("nightly", "shared"),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=1,
    )
    second = _record(
        "2",
        workflow_candidates=("weekly",),
        pipeline="pubchem_compound",
        run_type="backfill",
        run_status="failed",
        completed_offset=2,
    )
    records = (first, second)

    assert (
        selector_filters.filter_records(
            records,
            selected_workflows=("All",),
            selected_pipelines=("$__all",),
            selected_run_types=("__all",),
            selected_run_statuses=("*",),
            selected_run_id=None,
        )
        == records
    )
    assert selector_filters.filter_records(
        records,
        selected_workflows=("shared",),
        selected_pipelines=("chembl_activity",),
        selected_run_types=("incremental",),
        selected_run_statuses=("success",),
        selected_run_id=None,
    ) == (first,)
    assert selector_filters.filter_records(
        records,
        selected_workflows=("not-selected",),
        selected_pipelines=("not-selected",),
        selected_run_types=("not-selected",),
        selected_run_statuses=("not-selected",),
        selected_run_id="run-2",
    ) == (second,)

    assert selector_filters.latest_record(()) is None
    assert selector_filters.latest_record(records) is second


@pytest.mark.asyncio
async def test_routing_mixin_delegates_all_route_families_without_sockets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    writer = _writer()
    delegated: list[tuple[str, str, dict[str, str]]] = []

    def dispatcher(route_family: str):
        async def dispatch(
            _host: object,
            *,
            writer: asyncio.StreamWriter,
            path: str,
            query: dict[str, str],
        ) -> None:
            delegated.append((route_family, path, query))

        return dispatch

    monkeypatch.setattr(
        routing_module,
        "dispatch_quarantine_request",
        dispatcher("quarantine"),
    )
    monkeypatch.setattr(
        routing_module,
        "dispatch_control_plane_request",
        dispatcher("control-plane"),
    )
    monkeypatch.setattr(
        routing_module,
        "dispatch_observability_request",
        dispatcher("observability"),
    )

    await host._route_request(writer, "/health?probe=full")
    await host._route_request(writer, "/metrics")
    await host._route_request(writer, "/ops/quarantine/list?pipeline=chembl")
    await host._route_request(writer, "/ops/control-plane/ready")
    await host._route_request(writer, "/ops/observability/processed-records")
    await host._route_request(writer, "/not-a-route")

    assert isinstance(host.sent[0][1], HealthResponse)
    assert host.sent[1][0:2] == ("text_body", 200)
    assert delegated == [
        ("quarantine", "/ops/quarantine/list", {"pipeline": "chembl"}),
        ("control-plane", "/ops/control-plane/ready", {}),
        ("observability", "/ops/observability/processed-records", {}),
    ]
    assert host.sent[-1] == ("text", 404, "Not Found")


def test_routing_mixin_parses_scope_and_integer_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    fixed_now = datetime(2026, 8, 10, 13, 0, tzinfo=UTC)

    assert host._response_timestamp() == "2026-08-10T12:30:00+00:00"
    host._clock = None
    monkeypatch.setattr(routing_module, "current_utc_time", lambda: fixed_now)
    assert host._response_timestamp() == "2026-08-10T13:00:00+00:00"

    assert host._parse_query_params("a=1&a=2&empty=&scope=selected") == {
        "a": "2",
        "scope": "selected",
    }
    assert host._read_required_param({"scope": " selected "}, "scope") == "selected"
    with pytest.raises(ValueError, match="Missing required query parameter: scope"):
        host._read_required_param({"scope": " "}, "scope")

    assert host._read_optional_param({}, "scope") is None
    assert host._read_optional_param({"scope": " "}, "scope") is None
    assert host._read_optional_param({"scope": " selected "}, "scope") == "selected"
    assert host._is_all_scope_token(None) is False
    assert host._is_all_scope_token(" ") is False
    for token in ("All", "all", "*", "$__all", "__all"):
        assert host._is_all_scope_token(token) is True
    assert host._is_all_scope_token("selected") is False
    assert host._read_optional_scope_param({"scope": "All"}, "scope") is None
    assert (
        host._read_optional_scope_param({"scope": " selected "}, "scope") == "selected"
    )

    assert host._read_int_param({}, "limit", 20, minimum=1) == 20
    assert host._read_int_param({"limit": " 3 "}, "limit", 20, minimum=1) == 3
    with pytest.raises(ValueError, match="limit must be an integer"):
        host._read_int_param({"limit": "many"}, "limit", 20, minimum=1)
    with pytest.raises(ValueError, match="limit must be >= 1"):
        host._read_int_param({"limit": "0"}, "limit", 20, minimum=1)

    assert host._read_csv_param({}, "scope") == ()
    assert host._read_csv_param({"scope": "{a, b, a, }"}, "scope") == ("a", "b")
    assert host._read_scope_csv_param({"scope": "a,b"}, "scope") == ("a", "b")
    assert host._read_scope_csv_param({"scope": "a,$__all"}, "scope") == ()


@pytest.mark.asyncio
async def test_routing_mixin_health_lifecycle_is_deterministic_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _RoutingHost()
    monkeypatch.setattr(
        report_root_config,
        "report_root_readiness_check",
        lambda: {"status": "healthy", "marker": "valid"},
    )
    monkeypatch.setattr(
        report_root_config,
        "enforce_report_root_marker",
        lambda: False,
    )

    health = await host._handle_health()
    liveness = await host._handle_liveness()
    readiness_without_monitor = await host._handle_readiness()
    providers_without_monitor = await host._handle_providers()
    assert health.status == "healthy"
    assert health.checks["server"]["uptime_seconds"] == 12.35
    assert liveness.status == "healthy"
    assert readiness_without_monitor.status == "healthy"
    assert readiness_without_monitor.checks["message"] == (
        "No health monitor configured"
    )
    assert providers_without_monitor.status == "healthy"

    host._health_monitor = object()
    host.provider_statuses = {"chembl": {"status": "healthy"}}
    assert (await host._handle_readiness()).status == "healthy"

    host.provider_statuses = {"chembl": {"status": "unhealthy"}}
    assert (await host._handle_readiness()).status == "unhealthy"
    host.overall_status = HealthStatus.DEGRADED
    assert (await host._handle_providers()).status == "degraded"
    assert "providers" in (await host._handle_health()).checks

    monkeypatch.setattr(
        report_root_config,
        "report_root_readiness_check",
        lambda: {"status": "unhealthy", "marker": "missing"},
    )
    monkeypatch.setattr(
        report_root_config,
        "enforce_report_root_marker",
        lambda: True,
    )
    assert (await host._handle_readiness()).status == "unhealthy"
    assert host._handle_metrics() == "bioetl_health_server_scrape_up 1\n"


def test_routing_mixin_base_uptime_contract_is_abstract_by_behavior() -> None:
    with pytest.raises(NotImplementedError):
        _ = HealthServerRoutingMixin().uptime_seconds
