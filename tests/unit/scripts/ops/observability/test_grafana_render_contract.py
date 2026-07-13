from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight,
)
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender,
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
                "terminalStateValidation": {
                    "status": "ok",
                    "checkedPanelCount": 1,
                    "requiredPanelCount": 1,
                    "panelStates": [{"id": 1, "classification": classification}],
                },
            }
        ],
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
