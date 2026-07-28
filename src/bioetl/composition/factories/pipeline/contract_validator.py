"""Assembly wrapper for pipeline contract preflight and factory creation."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.registry import GenericPipeline
from bioetl.composition.factories.datasource.data_source_factory import (
    get_data_source_creator,
)
from bioetl.composition.factories.pipeline_support.contract_validation_helpers import (
    _resolve_silver_columns,
    _resolve_transformer_class_ref,
    _schema_columns,
    _validate_contract_policy,
)
from bioetl.composition.providers.provider_registry import (
    ProviderDataSourceAccessProtocol,
)
from bioetl.domain.types import GoldSchemaType

if TYPE_CHECKING:
    from bioetl.composition.factories.pipeline._assembler_factory import (
        GenericPipelineFactory,
    )
    from bioetl.composition.factories.pipeline.config_types import (
        PipelineFactoryConfig,
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

    transformer_class = _resolve_transformer_class_ref(config.transformer_class)

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
        transformer_class=transformer_class,
        data_source_creator=data_source_creator,
        provider_registry=provider_registry,
    )


__all__ = [
    "_resolve_transformer_class_ref",
    "_resolve_silver_columns",
    "_schema_columns",
    "_validate_contract_policy",
    "create_factory",
]
