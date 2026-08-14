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

import hashlib
import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight,
)
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender,
)
from scripts.ops.observability.grafana import (
    run_grafana_render_matrix as render_matrix,
)

pytestmark = pytest.mark.unit


def _png(width: int = 1024, height: int = 900) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
    )


def _manifest(*, classification: str = "incomplete") -> dict[str, object]:
    return {
        "engine": "playwright",
        "expand_collapsed_rows": True,
        "requested": {
            "viewport": {"width": 1024, "height": 2200},
            "theme": "light",
        },
        "terminal_state_validation": {
            "status": "ok",
            "dashboards": {"bioetl-runtime": "ok"},
        },
        "dashboards": [
            {
                "uid": "bioetl-runtime",
                "file": "bioetl-runtime.png",
                "renderStatus": "rendered",
                "actualViewport": {"width": 1024, "height": 1900},
                "actualTheme": "light",
                "typographyValidation": {
                    "status": "ok",
                    "bodyMinimumPx": 16.0,
                    "panelTitleMinimumPx": 14.0 * 4.0 / 3.0,
                    "violations": [],
                },
                "terminalStateValidation": {
                    "status": "ok",
                    "checkedPanelCount": 1,
                    "requiredPanelCount": 1,
                    "panelStates": [{"id": 1, "classification": classification}],
                },
            }
        ],
    }


def _bind_provenance(tmp_path: Path, manifest: dict[str, object]) -> None:
    source = {
        "path": "grafana/dashboards/bioetl-runtime.json",
        "sha256": "b" * 64,
        "version": 1,
    }
    dashboards = manifest["dashboards"]
    assert isinstance(dashboards, list)
    dashboard = dashboards[0]
    assert isinstance(dashboard, dict)
    dashboard["dashboardSource"] = source
    dashboard["browserState"] = {
        "requestedZoom": 100,
        "cssZoom": "1",
        "actualKiosk": "off",
    }
    requested = manifest["requested"]
    assert isinstance(requested, dict)
    requested.update({"browser_zoom": 100, "kiosk_mode": "off"})
    manifest.update(
        {
            "capture_id": "unit-capture",
            "manifest_kind": "selected-subset",
            "immutable_manifest": (
                "render-manifest--selected-subset--unit-capture.json"
            ),
            "file_count": 1,
            "file_set": ["bioetl-runtime.png"],
            "source": {
                "commit_sha": "a" * 40,
                "working_tree_dirty": False,
                "dashboards": {"bioetl-runtime": source},
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
        }
    )
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (tmp_path / "render-manifest.json").write_text(text, encoding="utf-8")
    (tmp_path / str(manifest["immutable_manifest"])).write_text(text, encoding="utf-8")


def test_git_capture_keeps_commit_when_dirty_probe_times_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(rerender, "_repo_root", lambda: tmp_path)

    def check_output(command: list[str], **_kwargs: object) -> str:
        if command[1:3] == ["rev-parse", "HEAD"]:
            return f"{'c' * 40}\n"
        raise rerender.subprocess.TimeoutExpired(command, timeout=15)

    monkeypatch.setattr(rerender.subprocess, "check_output", check_output)

    assert rerender._git_capture_source() == {
        "commit_sha": "c" * 40,
        "working_tree_dirty": None,
    }


@pytest.mark.parametrize(
    "classification", ["telemetry-absent", "not-applicable", "incomplete"]
)
def test_manifest_accepts_explicit_terminal_evidence_gaps(
    classification: str,
) -> None:
    error = preflight._validate_manifest_render_contract(
        _manifest(classification=classification),
        expected_uids=("bioetl-runtime",),
        expected_panel_ids={"bioetl-runtime": (1,)},
    )

    assert error is None


def test_manifest_requires_expanded_rows_and_exact_panel_coverage() -> None:
    manifest = _manifest()
    manifest["expand_collapsed_rows"] = False

    expansion_error = preflight._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-runtime",),
        expected_panel_ids={"bioetl-runtime": (1,)},
    )

    assert expansion_error == "render manifest must prove expand_collapsed_rows=true"

    manifest["expand_collapsed_rows"] = True
    coverage_error = preflight._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-runtime",),
        expected_panel_ids={"bioetl-runtime": (1, 2)},
    )

    assert coverage_error is not None
    assert "panel coverage drift" in coverage_error


def test_manifest_binds_panel_evidence_to_png_hash_and_dimensions(
    tmp_path: Path,
) -> None:
    screenshot = tmp_path / "bioetl-runtime.png"
    screenshot.write_bytes(_png())
    manifest = _manifest(classification="healthy")
    dashboards = manifest["dashboards"]
    assert isinstance(dashboards, list)
    dashboard = dashboards[0]
    assert isinstance(dashboard, dict)
    dashboard["screenshotEvidence"] = {
        "file": screenshot.name,
        "bytes": screenshot.stat().st_size,
        "width": 1024,
        "height": 900,
        "sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest(),
    }
    _bind_provenance(tmp_path, manifest)

    error = preflight._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-runtime",),
        expected_panel_ids={"bioetl-runtime": (1,)},
        screenshot_dir=tmp_path,
    )

    assert error is None

    evidence = dashboard["screenshotEvidence"]
    assert isinstance(evidence, dict)
    evidence["sha256"] = "0" * 64
    hash_error = preflight._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-runtime",),
        expected_panel_ids={"bioetl-runtime": (1,)},
        screenshot_dir=tmp_path,
    )

    assert hash_error is not None
    assert "sha256 drift" in hash_error


def test_immutable_manifest_rejects_occurrence_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = rerender.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="",
        service_account_token="",
        output_dir=tmp_path,
        width=1024,
        height=900,
        timeout_seconds=30,
        selected_uids=("bioetl-runtime",),
        fallback="playwright",
        occurrence_id="same-occurrence",
    )
    monkeypatch.setattr(
        rerender,
        "_dashboard_source_by_uid",
        lambda: {
            "bioetl-runtime": {
                "path": "grafana/dashboards/bioetl-runtime.json",
                "sha256": "b" * 64,
                "version": 1,
            },
            "other": {
                "path": "grafana/dashboards/other.json",
                "sha256": "c" * 64,
                "version": 1,
            },
        },
    )
    monkeypatch.setattr(
        rerender,
        "_git_capture_source",
        lambda: {"commit_sha": "a" * 40, "working_tree_dirty": False},
    )
    payload: dict[str, object] = {
        "dashboards": [{"uid": "bioetl-runtime", "file": "bioetl-runtime.png"}]
    }

    rerender._finalize_manifest(config, payload)
    with pytest.raises(FileExistsError):
        rerender._finalize_manifest(config, payload)


def test_playwright_retry_gate_rejects_unbound_or_dimension_drifted_png(
    tmp_path: Path,
) -> None:
    screenshot = tmp_path / "bioetl-runtime.png"
    screenshot.write_bytes(_png())
    config = rerender.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1024,
        height=2200,
        timeout_seconds=30.0,
        selected_uids=("bioetl-runtime",),
        fallback="playwright",
    )
    dashboard = {
        "uid": "bioetl-runtime",
        "file": screenshot.name,
        "renderStatus": "rendered",
        "renderedPanelCount": 1,
    }
    manifest: dict[str, object] = {"dashboards": [dashboard]}

    missing_error = rerender._playwright_manifest_screenshot_problem(config, manifest)

    assert missing_error is not None
    assert "lacks screenshotEvidence" in missing_error

    dashboard["screenshotEvidence"] = {
        "file": screenshot.name,
        "bytes": screenshot.stat().st_size,
        "width": 1600,
        "height": 900,
    }
    dimension_error = rerender._playwright_manifest_screenshot_problem(config, manifest)

    assert dimension_error is not None
    assert "dimension evidence drift" in dimension_error


def test_render_matrix_covers_standard_full_repeat_and_kiosk_profiles() -> None:
    names = {profile.name for profile in render_matrix.build_profiles()}

    assert names == {
        "1366x768-dark",
        "1366x768-light",
        "1440x900-dark",
        "1440x900-light",
        "1920x1080-dark",
        "1920x1080-light",
        "1440x900-dark-full",
        "1440x900-dark-repeat",
        "2560x1440-dark-kiosk",
        "2560x1440-light-kiosk",
        "3840x2160-dark-kiosk",
        "3840x2160-light-kiosk",
    }


def test_render_contract_rejects_missing_typography_evidence() -> None:
    manifest = _manifest(classification="data")
    dashboard = manifest["dashboards"][0]
    assert isinstance(dashboard, dict)
    dashboard.pop("typographyValidation")

    problem = preflight._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-runtime",),
    )

    assert problem == "render manifest dashboard bioetl-runtime lacks typography evidence"


def test_render_contract_rejects_title_font_floor_drift() -> None:
    manifest = _manifest(classification="data")
    dashboard = manifest["dashboards"][0]
    assert isinstance(dashboard, dict)
    typography = dashboard["typographyValidation"]
    assert isinstance(typography, dict)
    typography["panelTitleMinimumPx"] = 18.0

    problem = preflight._validate_manifest_render_contract(
        manifest,
        expected_uids=("bioetl-runtime",),
    )

    assert problem == "render manifest dashboard bioetl-runtime title typography floor drift"


def test_repeat_geometry_comparison_ignores_values_and_detects_layout_drift() -> None:
    baseline: dict[str, object] = {
        "dashboards": [
            {
                "uid": "bioetl-runtime",
                "layoutGeometry": {
                    "panelGeometry": {"1": {"x": 0, "y": 0, "width": 100, "height": 40}}
                },
                "terminalStateValidation": {
                    "panelStates": [{"id": 1, "bodyText": "10"}]
                },
            }
        ]
    }
    repeat: dict[str, object] = {
        "dashboards": [
            {
                "uid": "bioetl-runtime",
                "layoutGeometry": {
                    "panelGeometry": {"1": {"x": 0, "y": 0, "width": 100, "height": 40}}
                },
                "terminalStateValidation": {
                    "panelStates": [{"id": 1, "bodyText": "11"}]
                },
            }
        ]
    }

    assert render_matrix.compare_repeat_geometry(baseline, repeat)["status"] == "ok"

    repeat_dashboards = repeat["dashboards"]
    assert isinstance(repeat_dashboards, list)
    repeat_dashboard = repeat_dashboards[0]
    assert isinstance(repeat_dashboard, dict)
    repeat_dashboard["layoutGeometry"] = {
        "panelGeometry": {"1": {"x": 0, "y": 0, "width": 101, "height": 40}}
    }
    assert render_matrix.compare_repeat_geometry(baseline, repeat)["status"] == "error"


def test_retired_quarantine_explorer_is_not_applicable() -> None:
    assert preflight._quarantine_explorer_is_applicable() is False
    checks = [
        preflight.PreflightCheck("grafana", "ok", "reachable"),
        preflight.PreflightCheck("quarantine-explorer", "not_applicable", "retired"),
    ]

    assert preflight._exit_code_for_checks(checks) == preflight.EXIT_OK
