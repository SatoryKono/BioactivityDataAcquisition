"""Tests for file-backed contract registry persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.domain.control_plane.contract_registry import (
    ContractRegistry,
    ContractRegistryEntry,
)
from bioetl.domain.types.contract_identity import (
    CompatibilityLevel,
    ContractIdentity,
    LifecycleStatus,
)
from bioetl.infrastructure.control_plane.file_contract_registry_store import (
    FileContractRegistryStore,
    RegistryLoadError,
)


pytestmark = pytest.mark.unit

def _build_entry() -> ContractRegistryEntry:
    identity = ContractIdentity(
        contract_ref="test.contract.v1",
        contract_version="1.0.0",
        compatibility_level=CompatibilityLevel.PATCH,
        schema_hash="a" * 64,
        dq_policy_ref="test.dq.v1",
    )
    return ContractRegistryEntry(
        identity=identity,
        status=LifecycleStatus.ACTIVE,
        source_path="src/schemas/test.v1.yaml",
        published_artifacts=["data/schemas/test.v1.json"],
        supported_versions=["1.0.0"],
        migration_guides={},
        last_updated="2024-01-01T00:00:00+00:00",
        owners=["test-team"],
        dq_policy_ref="test.dq.v1",
    )


def test_registry_loading_from_yaml(tmp_path: Path) -> None:
    registry_data = {
        "version": "1.0",
        "entries": {
            "test.contract.v1": {
                "identity": {
                    "contract_version": "1.0.0",
                    "compatibility_level": "patch",
                    "schema_hash": "a" * 64,
                },
                "status": "active",
                "source_path": "src/schemas/test.v1.yaml",
                "supported_versions": ["1.0.0"],
                "last_updated": "2024-01-01T00:00:00+00:00",
                "owners": ["test-team"],
            }
        },
    }
    registry_file = tmp_path / "test_registry.yaml"
    registry_file.write_text(yaml.safe_dump(registry_data), encoding="utf-8")

    registry = FileContractRegistryStore(registry_file).load()

    assert len(registry.entries) == 1
    assert "test.contract.v1" in registry.entries
    assert registry.registry_hash is not None
    assert registry.registry_hash_v1 is not None
    assert registry.registry_hash_v2 is not None


def test_registry_loading_invalid_yaml(tmp_path: Path) -> None:
    invalid_file = tmp_path / "invalid_registry.yaml"
    invalid_file.write_text("invalid: yaml: content", encoding="utf-8")

    with pytest.raises(RegistryLoadError):
        FileContractRegistryStore(invalid_file).load()


def test_registry_filesystem_consistency_validation(tmp_path: Path) -> None:
    existing_source = tmp_path / "existing.yaml"
    existing_source.touch()

    registry = ContractRegistry()
    entry = ContractRegistryEntry(
        identity=ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        ),
        status=LifecycleStatus.ACTIVE,
        source_path=str(existing_source.absolute()),
        published_artifacts=["missing.json"],
        supported_versions=["1.0.0"],
        last_updated="2024-01-01T00:00:00+00:00",
        owners=["test-team"],
    )
    registry.register_contract(entry)

    store = FileContractRegistryStore(tmp_path / "registry.yaml")
    result = store.validate_filesystem_consistency(registry, tmp_path)

    assert result.valid is False
    assert len(result.issues) == 1
    assert "Published artifact not found" in result.issues[0].message


def test_registry_serialization_roundtrip(tmp_path: Path) -> None:
    registry = ContractRegistry()
    registry.register_contract(_build_entry())

    output_file = tmp_path / "test_registry.yaml"
    store = FileContractRegistryStore(output_file)
    store.save(registry)

    assert output_file.exists()
    data = yaml.safe_load(output_file.read_text(encoding="utf-8"))
    assert data["version"] == "1.0"
    assert "entries" in data
    assert "test.contract.v1" in data["entries"]

    loaded_registry = store.load()
    assert len(loaded_registry.entries) == 1
    assert loaded_registry.registry_hash is not None
