from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.engineering.qa import validate_dashboard_content_contract as subject

pytestmark = pytest.mark.integration


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_shipped_dashboard_content_contract_is_complete() -> None:
    assert subject.validate_content_contract() == []
    assert subject.main([]) == 0


def test_content_contract_fails_closed_when_inventory_key_panel_is_missing(
    tmp_path: Path,
) -> None:
    contract = yaml.safe_load(subject.CONTENT_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(contract, dict)
    dashboards = contract["dashboards"]
    assert isinstance(dashboards, dict)
    runtime = dashboards["bioetl-runtime"]
    assert isinstance(runtime, dict)
    panels = runtime["panels"]
    assert isinstance(panels, dict)
    panels.pop("9401")
    contract_path = tmp_path / "panel-content-contract.yaml"
    _write_yaml(contract_path, contract)

    errors = subject.validate_content_contract(
        content_contract_path=contract_path,
    )

    assert (
        "panel-content-contract.yaml:bioetl-runtime:9401: missing inventory key panel"
        in errors
    )


def test_content_contract_fails_closed_when_table_columns_are_omitted(
    tmp_path: Path,
) -> None:
    contract = yaml.safe_load(subject.CONTENT_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(contract, dict)
    dashboards = contract["dashboards"]
    assert isinstance(dashboards, dict)
    explorer = dashboards["bioetl-run-explorer-v1"]
    assert isinstance(explorer, dict)
    panels = explorer["panels"]
    assert isinstance(panels, dict)
    records = panels["9403"]
    assert isinstance(records, dict)
    records.pop("required_columns")
    contract_path = tmp_path / "panel-content-contract.yaml"
    _write_yaml(contract_path, contract)

    errors = subject.validate_content_contract(
        content_contract_path=contract_path,
    )

    assert (
        "panel-content-contract.yaml:bioetl-run-explorer-v1:9403: table role "
        "requires required_columns" in errors
    )
