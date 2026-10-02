"""Persist selected reconciliation overrides with isolated execution roots."""

from bioetl.domain.config.effective_config_payloads import _runtime_overrides_payload
from bioetl.domain.control_plane.effective_config_artifact import (
    RuntimeOverrideSnapshot,
)


def test_selected_mode_and_isolated_roots_survive_payload_projection():
    overrides = RuntimeOverrideSnapshot(
        cli_overrides={"reconciliation_mode": "selected-snapshot", "limit": 1000},
        env_overrides={
            "BIOETL_DATA_DIR": "/isolated/data",
            "BIOETL_REPORT_ROOT": "/isolated/reports",
            "BIOETL_ARCHIVE_ROOT": "/isolated/archive",
        },
        override_hash="selected-root-identity",
    )
    payload = _runtime_overrides_payload(overrides, lambda value: dict(value))
    assert payload == {
        "cli_overrides": overrides.cli_overrides,
        "env_overrides": overrides.env_overrides,
        "override_hash": "selected-root-identity",
    }
    assert "runtime_adjustments" not in payload
    assert (
        _runtime_overrides_payload(RuntimeOverrideSnapshot(), lambda value: dict(value))
        == {}
    )
