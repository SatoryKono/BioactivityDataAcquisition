"""Pipeline contract validation.

Validates that pipeline contract policy keys exist in Silver and Gold schemas.
Extracted from pipeline_factories.py for LOC compliance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.pipelines.generic import GenericPipeline
from bioetl.composition.factories.datasource.data_source_factory import (
    get_data_source_creator,
)
from bioetl.composition.factories.pipeline.configs import PipelineFactoryConfig
from bioetl.infrastructure.config import load_pipeline_contract_policy

if TYPE_CHECKING:
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
    from bioetl.composition.factories.pipeline.pipeline_assembler import (
        GenericPipelineFactory,
    )
    from bioetl.domain.types import GoldSchemaType


class _SchemaBuilder(Protocol):
    """Protocol for schema classes exposing ``to_schema``."""

    @classmethod
    def to_schema(cls) -> object:
        """Materialize schema representation."""
        ...


class _ResolvedSchema(Protocol):
    """Protocol for resolved schema objects exposing columns mapping."""

    columns: dict[str, object]


def _schema_columns(
    schema_class: object,
) -> set[str]:
    """Extract column names from a Pandera DataFrameModel class."""
    if not hasattr(schema_class, "to_schema"):
        raise ValueError(f"Schema {schema_class!r} does not expose to_schema()")
    try:
        schema_builder = cast("_SchemaBuilder", schema_class)
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


def _resolve_silver_columns(config: PipelineFactoryConfig) -> set[str]:
    """Resolve Silver column names from config's schema sources."""
    if config.pandera_silver_schema is not None:
        return _schema_columns(config.pandera_silver_schema)
    if config.silver_schema is not None:
        return set(config.silver_schema.names)
    raise ValueError(
        f"No Silver schema available for {config.provider}/{config.entity_type}"
    )


def _validate_contract_policy(config: PipelineFactoryConfig) -> None:
    """Preflight check that policy keys exist in Silver and Gold contracts."""
    policy = load_pipeline_contract_policy(config.provider, config.entity_type)

    silver_columns = _resolve_silver_columns(config)
    gold_columns = _schema_columns(config.gold_schema)

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
            f"Invalid contract policy for {config.provider}/{config.entity_type}: "
            + ", ".join(details)
        )


def create_factory(
    config: PipelineFactoryConfig,
) -> GenericPipelineFactory[GenericPipeline]:
    """Create a GenericPipelineFactory from configuration.

    Args:
        config: Pipeline factory configuration

    Returns:
        Configured GenericPipelineFactory instance
    """
    _validate_contract_policy(config)
    from bioetl.composition.factories.pipeline.assembler import (
        GenericPipelineFactory,
    )

    # Resolve data source creator: use data_source_provider override if set
    data_source_creator: DataSourceCreatorProtocol | None = None
    if config.data_source_provider:
        data_source_creator = get_data_source_creator(config.data_source_provider)

    return GenericPipelineFactory(
        pipeline_name=config.pipeline_name,
        pipeline_class=GenericPipeline,
        provider=config.provider,
        silver_schema=config.silver_schema,
        gold_schema=cast("GoldSchemaType", config.gold_schema),
        pandera_silver_schema=config.pandera_silver_schema,
        transformer_class=config.transformer_class,
        data_source_creator=data_source_creator,
    )


__all__ = [
    "create_factory",
]
