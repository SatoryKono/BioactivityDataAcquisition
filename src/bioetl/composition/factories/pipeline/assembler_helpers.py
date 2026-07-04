"""Helper implementations extracted from assembler to keep RF-014 seams thin."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from bioetl.application.core.wiring.factory import BasePipeline, PipelineRunner
from bioetl.application.core.wiring.transformer import BaseTransformer
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    _CreateFactoryRunnerRequest,
    _CreatePipelineWithServicesRequest,
    _PipelineFactoryContext,
    build_factory_services as build_factory_services,
    build_pipeline_factory_context,
    create_factory_runner,
    create_pipeline_instance_with_services as create_pipeline_instance_with_services,
    extract_entity_type as extract_entity_type,
)


class _FactoryLike(Protocol):
    @property
    def pipeline_name(self) -> str: ...

    @property
    def _create_data_source(self) -> DataSourceCreatorProtocol: ...

    @property
    def pipeline_class(self) -> type[BasePipeline]: ...

    @property
    def provider(self) -> str: ...

    @property
    def transformer_class(self) -> type[BaseTransformer] | None: ...

    @property
    def pandera_silver_schema(self) -> object | None: ...

    def create_with_services(
        self,
        request: _CreatePipelineWithServicesRequest,
    ) -> BasePipeline: ...


def build_factory_context(
    factory: _FactoryLike,
) -> _PipelineFactoryContext:
    """Build typed factory context used by composition helper methods."""
    return build_pipeline_factory_context(
        pipeline_name=factory.pipeline_name,
        create_data_source_fn=factory._create_data_source,
        pipeline_class=factory.pipeline_class,
        provider=factory.provider,
        transformer_class=factory.transformer_class,
        pandera_silver_schema=factory.pandera_silver_schema,
    )


def create_with_services_from_factory(
    factory: _FactoryLike,
    request: _CreatePipelineWithServicesRequest,
    *,
    create_pipeline_instance_with_services_fn: Callable[..., BasePipeline],
) -> BasePipeline:
    """Create a typed pipeline instance using shared factory helper plumbing."""
    return create_pipeline_instance_with_services_fn(
        factory_context=build_factory_context(factory),
        request=request,
    )


def create_runner_from_factory(
    factory: _FactoryLike,
    request: _CreateFactoryRunnerRequest,
    *,
    assemble_runner_fn: Callable[..., PipelineRunner],
) -> PipelineRunner:
    """Create a runner using the factory's current bound service constructor."""
    return create_factory_runner(
        request=request,
        create_with_services_fn=factory.create_with_services,
        assemble_runner_fn=assemble_runner_fn,
    )
