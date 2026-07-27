"""Integration vs e2e role matrix governance (T-10 / #6607)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MATRIX = _REPO_ROOT / "configs/quality/test_suite_role_matrix.yaml"


def test_suite_role_matrix_declares_provider_ownership() -> None:
    payload = yaml.safe_load(_MATRIX.read_text(encoding="utf-8"))
    assert "integration" in payload["roles"]
    assert "e2e" in payload["roles"]
    assert "gold_when_enabled" in payload["roles"]["e2e"]["required_stages"]
    ownership = payload["provider_ownership"]
    assert "chembl_activity" in ownership
    assert ownership["chembl_activity"]["e2e"] == "full_cycle_with_gold"
    assert payload["demotions"]
