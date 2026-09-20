"""Stream B IF: remaining interfaces private helpers and error branches."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from uuid import UUID

import click
import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.domain.run_reports.models import (
    BalanceStatus,
    StageFunnelRow,
    TrackingCoverage,
)
from bioetl.interfaces.cli.commands._workflow_run_support import (
    _resolve_workflow_step_required_profile,
    _validate_run_workflow_options,
    _validate_workflow_pipeline_replay_prerequisites,
    _workflow_failure_message,
    _workflow_metrics_pipeline_name,
    _workflow_metrics_run_type,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_failure_details import (
    _append_backend_startup_diagnostic,
    _build_backend_base_url,
    _build_startup_failure_detail,
    _describe_required_probe_failure,
    _probe_required_path,
    _read_backend_startup_log_excerpt,
)
from bioetl.interfaces.cli.commands.domains.maintenance.plan import (
    _append_notes,
    _append_required_actions,
    _append_transitions,
    _render_json_block,
    _render_plan_payload,
)
from bioetl.interfaces.cli.commands.domains.run.result_presenter import echo_run_result
from bioetl.interfaces.cli.commands.lineage import (
    _render_explain_payload,
    _render_fragment_payload,
    _render_node_lines,
    _render_relation_lines,
    _render_trace_payload,
    get_lineage_service,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.http import _processed_records_prometheus as prom
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    run_bounded_forensic_operation,
    table_error_as_http_ok,
)
from bioetl.interfaces.http._processed_records_value_support import (
    _optional_int,
    _optional_text,
)
from bioetl.interfaces.http.control_plane_identity.specs import (
    get_current_spec_version,
    is_spec_version_compatible,
)
from bioetl.interfaces.http.control_plane_identity.types import (
    AnchorSpec,
    _resolve_missing_severity,
)

pytestmark = pytest.mark.unit


def test_prometheus_query_and_parse_error_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*_a: object, **_k: object) -> object:
        raise URLError("down")

    monkeypatch.setattr(prom, "_open_url", _raise)
    with pytest.raises(RuntimeError, match="Prometheus query failed"):
        prom._fetch_prometheus_query_payload(
            prometheus_base_url="http://prom", query="up"
        )

    class _Resp:
        def read(self) -> bytes:
            return b"not-json"

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr(prom, "_open_url", lambda *_a, **_k: _Resp())
    with pytest.raises(RuntimeError, match="Prometheus query failed"):
        prom._fetch_prometheus_query_payload(
            prometheus_base_url="http://prom/", query="up"
        )

    class _Ok:
        def read(self) -> bytes:
            return b"[]"

        def __enter__(self) -> _Ok:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr(prom, "_open_url", lambda *_a, **_k: _Ok())
    with pytest.raises(RuntimeError, match="invalid payload"):
        prom._fetch_prometheus_query_payload(
            prometheus_base_url="http://prom", query="up"
        )

    assert prom._prometheus_error_message({"error": "boom"}) == "boom"
    assert prom._prometheus_error_message({"errorType": "bad_data"}) == "bad_data"
    assert prom._prometheus_error_message({}) == "unknown"
    with pytest.raises(RuntimeError, match="boom"):
        prom._require_prometheus_success({"status": "error", "error": "boom"})
    assert prom._prometheus_result_list({"data": "x"}) == []
    assert prom._prometheus_result_list({"data": {"result": {"a": 1}}}) == []
    assert prom._finite_float_from_value_pair(["t", "nan"]) is None
    assert prom._finite_float_from_value_pair(["t", object()]) is None
    assert prom._metric_name_from_sample({"metric": "nope"}) is None
    assert prom._parse_vector_sample("x") is None
    assert prom._scalar_from_payload({"data": {"result": []}}) is None
    assert prom._scalar_from_payload({"data": {"result": ["x"]}}) is None
    with pytest.raises(RuntimeError, match="http://a"):
        prom._query_prometheus_vector_with_fallbacks(
            prometheus_base_urls=("http://a", "http://b"),
            query="up",
        )


def test_workflow_option_conflicts_and_result_helpers() -> None:
    with pytest.raises(click.exceptions.Exit) as resume_last:
        _validate_run_workflow_options(
            incremental=False,
            resume_last=True,
            resume_manifest_id="m1",
            resume_run_id=None,
            start_offset=None,
        )
    assert resume_last.value.exit_code == ExitCode.CONFIG_ERROR
    with pytest.raises(click.exceptions.Exit):
        _validate_run_workflow_options(
            incremental=False,
            resume_last=True,
            resume_manifest_id=None,
            resume_run_id=UUID("12345678-1234-5678-1234-567812345678"),
            start_offset=None,
        )
    with pytest.raises(click.exceptions.Exit):
        _validate_run_workflow_options(
            incremental=False,
            resume_last=False,
            resume_manifest_id="m1",
            resume_run_id=UUID("12345678-1234-5678-1234-567812345678"),
            start_offset=None,
        )
    with pytest.raises(click.exceptions.Exit):
        _validate_run_workflow_options(
            incremental=True,
            resume_last=True,
            resume_manifest_id=None,
            resume_run_id=None,
            start_offset=None,
        )
    with pytest.raises(click.exceptions.Exit):
        _validate_run_workflow_options(
            incremental=True,
            resume_last=False,
            resume_manifest_id=None,
            resume_run_id=None,
            start_offset=1,
        )

    class _Step:
        def __init__(self, run_type: str) -> None:
            self.run_options = SimpleNamespace(run_type=run_type)

    class _Defaults:
        def merged_with(self, options: object) -> object:
            return options

    mixed = SimpleNamespace(
        pipeline_steps=[_Step("incremental"), _Step("backfill")],
        defaults=_Defaults(),
        single_pipeline_name=None,
    )
    assert _workflow_metrics_run_type(mixed) is None  # type: ignore[arg-type]
    named = SimpleNamespace(
        pipeline_steps=(),
        single_pipeline_name="chembl_activity",
        defaults=SimpleNamespace(run_type="backfill"),
        run_type_context=None,
    )
    assert _workflow_metrics_run_type(named) == "backfill"  # type: ignore[arg-type]
    ctx = SimpleNamespace(
        pipeline_steps=(),
        single_pipeline_name="chembl_activity",
        defaults=SimpleNamespace(run_type=None),
        run_type_context="rebuild",
    )
    assert _workflow_metrics_run_type(ctx) == "rebuild"  # type: ignore[arg-type]
    fallback = SimpleNamespace(
        pipeline_steps=(),
        single_pipeline_name="chembl_activity",
        defaults=SimpleNamespace(run_type=None),
        run_type_context=None,
    )
    assert _workflow_metrics_run_type(fallback) == "incremental"  # type: ignore[arg-type]
    empty_name = SimpleNamespace(
        pipeline_steps=(),
        single_pipeline_name="",
        defaults=SimpleNamespace(run_type=None),
        run_type_context=None,
    )
    assert _workflow_metrics_run_type(empty_name) is None  # type: ignore[arg-type]
    assert (
        _workflow_metrics_pipeline_name(SimpleNamespace(single_pipeline_name=1)) is None
    )  # type: ignore[arg-type]
    assert (
        _workflow_failure_message(SimpleNamespace(error_message="top", steps=()))
        == "top"
    )
    step_err = SimpleNamespace(
        error_message=None,
        steps=[SimpleNamespace(error_message="step boom")],
    )
    assert _workflow_failure_message(step_err) == "step boom"
    assert (
        _workflow_failure_message(SimpleNamespace(error_message=None, steps=()))
        == "Unknown error"
    )


def test_workflow_replay_prereq_requires_cached_bronze() -> None:
    step = SimpleNamespace(
        step_id="s1",
        pipeline_name="chembl_activity",
        run_options=SimpleNamespace(
            exact_replay=True,
            use_cached_bronze=False,
            required_persistence_profile=None,
        ),
    )
    defaults = SimpleNamespace(
        exact_replay=True,
        use_cached_bronze=False,
        required_persistence_profile=None,
    )
    config = SimpleNamespace(pipeline_steps=[step], defaults=defaults)
    with pytest.raises(ValueError, match="use-cached-bronze"):
        _validate_workflow_pipeline_replay_prerequisites(config)  # type: ignore[arg-type]
    step_no_underscore = SimpleNamespace(pipeline_name="activity")
    assert (
        _resolve_workflow_step_required_profile(
            step=step_no_underscore,  # type: ignore[arg-type]
            configured_profile="degraded_observable",
            exact_replay=False,
        )
        == "degraded_observable"
    )


def test_plan_and_lineage_renderers(monkeypatch: pytest.MonkeyPatch) -> None:
    lines: list[str] = ["head"]
    _append_transitions(lines, "nope")
    _append_transitions(lines, [])
    _append_transitions(
        lines,
        [
            "raw",
            {
                "from_version": "1",
                "to_version": "2",
                "migration_guide": "g",
                "affects_hash": True,
            },
        ],
    )
    _append_required_actions(lines, "nope")
    _append_required_actions(lines, [])
    _append_required_actions(
        lines,
        ["raw", {"title": "T", "code": "C", "description": "D"}],
    )
    _append_notes(lines, "nope")
    _append_notes(lines, [])
    _append_notes(lines, ["n1"])
    blob = "\n".join(lines)
    assert "Transitions" in blob
    assert "[affects_hash]" in blob
    assert "Required Actions" in blob
    assert "Notes" in blob
    assert _render_json_block({"a": 1})
    assert "Contract Migration Plan" in _render_plan_payload({"pipeline_name": "p"})
    assert _render_node_lines([]) == ["  - none"]
    assert (
        "label=L"
        in _render_node_lines([{"node_type": "run", "node_id": "r1", "label": "L"}])[0]
    )
    assert _render_node_lines(["x"])[0] == "  - x"
    rel = _render_relation_lines(
        [
            "raw",
            {
                "node": {"node_id": "n1", "label": "L"},
                "fragment_id": "f1",
                "stored_fragment_id": "other",
                "edge_type": "uses",
            },
            {
                "node": "plain",
                "fragment_id": "f2",
                "stored_fragment_id": "f2",
                "edge_type": "uses",
            },
        ]
    )
    assert any("occurrence=other" in item for item in rel)
    assert _render_relation_lines([]) == ["  - none"]
    assert "Lineage Fragment" in _render_fragment_payload(
        {"fragment": {"fragment_id": "f", "nodes": [{"node_id": "n"}]}}
    )
    assert _render_fragment_payload({"fragment": "x"})
    assert "Upstream" in _render_trace_payload(
        {
            "dataset_ref": "d",
            "fragment_ids": ["a"],
            "stored_fragment_ids": ["b"],
            "upstream": [{"node": {"node_id": "u"}, "fragment_id": "f"}],
            "downstream": "x",
        }
    )
    assert "Lineage Run" in _render_explain_payload(
        {"identifier": "r", "fragment_ids": ["a"], "stored_fragment_ids": []}
    )
    sentinel = object()
    monkeypatch.setattr(
        "bioetl.composition.control_plane_service_access.get_lineage_service",
        lambda: sentinel,
    )
    assert get_lineage_service() is sentinel


def test_backend_log_excerpt_probes_and_url(tmp_path: Path) -> None:
    missing = tmp_path / "gone.log"
    assert _read_backend_startup_log_excerpt(missing) is None
    empty = tmp_path / "empty.log"
    empty.write_bytes(b"\n\n")
    assert _read_backend_startup_log_excerpt(empty) is None
    log = tmp_path / "ok.log"
    log.write_text("line-one\nline-two\n", encoding="utf-8")
    excerpt = _read_backend_startup_log_excerpt(log, max_lines=1, max_chars=8)
    assert excerpt is not None
    assert _build_backend_base_url("http://h/health") == "http://h"
    assert _build_backend_base_url("http://h/ready/") == "http://h/ready"
    detail = _build_startup_failure_detail(log, process=SimpleNamespace(poll=lambda: 2))
    assert "Exit code" in detail
    _append_backend_startup_diagnostic(
        log,
        parent_pid=1,
        child_pid=None,
        command=(),
        diagnostic_lines=["note"],
    )
    _append_backend_startup_diagnostic(
        tmp_path,
        parent_pid=1,
        child_pid=2,
        command=("cmd",),
        diagnostic_lines=["note"],
    )
    assert (
        _describe_required_probe_failure("http://h/health", required_probe_paths=())
        is None
    )

    class _Bad:
        status = 500

        def __enter__(self) -> _Bad:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    assert (
        _probe_required_path(
            "http://h/ready",
            timeout_seconds=0.1,
            urlopen_fn=lambda *_a, **_k: _Bad(),
        )
        is not None
    )

    def _http(*_a: object, **_k: object) -> object:
        raise HTTPError("http://h/x", 503, "nope", hdrs=None, fp=None)  # type: ignore[arg-type]

    assert _probe_required_path("http://h/x", timeout_seconds=0.1, urlopen_fn=_http)
    assert _probe_required_path(
        "http://h/x",
        timeout_seconds=0.1,
        urlopen_fn=lambda *_a, **_k: (_ for _ in ()).throw(URLError("down")),
    )
    assert _probe_required_path(
        "http://h/x",
        timeout_seconds=0.1,
        urlopen_fn=lambda *_a, **_k: (_ for _ in ()).throw(OSError("io")),
    )
    assert _probe_required_path(
        "http://h/x",
        timeout_seconds=0.1,
        urlopen_fn=lambda *_a, **_k: (_ for _ in ()).throw(ValueError("bad")),
    )


def test_result_presenter_and_http_helpers() -> None:
    funnel = StageFunnelRow(
        stage_id="bronze",
        records_in=2,
        records_out=1,
        removed_total=1,
        removals=(),
        balance_status=BalanceStatus.OK,
        tracking=TrackingCoverage.FULL,
    )

    def _result(**overrides: object) -> RunResult:
        payload: dict[str, object] = {
            "status": PipelineRunResult.SUCCESS,
            "pipeline_name": "chembl_activity",
            "run_id": "abcdefghijkl",
            "run_type": "incremental",
            "records_fetched": 1,
            "records_silver": 1,
            "records_gold": 1,
            "records_filtered_out": 0,
            "records_quarantined": 0,
            "records_gold_excluded_by_contract": 1,
            "error_message": None,
            "run_report_error": "missing",
            "run_report_json_path": "a.json",
            "run_report_markdown_path": "a.md",
            "run_report_funnel": (funnel,),
        }
        payload.update(overrides)
        return RunResult(**payload)  # type: ignore[arg-type]

    echo_run_result(_result())
    echo_run_result(_result(status=PipelineRunResult.DRY_RUN, run_id="short"))
    echo_run_result(_result(status=PipelineRunResult.SHUTDOWN))
    echo_run_result(_result(status=PipelineRunResult.FAILED, error_message=None))
    assert _optional_text(None) is None
    assert _optional_text("  ") is None
    assert _optional_int(True) is None
    assert _optional_int(object()) is None
    assert _optional_int("nope") is None
    assert get_current_spec_version() == "1.0.0"
    assert is_spec_version_compatible("1.9.9") is True
    assert is_spec_version_compatible("9.9.9") is False
    spec = AnchorSpec(
        "P0",
        name="n",
        label="l",
        source="s",
        value_format="f",
        why="w",
        rendering="r",
        copy=True,
        drilldown="d",
        missing_severity="INFO",
    )
    assert spec.implementation_status == "SHIPPED"
    warn = AnchorSpec(
        "P1",
        name="n",
        label="l",
        source="s",
        value_format="f",
        why="w",
        rendering="r",
        copy=False,
        drilldown="d",
        missing_severity="WARNING",
    )
    assert warn.implementation_status == "DEGRADED"
    other = AnchorSpec(
        "P2",
        name="n",
        label="l",
        source="s",
        value_format="f",
        why="w",
        rendering="r",
        copy=False,
        drilldown="d",
        missing_severity="FAILING",
    )
    assert other.implementation_status == "FAILING"
    assert _resolve_missing_severity(None, "SHIPPED") == "INFO"
    assert _resolve_missing_severity(None, "DEGRADED") == "WARNING"
    assert _resolve_missing_severity("FAILING", None) == "FAILING"
    assert table_error_as_http_ok({"error_as_row": "true"}) is True


@pytest.mark.asyncio
async def test_forensic_deadline_and_cancel() -> None:
    limiter = asyncio.Semaphore(1)

    async def _slow() -> str:
        await asyncio.sleep(0.2)
        return "ok"

    with pytest.raises(ForensicEndpointUnavailable):
        await run_bounded_forensic_operation(
            limiter=limiter,
            operation_factory=_slow,
            timeout_seconds=0.01,
        )

    async def _blocker() -> str:
        await asyncio.sleep(10)
        return "ok"

    task = asyncio.create_task(
        run_bounded_forensic_operation(
            limiter=asyncio.Semaphore(1),
            operation_factory=_blocker,
            timeout_seconds=30,
        )
    )
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
