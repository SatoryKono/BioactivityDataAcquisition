"""Interface-layer wiring for application ports to infrastructure implementations."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable

from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.application.container import build_pipeline_dependencies
from bioetl.domain.clients.base.output.contracts import RunMetadataBuilderProtocol
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
from bioetl.domain.observability import PipelineMetricsPortABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.record_source import FileRecordSourceFactoryABC
from bioetl.domain.validation import ValidatorFactoryABC
from bioetl.infrastructure.config.loader import (
    get_pipeline_config,
    get_pipeline_config_from_path,
)
from bioetl.infrastructure.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.infrastructure.observability import metrics
from bioetl.infrastructure.observability.factories import default_logging_port
from bioetl.infrastructure.output.factories import (
    default_metadata_writer,
    default_output_writer,
    default_quality_reporter,
    default_writer,
)
from bioetl.infrastructure.output.metadata import (
    build_dry_run_metadata,
    build_run_metadata,
)
from bioetl.infrastructure.validation.factories import default_validator_factory


def create_config_loader() -> PipelineConfigLoaderProtocol:
    """Return config loader port backed by infrastructure loader."""

    return SimpleNamespace(
        get_by_id=get_pipeline_config,
        get_from_path=get_pipeline_config_from_path,
    )


def _create_record_source_factory() -> FileRecordSourceFactoryABC:
    """Return factory producing CSV/ID list record sources."""

    return SimpleNamespace(
        create_csv_source=(
            lambda **kwargs: CsvRecordSourceImpl(**kwargs)  # type: ignore[arg-type]
        ),
        create_id_list_source=(
            lambda **kwargs: IdListRecordSourceImpl(**kwargs)  # type: ignore[arg-type]
        ),
    )


def _create_metadata_builder() -> RunMetadataBuilderProtocol:
    """Return metadata builder port using infrastructure helpers."""

    return SimpleNamespace(
        build_run_metadata=build_run_metadata,
        build_dry_run_metadata=build_dry_run_metadata,
    )


def _create_metrics_port() -> PipelineMetricsPortABC:
    """Return metrics port backed by Prometheus collectors."""

    return SimpleNamespace(
        update_stage_duration=lambda **kwargs: metrics.STAGE_DURATION_SECONDS.labels(
            pipeline=kwargs["pipeline"],
            provider=kwargs["provider"],
            entity=kwargs["entity"],
            stage=kwargs["stage"],
            outcome=kwargs["outcome"],
        ).observe(kwargs["duration_sec"]),
        update_stage_total=lambda **kwargs: metrics.STAGE_TOTAL.labels(
            pipeline=kwargs["pipeline"],
            provider=kwargs["provider"],
            entity=kwargs["entity"],
            stage=kwargs["stage"],
            outcome=kwargs["outcome"],
        ).inc(),
    )


def _create_validator_factory() -> ValidatorFactoryABC:
    """Return validator factory backed by infrastructure implementation."""

    return default_validator_factory()


def build_default_container(
    config: PipelineConfig,
    *,
    provider_registry: ProviderRegistryABC | None = None,
    provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
) -> PipelineContainerABC:
    """Construct application container with infrastructure defaults."""

    logger = default_logging_port()
    writer = default_writer()
    metadata_writer = default_metadata_writer()
    quality_reporter = default_quality_reporter()
    output_writer = default_output_writer(
        config=config.determinism,
        qc_config=config.qc,
        writer=writer,
        metadata_writer=metadata_writer,
        quality_reporter=quality_reporter,
    )
    record_source_factory = _create_record_source_factory()
    metadata_builder = _create_metadata_builder()
    metrics_port = _create_metrics_port()
    validator_factory = _create_validator_factory()

    return build_pipeline_dependencies(
        config,
        logger=logger,
        output_writer=output_writer,
        validator_factory=validator_factory,
        record_source_factory=record_source_factory,
        metadata_builder=metadata_builder,
        metrics_port=metrics_port,
        provider_registry=provider_registry,
        provider_registry_provider=provider_registry_provider,
    )


def create_container_factory() -> Callable[..., Any]:
    """Expose default container factory."""

    return build_default_container


__all__ = [
    "create_config_loader",
    "create_container_factory",
    "build_default_container",
]
