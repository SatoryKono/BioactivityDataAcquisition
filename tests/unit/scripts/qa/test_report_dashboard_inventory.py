from __future__ import annotations

import pytest

import json
from pathlib import Path

import yaml

from scripts.engineering.qa import __main__ as qa_router
from scripts.engineering.qa import report_dashboard_inventory as inventory
from tests.helpers import run_main_in_process


pytestmark = pytest.mark.unit


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_canonical_test_layout(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    dashboards_dir = tmp_path / "grafana" / "dashboards"
    docs_dir = tmp_path / "docs" / "03-guides" / "dashboards"
    contracts_dir = docs_dir / "contracts"
    provisioning_path = (
        tmp_path / "grafana" / "provisioning" / "dashboards" / "bioetl.yaml"
    )

    dashboards_dir.mkdir(parents=True)
    contracts_dir.mkdir(parents=True)
    provisioning_path.parent.mkdir(parents=True, exist_ok=True)

    dashboard = {
        "uid": "bioetl-overview-v2",
        "title": "Overview",
        "style": "dark",
        "timezone": "browser",
        "refresh": "30s",
        "editable": True,
        "graphTooltip": 1,
        "tags": ["bioetl", "overview"],
        "templating": {"list": [{"name": "pipeline"}, {"name": "run_type"}]},
        "links": [],
        "panels": [
            {
                "id": 1000,
                "datasource": {"type": "prometheus", "uid": "prometheus"},
                "type": "text",
                "title": "Review Dashboard Navigation",
                "links": [
                    {"title": "2. Runtime", "url": "/d/bioetl-runtime/bioetl-runtime"},
                    {
                        "title": "3. Provider Health",
                        "url": "/d/bioetl-provider-health-v2/bioetl-provider-health-v2",
                    },
                    {"title": "4. Data Quality", "url": "/d/bioetl-dq-v2/bioetl-dq-v2"},
                    {
                        "title": "0. Control Plane",
                        "url": "/d/bioetl-control-plane-v1/bioetl-control-plane-v1",
                    },
                    {
                        "title": "5. Workflow",
                        "url": "/d/bioetl-workflow-overview/bioetl-workflow-overview",
                    },
                ],
                "panels": [],
            }
        ],
    }
    _write_json(dashboards_dir / "bioetl-overview-v2.json", dashboard)

    (docs_dir / "variables-guide.md").write_text(
        "| `bioetl-overview-v2` | `$pipeline`, `$run_type` |\n",
        encoding="utf-8",
    )
    (docs_dir / "monitoring-index.md").write_text(
        "bioetl-overview-v2\n", encoding="utf-8"
    )
    selector_contract = {
        "shipped_selector_registry": {
            "bioetl-overview-v2": {
                "visible_selectors": ["pipeline", "run_type"],
                "hidden_context_selectors": [],
                "hidden_detail_selectors": [],
            }
        }
    }
    (contracts_dir / "selector-contracts.yaml").write_text(
        yaml.safe_dump(selector_contract, sort_keys=False), encoding="utf-8"
    )
    dashboard_inventory = {
        "dashboards": [
            {
                "uid": "bioetl-overview-v2",
                "title": "Overview",
                "family": "primary",
                "navigation_id": 1,
                "data_sources": ["Prometheus"],
                "panel_count": 1,
                "key_panels": [
                    {
                        "id": 1000,
                        "title": "Review Dashboard Navigation",
                        "type": "text",
                    }
                ],
                "selector_variables": ["pipeline", "run_type"],
            }
        ]
    }
    (contracts_dir / "dashboard-inventory.yaml").write_text(
        yaml.safe_dump(dashboard_inventory, sort_keys=False), encoding="utf-8"
    )
    provisioning = {
        "apiVersion": 1,
        "providers": [
            {
                "name": "BioETL",
                "folderUid": "bioetl",
                "type": "file",
                "allowUiUpdates": False,
                "updateIntervalSeconds": 30,
                "options": {"path": "/var/lib/grafana/dashboards"},
            }
        ],
    }
    provisioning_path.write_text(
        yaml.safe_dump(provisioning, sort_keys=False), encoding="utf-8"
    )

    return dashboards_dir, docs_dir, contracts_dir, provisioning_path


def test_normalize_dashboard_payload_ignores_root_id_version_and_plugin_version() -> (
    None
):
    payload = {
        "dashboard": {
            "uid": "bioetl-runtime",
            "title": "Runtime",
            "id": 42,
            "version": 99,
            "panels": [
                {
                    "id": 1,
                    "title": "Panel",
                    "pluginVersion": "12.2.0",
                    "type": "stat",
                }
            ],
        },
        "meta": {"folderTitle": "BioETL"},
    }

    normalized = inventory._normalize_dashboard_payload(payload)

    assert normalized == {
        "uid": "bioetl-runtime",
        "title": "Runtime",
        "panels": [{"id": 1, "title": "Panel", "type": "stat"}],
    }


def test_compare_deployed_dashboards_ignores_benign_export_noise(
    tmp_path: Path, monkeypatch
) -> None:
    dashboards_dir, docs_dir, contracts_dir, provisioning_path = (
        _write_canonical_test_layout(tmp_path)
    )
    monkeypatch.setattr(inventory, "DASHBOARDS_DIR", dashboards_dir)
    monkeypatch.setattr(inventory, "VARIABLES_GUIDE", docs_dir / "variables-guide.md")
    monkeypatch.setattr(inventory, "MONITORING_INDEX", docs_dir / "monitoring-index.md")
    monkeypatch.setattr(
        inventory, "SELECTOR_CONTRACT", contracts_dir / "selector-contracts.yaml"
    )
    monkeypatch.setattr(
        inventory,
        "DASHBOARD_INVENTORY_CONTRACT",
        contracts_dir / "dashboard-inventory.yaml",
    )
    monkeypatch.setattr(inventory, "PROVISIONING_CONFIG", provisioning_path)

    deployed_dir = tmp_path / "deployed"
    deployed_dir.mkdir()
    deployed_payload = {
        "dashboard": {
            "uid": "bioetl-overview-v2",
            "title": "Overview",
            "style": "dark",
            "timezone": "browser",
            "refresh": "30s",
            "editable": True,
            "graphTooltip": 1,
            "tags": ["bioetl", "overview"],
            "templating": {"list": [{"name": "pipeline"}, {"name": "run_type"}]},
            "links": [],
            "id": 777,
            "version": 123,
            "panels": [
                    {
                        "id": 1000,
                        "datasource": {"type": "prometheus", "uid": "prometheus"},
                        "type": "text",
                        "title": "Review Dashboard Navigation",
                    "pluginVersion": "10.4.0",
                    "links": [
                        {
                            "title": "2. Runtime",
                            "url": "/d/bioetl-runtime/bioetl-runtime",
                        },
                        {
                            "title": "3. Provider Health",
                            "url": "/d/bioetl-provider-health-v2/bioetl-provider-health-v2",
                        },
                        {
                            "title": "4. Data Quality",
                            "url": "/d/bioetl-dq-v2/bioetl-dq-v2",
                        },
                        {
                            "title": "0. Control Plane",
                            "url": "/d/bioetl-control-plane-v1/bioetl-control-plane-v1",
                        },
                        {
                            "title": "5. Workflow",
                            "url": "/d/bioetl-workflow-overview/bioetl-workflow-overview",
                        },
                    ],
                    "panels": [],
                }
            ],
        }
    }
    _write_json(deployed_dir / "overview-export.json", deployed_payload)

    inv = inventory._load_inventory()
    errors, per_dashboard = inventory._compare_deployed_dashboards(
        inv, deployed_dir=deployed_dir
    )

    assert errors == []
    assert per_dashboard == {}


def test_build_health_summary_marks_noncanonical_root_config(
    tmp_path: Path, monkeypatch
) -> None:
    dashboards_dir, docs_dir, contracts_dir, provisioning_path = (
        _write_canonical_test_layout(tmp_path)
    )
    monkeypatch.setattr(inventory, "DASHBOARDS_DIR", dashboards_dir)
    monkeypatch.setattr(inventory, "VARIABLES_GUIDE", docs_dir / "variables-guide.md")
    monkeypatch.setattr(inventory, "MONITORING_INDEX", docs_dir / "monitoring-index.md")
    monkeypatch.setattr(
        inventory, "SELECTOR_CONTRACT", contracts_dir / "selector-contracts.yaml"
    )
    monkeypatch.setattr(
        inventory,
        "DASHBOARD_INVENTORY_CONTRACT",
        contracts_dir / "dashboard-inventory.yaml",
    )
    monkeypatch.setattr(inventory, "PROVISIONING_CONFIG", provisioning_path)

    dashboard_path = dashboards_dir / "bioetl-overview-v2.json"
    payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
    payload["style"] = "light"
    dashboard_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    inv = inventory._load_inventory()
    parity_errors, parity_by_dashboard = inventory._check_parity(inv)
    provisioning_errors, provisioning_metadata = (
        inventory._check_provisioning_contract()
    )
    summary = inventory._build_health_summary(
        inv,
        parity_issues=parity_by_dashboard,
        provisioning_issues=provisioning_errors,
        provisioning_metadata=provisioning_metadata,
    )

    assert parity_errors == []
    assert summary["overall_status"] == "degraded"
    dashboard_summary = summary["dashboards"][0]
    assert dashboard_summary["status"] == "degraded"
    assert "non-canonical style='light'" in dashboard_summary["issues"]


def test_scripts_engineering_qa_router_exposes_report_dashboard_inventory_command() -> (
    None
):
    spec = qa_router.COMMAND_SPECS["report-dashboard-inventory"]
    assert spec.runner == "module"
    assert spec.target == "scripts.engineering.qa.report_dashboard_inventory"


def test_check_parity_detects_dashboard_inventory_key_panel_drift(
    tmp_path: Path, monkeypatch
) -> None:
    dashboards_dir, docs_dir, contracts_dir, provisioning_path = (
        _write_canonical_test_layout(tmp_path)
    )
    monkeypatch.setattr(inventory, "DASHBOARDS_DIR", dashboards_dir)
    monkeypatch.setattr(inventory, "VARIABLES_GUIDE", docs_dir / "variables-guide.md")
    monkeypatch.setattr(inventory, "MONITORING_INDEX", docs_dir / "monitoring-index.md")
    monkeypatch.setattr(
        inventory, "SELECTOR_CONTRACT", contracts_dir / "selector-contracts.yaml"
    )
    monkeypatch.setattr(
        inventory,
        "DASHBOARD_INVENTORY_CONTRACT",
        contracts_dir / "dashboard-inventory.yaml",
    )
    monkeypatch.setattr(inventory, "PROVISIONING_CONFIG", provisioning_path)

    dashboard_inventory = yaml.safe_load(
        (contracts_dir / "dashboard-inventory.yaml").read_text(encoding="utf-8")
    )
    dashboard_inventory["dashboards"][0]["key_panels"][0]["type"] = "stat"
    (contracts_dir / "dashboard-inventory.yaml").write_text(
        yaml.safe_dump(dashboard_inventory, sort_keys=False), encoding="utf-8"
    )

    errors, per_dashboard = inventory._check_parity(inventory._load_inventory())

    assert any(
        "dashboard-inventory: bioetl-overview-v2 key_panel id=1000 type mismatch"
        in error
        for error in errors
    )
    assert "bioetl-overview-v2" in per_dashboard


def test_check_parity_detects_dashboard_inventory_datasource_drift(
    tmp_path: Path, monkeypatch
) -> None:
    dashboards_dir, docs_dir, contracts_dir, provisioning_path = (
        _write_canonical_test_layout(tmp_path)
    )
    monkeypatch.setattr(inventory, "DASHBOARDS_DIR", dashboards_dir)
    monkeypatch.setattr(inventory, "VARIABLES_GUIDE", docs_dir / "variables-guide.md")
    monkeypatch.setattr(inventory, "MONITORING_INDEX", docs_dir / "monitoring-index.md")
    monkeypatch.setattr(
        inventory, "SELECTOR_CONTRACT", contracts_dir / "selector-contracts.yaml"
    )
    monkeypatch.setattr(
        inventory,
        "DASHBOARD_INVENTORY_CONTRACT",
        contracts_dir / "dashboard-inventory.yaml",
    )
    monkeypatch.setattr(inventory, "PROVISIONING_CONFIG", provisioning_path)

    dashboard_inventory = yaml.safe_load(
        (contracts_dir / "dashboard-inventory.yaml").read_text(encoding="utf-8")
    )
    dashboard_inventory["dashboards"][0]["data_sources"] = ["Loki"]
    (contracts_dir / "dashboard-inventory.yaml").write_text(
        yaml.safe_dump(dashboard_inventory, sort_keys=False), encoding="utf-8"
    )

    errors, per_dashboard = inventory._check_parity(inventory._load_inventory())

    assert any(
        "dashboard-inventory: data_sources mismatch for bioetl-overview-v2"
        in error
        for error in errors
    )
    assert "bioetl-overview-v2" in per_dashboard


def test_qa_cli_report_dashboard_inventory_help_mentions_health_and_deployed_dir() -> (
    None
):
    result = run_main_in_process(inventory.main, "--help")

    assert result.returncode == 0
    assert "--health-summary" in result.stdout
    assert "--deployed-dir" in result.stdout
