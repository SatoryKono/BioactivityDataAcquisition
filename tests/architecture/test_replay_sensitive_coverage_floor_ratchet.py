"""Architecture guardrails for replay-sensitive module coverage floors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = PROJECT_ROOT / "configs/quality/module_coverage_gates.yaml"
INVENTORY_PATH = PROJECT_ROOT / "reports/quality/module-coverage-inventory.json"


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_replay_sensitive_module_coverage_floors_hold() -> None:
    """Replay-sensitive modules must stay above committed coverage floors."""
    policy = _load_yaml(POLICY_PATH).get("replay_sensitive_coverage_floors", {})
    assert isinstance(policy, dict)
    assert policy.get("mode") == "fail-fast"

    modules = policy.get("modules", [])
    assert isinstance(modules, list) and modules

    inventory = _load_json(INVENTORY_PATH)
    rows = inventory.get("modules", [])
    assert isinstance(rows, list)
    by_module = {
        str(row["module"]): row for row in rows if isinstance(row, dict) and row.get("module")
    }

    for entry in modules:
        assert isinstance(entry, dict)
        module_name = entry.get("module")
        min_coverage = entry.get("min_coverage_percent")
        owner_tests = entry.get("owner_tests", [])
        assert isinstance(module_name, str)
        assert isinstance(min_coverage, (int, float))
        assert isinstance(owner_tests, list) and owner_tests
        for test_path in owner_tests:
            assert (PROJECT_ROOT / str(test_path)).exists()

        row = by_module.get(module_name)
        assert row is not None, f"Missing inventory row for {module_name}"
        coverage = row.get("coverage_percent")
        assert isinstance(coverage, (int, float))
        assert coverage >= float(min_coverage), (
            f"{module_name} coverage {coverage} below floor {min_coverage}"
        )
