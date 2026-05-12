"""Unit tests for contract registry CI validator helpers."""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.control_plane.contract_registry import ContractRegistry
from scripts.engineering.ci.validate_contract_registry import (
    _active_gold_surface_issues,
)


def _write_entity_config(
    repo_root: Path,
    *,
    provider: str,
    entity: str,
    gold_enabled: bool | None = True,
) -> None:
    config_path = repo_root / "configs" / "entities" / provider / f"{entity}.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    gold_payload: dict[str, object] = {"mode": "overwrite"}
    if gold_enabled is not None:
        gold_payload["enabled"] = gold_enabled
    config_path.write_text(
        yaml.safe_dump(
            {
                "provider": provider,
                "entity": entity,
                "pipeline": {
                    "sink": {
                        "gold": gold_payload,
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _registry_entry(*, status: str) -> dict[str, object]:
    return {
        "identity": {
            "contract_version": "1.0.0",
            "compatibility_level": "major",
            "schema_hash": "abc123",
            "dq_policy_ref": "chembl.dq.v1",
            "rule_bundle_version": "dq-rules.v1.0",
            "normalization_profile_ref": "chembl.assay_parameters",
            "normalization_profile_version": "1.0.0",
            "normalization_profile_hash": "d" * 64,
        },
        "status": status,
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_activity_assay_schemas.py",
        "published_artifacts": [
            "../../docs/04-reference/contracts/gold/chembl_assay_parameters_v1.0.json"
        ],
        "supported_versions": ["1.0.0"],
        "migration_guides": {},
        "last_updated": "2026-05-06T00:00:00Z",
        "owners": ["chembl-team"],
        "dq_policy_ref": "chembl.dq.v1",
        "rule_bundle_version": "dq-rules.v1.0",
        "normalization_profile_ref": "chembl.assay_parameters",
        "normalization_profile_version": "1.0.0",
        "normalization_profile_hash": "d" * 64,
    }


def test_active_gold_surface_issues_reports_missing_registry_entry(
    tmp_path: Path,
) -> None:
    """Active Gold entity configs must not be missing from the registry."""
    _write_entity_config(
        tmp_path,
        provider="chembl",
        entity="assay_parameters",
    )
    registry = ContractRegistry.from_dict({"version": "1.0", "entries": {}})

    issues = _active_gold_surface_issues(tmp_path, registry)

    assert len(issues) == 1
    assert issues[0].contract_ref == "chembl.assay_parameters"
    assert "missing a matching contract registry entry" in issues[0].message


def test_active_gold_surface_issues_reports_non_active_registry_status(
    tmp_path: Path,
) -> None:
    """Active Gold entity configs must not point to deprecated registry refs."""
    _write_entity_config(
        tmp_path,
        provider="chembl",
        entity="assay_parameters",
    )
    registry = ContractRegistry.from_dict(
        {
            "version": "1.0",
            "entries": {
                "chembl.assay_parameters": _registry_entry(
                    status="deprecated",
                )
            },
        }
    )

    issues = _active_gold_surface_issues(tmp_path, registry)

    assert len(issues) == 1
    assert issues[0].contract_ref == "chembl.assay_parameters"
    assert "requires an active registry status" in issues[0].message


def test_active_gold_surface_issues_accepts_active_registry_surface(
    tmp_path: Path,
) -> None:
    """Active Gold entity configs pass when the registry ref is active."""
    _write_entity_config(
        tmp_path,
        provider="chembl",
        entity="assay_parameters",
    )
    registry = ContractRegistry.from_dict(
        {
            "version": "1.0",
            "entries": {
                "chembl.assay_parameters": _registry_entry(
                    status="active",
                )
            },
        }
    )

    issues = _active_gold_surface_issues(tmp_path, registry)

    assert issues == []
