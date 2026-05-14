"""Unit tests for DQContractConfigLoader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.infrastructure.config.dq_contract_config_loader import (
    DQContractConfigLoader,
    load_dq_config_for_pipeline,
)


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


@pytest.fixture
def temp_contract_root(tmp_path: Path) -> Path:
    """Create minimal configs tree with registry and DQ contract file."""
    registry_payload = {
        "version": "1.0",
        "entries": {
            "chembl.activity": {
                "identity": {
                    "contract_version": "1.0.0",
                    "compatibility_level": "major",
                    "schema_hash": "a" * 64,
                    "dq_policy_ref": "chembl.dq.v1",
                    "rule_bundle_version": "dq-rules.v1.0",
                },
                "status": "active",
                "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_activity_assay_schemas.py",
                "published_artifacts": [
                    "../../docs/04-reference/contracts/gold/chembl_activity_v1.0.json"
                ],
                "supported_versions": ["1.0.0"],
                "migration_guides": {},
                "last_updated": "2026-03-25T00:00:00Z",
                "owners": ["chembl-team"],
                "dq_policy_ref": "chembl.dq.v1",
                "rule_bundle_version": "dq-rules.v1.0",
            }
        },
    }
    _write_yaml(tmp_path / "base" / "contract_registry.yaml", registry_payload)

    contract_payload = {
        "default_disposition_policy": "warn",
        "strictness_mode": "moderate",
        "thresholds": {"soft_fail": 0.03, "hard_fail": 0.25},
    }
    _write_yaml(tmp_path / "contracts" / "chembl" / "activity.yaml", contract_payload)
    return tmp_path


def test_loader_aligns_identity_from_registry(temp_contract_root: Path) -> None:
    """Loader should align identity tuple from registry when missing in file."""
    loader = DQContractConfigLoader(temp_contract_root)
    dq_config = loader.load_dq_config_for_pipeline("chembl_activity")

    assert dq_config.contract_ref == "chembl.activity"
    assert dq_config.contract_version == "1.0.0"
    assert dq_config.rule_bundle_version == "dq-rules.v1.0"
    assert dq_config.default_disposition_policy == DQDisposition.WARN
    assert dq_config.soft_fail_threshold == pytest.approx(0.03)
    assert dq_config.hard_fail_threshold == pytest.approx(0.25)


def test_loader_rejects_registry_identity_mismatch(temp_contract_root: Path) -> None:
    """Loader should fail when contract file identity conflicts with registry."""
    contract_path = temp_contract_root / "contracts" / "chembl" / "activity.yaml"
    _write_yaml(
        contract_path,
        {
            "contract_ref": "chembl.invalid",
            "contract_version": "1.0.0",
            "rule_bundle_version": "dq-rules.v1.0",
            "dq_policy_ref": "chembl.dq.v1",
        },
    )

    loader = DQContractConfigLoader(temp_contract_root)
    with pytest.raises(ValueError, match="contract_ref mismatch"):
        _ = loader.load_dq_config_for_pipeline("chembl_activity")


def test_loader_supports_flat_threshold_fields(temp_contract_root: Path) -> None:
    """Flat *_threshold fields should override nested threshold defaults."""
    contract_path = temp_contract_root / "contracts" / "chembl" / "activity.yaml"
    _write_yaml(
        contract_path,
        {
            "soft_fail_threshold": 0.04,
            "hard_fail_threshold": 0.31,
            "thresholds": {"soft_fail": 0.01, "hard_fail": 0.10},
        },
    )

    loader = DQContractConfigLoader(temp_contract_root)
    dq_config = loader.load_dq_config_for_pipeline("chembl_activity")
    assert dq_config.soft_fail_threshold == pytest.approx(0.04)
    assert dq_config.hard_fail_threshold == pytest.approx(0.31)


def test_loader_prefers_strict_dq_validation_key(temp_contract_root: Path) -> None:
    """Canonical contract key should drive DQ strictness semantics."""
    contract_path = temp_contract_root / "contracts" / "chembl" / "activity.yaml"
    _write_yaml(
        contract_path,
        {
            "strict_dq_validation": True,
            "strict_validation": False,
        },
    )

    loader = DQContractConfigLoader(temp_contract_root)
    dq_config = loader.load_dq_config_for_pipeline("chembl_activity")
    assert dq_config.strict_validation is True


def test_loader_supports_legacy_strict_validation_alias(temp_contract_root: Path) -> (
    None
):
    """Legacy contract key remains readable during config migration."""
    contract_path = temp_contract_root / "contracts" / "chembl" / "activity.yaml"
    _write_yaml(
        contract_path,
        {
            "strict_validation": True,
        },
    )

    loader = DQContractConfigLoader(temp_contract_root)
    dq_config = loader.load_dq_config_for_pipeline("chembl_activity")
    assert dq_config.strict_validation is True


def test_loader_does_not_fallback_to_legacy_dq_files(tmp_path: Path) -> None:
    """Missing contract files should fail fast without consulting legacy *_dq files."""
    registry_payload = {
        "version": "1.0",
        "entries": {
            "chembl.activity": {
                "identity": {
                    "contract_version": "1.0.0",
                    "compatibility_level": "major",
                    "schema_hash": "a" * 64,
                    "dq_policy_ref": "chembl.dq.v1",
                    "rule_bundle_version": "dq-rules.v1.0",
                },
                "status": "active",
                "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_activity_assay_schemas.py",
                "published_artifacts": [
                    "../../docs/04-reference/contracts/gold/chembl_activity_v1.0.json"
                ],
                "supported_versions": ["1.0.0"],
                "migration_guides": {},
                "last_updated": "2026-03-25T00:00:00Z",
                "owners": ["chembl-team"],
                "dq_policy_ref": "chembl.dq.v1",
                "rule_bundle_version": "dq-rules.v1.0",
            }
        },
    }
    _write_yaml(tmp_path / "base" / "contract_registry.yaml", registry_payload)
    _write_yaml(
        tmp_path / "entities" / "chembl" / "activity_dq.yaml",
        {
            "contract_ref": "chembl.activity",
            "default_disposition_policy": "warn",
            "strictness_mode": "moderate",
        },
    )
    _write_yaml(
        tmp_path / "providers" / "chembl_dq.yaml",
        {
            "contract_ref": "chembl.activity",
            "default_disposition_policy": "warn",
            "strictness_mode": "moderate",
        },
    )

    loader = DQContractConfigLoader(tmp_path)
    with pytest.raises(FileNotFoundError, match="DQ contract config not found"):
        _ = loader.load_dq_config_for_pipeline("chembl_activity")


def test_loader_fails_fast_when_registry_is_missing(tmp_path: Path) -> None:
    """Contract config loading must not silently bypass missing registry."""
    _write_yaml(
        tmp_path / "contracts" / "chembl" / "activity.yaml",
        {
            "default_disposition_policy": "warn",
            "strictness_mode": "moderate",
        },
    )

    loader = DQContractConfigLoader(tmp_path)
    with pytest.raises(FileNotFoundError, match="DQ contract registry not found"):
        _ = loader.load_dq_config_for_pipeline("chembl_activity")


def test_loader_fails_fast_when_registry_entry_is_missing(tmp_path: Path) -> None:
    """Every loaded DQ contract must be registered by contract_ref."""
    _write_yaml(tmp_path / "base" / "contract_registry.yaml", {"entries": {}})
    _write_yaml(
        tmp_path / "contracts" / "chembl" / "activity.yaml",
        {
            "default_disposition_policy": "warn",
            "strictness_mode": "moderate",
        },
    )

    loader = DQContractConfigLoader(tmp_path)
    with pytest.raises(KeyError, match=r"chembl\.activity"):
        _ = loader.load_dq_config_for_pipeline("chembl_activity")


def test_loader_fails_fast_on_malformed_registry_entries(tmp_path: Path) -> None:
    """Malformed registry entries payloads are governance failures."""
    _write_yaml(
        tmp_path / "base" / "contract_registry.yaml",
        {"entries": ["chembl.activity"]},
    )
    _write_yaml(
        tmp_path / "contracts" / "chembl" / "activity.yaml",
        {
            "default_disposition_policy": "warn",
            "strictness_mode": "moderate",
        },
    )

    loader = DQContractConfigLoader(tmp_path)
    with pytest.raises(ValueError, match="entries must be a mapping"):
        _ = loader.load_dq_config_for_pipeline("chembl_activity")


def test_loader_fails_fast_on_malformed_registry_identity(tmp_path: Path) -> None:
    """Registry entry identity must be a mapping with DQ identity fields."""
    _write_yaml(
        tmp_path / "base" / "contract_registry.yaml",
        {
            "entries": {
                "chembl.activity": {
                    "identity": "chembl.activity.v1",
                    "dq_policy_ref": "chembl.dq.v1",
                    "rule_bundle_version": "dq-rules.v1.0",
                }
            }
        },
    )
    _write_yaml(
        tmp_path / "contracts" / "chembl" / "activity.yaml",
        {
            "default_disposition_policy": "warn",
            "strictness_mode": "moderate",
        },
    )

    loader = DQContractConfigLoader(tmp_path)
    with pytest.raises(ValueError, match="identity must be a mapping"):
        _ = loader.load_dq_config_for_pipeline("chembl_activity")


def test_convenience_loader_requires_explicit_configs_root(
    temp_contract_root: Path,
) -> None:
    """Convenience helper must avoid implicit CWD-sensitive configs root."""
    dq_config = load_dq_config_for_pipeline(
        "chembl_activity",
        configs_root=temp_contract_root,
    )

    assert dq_config.contract_ref == "chembl.activity"
