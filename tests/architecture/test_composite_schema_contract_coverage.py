"""Architecture test: composite configs must have schema and Gold contract coverage."""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.infrastructure.config.composite_config_api import (
    DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY as COMPOSITE_GOLD_SCHEMA_REGISTRY,
)
from bioetl.domain.contracts.gold import composite as composite_contracts

_FORBIDDEN_OCCURRENCE_FIELDS = frozenset(
    {
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
    }
)


def _expected_contract_name(stem: str) -> str:
    return f"Composite{stem.capitalize()}GoldSchema"


def _resolve_composite_config_dir() -> Path:
    """Resolve canonical composite config dir."""
    return Path("configs/composites")


def test_each_composite_pipeline_has_schema_and_contract() -> None:
    """Every composite pipeline config must define matching schema and contract."""
    config_dir = _resolve_composite_config_dir()

    config_stems = sorted(path.stem for path in config_dir.glob("*.yaml"))
    assert config_stems, "No composite pipeline configs found"

    missing_schemas: list[str] = []
    missing_contracts: list[str] = []
    missing_registry_links: list[str] = []

    for stem in config_stems:
        config_path = config_dir / f"{stem}.yaml"
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        merge = raw.get("composite", {}).get("merge", {})
        groups = merge.get("column_groups")
        if not isinstance(groups, list) or not groups:
            missing_schemas.append(
                f"{config_path}: missing composite.merge.column_groups"
            )

        contract_name = _expected_contract_name(stem)
        if not hasattr(composite_contracts, contract_name):
            missing_contracts.append(contract_name)

        if stem not in COMPOSITE_GOLD_SCHEMA_REGISTRY:
            missing_registry_links.append(stem)

    assert not missing_schemas, "Missing inline composite schemas:\n" + "\n".join(
        f"  - {path}" for path in missing_schemas
    )
    assert not missing_contracts, (
        "Missing composite Gold contract classes:\n"
        + "\n".join(f"  - {name}" for name in missing_contracts)
    )
    assert not missing_registry_links, (
        "Missing composite contract registry links in runner bootstrap:\n"
        + "\n".join(f"  - {stem}" for stem in missing_registry_links)
    )


def test_composite_column_groups_exclude_occurrence_scoped_runtime_fields() -> None:
    """Composite persisted output groups must not include occurrence-scoped provenance."""
    config_dir = _resolve_composite_config_dir()
    violations: list[str] = []

    for config_path in sorted(config_dir.glob("*.yaml")):
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        groups = raw.get("composite", {}).get("merge", {}).get("column_groups", [])
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", "<unknown>"))
            fields = group.get("fields", [])
            if not isinstance(fields, list):
                continue
            forbidden_hits = sorted(
                _FORBIDDEN_OCCURRENCE_FIELDS & {str(x) for x in fields}
            )
            if forbidden_hits:
                violations.append(
                    f"{config_path}: group={group_name} contains {forbidden_hits}"
                )

    assert not violations, (
        "Composite merge.column_groups must not carry occurrence-scoped runtime provenance.\n"
        + "\n".join(f"  - {entry}" for entry in violations)
    )
