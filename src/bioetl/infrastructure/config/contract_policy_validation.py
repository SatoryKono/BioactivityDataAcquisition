"""Canonical helpers for validating pipeline contract policies against schemas."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)

__all__ = [
    "resolve_silver_columns",
    "schema_columns",
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


def schema_columns(schema_class: object) -> set[str]:
    """Extract column names from a Pandera DataFrameModel class."""
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
