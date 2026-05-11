"""Parity gates across active ChEMBL entity configs, fixtures, and Gold contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.infrastructure.control_plane import FileContractRegistryStore

ROOT = Path(".")
ENTITY_CONFIG_ROOT = ROOT / "configs" / "entities" / "chembl"
FIXTURE_MANIFEST_PATH = ROOT / "configs" / "base" / "bronze_fixture_manifest.yaml"
CONTRACT_REGISTRY_PATH = ROOT / "configs" / "base" / "contract_registry.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    return payload


def _active_chembl_entity_configs() -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}
    for path in sorted(ENTITY_CONFIG_ROOT.glob("*.yaml")):
        payload = _load_yaml(path)
        if payload.get("status", "active") == "disabled":
            continue
        configs[path.stem] = payload
    return configs


def _fixture_manifest_entries() -> dict[str, dict[str, Any]]:
    payload = _load_yaml(FIXTURE_MANIFEST_PATH)
    fixtures = payload.get("fixtures")
    assert isinstance(fixtures, dict)
    return {
        str(key): value for key, value in fixtures.items() if isinstance(value, dict)
    }


def _gold_runtime_enabled(config: dict[str, Any]) -> bool:
    gold = ((config.get("pipeline") or {}).get("sink") or {}).get("gold") or {}
    if not isinstance(gold, dict):
        return True
    enabled = gold.get("enabled")
    return True if enabled is None else bool(enabled)


@pytest.mark.integration
def test_active_chembl_entity_configs_have_tracked_fixture_manifest_entries() -> None:
    configs = _active_chembl_entity_configs()
    fixtures = _fixture_manifest_entries()

    expected = {f"chembl/{entity}" for entity in configs}
    observed = {key for key in fixtures if key.startswith("chembl/")}

    assert expected <= observed, (
        "Active ChEMBL entities missing tracked Bronze fixtures: "
        f"{sorted(expected - observed)}"
    )

    for fixture_key in sorted(expected):
        entry = fixtures[fixture_key]
        fixture_path = ROOT / str(entry["fixture_path"])
        assert entry.get("fixture_kind") == "tracked_ci_sample"
        assert entry.get("validation_status") == "valid"
        assert fixture_path.exists(), f"Missing tracked fixture file: {fixture_path}"


@pytest.mark.integration
def test_active_gold_enabled_chembl_entities_have_active_contract_registry_entries() -> (
    None
):
    configs = _active_chembl_entity_configs()
    registry = FileContractRegistryStore(CONTRACT_REGISTRY_PATH).load()

    expected = {
        f"chembl.{entity}"
        for entity, config in configs.items()
        if _gold_runtime_enabled(config)
    }
    observed = {
        ref
        for ref, entry in registry.entries.items()
        if ref.startswith("chembl.") and entry.status.value == "active"
    }

    assert expected <= observed, (
        "Gold-enabled ChEMBL entities missing active contract registry entries: "
        f"{sorted(expected - observed)}"
    )


@pytest.mark.integration
def test_derived_chembl_fixture_manifest_entries_publish_source_entity_metadata() -> (
    None
):
    fixtures = _fixture_manifest_entries()

    publication_term = fixtures["chembl/publication_term"]
    subcellular_fraction = fixtures["chembl/subcellular_fraction"]

    assert publication_term.get("source_entity") == "chembl/publication"
    assert publication_term.get("resolution_kind") == (
        "recorded_provider_or_deterministic_derived_source"
    )
    assert subcellular_fraction.get("source_entity") == "chembl/assay"
    assert subcellular_fraction.get("resolution_kind") == "controlled_extraction_run"
