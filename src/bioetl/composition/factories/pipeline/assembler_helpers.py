"""Helper implementations extracted from assembler to keep RF-014 seams thin."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, cast

from bioetl.application.core.wiring.factory import BasePipeline, PipelineRunner
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    _ControlPlaneArtifacts,
    _CreateFactoryRunnerRequest,
    _CreatePipelineWithServicesRequest,
    _PipelineFactoryContext,
    build_create_pipeline_with_services_request,
    build_pipeline_factory_context,
    create_factory_runner,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort, TracingPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.composition.factories.pipeline.assembler import GenericPipelineFactory
    from bioetl.domain.types import GoldSchemaType

TPipeline = TypeVar("TPipeline", bound=BasePipeline)


def build_factory_context(
    factory: GenericPipelineFactory[TPipeline],
) -> _PipelineFactoryContext:
    """Build typed factory context used by composition helper methods."""
    return build_pipeline_factory_context(
        pipeline_name=factory.pipeline_name,
        create_data_source_fn=factory._create_data_source,
        pipeline_class=cast(type[BasePipeline] | None, factory.pipeline_class),
        provider=factory.provider,
        transformer_class=factory.transformer_class,
        pandera_silver_schema=factory.pandera_silver_schema,
    )


def create_with_services_from_factory(
    factory: GenericPipelineFactory[TPipeline],
    request: _CreatePipelineWithServicesRequest,
    *,
    create_pipeline_instance_with_services_fn: object,
) -> TPipeline:
    """Create a typed pipeline instance using shared factory helper plumbing."""
    return cast(
        TPipeline,
        create_pipeline_instance_with_services_fn(
            factory_context=build_factory_context(factory),
            request=request,
        ),
    )


def create_runner_from_factory(
    factory: GenericPipelineFactory[TPipeline],
    request: _CreateFactoryRunnerRequest,
    *,
    assemble_runner_fn: object,
) -> PipelineRunner:
    """Create a runner using the factory's current bound service constructor."""
    return create_factory_runner(
        request=request,
        create_with_services_fn=factory.create_with_services,
        assemble_runner_fn=assemble_runner_fn,
    )
