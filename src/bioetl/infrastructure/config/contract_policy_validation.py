"""Canonical helpers for validating pipeline contract policies against schemas."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, cast

from bioetl.infrastructure.config.contract_registry_loader import (
    try_load_contract_registry_entries,
)
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)

__all__ = [
    "load_contract_registry_entries",
    "resolve_silver_columns",
    "schema_columns",
    "validate_contract_policy_registry_alignment",
    "validate_pipeline_contract_policy",
]


class _SchemaBuilder(Protocol):
    """Protocol for schema classes exposing ``to_schema``."""

    @classmethod
    def to_schema(cls) -> object:
        """Materialize schema representation."""
        ...


class _ResolvedSchema(Protocol):
    """Protocol for resolved schema objects exposing columns mapping."""

    columns: dict[str, object]


class _ArrowSchemaLike(Protocol):
    """Protocol for Arrow-like schema objects exposing ``names``."""

    names: list[str]


def _schema_columns_from_pandera_fields(schema_class: object) -> set[str] | None:
    """Return DataFrameModel columns from ``__fields__`` when available.

    Pandera ``DataFrameModel`` classes expose ``__fields__`` with resolved output
    column names (including aliases). Reading this mapping avoids materializing a
    full schema via ``to_schema()``, which can trigger expensive optional dtype
    imports (e.g., geopandas) during architecture/test bootstrap.
    """
    fields = getattr(schema_class, "__fields__", None)
    if isinstance(fields, dict) and fields:
        return {str(name) for name in fields}
    return None


def load_contract_registry_entries(
    registry_path: Path | None = None,
) -> dict[str, dict[str, object]]:
    """Load contract registry entries via the canonical validated loader."""
    return try_load_contract_registry_entries(cast("Path | None", registry_path))


def _supported_versions(entry: dict[str, object]) -> set[str]:
    """Return supported contract versions declared in the registry entry."""
    supported_versions = entry.get("supported_versions")
    if not isinstance(supported_versions, list):
        return set()
    return {str(version) for version in supported_versions}


def _validate_supported_rollout_versions(
    *,
    contract_ref: str,
    rollout_versions: set[str],
    supported_versions: set[str],
) -> None:
    """Ensure every rollout version is declared in the registry."""
    unsupported_versions = sorted(
        version for version in rollout_versions if version not in supported_versions
    )
    if unsupported_versions:
        raise ValueError(
            f"Unsupported contract versions for {contract_ref}: {unsupported_versions}"
        )


def _migration_guides(entry: dict[str, object]) -> dict[str, object]:
    """Return migration-guide metadata for a registry entry."""
    guides = entry.get("migration_guides")
    return guides if isinstance(guides, dict) else {}


def _validate_major_transition_guides(
    *,
    contract_ref: str,
    active_version: str,
    rollout_versions: set[str],
    guides: dict[str, object],
) -> None:
    """Require a migration guide when rollout spans contract major versions."""
    active_major = active_version.split(".", 1)[0]
    for version in rollout_versions:
        if version == active_version or version.split(".", 1)[0] == active_major:
            continue
        forward_key = f"{version}->{active_version}"
        reverse_key = f"{active_version}->{version}"
        if forward_key not in guides and reverse_key not in guides:
            raise ValueError(
                f"Missing migration guide for major contract transition {contract_ref}: "
                f"{forward_key}"
            )


def validate_contract_policy_registry_alignment(
    policy: PipelineContractPolicy,
    *,
    registry_entries: dict[str, dict[str, object]] | None = None,
) -> None:
    """Validate rollout versions against registry governance metadata when present."""
    if not hasattr(policy, "contract_ref") or not hasattr(policy, "active_version"):
        return
    entries = registry_entries or load_contract_registry_entries()
    entry = entries.get(policy.contract_ref)
    if not isinstance(entry, dict):
        return

    rollout_versions = set(policy.read_order) | set(policy.write_versions)
    _validate_supported_rollout_versions(
        contract_ref=policy.contract_ref,
        rollout_versions=rollout_versions,
        supported_versions=_supported_versions(entry),
    )
    _validate_major_transition_guides(
        contract_ref=policy.contract_ref,
        active_version=policy.active_version,
        rollout_versions=rollout_versions,
        guides=_migration_guides(entry),
    )


def schema_columns(schema_class: object) -> set[str]:
    """Extract column names from a Pandera DataFrameModel class."""
    fields_columns = _schema_columns_from_pandera_fields(schema_class)
    if fields_columns is not None:
        return fields_columns

    if not hasattr(schema_class, "to_schema"):
        raise ValueError(f"Schema {schema_class!r} does not expose to_schema()")
    try:
        schema_builder = cast(_SchemaBuilder, schema_class)
        schema = cast(_ResolvedSchema, schema_builder.to_schema())
    except (
        AttributeError,
        TypeError,
        ValueError,
        RuntimeError,
        ImportError,
    ) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Failed to materialize schema {schema_class}: {exc}") from exc
    return set(schema.columns.keys())


def resolve_silver_columns(
    *,
    provider: str,
    entity_type: str,
    pandera_silver_schema: object | None,
    silver_schema: object | None,
) -> set[str]:
    """Resolve Silver column names from assembly-provided schema sources."""
    if pandera_silver_schema is not None:
        return schema_columns(pandera_silver_schema)
    if silver_schema is not None:
        return set(cast(_ArrowSchemaLike, silver_schema).names)
    raise ValueError(f"No Silver schema available for {provider}/{entity_type}")


def validate_pipeline_contract_policy(
    *,
    provider: str,
    entity_type: str,
    pandera_silver_schema: object | None,
    silver_schema: object | None,
    gold_schema: object,
    load_policy: Callable[[str, str], PipelineContractPolicy],
) -> None:
    """Check that policy keys exist in both Silver and Gold contracts."""
    policy = load_policy(provider, entity_type)
    validate_contract_policy_registry_alignment(policy)

    silver_columns = resolve_silver_columns(
        provider=provider,
        entity_type=entity_type,
        pandera_silver_schema=pandera_silver_schema,
        silver_schema=silver_schema,
    )
    gold_columns = schema_columns(gold_schema)

    required_keys = set(policy.primary_key) | set(policy.merge_keys)
    missing_in_silver = sorted(required_keys - silver_columns)
    missing_in_gold = sorted(required_keys - gold_columns)

    details: list[str] = []
    if missing_in_silver:
        details.append(f"silver missing {missing_in_silver}")
    if missing_in_gold:
        details.append(f"gold missing {missing_in_gold}")
    if details:
        raise ValueError(
            f"Invalid contract policy for {provider}/{entity_type}: "
            + ", ".join(details)
        )
