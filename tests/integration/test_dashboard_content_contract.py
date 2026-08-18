from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.engineering.qa import (
    generate_dashboard_content_contract as generator,
)
from scripts.engineering.qa import validate_dashboard_content_contract as subject

pytestmark = pytest.mark.integration


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_shipped_dashboard_content_contract_covers_every_shipped_panel() -> None:
    assert subject.validate_content_contract() == []
    assert subject.main([]) == 0
    contract = yaml.safe_load(subject.CONTENT_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(contract, dict)
    contract_records, errors = subject._contract_panel_records(contract)
    assert errors == []
    assert set(contract_records) == set(subject._dashboard_panel_records())


def test_shipped_dashboard_content_contract_is_generator_current() -> None:
    assert generator.main(["--check"]) == 0


def test_content_contract_fails_closed_when_shipped_panel_is_missing(
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
        "panel-content-contract.yaml:bioetl-runtime:9401: missing shipped panel"
        in errors
    )


def test_content_contract_fails_closed_when_non_key_shipped_panel_is_missing(
    tmp_path: Path,
) -> None:
    contract = yaml.safe_load(subject.CONTENT_CONTRACT_PATH.read_text(encoding="utf-8"))
    inventory = yaml.safe_load(subject.INVENTORY_PATH.read_text(encoding="utf-8"))
    assert isinstance(contract, dict)
    assert isinstance(inventory, dict)
    contract_records, contract_errors = subject._contract_panel_records(contract)
    inventory_records, inventory_errors = subject._inventory_key_panels(inventory)
    assert contract_errors == []
    assert inventory_errors == []
    uid, panel_id = next(
        key for key in sorted(contract_records) if key not in inventory_records
    )
    dashboards = contract["dashboards"]
    assert isinstance(dashboards, dict)
    dashboard = dashboards[uid]
    assert isinstance(dashboard, dict)
    panels = dashboard["panels"]
    assert isinstance(panels, dict)
    panels.pop(panel_id)
    contract_path = tmp_path / "panel-content-contract.yaml"
    _write_yaml(contract_path, contract)

    errors = subject.validate_content_contract(content_contract_path=contract_path)

    assert (
        f"panel-content-contract.yaml:{uid}:{panel_id}: missing shipped panel" in errors
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
