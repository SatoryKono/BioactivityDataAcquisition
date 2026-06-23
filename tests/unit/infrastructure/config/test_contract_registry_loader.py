"""Unit tests for the canonical contract-registry loader helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.contract_registry_loader import (
    DEFAULT_CONTRACT_REGISTRY_PATH,
    resolve_contract_registry_path,
)


@pytest.mark.unit
def test_resolve_contract_registry_path_defaults_to_canonical_relative_path() -> None:
    assert resolve_contract_registry_path() == DEFAULT_CONTRACT_REGISTRY_PATH


@pytest.mark.unit
def test_resolve_contract_registry_path_from_repo_root() -> None:
    repo_root = Path("/tmp/bioetl-repo")

    assert resolve_contract_registry_path(repo_root=repo_root) == (
        repo_root / DEFAULT_CONTRACT_REGISTRY_PATH
    )


@pytest.mark.unit
def test_resolve_contract_registry_path_from_configs_root() -> None:
    configs_root = Path("/tmp/bioetl-repo/configs")

    assert resolve_contract_registry_path(configs_root=configs_root) == (
        configs_root / "base" / "contract_registry.yaml"
    )


@pytest.mark.unit
def test_resolve_contract_registry_path_rejects_conflicting_roots() -> None:
    with pytest.raises(ValueError, match="either repo_root or configs_root"):
        resolve_contract_registry_path(
            repo_root=Path("/tmp/repo"),
            configs_root=Path("/tmp/repo/configs"),
        )
