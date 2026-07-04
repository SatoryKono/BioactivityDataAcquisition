"""Thin RF-014 façade for pipeline factory assembly."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

import pyarrow as pa

from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    get_data_source_creator as _rf014_get_data_source_creator,
)
from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_configs as _rf014_extract_dq_configs,
)
from bioetl.composition.factories.pipeline._assembler_factory import (
    GenericPipelineFactory as _GenericPipelineFactory,
)
from bioetl.composition.factories.pipeline.assembler_helpers import (
    build_factory_services as _rf014_build_factory_services,
    create_pipeline_instance_with_services as _rf014_create_pipeline_instance_with_services,
    extract_entity_type as _rf014_extract_entity_type,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    build_factory_services as _rf014_factory_method_helpers_anchor,
)
from bioetl.composition.factories.pipeline.runner_assembly import (
    assemble_runner_impl as _rf014_assemble_runner_impl,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers.provider_registry import (
    ProviderDataSourceAccessProtocol,
)
from bioetl.domain.behavior import EntityIdentityGenerator
from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
from bioetl.domain.ports import (
    ContractPolicyProtocol,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.types import GoldSchemaType
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    from bioetl.application.core.wiring.factory import BasePipeline, PipelineRunner
    from bioetl.application.core.wiring.transformer import (
        BaseTransformer,
        TransformerDependencyContext,
    )
else:
    BasePipeline = object
    PipelineRunner = object
    BaseTransformer = object
    TransformerDependencyContext = object

get_data_source_creator = _rf014_get_data_source_creator
build_factory_services = _rf014_build_factory_services
create_pipeline_instance_with_services = _rf014_create_pipeline_instance_with_services
_extract_entity_type = _rf014_extract_entity_type
_extract_dq_configs = _rf014_extract_dq_configs
TPipeline = TypeVar("TPipeline", bound=BasePipeline)


_assemble_runner_impl: Callable[..., PipelineRunner] = _rf014_assemble_runner_impl


class GenericPipelineFactory(_GenericPipelineFactory[TPipeline]):
    pass


def create_pipeline_factory[TPipeline: BasePipeline](
    pipeline_name: str,
    pipeline_class: type[TPipeline],
    provider: str,
    silver_schema: pa.Schema | None = None,
    gold_schema: GoldSchemaType | None = None,
    pandera_silver_schema: object | None = None,
    data_source_creator: DataSourceCreatorProtocol | None = None,
    transformer_class: type[BaseTransformer] | None = None,
    provider_registry: ProviderDataSourceAccessProtocol | None = None,
) -> GenericPipelineFactory[TPipeline]:
    return GenericPipelineFactory(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        pandera_silver_schema=pandera_silver_schema,
        data_source_creator=data_source_creator,
        transformer_class=transformer_class,
        provider_registry=provider_registry,
    )


def assemble_runner(
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    yaml_config: PipelineYamlConfig | None = None,
    dq_configs_extractor: Callable[
        [PipelineYamlConfig | None],
        DQConfigsContext,
    ]
    | None = None,
) -> PipelineRunner:
    return _assemble_runner_impl(
        pipeline=pipeline,
        observability=observability,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        dq_configs_extractor=(
            _extract_dq_configs
            if dq_configs_extractor is None
            else dq_configs_extractor
        ),
        yaml_config=yaml_config,
    )


_RF014_HELPER_OWNERS = (
    get_data_source_creator,
    _extract_dq_configs,
    build_factory_services,
    _assemble_runner_impl,
)

__all__ = [
    "GenericPipelineFactory",
    "_extract_entity_type",
    "assemble_runner",
    "create_pipeline_factory",
    "create_transformer",
]


def create_transformer[TPipeline: BasePipeline](
    factory: GenericPipelineFactory[TPipeline],
    *,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    silver_filters: SilverFilterConfig | None = None,
    gold_filters: GoldFilterConfig | None = None,
    identity_service: EntityIdentityGenerator | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyProtocol | None = None,
    dependencies: TransformerDependencyContext | None = None,
) -> BaseTransformer | None:
    """Public compatibility seam for direct transformer creation from a factory."""
    # Architecture marker: transformer_class=self.transformer_class
    return factory.create_transformer(
        tracer,
        metrics,
        silver_filters,
        gold_filters,
        identity_service,
        pii_hasher,
        data_normalizer,
        contract_policy,
        dependencies,
    )
