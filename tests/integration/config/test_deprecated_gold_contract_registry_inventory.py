"""Governance checks for deprecated Gold contract registry entries."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.control_plane import FileContractRegistryStore

_ROOT = Path("configs")
_REGISTRY_PATH = _ROOT / "base" / "contract_registry.yaml"
_INVENTORY_PATH = _ROOT / "quality" / "deprecated_gold_contract_registry_inventory.yaml"
_ENTITY_CONFIGS_ROOT = _ROOT / "entities"
_FIXTURE_MANIFEST_PATH = _ROOT / "base" / "bronze_fixture_manifest.yaml"
_STANDARD_CONTRACT_PROVIDERS = frozenset(
    {
        "chembl",
        "crossref",
        "openalex",
        "pubchem",
        "pubmed",
        "semanticscholar",
        "uniprot",
    }
)
_ALLOWED_CLASSIFICATIONS = frozenset(
    {"gold_runtime_disabled", "fixture_only_surface", "compatibility_alias"}
)


def _inventory_entries() -> dict[str, dict[str, object]]:
    payload = yaml.safe_load(_INVENTORY_PATH.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    entries = payload.get("entries")
    assert isinstance(entries, dict)
    return {
        str(key): value for key, value in entries.items() if isinstance(value, dict)
    }


def _fixture_manifest() -> dict[str, object]:
    payload = yaml.safe_load(_FIXTURE_MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    fixtures = payload.get("fixtures")
    assert isinstance(fixtures, dict)
    return fixtures


def _deprecated_standard_registry_refs() -> dict[str, object]:
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()
    return {
        ref: entry
        for ref, entry in registry.entries.items()
        if ref.split(".", maxsplit=1)[0] in _STANDARD_CONTRACT_PROVIDERS
        and entry.status.value == "deprecated"
    }


def _gold_runtime_enabled(config_path: Path) -> bool:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    assert isinstance(config, dict)
    pipeline = config.get("pipeline")
    if not isinstance(pipeline, dict):
        return True
    sink = pipeline.get("sink")
    if not isinstance(sink, dict):
        return True
    gold = sink.get("gold")
    if not isinstance(gold, dict):
        return True
    enabled = gold.get("enabled")
    return True if enabled is None else bool(enabled)


@pytest.mark.integration
def test_deprecated_standard_registry_refs_are_inventory_governed() -> None:
    inventory = _inventory_entries()
    deprecated_refs = _deprecated_standard_registry_refs()

    assert set(deprecated_refs) == set(inventory), (
        "Deprecated standard Gold registry refs must be explicitly inventoried: "
        f"registry_only={sorted(set(deprecated_refs) - set(inventory))}, "
        f"inventory_only={sorted(set(inventory) - set(deprecated_refs))}"
    )


@pytest.mark.integration
def test_deprecated_gold_contract_inventory_has_known_classifications() -> None:
    inventory = _inventory_entries()

    classifications = {
        ref: str(entry.get("classification", ""))
        for ref, entry in sorted(inventory.items())
    }

    assert set(classifications.values()) <= _ALLOWED_CLASSIFICATIONS


@pytest.mark.integration
def test_gold_runtime_disabled_deprecated_contracts_have_disabled_entity_configs() -> (
    None
):
    inventory = _inventory_entries()

    for contract_ref, entry in sorted(inventory.items()):
        if entry.get("classification") != "gold_runtime_disabled":
            continue
        entity_config_path = entry.get("entity_config_path")
        assert isinstance(entity_config_path, str)
        config_path = Path(entity_config_path)
        assert config_path.exists()
        assert _gold_runtime_enabled(config_path) is False
        assert entry.get("replacement_contract_ref") is None


@pytest.mark.integration
def test_fixture_only_deprecated_contracts_are_manifest_backed() -> None:
    inventory = _inventory_entries()
    fixtures = _fixture_manifest()

    for contract_ref, entry in sorted(inventory.items()):
        if entry.get("classification") != "fixture_only_surface":
            continue
        fixture_manifest_key = entry.get("fixture_manifest_key")
        assert isinstance(fixture_manifest_key, str)
        fixture = fixtures.get(fixture_manifest_key)
        assert isinstance(fixture, dict), (
            f"Missing fixture manifest entry for deprecated contract {contract_ref}: "
            f"{fixture_manifest_key}"
        )
        assert fixture.get("fixture_kind") == "tracked_ci_sample"
        assert fixture.get("validation_status") == "valid"


@pytest.mark.integration
def test_compatibility_alias_deprecated_contracts_point_to_active_replacements() -> (
    None
):
    inventory = _inventory_entries()
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()

    for contract_ref, entry in sorted(inventory.items()):
        if entry.get("classification") != "compatibility_alias":
            continue
        replacement_contract_ref = entry.get("replacement_contract_ref")
        assert isinstance(replacement_contract_ref, str)
        assert registry.entries[contract_ref].status.value == "deprecated"
        assert registry.entries[replacement_contract_ref].status.value == "active"
        assert (
            registry.entries[contract_ref].published_artifacts
            == registry.entries[replacement_contract_ref].published_artifacts
        )
