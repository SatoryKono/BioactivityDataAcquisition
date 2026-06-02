"""Assembly wrapper for pipeline contract preflight and factory creation."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.registry import GenericPipeline
from bioetl.composition.factories.datasource.data_source_factory import (
    get_data_source_creator,
)
from bioetl.composition.factories.pipeline.registry_manifest import (
    PipelineFactoryConfig,
)
from bioetl.composition.providers.provider_registry import (
    ProviderDataSourceAccessProtocol,
)
from bioetl.domain.types import GoldSchemaType
from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    resolve_silver_columns as _resolve_silver_columns_impl,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    schema_columns as _schema_columns_impl,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    validate_pipeline_contract_policy as _validate_pipeline_contract_policy_impl,
)

if TYPE_CHECKING:
    from bioetl.composition.factories.pipeline._assembler_factory import (
        GenericPipelineFactory,
    )


def _schema_columns(
    schema_class: object,
) -> set[str]:
    """Compatibility wrapper over canonical schema-column extraction helper."""
    return _schema_columns_impl(schema_class)


def _resolve_silver_columns(config: PipelineFactoryConfig) -> set[str]:
    """Compatibility wrapper over canonical Silver schema resolution helper."""
    return _resolve_silver_columns_impl(
        provider=config.provider,
        entity_type=config.entity_type,
        pandera_silver_schema=config.pandera_silver_schema,
        silver_schema=config.silver_schema,
    )


def _validate_contract_policy(config: PipelineFactoryConfig) -> None:
    """Assembly-scoped wrapper over canonical contract-policy validation."""
    _validate_pipeline_contract_policy_impl(
        provider=config.provider,
        entity_type=config.entity_type,
        pandera_silver_schema=config.pandera_silver_schema,
        silver_schema=config.silver_schema,
        gold_schema=config.gold_schema,
        load_policy=load_pipeline_contract_policy,
    )


def create_factory(
    config: PipelineFactoryConfig,
    *,
    provider_registry: ProviderDataSourceAccessProtocol | None = None,
) -> GenericPipelineFactory[GenericPipeline]:
    """Create a GenericPipelineFactory from configuration.

    Args:
        config: Pipeline factory configuration

    Returns:
        Configured GenericPipelineFactory instance
    """
    _validate_contract_policy(config)
    from bioetl.composition.factories.pipeline._assembler_factory import (
        GenericPipelineFactory,
    )

    # Resolve data source creator: use data_source_provider override if set
    data_source_creator = (
        get_data_source_creator(
            config.data_source_provider,
            provider_registry=provider_registry,
        )
        if config.data_source_provider
        else None
    )

    return GenericPipelineFactory(
        pipeline_name=config.pipeline_name,
        pipeline_class=GenericPipeline,
        provider=config.provider,
        silver_schema=config.silver_schema,
        gold_schema=cast("GoldSchemaType", config.gold_schema),
        pandera_silver_schema=config.pandera_silver_schema,
        transformer_class=config.transformer_class,
        data_source_creator=data_source_creator,
        provider_registry=provider_registry,
    )


__all__ = [
    "create_factory",
]
