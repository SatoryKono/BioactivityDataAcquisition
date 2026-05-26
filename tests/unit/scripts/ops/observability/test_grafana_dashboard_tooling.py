from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import URLError

from scripts.ops import __main__ as ops_router
from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject
from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight_subject,
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
        source_kind="prometheus",
        semantic_kind="freshness",
    )
    panel = {"targets": [{"expr": "max(bioetl_checkpoint_age_seconds)"}]}
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
        lambda *_args, **_kwargs: {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        },
    )

    result = audit_subject._audit_prometheus_panel(spec, panel, config)

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
    args = parser.parse_args(["--screenshot-dir", str(tmp_path), "--json"])

    assert args.grafana_username == "viewer"
    assert args.grafana_password == "secret"
    assert args.screenshot_dir == tmp_path
    assert args.json is True


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
