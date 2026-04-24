"""Private runtime helpers for pipeline factory method wrappers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.composition.factories.pipeline._factory_method_control_plane import (
    resolve_strict_gold_validation,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    _CreatePipelineWithServicesRequest,
    _PipelineFactoryContext,
)
from bioetl.composition.factories.pipeline.creation_support import (
    _PipelineCreationInputs,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.factories.pipeline._factory_method_types import (
        _ControlPlaneArtifacts,
        _CreatePipelineWithServicesRequest,
    )
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.types import GoldSchemaType, RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def create_pipeline_instance_from_request(
    *,
    factory_context: _PipelineFactoryContext,
    request: _CreatePipelineWithServicesRequest,
    create_pipeline_with_services_fn: Callable[..., BasePipeline],
    apply_optional_control_plane_kwargs_fn: Callable[..., None],
) -> BasePipeline:
    """Create a pipeline instance from typed factory/request objects."""
    if factory_context.pipeline_class is None or factory_context.provider is None:
        raise AssertionError(
            "factory_context must include pipeline_class and provider for pipeline creation"
        )
    del apply_optional_control_plane_kwargs_fn
    pipeline_inputs = _PipelineCreationInputs(
        pipeline_name=factory_context.pipeline_name,
        pipeline_class=factory_context.pipeline_class,
        provider=factory_context.provider,
        create_data_source_fn=factory_context.create_data_source_fn,
        transformer_class=factory_context.transformer_class,
        request=request,
        pandera_silver_schema=factory_context.pandera_silver_schema,
    )
    return cast(
        "BasePipeline",
        cast("Any", create_pipeline_with_services_fn)(  # Any: Dynamic factory function
            inputs=pipeline_inputs,
        ),
    )


def create_factory_runner_from_request(
    *,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    run_id: RunID,
    runtime: RuntimeConfig,
    started_at: datetime,
    settings: Settings,
    observability: ObservabilityBundle,
    yaml_config: PipelineYamlConfig,
    control_plane_artifacts: _ControlPlaneArtifacts | None,
    create_with_services_fn: Callable[..., BasePipeline],
    assemble_runner_fn: Callable[..., PipelineRunner],
    filter_config: InputFilterConfig | None,
    cached_bronze: CachedBronzeContext | None,
) -> PipelineRunner:
    """Create a pipeline and assemble a runner from resolved runtime inputs."""
    artifacts = control_plane_artifacts
    pipeline_request = _CreatePipelineWithServicesRequest(
        run_id=run_id,
        runtime=runtime,
        started_at=started_at,
        settings=settings,
        logger=observability.logger,
        audit=observability.audit,
        manifest_id=None if artifacts is None else artifacts.manifest_id,
        execution_fingerprint=(
            None if artifacts is None else artifacts.execution_fingerprint
        ),
        config_hash=None if artifacts is None else artifacts.config_hash,
        resolved_config_hash=(
            None if artifacts is None else artifacts.resolved_config_hash
        ),
        effective_config_hash=(
            None if artifacts is None else artifacts.effective_config_hash
        ),
        dq_contract_compatibility_hash=(
            None if artifacts is None else artifacts.dq_contract_compatibility_hash
        ),
        effective_config_artifact_id=(
            None if artifacts is None else artifacts.effective_config_artifact_id
        ),
        config=yaml_config,
        filter_config=filter_config,
        tracer=observability.tracer,
        dq_monitor=observability.dq_monitor,
        metrics=observability.metrics,
        cached_bronze=cached_bronze,
    )
    pipeline = cast(
        "Any",  # Any: Dynamic factory function
        create_with_services_fn,
    )(pipeline_request)
    return assemble_runner_fn(
        pipeline=pipeline,
        observability=observability,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=resolve_strict_gold_validation(
            runtime=runtime,
            settings=settings,
        ),
        yaml_config=yaml_config,
    )
