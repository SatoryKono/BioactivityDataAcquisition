"""Private runtime helpers for pipeline factory method wrappers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.factories.pipeline._factory_method_types import (
        _CreatePipelineWithServicesRequest,
        _PipelineFactoryContext,
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
    create_pipeline_kwargs: dict[str, object] = {
        "pipeline_name": factory_context.pipeline_name,
        "pipeline_class": factory_context.pipeline_class,
        "provider": factory_context.provider,
        "create_data_source_fn": factory_context.create_data_source_fn,
        "transformer_class": factory_context.transformer_class,
        "pandera_silver_schema": factory_context.pandera_silver_schema,
        "run_id": request.run_id,
        "runtime": request.runtime,
        "settings": request.settings,
        "logger": request.logger,
        "config": request.config,
        "filter_config": cast("InputFilterConfig | None", request.filter_config),
        "tracer": request.tracer,
        "dq_monitor": request.dq_monitor,
        "metrics": request.metrics,
        "cached_bronze": cast("CachedBronzeContext | None", request.cached_bronze),
    }
    apply_optional_control_plane_kwargs_fn(
        create_pipeline_kwargs,
        manifest_id=request.manifest_id,
        config_hash=request.config_hash,
        dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
        effective_config_artifact_id=request.effective_config_artifact_id,
    )
    return cast(
        "BasePipeline",
        cast("Any", create_pipeline_with_services_fn)(
            **cast("dict[str, Any]", create_pipeline_kwargs)
        ),
    )


def create_factory_runner_from_request(
    *,
    pipeline_name: str,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    observability: ObservabilityBundle,
    yaml_config: PipelineYamlConfig,
    manifest_id: str | None,
    config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    effective_config_artifact_id: str | None,
    create_with_services_fn: Callable[..., BasePipeline],
    assemble_runner_fn: Callable[..., PipelineRunner],
    filter_config: InputFilterConfig | None,
    cached_bronze: CachedBronzeContext | None,
    apply_optional_control_plane_kwargs_fn: Callable[..., None],
    resolve_strict_gold_validation_fn: Callable[..., bool],
) -> PipelineRunner:
    """Create a pipeline and assemble a runner from resolved runtime inputs."""
    create_with_services_kwargs: dict[str, object] = {
        "run_id": run_id,
        "runtime": runtime,
        "settings": settings,
        "logger": observability.logger,
        "config": yaml_config,
        "filter_config": filter_config,
        "tracer": observability.tracer,
        "dq_monitor": observability.dq_monitor,
        "metrics": observability.metrics,
        "cached_bronze": cached_bronze,
    }
    apply_optional_control_plane_kwargs_fn(
        create_with_services_kwargs,
        manifest_id=manifest_id,
        config_hash=config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
    )
    pipeline = cast(
        "Any",
        create_with_services_fn,
    )(**cast("dict[str, Any]", create_with_services_kwargs))
    return assemble_runner_fn(
        pipeline=pipeline,
        observability=observability,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=resolve_strict_gold_validation_fn(
            runtime=runtime,
            settings=settings,
        ),
        yaml_config=yaml_config,
    )
