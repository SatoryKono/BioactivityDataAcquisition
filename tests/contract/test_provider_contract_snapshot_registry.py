"""Local registry checks for provider-facing contract snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from tests.contract._provider_contract_drift import (
    _resolve_path,
    assert_provider_snapshot_registry_shape,
    load_provider_contract_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
TEST_MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"

pytestmark = pytest.mark.no_api


def _load_contract_snapshot_registry() -> dict[str, Any]:
    payload = cast(
        dict[str, Any], yaml.safe_load(TEST_MATRIX_PATH.read_text(encoding="utf-8"))
    )
    return cast(
        dict[str, Any], payload["fixture_governance"]["contract_snapshot_registry"]
    )


@pytest.mark.parametrize(
    "provider",
    sorted(_load_contract_snapshot_registry()["providers"]),
)
def test_provider_snapshot_registry_shape(provider: str) -> None:
    snapshot = load_provider_contract_snapshot(provider)
    assert_provider_snapshot_registry_shape(snapshot)
    assert snapshot["provider"] == provider


def test_matrix_declared_providers_have_snapshot_test_module_and_update_path() -> None:
    registry = _load_contract_snapshot_registry()
    documentation_path = ROOT / cast(str, registry["documentation"])
    helper_module_path = ROOT / cast(str, registry["helper_module"])
    replay_module_path = ROOT / cast(str, registry["replay_registry_module"])
    registry_test_module_path = ROOT / cast(str, registry["registry_test_module"])
    replay_test_module_path = ROOT / cast(str, registry["replay_test_module"])

    assert registry["scope"] == "bounded_live_provider_baseline"
    assert registry["update_env_var"] == "UPDATE_SNAPSHOTS"
    assert documentation_path.exists()
    assert helper_module_path.exists()
    assert replay_module_path.exists()
    assert registry_test_module_path.exists()
    assert replay_test_module_path.exists()

    readme_text = documentation_path.read_text(encoding="utf-8")
    assert "UPDATE_SNAPSHOTS" in readme_text
    assert ".github/workflows/provider-contract-drift.yml" in readme_text
    assert ".github/workflows/contract-tests.yml" in readme_text
    assert "without live network" in readme_text.lower()

    for provider, provider_payload in cast(
        dict[str, dict[str, Any]], registry["providers"]
    ).items():
        snapshot = load_provider_contract_snapshot(provider)
        test_module_path = ROOT / cast(str, provider_payload["test_module"])
        assert test_module_path.exists(), provider

        test_module_text = test_module_path.read_text(encoding="utf-8")
        assert "UPDATE_SNAPSHOTS" in test_module_text
        assert "assert_provider_probe_matches_snapshot(" in test_module_text

        required_probes = cast(list[str], provider_payload["required_probes"])
        assert set(required_probes).issubset(snapshot["probes"])
        for probe in required_probes:
            assert f'"{probe}"' in test_module_text or f"'{probe}'" in test_module_text
        assert provider in readme_text


def test_root_list_snapshot_paths_are_supported() -> None:
    payload = [{"paperId": "paper-1"}]

    assert _resolve_path(payload, "[0].paperId") == "paper-1"
