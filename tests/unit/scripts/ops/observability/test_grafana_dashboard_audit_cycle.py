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
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest

from scripts.ops import __main__ as ops_router
from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject
from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight_subject,
)
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender_subject,
)
from scripts.ops.observability.grafana import (
    run_grafana_dashboard_audit_cycle as cycle_subject,
)
from tests.helpers import assert_router_python_command

pytestmark = pytest.mark.unit


def _backend_result(
    *,
    backend_available: bool,
    health_url: str = "http://127.0.0.1:8000/health",
    message: str = "ok",
    status: str = "started",
) -> SimpleNamespace:
    return SimpleNamespace(
        backend_available=backend_available,
        health_url=health_url,
        message=message,
        status=status,
    )


def _write_gate_sources(
    config: cycle_subject.AuditCycleConfig,
    *,
    semantic_status: str,
    render_status: str,
    occurrence_id: str | None = None,
) -> None:
    observed_occurrence = occurrence_id or config.occurrence_id
    config.semantic_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.semantic_output_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-16T00:00:00+00:00",
                "occurrence_id": observed_occurrence,
                "semantic_gate": {"status": semantic_status},
                "results": [{"dashboard_uid": "bioetl-dq-v2", "panel_id": 101}],
            }
        ),
        encoding="utf-8",
    )
    config.screenshot_dir.mkdir(parents=True, exist_ok=True)
    (config.screenshot_dir / "render-manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-16T00:00:00+00:00",
                "occurrence_id": observed_occurrence,
                "terminal_state_validation": {
                    "status": "ok" if render_status == "pass" else "error"
                },
                "dashboards": [
                    {
                        "uid": "bioetl-dq-v2",
                        "renderStatus": (
                            "rendered" if render_status == "pass" else "error"
                        ),
                        "terminalStateValidation": {
                            "status": "ok" if render_status == "pass" else "error",
                            "panelStates": [{"id": 101, "classification": "healthy"}],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def matching_gate_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """Materialize occurrence-matched sources for mocked successful gate stages."""
    write_gate_report = cycle_subject._write_gate_report

    def write_matching_gate_report(
        config: cycle_subject.AuditCycleConfig,
        *,
        semantic_status: str,
        render_status: str,
        semantic_detail: str,
        render_detail: str,
    ) -> bool:
        _write_gate_sources(
            config,
            semantic_status=semantic_status,
            render_status=render_status,
        )
        return write_gate_report(
            config,
            semantic_status=semantic_status,
            render_status=render_status,
            semantic_detail=semantic_detail,
            render_detail=render_detail,
        )

    monkeypatch.setattr(cycle_subject, "_write_gate_report", write_matching_gate_report)


def test_grafana_audit_preflight_router_exposes_command() -> None:
    assert_router_python_command(
        ops_router,
        "check-grafana-audit-preflight",
        expected_target="observability/grafana/check_grafana_dashboard_audit_preflight.py",
    )


def test_grafana_audit_preflight_parser_uses_grafana_env_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
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


def test_grafana_audit_preflight_render_auth_reports_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_unauthorized(*_args: object, **_kwargs: object) -> object:
        raise HTTPError(
            url="http://localhost:3000/api/frontend/settings",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(rerender_subject, "_request_json", raise_unauthorized)

    result = preflight_subject._check_grafana_render_auth(
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
    )

    assert result.name == "grafana-render-auth"
    assert result.status == "error"
    assert "Grafana auth failed" in result.detail


def test_grafana_audit_preflight_playwright_runtime_surfaces_probe_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rerender_subject,
        "check_playwright_runtime",
        lambda *_args, **_kwargs: (
            False,
            "Playwright browser executable is missing",
        ),
    )

    result = preflight_subject._check_playwright_runtime()

    assert result.name == "playwright-runtime"
    assert result.status == "error"
    assert "browser executable is missing" in result.detail


def test_grafana_audit_preflight_expanded_row_capture_requires_playwright() -> None:
    result = preflight_subject._check_expanded_row_capture(
        preflight_subject.PreflightCheck(
            name="playwright-runtime",
            status="error",
            detail="missing browser runtime",
        )
    )

    assert result.name == "expanded-row-capture"
    assert result.status == "error"
    assert "missing browser runtime" in result.detail


def test_grafana_audit_cycle_parser_exposes_backend_boolean_flag() -> None:
    parser = cycle_subject._build_parser()

    default_args = parser.parse_args([])
    disabled_args = parser.parse_args(
        [
            "--no-ensure-observability-backend",
            "--no-refresh-observability-backend",
            "--no-render-filled-only",
        ]
    )

    assert default_args.ensure_observability_backend is False
    assert default_args.refresh_observability_backend is False
    assert default_args.render_filled_only is True
    assert disabled_args.ensure_observability_backend is False
    assert disabled_args.refresh_observability_backend is False
    assert disabled_args.render_filled_only is False


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

    result = preflight_subject._check_screenshot_artifacts(screenshot_dir)

    assert result.status == "error"
    assert "stale dashboard screenshots" in result.detail


def _terminal_render_manifest(
    *,
    uid: str = "bioetl-dq-v2",
    classification: str = "healthy",
    theme: str = "light",
    width: int = 1024,
) -> dict[str, object]:
    file_name = f"{uid}.png"
    dashboard_source = {
        "path": f"grafana/dashboards/{uid}.json",
        "sha256": "b" * 64,
        "version": 1,
    }
    return {
        "capture_id": "unit-capture",
        "engine": "playwright",
        "expand_collapsed_rows": True,
        "file_count": 1,
        "file_set": [file_name],
        "immutable_manifest": (
            "render-manifest--selected-subset--unit-capture.json"
        ),
        "manifest_kind": "selected-subset",
        "requested": {
            "browser_zoom": 100,
            "kiosk_mode": "off",
            "viewport": {"width": width, "height": 2200},
            "theme": theme,
        },
        "source": {
            "commit_sha": "a" * 40,
            "working_tree_dirty": False,
            "dashboards": {uid: dict(dashboard_source)},
        },
        "capture_context": {
            "time_range": {
                "from": "now-12h",
                "to": "now",
                "timezone": "UTC",
            },
            "variables": {
                "workflow": "",
                "pipeline": "",
                "run_type": "",
                "run_id": "",
            },
            "row_state": {"expand_collapsed_rows": True},
        },
        "terminal_state_validation": {
            "status": "ok",
            "dashboards": {uid: "ok"},
        },
        "dashboards": [
            {
                "uid": uid,
                "file": file_name,
                "renderStatus": "rendered",
                "actualViewport": {"width": width, "height": 1900},
                "actualTheme": theme,
                "dashboardSource": dict(dashboard_source),
                "browserState": {
                    "requestedZoom": 100,
                    "cssZoom": "1",
                    "actualKiosk": "off",
                },
                "terminalStateValidation": {
                    "status": "ok",
                    "checkedPanelCount": 1,
                    "requiredPanelCount": 1,
                    "panelStates": [{"id": 13, "classification": classification}],
                },
            }
        ],
    }


@pytest.mark.parametrize("classification", ["healthy", "explicit-error", "valid-empty"])
def test_grafana_audit_preflight_accepts_silver_backend_terminal_states(
    classification: str,
) -> None:
    error = preflight_subject._validate_manifest_render_contract(
        _terminal_render_manifest(classification=classification),
        expected_uids=("bioetl-dq-v2",),
    )

    assert error is None


def test_grafana_audit_preflight_rejects_dashboard_source_provenance_drift(
    tmp_path: Path,
) -> None:
    manifest = _terminal_render_manifest()
    dashboards = manifest["dashboards"]
    assert isinstance(dashboards, list)
    dashboard = dashboards[0]
    assert isinstance(dashboard, dict)
    dashboard_source = dashboard["dashboardSource"]
    assert isinstance(dashboard_source, dict)
    dashboard_source["version"] = 2

    source = manifest["source"]
    assert isinstance(source, dict)
    source_dashboards = source["dashboards"]
    assert isinstance(source_dashboards, dict)
    assert source_dashboards["bioetl-dq-v2"]["version"] == 1

    (tmp_path / "bioetl-dq-v2.png").write_bytes(b"png")
    manifest_text = json.dumps(manifest)
    (tmp_path / "render-manifest.json").write_text(manifest_text, encoding="utf-8")
    immutable_name = manifest["immutable_manifest"]
    assert isinstance(immutable_name, str)
    (tmp_path / immutable_name).write_text(manifest_text, encoding="utf-8")

    error = preflight_subject._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-dq-v2",),
        screenshot_dir=tmp_path,
    )

    assert error == "render manifest dashboard bioetl-dq-v2 source provenance drift"


@pytest.mark.parametrize(
    "classification", ["telemetry-absent", "not-applicable", "incomplete"]
)
def test_grafana_audit_preflight_accepts_explicit_terminal_evidence_gaps(
    classification: str,
) -> None:
    manifest = _terminal_render_manifest(
        uid="bioetl-runtime", classification=classification
    )

    error = preflight_subject._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-runtime",),
    )

    assert error is None


def test_grafana_audit_preflight_requires_expanded_rows_and_exact_panel_ids() -> None:
    manifest = _terminal_render_manifest(uid="bioetl-runtime")
    manifest["expand_collapsed_rows"] = False

    expansion_error = preflight_subject._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-runtime",),
        expected_panel_ids={"bioetl-runtime": (13,)},
    )

    assert expansion_error == "render manifest must prove expand_collapsed_rows=true"

    manifest["expand_collapsed_rows"] = True
    coverage_error = preflight_subject._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-runtime",),
        expected_panel_ids={"bioetl-runtime": (13, 14)},
    )

    assert coverage_error is not None
    assert "panel coverage drift" in coverage_error


@pytest.mark.parametrize("classification", ["blank", "loading", "contradictory"])
def test_grafana_audit_preflight_rejects_non_terminal_panel_states(
    classification: str,
) -> None:
    error = preflight_subject._validate_manifest_render_contract(
        _terminal_render_manifest(classification=classification),
        expected_uids=("bioetl-dq-v2",),
    )

    assert error is not None
    assert "non-terminal or contradictory" in error


def test_grafana_audit_preflight_rejects_actual_viewport_or_theme_drift() -> None:
    manifest = _terminal_render_manifest()
    dashboards = manifest["dashboards"]
    assert isinstance(dashboards, list)
    dashboard = dashboards[0]
    assert isinstance(dashboard, dict)
    actual_viewport = dashboard["actualViewport"]
    assert isinstance(actual_viewport, dict)
    actual_viewport["width"] = 1600

    viewport_error = preflight_subject._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-dq-v2",),
    )

    assert viewport_error is not None
    assert "width drift" in viewport_error

    actual_viewport["width"] = 1024
    dashboard["actualTheme"] = "dark"
    theme_error = preflight_subject._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-dq-v2",),
    )

    assert theme_error is not None
    assert "theme drift" in theme_error


def test_grafana_audit_preflight_screenshot_check_enforces_terminal_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    screenshot_dir = tmp_path / "screens"
    screenshot_dir.mkdir()
    dashboard_path = tmp_path / "silver.json"
    screenshot_path = screenshot_dir / "bioetl-dq-v2.png"
    manifest_path = screenshot_dir / "render-manifest.json"
    dashboard_path.write_text(
        json.dumps({"uid": "bioetl-dq-v2", "panels": [{"id": 13, "type": "table"}]}),
        encoding="utf-8",
    )
    screenshot_path.write_bytes(b"png")
    manifest = _terminal_render_manifest(classification="loading")
    manifest_text = json.dumps(manifest)
    manifest_path.write_text(manifest_text, encoding="utf-8")
    immutable_name = manifest["immutable_manifest"]
    assert isinstance(immutable_name, str)
    (screenshot_dir / immutable_name).write_text(manifest_text, encoding="utf-8")
    os.utime(dashboard_path, (1, 1))
    os.utime(screenshot_path, (2, 2))
    monkeypatch.setattr(
        preflight_subject,
        "_expected_dashboard_screenshot_pairs",
        lambda *_args, **_kwargs: [
            (
                dashboard_path,
                screenshot_path,
                "bioetl-dq-v2",
            )
        ],
    )

    result = preflight_subject._check_screenshot_artifacts(screenshot_dir)

    assert result.status == "error"
    assert "non-terminal or contradictory" in result.detail


def test_grafana_audit_preflight_run_checks_collects_ok_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
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
        preflight_subject,
        "_check_grafana_render_auth",
        lambda **_kwargs: preflight_subject.PreflightCheck(
            name="grafana-render-auth",
            status="ok",
            detail="frontend settings auth probe succeeded",
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_playwright_runtime",
        lambda *_args, **_kwargs: preflight_subject.PreflightCheck(
            name="playwright-runtime",
            status="ok",
            detail="playwright ready",
        ),
    )
    monkeypatch.setattr(
        audit_subject,
        "_resolve_app_base_url",
        lambda *_args, **_kwargs: "http://localhost:8000",
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_screenshot_artifacts",
        lambda *args, **kwargs: preflight_subject.PreflightCheck(
            name="screenshots",
            status="ok",
            detail="screens current",
        ),
    )

    checks = preflight_subject.run_checks(
        grafana_base_url="http://localhost:3000",
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8000",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
        screenshot_dir=tmp_path,
    )

    assert [check.name for check in checks] == [
        "grafana",
        "grafana-render-auth",
        "prometheus",
        "playwright-runtime",
        "expanded-row-capture",
        "quarantine-explorer",
        "screenshots",
    ]
    assert all(check.status in {"ok", "not_applicable"} for check in checks)
    quarantine = next(check for check in checks if check.name == "quarantine-explorer")
    assert quarantine.status == "not_applicable"


def test_grafana_audit_preflight_can_skip_screenshot_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
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
        preflight_subject,
        "_check_grafana_render_auth",
        lambda **_kwargs: preflight_subject.PreflightCheck(
            name="grafana-render-auth",
            status="ok",
            detail="frontend settings auth probe succeeded",
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_playwright_runtime",
        lambda *_args, **_kwargs: preflight_subject.PreflightCheck(
            name="playwright-runtime",
            status="ok",
            detail="playwright ready",
        ),
    )
    monkeypatch.setattr(
        audit_subject,
        "_resolve_app_base_url",
        lambda *_args, **_kwargs: "http://localhost:8000",
    )
    called = False

    def fake_screenshot_check(
        _path: Path, *args, **kwargs
    ) -> preflight_subject.PreflightCheck:
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
        app_base_url="http://localhost:8000",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
        screenshot_dir=tmp_path,
        include_screenshot_check=False,
    )

    assert [check.name for check in checks] == [
        "grafana",
        "grafana-render-auth",
        "prometheus",
        "playwright-runtime",
        "expanded-row-capture",
        "quarantine-explorer",
    ]
    assert called is False


def test_grafana_audit_preflight_can_run_semantic_checks_without_render_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        preflight_subject,
        "_check_http_json",
        lambda **kwargs: preflight_subject.PreflightCheck(
            name=str(kwargs["name"]), status="ok", detail="ok"
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_grafana_render_auth",
        lambda **_kwargs: pytest.fail("render auth must be skipped"),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_playwright_runtime",
        lambda *_args, **_kwargs: pytest.fail("Playwright must be skipped"),
    )
    monkeypatch.setattr(
        audit_subject,
        "_resolve_app_base_url",
        lambda *_args, **_kwargs: "http://localhost:8000",
    )

    checks = preflight_subject.run_checks(
        grafana_base_url="http://localhost:3000",
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8000",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
        screenshot_dir=tmp_path,
        include_screenshot_check=False,
        include_render_checks=False,
    )

    assert [check.name for check in checks] == [
        "grafana",
        "prometheus",
        "quarantine-explorer",
    ]


def test_preflight_can_run_render_checks_without_semantic_checks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        preflight_subject,
        "_check_http_json",
        lambda **kwargs: preflight_subject.PreflightCheck(
            name=str(kwargs["name"]), status="ok", detail="ok"
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_grafana_render_auth",
        lambda **_kwargs: preflight_subject.PreflightCheck(
            name="grafana-render-auth", status="ok", detail="ok"
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_playwright_runtime",
        lambda *_args, **_kwargs: preflight_subject.PreflightCheck(
            name="playwright-runtime", status="ok", detail="ok"
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_expanded_row_capture",
        lambda _check: preflight_subject.PreflightCheck(
            name="expanded-row-capture", status="ok", detail="ok"
        ),
    )
    monkeypatch.setattr(
        audit_subject,
        "_resolve_app_base_url",
        lambda *_args, **_kwargs: pytest.fail(
            "semantic backend discovery must be skipped"
        ),
    )

    checks = preflight_subject.run_checks(
        grafana_base_url="http://localhost:3000",
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8000",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
        screenshot_dir=tmp_path,
        include_screenshot_check=False,
        include_semantic_checks=False,
    )

    assert [check.name for check in checks] == [
        "grafana",
        "grafana-render-auth",
        "playwright-runtime",
        "expanded-row-capture",
    ]


def test_grafana_audit_cycle_writes_independent_gate_evidence(tmp_path: Path) -> None:
    config = cycle_subject._parse_args(
        [
            "--screenshot-dir",
            str(tmp_path / "screenshots"),
            "--gate-output",
            str(tmp_path / "dashboard-release-gates.json"),
        ]
    )
    _write_gate_sources(config, semantic_status="pass", render_status="fail")

    cycle_subject._write_gate_report(
        config,
        semantic_status="pass",
        render_status="fail",
        semantic_detail="Live panel audit passed.",
        render_detail="Playwright unavailable.",
    )

    payload = json.loads(config.gate_output_path.read_text(encoding="utf-8"))
    assert payload["dashboard_semantic_gate"]["status"] == "pass"
    assert payload["dashboard_render_gate"]["status"] == "fail"
    assert payload["dashboard_semantic_gate"]["source_artifact"]["path"].endswith(
        "live-panel-audit.json"
    )
    assert payload["dashboard_semantic_gate"]["source_artifact"]["validated"] is True
    assert payload["dashboard_semantic_gate"]["source_artifact"]["dashboard_scope"] == [
        "bioetl-dq-v2#101"
    ]
    assert payload["dashboard_render_gate"]["source_artifact"]["dashboard_scope"] == []
    assert payload["dashboard_render_gate"]["source_artifact"]["validated"] is False


def test_grafana_audit_cycle_records_render_gate_when_semantic_gate_fails(
    tmp_path: Path,
) -> None:
    config = cycle_subject._parse_args(
        [
            "--screenshot-dir",
            str(tmp_path / "screenshots"),
            "--gate-output",
            str(tmp_path / "dashboard-release-gates.json"),
        ]
    )
    _write_gate_sources(config, semantic_status="fail", render_status="pass")

    cycle_subject._write_gate_report(
        config,
        semantic_status="fail",
        render_status="pass",
        semantic_detail="Live panel audit reported blocking semantic results.",
        render_detail="Screenshot render and manifest contract passed.",
    )

    payload = json.loads(config.gate_output_path.read_text(encoding="utf-8"))
    assert payload["dashboard_semantic_gate"]["status"] == "fail"
    assert payload["dashboard_render_gate"]["status"] == "pass"
    assert "manifest contract passed" in payload["dashboard_render_gate"]["detail"]


def test_grafana_gate_rejects_cross_occurrence_source_artifacts(
    tmp_path: Path,
) -> None:
    config = cycle_subject._parse_args(
        [
            "--screenshot-dir",
            str(tmp_path / "screenshots"),
            "--gate-output",
            str(tmp_path / "dashboard-release-gates.json"),
            "--occurrence-id",
            "current-occurrence",
        ]
    )
    _write_gate_sources(
        config,
        semantic_status="pass",
        render_status="pass",
        occurrence_id="stale-occurrence",
    )

    cycle_subject._write_gate_report(
        config,
        semantic_status="pass",
        render_status="pass",
        semantic_detail="claimed pass",
        render_detail="claimed pass",
    )

    payload = json.loads(config.gate_output_path.read_text(encoding="utf-8"))
    assert payload["dashboard_semantic_gate"]["status"] == "fail"
    assert payload["dashboard_render_gate"]["status"] == "fail"
    assert payload["release_passed"] is False


@pytest.mark.parametrize(
    "terminal_mutation",
    ["missing", "empty_panel_states", "failed_status"],
)
def test_grafana_gate_rejects_render_source_without_valid_panel_scope(
    tmp_path: Path,
    terminal_mutation: str,
) -> None:
    config = cycle_subject._parse_args(
        [
            "--screenshot-dir",
            str(tmp_path / "screenshots"),
            "--gate-output",
            str(tmp_path / "dashboard-release-gates.json"),
        ]
    )
    _write_gate_sources(config, semantic_status="pass", render_status="pass")
    manifest_path = config.screenshot_dir / "render-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    terminal_validation = manifest["dashboards"][0]["terminalStateValidation"]
    if terminal_mutation == "missing":
        manifest["dashboards"][0].pop("terminalStateValidation")
    elif terminal_mutation == "empty_panel_states":
        terminal_validation["panelStates"] = []
    else:
        terminal_validation["status"] = "error"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    cycle_subject._write_gate_report(
        config,
        semantic_status="pass",
        render_status="pass",
        semantic_detail="Semantic source passed.",
        render_detail="Render source claimed pass.",
    )

    payload = json.loads(config.gate_output_path.read_text(encoding="utf-8"))
    render_source = payload["dashboard_render_gate"]["source_artifact"]
    assert payload["dashboard_render_gate"]["status"] == "fail"
    assert render_source["terminal_status"] == "fail"
    assert render_source["dashboard_scope"] == []
    assert render_source["validated"] is False


def test_grafana_audit_cycle_router_exposes_command() -> None:
    assert_router_python_command(
        ops_router,
        "run-grafana-audit-cycle",
        expected_target="observability/grafana/run_grafana_dashboard_audit_cycle.py",
    )


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_runs_preflight_rerender_and_live_audit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: ("bioetl-dq-v2", "bioetl-runtime"),
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
        "audit",
        "rerender",
        "rerender",
        "preflight",
    ]
    assert "--skip-screenshot-check" in calls[0][1]
    assert "--skip-render-checks" in calls[0][1]
    assert "--skip-screenshot-check" not in calls[4][1]
    assert "--skip-semantic-checks" in calls[4][1]
    assert "--uids" in calls[2][1]
    assert "--fallback" in calls[2][1]
    assert calls[2][1][calls[2][1].index("--fallback") + 1] == "none"
    assert "--fallback" in calls[3][1]
    assert calls[3][1][calls[3][1].index("--fallback") + 1] == "playwright"
    assert any("render-api" in item for item in calls[2][1])
    assert str(tmp_path) in calls[3][1]
    assert "--screenshot-uids" in calls[4][1]
    assert "http://127.0.0.1:8000" in calls[0][1]
    assert "http://127.0.0.1:8000" in calls[1][1]
    assert "http://127.0.0.1:8000" in calls[4][1]


def test_grafana_audit_cycle_exit_code_uses_validated_release_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observed_claims: dict[str, str] = {}

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(cycle_subject, "drop_listening_backend_on_port", lambda _: True)
    monkeypatch.setattr(cycle_subject, "_run_preflight", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda *_args, **_kwargs: (),
    )
    monkeypatch.setattr(cycle_subject, "_run_live_audit", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(cycle_subject, "_run_rerender", lambda *_args, **_kwargs: 0)

    def reject_invalid_sources(
        _config: cycle_subject.AuditCycleConfig,
        *,
        semantic_status: str,
        render_status: str,
        semantic_detail: str,
        render_detail: str,
    ) -> bool:
        del semantic_detail, render_detail
        observed_claims.update(
            semantic_status=semantic_status,
            render_status=render_status,
        )
        return False

    monkeypatch.setattr(cycle_subject, "_write_gate_report", reject_invalid_sources)

    result = cycle_subject.main(
        ["--screenshot-dir", str(tmp_path), "--no-refresh-observability-backend"]
    )

    assert observed_claims == {"semantic_status": "pass", "render_status": "pass"}
    assert result == 1


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_keeps_render_gate_after_semantic_preflight_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append("preflight") or 1,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append("audit") or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda *_args, **_kwargs: (),
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append("rerender") or 0,
    )

    result = cycle_subject.main(
        ["--screenshot-dir", str(tmp_path), "--no-refresh-observability-backend"]
    )

    assert result == 1
    assert calls == ["preflight", "audit", "rerender", "rerender", "preflight"]


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_skips_semantic_network_when_backend_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: (
            calls.append("ensure")
            or _backend_result(
                backend_available=False,
                message="bind failed",
                status="failed",
            )
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_reuse_existing_backend_if_healthy",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_start_managed_observability_backend",
        lambda **_kwargs: cycle_subject.BackendEnsureOutcome(
            result=_backend_result(
                backend_available=False,
                message="managed failed",
                status="failed",
            ),
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_find_available_local_port",
        lambda: 18081,
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append("preflight") or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda *_args, **_kwargs: pytest.fail(
            "semantic discovery must be skipped without its backend"
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_run_live_audit",
        lambda *_args, **_kwargs: pytest.fail(
            "semantic live audit must be skipped without its backend"
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_run_rerender",
        lambda *_args, **_kwargs: calls.append("render") or 0,
    )

    result = cycle_subject.main(
        [
            "--screenshot-dir",
            str(tmp_path),
            "--ensure-observability-backend",
            "--no-refresh-observability-backend",
        ]
    )

    assert result == 1
    assert calls == ["ensure", "ensure", "render", "preflight"]


def test_nondefault_screenshot_dir_cannot_write_canonical_gate(tmp_path: Path) -> None:
    config = cycle_subject._parse_args(["--screenshot-dir", str(tmp_path)])

    assert config.gate_output_path == tmp_path / "dashboard-release-gates.json"
    assert config.gate_output_path != cycle_subject.DEFAULT_GATE_OUTPUT_PATH


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_keeps_both_gates_when_filled_discovery_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append("preflight") or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: (_ for _ in ()).throw(
            OSError("audit backend unavailable")
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_load_cached_filled_dashboard_uids",
        lambda _config: (_ for _ in ()).throw(FileNotFoundError("no cache")),
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

    result = cycle_subject.main(
        ["--screenshot-dir", str(tmp_path), "--no-refresh-observability-backend"]
    )

    assert result == 0
    assert calls == ["preflight", "audit", "rerender", "rerender", "preflight"]


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_uses_cached_filled_dashboards_after_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append(("audit", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append(("rerender", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "run_audit",
        lambda _config: (_ for _ in ()).throw(OSError("timed out")),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_load_cached_filled_dashboard_uids",
        lambda _config: ("bioetl-control-plane-v1", "bioetl-dq-v2"),
    )

    result = cycle_subject.main(
        ["--screenshot-dir", str(tmp_path), "--no-refresh-observability-backend"]
    )

    assert result == 0
    assert [name for name, _argv in calls] == [
        "preflight",
        "audit",
        "rerender",
        "rerender",
        "preflight",
    ]
    assert "--uids" in calls[2][1]
    assert "bioetl-control-plane-v1" in calls[2][1]
    assert "bioetl-dq-v2" in calls[2][1]


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_can_disable_filled_dashboard_filtering(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rerender_argv: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(cycle_subject.preflight, "main", lambda argv: 0)
    monkeypatch.setattr(cycle_subject.live_audit, "main", lambda argv: 0)
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: rerender_argv.extend(list(argv)) or 0,
    )

    result = cycle_subject.main(
        [
            "--screenshot-dir",
            str(tmp_path),
            "--no-render-filled-only",
        ]
    )

    assert result == 0
    assert "--uids" not in rerender_argv


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_retries_backend_on_fallback_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ensured_ports: list[int] = []
    calls: list[tuple[str, list[str]]] = []

    def fake_ensure(**kwargs: Any) -> SimpleNamespace:
        port = int(kwargs["port"])
        ensured_ports.append(port)
        if len(ensured_ports) == 1:
            return _backend_result(
                backend_available=False,
                health_url=f"http://127.0.0.1:{port}/health",
                message=(
                    "Existing backend is missing required audit capabilities and "
                    f"could not be restarted on port {port}."
                ),
                status="failed",
            )
        return _backend_result(
            backend_available=True,
            health_url=f"http://127.0.0.1:{port}/health",
            message="ok",
            status="started",
        )

    monkeypatch.setattr(
        cycle_subject, "ensure_observability_backend_started", fake_ensure
    )
    monkeypatch.setattr(
        cycle_subject, "drop_listening_backend_on_port", lambda _port: False
    )
    monkeypatch.setattr(
        cycle_subject,
        "probe_observability_backend_required_paths",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        cycle_subject,
        "probe_observability_backend",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(cycle_subject, "_find_available_local_port", lambda: 18081)
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: ("bioetl-dq-v2",),
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
            "--ensure-observability-backend",
            "--no-refresh-observability-backend",
        ]
    )

    assert result == 0
    assert ensured_ports == [8000, 18081]
    assert "http://127.0.0.1:18081" in calls[0][1]
    assert "http://127.0.0.1:18081" in calls[1][1]
    assert "http://127.0.0.1:18081" in calls[4][1]


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_reuses_existing_backend_when_fallback_start_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cycle_subject, "drop_listening_backend_on_port", lambda _port: False
    )
    monkeypatch.setattr(
        cycle_subject,
        "probe_observability_backend_required_paths",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        cycle_subject,
        "probe_observability_backend",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(cycle_subject, "_find_available_local_port", lambda: 18081)
    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(
            backend_available=False,
            health_url="http://127.0.0.1:18081/health",
            message="Detached backend did not become ready at http://127.0.0.1:18081/health.",
            status="failed",
        ),
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: ("bioetl-dq-v2",),
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
            "--ensure-observability-backend",
            "--no-refresh-observability-backend",
        ]
    )

    assert result == 0
    assert [name for name, _argv in calls] == [
        "preflight",
        "audit",
        "rerender",
        "rerender",
        "preflight",
    ]
    assert "http://127.0.0.1:8000" in calls[0][1]
    assert "http://127.0.0.1:8000" in calls[1][1]
    assert "http://127.0.0.1:8000" in calls[4][1]


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_uses_managed_backend_when_detached_backend_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cycle_subject, "drop_listening_backend_on_port", lambda _port: True
    )
    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(
            backend_available=False,
            health_url="http://127.0.0.1:8000/health",
            message="Detached backend did not become ready",
            status="failed",
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_reuse_existing_backend_if_healthy",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(cycle_subject, "_find_available_local_port", lambda: 18081)
    monkeypatch.setattr(
        cycle_subject,
        "_start_managed_observability_backend",
        lambda **_kwargs: cycle_subject.BackendEnsureOutcome(
            result=cycle_subject.ObservabilityBackendEnsureResult(
                status="started",
                health_url="http://127.0.0.1:8000/health",
                message="Managed backend started.",
            ),
            managed_process=MagicMock(poll=lambda: 0),
        ),
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: ("bioetl-dq-v2",),
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
            "--ensure-observability-backend",
            "--no-refresh-observability-backend",
        ]
    )

    assert result == 0
    assert [name for name, _argv in calls] == [
        "preflight",
        "audit",
        "rerender",
        "rerender",
        "preflight",
    ]
    assert "http://127.0.0.1:8000" in calls[0][1]


@pytest.mark.usefixtures("matching_gate_sources")
def test_grafana_audit_cycle_can_disable_backend_refresh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dropped: list[int] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(
            backend_available=True,
            health_url="http://127.0.0.1:8000/health",
            message="ok",
            status="reused",
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda port: dropped.append(int(port)) or True,
    )
    monkeypatch.setattr(cycle_subject.preflight, "main", lambda argv: 0)
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: (),
    )
    monkeypatch.setattr(cycle_subject.rerender, "main", lambda argv: 0)
    monkeypatch.setattr(cycle_subject.live_audit, "main", lambda argv: 0)

    result = cycle_subject.main(
        [
            "--screenshot-dir",
            str(tmp_path),
            "--no-refresh-observability-backend",
        ]
    )

    assert result == 0
    assert dropped == []


def test_live_audit_writes_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "live-panel-audit.json"
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8000",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
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
    assert payload["semantic_gate"]["status"] == "pass"


def test_live_audit_semantic_gate_requires_review_for_unreviewed_empty() -> None:
    result = audit_subject.AuditResult(
        dashboard_uid="bioetl-overview-v2",
        panel_id=999_001,
        title="Unreviewed empty",
        source_kind="prometheus",
        semantic_kind="prometheus_query",
        status="ok",
        classification="empty_result",
        detail="no samples",
        query_preview="sum(metric)",
    )

    evidence = audit_subject.semantic_gate_evidence([result])

    assert evidence["status"] == "review_required"
    assert evidence["review_count"] == 1
    assert evidence["panel_outcomes"][0]["decision"] == "review"


def test_live_audit_semantic_gate_accepts_reviewed_freshness_gap() -> None:
    result = audit_subject.AuditResult(
        dashboard_uid="bioetl-dq-v2",
        panel_id=101,
        title="Review: Latest Successful Data Timestamp",
        source_kind="prometheus",
        semantic_kind="freshness",
        status="ok",
        classification="telemetry_missing",
        detail="render UNKNOWN",
        query_preview="max(max_over_time(...))",
    )

    evidence = audit_subject.semantic_gate_evidence([result])

    assert evidence["status"] == "pass"
    assert evidence["panel_outcomes"][0]["decision"] == "pass_reviewed"


def test_live_audit_semantic_gate_blocks_invalid_query() -> None:
    result = audit_subject.AuditResult(
        dashboard_uid="bioetl-dq-v2",
        panel_id=101,
        title="Review: Latest Successful Data Timestamp",
        source_kind="prometheus",
        semantic_kind="freshness",
        status="error",
        classification="query_error",
        detail="bad_data",
        query_preview="invalid(",
    )

    evidence = audit_subject.semantic_gate_evidence([result])

    assert evidence["status"] == "fail"
    assert evidence["blocking_count"] == 1
    assert evidence["panel_outcomes"][0]["canonical_classification"] == "query_invalid"
