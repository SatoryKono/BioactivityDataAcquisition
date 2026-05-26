from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from urllib.error import URLError

from scripts.ops import __main__ as ops_router
from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject
from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight_subject,
)
from scripts.ops.observability.grafana import (
    run_grafana_dashboard_audit_cycle as cycle_subject,
)
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender_subject,
)
from tests.helpers import assert_router_python_command


def test_rerender_config_uses_env_defaults(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("GRAFANA_BASE_URL", "http://grafana.local:3000")
    monkeypatch.setenv("GRAFANA_USERNAME", "viewer")
    monkeypatch.setenv("GRAFANA_PASSWORD", "secret")

    config = rerender_subject._parse_args(
        ["--output-dir", str(tmp_path), "--uids", "bioetl-dq-v2"]
    )

    assert config.base_url == "http://grafana.local:3000"
    assert config.username == "viewer"
    assert config.password == "secret"
    assert config.output_dir == tmp_path
    assert config.selected_uids == ("bioetl-dq-v2",)
    assert config.fallback == "auto"


def test_rerender_load_dashboards_filters_and_sorts(monkeypatch: Any) -> None:
    payload = [
        {"uid": "bioetl-runtime", "url": "/d/runtime/runtime", "title": "Runtime"},
        {"uid": "bioetl-dq-v2", "url": "/d/dq/dq", "title": "DQ"},
    ]
    monkeypatch.setattr(rerender_subject, "_request_json", lambda *_, **__: payload)
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="admin",
        output_dir=Path("reports/observability/grafana/screenshots"),
        width=1600,
        height=2200,
        timeout_seconds=30.0,
        selected_uids=("bioetl-dq-v2",),
        fallback="auto",
    )

    dashboards = rerender_subject._load_dashboards(config)

    assert dashboards == [
        rerender_subject.DashboardRecord(
            uid="bioetl-dq-v2",
            url="/d/dq/dq",
            title="DQ",
        )
    ]


def test_rerender_failure_hint_includes_frontend_renderer_state(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        rerender_subject,
        "_request_json",
        lambda *_, **__: {
            "rendererAvailable": True,
            "rendererVersion": "5.0.0",
        },
    )
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="admin",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=30.0,
        selected_uids=(),
        fallback="auto",
    )

    hint = rerender_subject._render_failure_hint(config)

    assert "rendererAvailable=True" in hint
    assert "rendererVersion='5.0.0'" in hint
    assert "Playwright fallback" in hint


def test_rerender_builds_playwright_env(tmp_path: Path) -> None:
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=45.0,
        selected_uids=("bioetl-control-plane-v1",),
        fallback="auto",
    )

    env = rerender_subject._playwright_env(config)

    assert env["GRAFANA_BASE_URL"] == "http://localhost:3000"
    assert env["GRAFANA_USERNAME"] == "admin"
    assert env["GRAFANA_PASSWORD"] == "changeme"
    assert env["GRAFANA_SCREENSHOT_OUTPUT_DIR"] == str(tmp_path)
    assert env["GRAFANA_SCREENSHOT_TIMEOUT_MS"] == "45000"
    assert env["GRAFANA_SCREENSHOT_CAPTURE_TIMEOUT_MS"] == "180000"
    assert env["GRAFANA_SCREENSHOT_UIDS"] == "bioetl-control-plane-v1"


def test_rerender_playwright_fallback_streams_output_from_repo_root(
    monkeypatch: Any, tmp_path: Path
) -> None:
    script_path = tmp_path / "rerender_grafana_screenshots.cjs"
    script_path.write_text("// noop\n", encoding="utf-8")
    captured: dict[str, object] = {}

    class _Result:
        returncode = 0

    monkeypatch.setattr(rerender_subject, "_playwright_script_path", lambda: script_path)
    monkeypatch.setattr(rerender_subject.shutil, "which", lambda _name: "/usr/bin/node")
    monkeypatch.setattr(rerender_subject, "_repo_root", lambda: tmp_path)

    def fake_run(command: list[str], **kwargs: object) -> _Result:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _Result()

    monkeypatch.setattr(rerender_subject.subprocess, "run", fake_run)

    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=45.0,
        selected_uids=(),
        fallback="auto",
    )

    result = rerender_subject._run_playwright_fallback(config)

    assert result == 0
    assert captured["command"] == ["node", str(script_path)]
    assert captured["kwargs"]["check"] is False
    assert captured["kwargs"]["cwd"] == str(tmp_path)
    assert "capture_output" not in captured["kwargs"]
    assert captured["kwargs"]["env"]["GRAFANA_BASE_URL"] == "http://localhost:3000"


def test_rerender_falls_back_to_playwright_on_render_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(rerender_subject, "_load_dashboards", lambda *_: [])
    monkeypatch.setattr(
        rerender_subject,
        "_render_via_api",
        lambda *_: (_ for _ in ()).throw(URLError("timed out")),
    )
    monkeypatch.setattr(rerender_subject, "_run_playwright_fallback", lambda *_: 0)

    result = rerender_subject.main(
        [
            "--output-dir",
            str(tmp_path),
            "--fallback",
            "auto",
        ]
    )

    assert result == 0


def test_live_audit_router_exposes_command() -> None:
    assert_router_python_command(
        ops_router,
        "audit-live-grafana",
        expected_target="observability/grafana/audit_live_grafana_panels.py",
    )


def test_live_audit_reviewed_specs_cover_semantically_sensitive_panels() -> None:
    covered = {
        (spec.dashboard_uid, spec.panel_id): spec.title
        for spec in audit_subject.REVIEWED_PANEL_SPECS
    }

    assert (
        covered[("bioetl-control-plane-v1", 132)]
        == "Monitor: Manifest Write Failure Ratio"
    )
    assert (
        covered[("bioetl-control-plane-v1", 133)]
        == "Monitor: Ledger Append Failure Ratio"
    )
    assert (
        covered[("bioetl-control-plane-v1", 892)]
        == "Monitor: Checkpoint Freshness Lag (seconds)"
    )
    assert covered[("bioetl-dq-v2", 101)] == "Review: Latest Successful Data Timestamp"
    assert covered[("bioetl-dq-v2", 8)] == "Monitor: Worst Data Freshness Lag (seconds)"
    assert (
        covered[("bioetl-silver-reject-explorer", 3)] == "Track Reject Rate vs Bronze"
    )


def test_live_audit_classifies_prometheus_zero_and_nonzero_results() -> None:
    zero_payload = {
        "status": "success",
        "data": {"resultType": "vector", "result": [{"value": [1, "0"]}]},
    }
    nonzero_payload = {
        "status": "success",
        "data": {"resultType": "scalar", "result": [1, "5"]},
    }

    assert audit_subject._classify_prometheus_payload(zero_payload)[0] == "zero_result"
    assert (
        audit_subject._classify_prometheus_payload(nonzero_payload)[0]
        == "nonzero_result"
    )


def test_live_audit_marks_freshness_empty_result_as_error(monkeypatch: Any) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=892,
        title="Monitor: Checkpoint Freshness Lag (seconds)",
        source_kind="http",
        semantic_kind="freshness",
    )
    panel = {
        "targets": [
            {
                "url": "/ops/control-plane/checkpoint-freshness?pipeline=${pipeline}"
            }
        ]
    }
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="admin",
        pipeline="chembl_target",
        run_type="incremental",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(
        audit_subject,
        "_fetch_json",
        lambda *_args, **_kwargs: {"status": "UNKNOWN", "age_seconds": None},
    )

    result = audit_subject._audit_http_panel(
        spec,
        panel,
        config,
        app_base_url="http://localhost:8081",
    )

    assert result.classification == "empty_result"
    assert result.status == "error"


def test_live_audit_classifies_http_zero_state_and_nonzero() -> None:
    zero_payload = {"total": 0, "bronze_records": 0, "reject_ratio": 0.0}
    nonzero_payload = {"total": 2, "bronze_records": 10, "reject_ratio": 0.2}

    assert (
        audit_subject._classify_http_payload(zero_payload)[0]
        == "zero_state_unknown_denominator"
    )
    assert audit_subject._classify_http_payload(nonzero_payload)[0] == "nonzero_result"


def test_live_audit_classifies_http_freshness_zero_and_empty() -> None:
    zero_payload = {"status": "OK", "age_seconds": 0.0}
    empty_payload = {"status": "UNKNOWN", "age_seconds": None}

    assert (
        audit_subject._classify_http_freshness_payload(zero_payload)[0]
        == "zero_result"
    )
    assert (
        audit_subject._classify_http_freshness_payload(empty_payload)[0]
        == "empty_result"
    )


def test_live_audit_parse_args_uses_grafana_env_defaults(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("GRAFANA_BASE_URL", "http://grafana.local:3000")
    monkeypatch.setenv("GRAFANA_USERNAME", "viewer")
    monkeypatch.setenv("GRAFANA_PASSWORD", "secret")

    config = audit_subject._parse_args(["--output", str(tmp_path / "audit.json")])

    assert config.app_base_url == "http://localhost:8081"
    assert config.grafana_base_url == "http://grafana.local:3000"
    assert config.grafana_username == "viewer"
    assert config.grafana_password == "secret"


def test_live_audit_normalizes_docker_gateway_to_localhost() -> None:
    assert (
        audit_subject._normalize_host_access_url("http://host.docker.internal:8081")
        == "http://localhost:8081"
    )


def test_live_audit_resolves_http_backend_from_datasource_candidates(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        pipeline="chembl_target",
        run_type="incremental",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(
        audit_subject,
        "_discover_http_datasource_url",
        lambda *_args, **_kwargs: "http://host.docker.internal:8081",
    )

    def fake_fetch_json(url: str) -> object:
        if url == "http://localhost:8081/health/live":
            return {"status": "ok"}
        raise OSError(url)

    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    assert audit_subject._resolve_app_base_url(config) == "http://localhost:8081"


def test_grafana_audit_preflight_router_exposes_command() -> None:
    assert_router_python_command(
        ops_router,
        "check-grafana-audit-preflight",
        expected_target="observability/grafana/check_grafana_dashboard_audit_preflight.py",
    )


def test_grafana_audit_preflight_parser_uses_grafana_env_defaults(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("GRAFANA_USERNAME", "viewer")
    monkeypatch.setenv("GRAFANA_PASSWORD", "secret")

    parser = preflight_subject._build_parser()
    args = parser.parse_args(
        ["--screenshot-dir", str(tmp_path), "--json", "--skip-screenshot-check"]
    )

    assert args.grafana_username == "viewer"
    assert args.grafana_password == "secret"
    assert args.screenshot_dir == tmp_path
    assert args.json is True
    assert args.skip_screenshot_check is True


def test_grafana_audit_cycle_parser_exposes_backend_boolean_flag() -> None:
    parser = cycle_subject._build_parser()

    default_args = parser.parse_args([])
    disabled_args = parser.parse_args(["--no-ensure-observability-backend"])

    assert default_args.ensure_observability_backend is True
    assert disabled_args.ensure_observability_backend is False


def test_grafana_audit_preflight_detects_stale_screenshot(tmp_path: Path) -> None:
    dashboard_path = tmp_path / "bioetl-control-plane-v1.json"
    screenshot_dir = tmp_path / "screens"
    screenshot_dir.mkdir()
    screenshot_path = screenshot_dir / "bioetl-control-plane-v1.png"
    manifest_path = screenshot_dir / "render-manifest.json"
    dashboard_path.write_text('{"uid":"bioetl-control-plane-v1"}\n', encoding="utf-8")
    screenshot_path.write_bytes(b"png")
    manifest_path.write_text("{}\n", encoding="utf-8")
    os.utime(screenshot_path, (1, 1))
    os.utime(dashboard_path, (2, 2))

    result = preflight_subject._check_screenshot_artifacts(
        screenshot_dir
    )

    assert result.status == "error"
    assert "stale dashboard screenshots" in result.detail


def test_grafana_audit_preflight_run_checks_collects_ok_results(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        preflight_subject,
        "_check_http_json",
        lambda **kwargs: preflight_subject.PreflightCheck(
            name=str(kwargs["name"]),
            status="ok",
            detail=f"{kwargs['url']} reachable",
        ),
    )
    monkeypatch.setattr(
        audit_subject,
        "_resolve_app_base_url",
        lambda *_args, **_kwargs: "http://localhost:8081",
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_screenshot_artifacts",
        lambda _path: preflight_subject.PreflightCheck(
            name="screenshots",
            status="ok",
            detail="screens current",
        ),
    )

    checks = preflight_subject.run_checks(
        grafana_base_url="http://localhost:3000",
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
        screenshot_dir=tmp_path,
    )

    assert [check.name for check in checks] == [
        "grafana",
        "prometheus",
        "quarantine-explorer",
        "screenshots",
    ]
    assert all(check.status == "ok" for check in checks)


def test_grafana_audit_preflight_can_skip_screenshot_check(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        preflight_subject,
        "_check_http_json",
        lambda **kwargs: preflight_subject.PreflightCheck(
            name=str(kwargs["name"]),
            status="ok",
            detail="ok",
        ),
    )
    monkeypatch.setattr(
        audit_subject,
        "_resolve_app_base_url",
        lambda *_args, **_kwargs: "http://localhost:8081",
    )
    called = False

    def fake_screenshot_check(_path: Path) -> preflight_subject.PreflightCheck:
        nonlocal called
        called = True
        return preflight_subject.PreflightCheck(
            name="screenshots",
            status="ok",
            detail="screens current",
        )

    monkeypatch.setattr(
        preflight_subject,
        "_check_screenshot_artifacts",
        fake_screenshot_check,
    )

    checks = preflight_subject.run_checks(
        grafana_base_url="http://localhost:3000",
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
        screenshot_dir=tmp_path,
        include_screenshot_check=False,
    )

    assert [check.name for check in checks] == [
        "grafana",
        "prometheus",
        "quarantine-explorer",
    ]
    assert called is False


def test_grafana_audit_cycle_router_exposes_command() -> None:
    assert_router_python_command(
        ops_router,
        "run-grafana-audit-cycle",
        expected_target="observability/grafana/run_grafana_dashboard_audit_cycle.py",
    )


def test_grafana_audit_cycle_runs_preflight_rerender_and_live_audit(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: MagicMock(backend_available=True, message="ok"),
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append(("rerender", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append(("audit", list(argv))) or 0,
    )

    result = cycle_subject.main(
        [
            "--screenshot-dir",
            str(tmp_path),
            "--grafana-username",
            "admin",
            "--grafana-password",
            "changeme",
        ]
    )

    assert result == 0
    assert [name for name, _argv in calls] == [
        "preflight",
        "rerender",
        "preflight",
        "audit",
    ]
    assert "--skip-screenshot-check" in calls[0][1]
    assert "--skip-screenshot-check" not in calls[2][1]
    assert "http://127.0.0.1:8081" in calls[0][1]
    assert "http://127.0.0.1:8081" in calls[3][1]


def test_grafana_audit_cycle_stops_on_service_preflight_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: MagicMock(backend_available=True, message="ok"),
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append("preflight") or 1,
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append("rerender") or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append("audit") or 0,
    )

    result = cycle_subject.main(["--screenshot-dir", str(tmp_path)])

    assert result == 1
    assert calls == ["preflight"]


def test_grafana_audit_cycle_stops_when_backend_cannot_be_ensured(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: calls.append("ensure")
        or MagicMock(backend_available=False, message="bind failed"),
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append("preflight") or 0,
    )

    result = cycle_subject.main(["--screenshot-dir", str(tmp_path)])

    assert result == 1
    assert calls == ["ensure"]


def test_live_audit_writes_report(monkeypatch: Any, tmp_path: Path) -> None:
    output_path = tmp_path / "live-panel-audit.json"
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="admin",
        pipeline="chembl_target",
        run_type="incremental",
        range_hours=24,
        output_path=output_path,
    )
    results = [
        audit_subject.AuditResult(
            dashboard_uid="bioetl-dq-v2",
            panel_id=101,
            title="Review: Latest Successful Data Timestamp",
            source_kind="prometheus",
            semantic_kind="freshness",
            status="ok",
            classification="nonzero_result",
            detail="ok",
            query_preview="max(...)",
        )
    ]

    audit_subject._write_report(config, results)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["config"]["pipeline"] == "chembl_target"
    assert payload["results"][0]["panel_id"] == 101
