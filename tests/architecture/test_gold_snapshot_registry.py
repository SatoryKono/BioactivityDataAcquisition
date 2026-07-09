"""Architecture guards for Gold snapshot governance wiring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
YamlMap = dict[str, Any]


def _load_matrix() -> YamlMap:
    with MATRIX_PATH.open(encoding="utf-8") as handle:
        return cast(YamlMap, yaml.safe_load(handle))


def _gold_registry_from_matrix() -> YamlMap:
    matrix = _load_matrix()
    fixture_governance = cast(YamlMap, matrix["fixture_governance"])
    return cast(YamlMap, fixture_governance["gold_snapshot_registry"])


@pytest.mark.architecture
class TestGoldSnapshotRegistry:
    """Keep Gold contract governance tied to an explicit registry surface."""

    def test_matrix_declares_gold_snapshot_registry(self) -> None:
        registry_meta = _gold_registry_from_matrix()
        registry_path = ROOT / cast(str, registry_meta["registry_path"])

        assert (
            registry_meta["scope"] == "bounded_contract_and_dq_sensitive_gold_baseline"
        )
        assert registry_path.exists()
        assert (ROOT / cast(str, registry_meta["helper_module"])).exists()
        assert (ROOT / cast(str, registry_meta["registry_test_module"])).exists()
        assert (ROOT / cast(str, registry_meta["dq_snapshot_test_module"])).exists()
        assert registry_meta["update_env_var"] == "UPDATE_SNAPSHOTS"

    def test_matrix_dq_snapshot_inventory_matches_registry_file(self) -> None:
        registry_meta = _gold_registry_from_matrix()
        registry_path = ROOT / cast(str, registry_meta["registry_path"])
        registry_payload = cast(
            YamlMap, json.loads(registry_path.read_text(encoding="utf-8"))
        )
        tracked_snapshot_paths = cast(
            list[str], registry_meta["tracked_snapshot_paths"]
        )
        actual_snapshot_paths = sorted(
            cast(str, output["snapshot_path"])
            for output in cast(
                YamlMap, registry_payload["dq_sensitive_outputs"]
            ).values()
        )

        assert tracked_snapshot_paths == actual_snapshot_paths
        for relative_path in tracked_snapshot_paths:
            assert (ROOT / relative_path).exists(), (
                f"Gold DQ snapshot is missing: {relative_path}"
            )

    def test_gold_snapshot_docs_reject_blanket_dq_bundle_expansion(self) -> None:
        registry_meta = _gold_registry_from_matrix()
        docs_path = ROOT / cast(str, registry_meta["documentation"])
        text = docs_path.read_text(encoding="utf-8")

        assert "DQ bundle coverage policy is intentionally bounded" in text
        assert "blanket snapshot-expansion policy" in text
        assert "adding a new Gold bundle requires registry" in text
        assert "not for every Gold" in text
        assert "entity in `entities`" in text
