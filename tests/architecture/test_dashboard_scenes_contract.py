"""Architecture contracts for optional ADR-053 Scenes delivery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa.report_dashboard_scenes_parity import build_payload

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "grafana/plugins/bioetl-scenes-app"
ROUTES = PLUGIN / "src/routes/routes.json"
PARITY = ROOT / "reports/observability/scenes-parity-ledger.json"
RENDER_ROOT = ROOT / "reports/observability/scenes-baseline"


def _json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_scenes_package_is_optional_read_only_app_boundary() -> None:
    plugin = _json(PLUGIN / "src/plugin.json")
    contract = _json(ROUTES)

    assert plugin["type"] == "app"
    assert plugin["id"] == "bioetl-scenes-app"
    assert contract["read_only"] is True
    assert contract["hidden_datasources"] == []
    assert contract["write_actions"] == []
    assert not (PLUGIN / "pkg").exists()
    assert not (PLUGIN / "Magefile.go").exists()
    monitoring_compose = (ROOT / "docker-compose.monitoring.yml").read_text(
        encoding="utf-8"
    )
    assert "bioetl-scenes-app" not in monitoring_compose
    provisioner = (ROOT / "grafana/provisioning/dashboards/bioetl.yaml").read_text(
        encoding="utf-8"
    )
    assert "/var/lib/grafana/dashboards" in provisioner


def test_six_routes_keep_seven_json_fallback_uids() -> None:
    contract = _json(ROUTES)
    routes = contract["routes"]
    assert isinstance(routes, list)
    assert len(routes) == 6
    uids = {
        uid
        for route in routes
        for uid in route["compatibilityUids"]  # type: ignore[index]
    }
    assert uids == {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-incident-v1",
        "bioetl-run-explorer-v1",
    }
    for route in routes:
        assert len(route["decisionObjects"]) <= 5  # type: ignore[index]
        assert route["dominantLocalization"]  # type: ignore[index]


def test_committed_scenes_parity_ledger_matches_live_dashboards() -> None:
    assert _json(PARITY) == build_payload()
    summary = _json(PARITY)["summary"]
    assert summary["parity_status"] == "pass"  # type: ignore[index]
    assert summary["run_id_prometheus_violations"] == []  # type: ignore[index]
    assert summary["hidden_datasources"] == []  # type: ignore[index]
    assert summary["write_actions"] == []  # type: ignore[index]


@pytest.mark.parametrize(
    ("group", "theme", "width", "height"),
    [
        ("1024-dark", "dark", 1024, 768),
        ("1024-light", "light", 1024, 768),
        ("1600-dark", "dark", 1600, 900),
        ("1600-light", "light", 1600, 900),
    ],
)
def test_json_fallback_render_evidence_is_terminal_and_responsive(
    group: str,
    theme: str,
    width: int,
    height: int,
) -> None:
    manifest = _json(RENDER_ROOT / group / "render-manifest.json")
    requested = manifest["requested"]
    terminal = manifest["terminal_state_validation"]
    dashboards = manifest["dashboards"]

    assert requested["theme"] == theme  # type: ignore[index]
    assert requested["viewport"] == {  # type: ignore[index]
        "width": width,
        "height": height,
    }
    assert requested["capture_surface"] == "full"  # type: ignore[index]
    assert manifest["expand_collapsed_rows"] is True
    assert terminal["status"] == "ok"  # type: ignore[index]
    assert len(dashboards) == 7  # type: ignore[arg-type]
    assert all(  # type: ignore[union-attr]
        value == "ok"
        for value in terminal["dashboards"].values()  # type: ignore[index]
    )
