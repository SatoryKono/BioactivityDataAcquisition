"""Registry-manifest validation against tracked config surfaces.

The pipeline registry manifest is the canonical composition-owned runtime
binding surface. Entity/provider YAML remains the canonical tracked config
surface. This module validates that the two remain in sync.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import yaml


class RegistryEntryProtocol(Protocol):
    """Structural fields required by registry-manifest validation."""

    pipeline_name: str
    provider: str
    entity_type: str
    transformer_class: object | None
    gold_schema: object | None
    pandera_silver_schema: object | None


__all__ = ["RegistryEntryProtocol"]


def _iter_entity_files(configs_root: Path) -> list[Path]:
    entities_dir = configs_root / "entities"
    if not entities_dir.exists():
        return []
    return [
        path
        for path in sorted(entities_dir.rglob("*.yaml"))
        if not path.name.startswith("_") and not _is_legacy_composite_entity_stub(path)
    ]


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _is_legacy_composite_entity_stub(config_path: Path) -> bool:
    """Return True for historical composite stubs under configs/entities.

    Identification is path-based only (``configs/entities/composite/**``).
    The YAML ``provider`` field must not bypass registry validation
    (ARCH-CR-02 / #6864).
    """
    return config_path.parent.name.strip().lower() == "composite"


def _pipeline_name(provider: str, entity: str) -> str:
    return f"{provider}_{entity}"


def _display_path(path: Path, *, repo_root: Path) -> str:
    """Render stable repo-relative POSIX paths for diagnostics."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _validate_registry_entry(
    entry: RegistryEntryProtocol,
    *,
    resolved_configs_root: Path,
    repo_root: Path,
    seen_pipeline_names: set[str],
    seen_provider_entities: set[tuple[str, str]],
    registered_pipeline_names: set[str],
    registered_provider_entities: set[tuple[str, str]],
) -> list[str]:
    pipeline_name = str(entry.pipeline_name).strip()
    provider = str(entry.provider).strip()
    entity = str(entry.entity_type).strip()
    key = (provider, entity)
    errors: list[str] = []

    if pipeline_name in seen_pipeline_names:
        errors.append(
            "pipeline registry manifest contains duplicate pipeline_name: "
            f"{pipeline_name}"
        )
    seen_pipeline_names.add(pipeline_name)
    registered_pipeline_names.add(pipeline_name)

    if key in seen_provider_entities:
        errors.append(
            "pipeline registry manifest contains duplicate provider/entity "
            f"binding: {provider}/{entity}"
        )
    seen_provider_entities.add(key)
    registered_provider_entities.add(key)

    expected_entity_path = (
        resolved_configs_root / "entities" / provider / f"{entity}.yaml"
    )
    if not expected_entity_path.exists():
        errors.append(
            "pipeline registry entry has no entity config: "
            f"{pipeline_name} -> {_display_path(expected_entity_path, repo_root=repo_root)}"
        )

    expected_provider_path = resolved_configs_root / "providers" / f"{provider}.yaml"
    if not expected_provider_path.exists():
        errors.append(
            "pipeline registry entry has no provider config: "
            f"{pipeline_name} -> {_display_path(expected_provider_path, repo_root=repo_root)}"
        )

    if entry.transformer_class is None:
        errors.append(
            f"pipeline registry entry is missing transformer binding: {pipeline_name}"
        )
    if entry.gold_schema is None:
        errors.append(
            f"pipeline registry entry is missing Gold contract binding: {pipeline_name}"
        )
    if entry.pandera_silver_schema is None:
        errors.append(
            "pipeline registry entry is missing Pandera Silver schema binding: "
            f"{pipeline_name}"
        )

    return errors


def _validate_entity_config_against_registry(
    entity_path: Path,
    *,
    repo_root: Path,
    registered_pipeline_names: set[str],
    registered_provider_entities: set[tuple[str, str]],
) -> list[str]:
    provider = entity_path.parent.name
    entity = entity_path.stem
    derived_pipeline_name = _pipeline_name(provider, entity)
    display_entity_path = _display_path(entity_path, repo_root=repo_root)
    payload = _load_yaml_mapping(entity_path)
    registered_key = (provider, entity)
    errors: list[str] = []

    if derived_pipeline_name not in registered_pipeline_names:
        errors.append(
            "entity config has no pipeline registry binding: "
            f"{display_entity_path} -> {derived_pipeline_name}"
        )
    if registered_key not in registered_provider_entities:
        errors.append(
            "entity config has no provider/entity registry binding: "
            f"{display_entity_path} -> {provider}/{entity}"
        )

    top_level_provider = payload.get("provider")
    if isinstance(top_level_provider, str) and top_level_provider != provider:
        errors.append(
            f"{display_entity_path}: top-level provider '{top_level_provider}' does not match path '{provider}'"
        )
    top_level_entity = payload.get("entity")
    if isinstance(top_level_entity, str) and top_level_entity != entity:
        errors.append(
            f"{display_entity_path}: top-level entity '{top_level_entity}' does not match path '{entity}'"
        )

    pipeline_payload = payload.get("pipeline")
    if isinstance(pipeline_payload, dict):
        declared_pipeline_name = pipeline_payload.get("pipeline_name")
        if (
            isinstance(declared_pipeline_name, str)
            and declared_pipeline_name != derived_pipeline_name
        ):
            errors.append(
                f"{display_entity_path}: pipeline.pipeline_name "
                f"'{declared_pipeline_name}' does not match derived registry "
                f"name '{derived_pipeline_name}'"
            )

    errors.extend(_validate_entity_contract_fields(display_entity_path, payload))
    return errors


def _validate_entity_contract_fields(
    display_entity_path: str,
    payload: dict[str, object],
) -> list[str]:
    contracts = payload.get("contracts")
    if not isinstance(contracts, dict):
        return [
            f"{display_entity_path}: missing contracts section for registry validation"
        ]

    primary_key = contracts.get("primary_key")
    if isinstance(primary_key, dict):
        business = primary_key.get("business")
        if not isinstance(business, list) or not business:
            return [
                f"{display_entity_path}: contracts.primary_key.business must be a non-empty list"
            ]
        return []

    if not isinstance(primary_key, list) or not primary_key:
        return [
            f"{display_entity_path}: contracts.primary_key must be a non-empty list or mapping"
        ]
    return []


__all__ = [
    "_display_path",
    "_is_legacy_composite_entity_stub",
    "_iter_entity_files",
    "_load_yaml_mapping",
    "_pipeline_name",
    "_validate_entity_config_against_registry",
    "_validate_entity_contract_fields",
    "_validate_registry_entry",
]
