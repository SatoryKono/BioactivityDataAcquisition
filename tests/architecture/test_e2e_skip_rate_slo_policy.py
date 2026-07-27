"""E2E skip-rate SLO policy governance (T-08 / #6604)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SLO = _REPO_ROOT / "configs/quality/e2e_skip_rate_slo.yaml"
_E2E_CONFTEST = _REPO_ROOT / "tests/e2e/conftest.py"


def test_e2e_skip_rate_slo_policy_is_complete() -> None:
    payload = yaml.safe_load(_SLO.read_text(encoding="utf-8"))
    assert payload["policy"]["forbid_retries_to_heal_flakes"] is True
    assert payload["policy"]["forbid_assertion_weakening"] is True
    assert payload["slo"]["max_skip_rate_percent"] <= 15.0
    assert payload["slo"]["mode"] in {"advisory", "blocking"}
    assert "e2e" in payload["slo"]["evaluation_lanes"]
    assert set(payload["telemetry"]["required_fields"]) >= {
        "suite",
        "nodeid",
        "category",
        "reason_code",
    }


def test_e2e_harness_exposes_skip_reason_builder() -> None:
    source = _E2E_CONFTEST.read_text(encoding="utf-8")
    assert "def build_e2e_skip_reason" in source
    assert "run_pipeline_or_skip_transient" in source or "_skip_transient" in source
