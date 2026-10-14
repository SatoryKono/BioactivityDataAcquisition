"""AST location refresh cannot silently expand protocol inventory or its budgets."""

from copy import deepcopy

import pytest

from scripts.engineering.qa.report_composition_protocol_inventory import (
    refresh_protocol_lines,
)

pytestmark = pytest.mark.unit


def inventory():
    return {
        "expected_total": 1,
        "max_composition_declarations_outside_contracts": 0,
        "protocols": [
            {
                "name": "Port",
                "path": "src/bioetl/application/ports/storage.py",
                "line": 1,
            }
        ],
    }


def test_location_refresh_preserves_config_and_budget():
    config = inventory()
    original = deepcopy(config)
    updated = refresh_protocol_lines(config, [{**config["protocols"][0], "line": 9}])
    assert config == original
    assert updated["protocols"][0]["line"] == 9
    assert updated["expected_total"] == config["expected_total"]
    assert updated["max_composition_declarations_outside_contracts"] == 0


def test_location_refresh_rejects_new_identity():
    with pytest.raises(ValueError, match="identities changed"):
        refresh_protocol_lines(
            inventory(),
            [
                {
                    "name": "Other",
                    "path": "src/bioetl/application/ports/storage.py",
                    "line": 9,
                }
            ],
        )


def test_location_refresh_rejects_gate_growth():
    config = inventory()
    config["protocols"][0]["path"] = "src/bioetl/composition/unsafe.py"
    with pytest.raises(ValueError):
        refresh_protocol_lines(config, [{**config["protocols"][0], "line": 9}])
