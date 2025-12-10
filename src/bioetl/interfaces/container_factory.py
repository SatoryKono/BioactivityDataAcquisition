"""
Factory for creating PipelineContainer with default infrastructure implementations.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, cast

from bioetl.application.container import PipelineContainer
from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.domain.clients.base.output.contracts import RunMetadataBuilderProtocol
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import PipelineMetricsPortABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.validation import ValidatorFactoryABC
from bioetl.infrastructure.clients.base.abc_registry_resolver import ABCRegistryResolver
from bioetl.infrastructure.output.metadata import (
    build_dry_run_metadata,
    build_run_metadata,
)
from bioetl.interfaces.monitoring import create_prometheus_metrics_port


def _create_metadata_builder() -> RunMetadataBuilderProtocol:
    """Return metadata builder port using infrastructure helpers."""
    return cast(
        RunMetadataBuilderProtocol,
        SimpleNamespace(
            build_run_metadata=build_run_metadata,
            build_dry_run_metadata=build_dry_run_metadata,
        ),
    )


def _create_metrics_port() -> PipelineMetricsPortABC:
    """Return metrics port backed by Prometheus collectors."""

    return create_prometheus_metrics_port()


def _create_validator_factory() -> ValidatorFactoryABC:
    """Return validator factory backed by infrastructure implementation."""
    loader = ABCRegistryResolver()
    factory = loader.resolve_default_factory("ValidatorFactoryABC")
    return factory()


def build_default_container(
    config: PipelineConfig,
    *,
    provider_registry: ProviderRegistryABC | None = None,
    provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
) -> PipelineContainerABC:
    """Construct application container with infrastructure defaults."""

    registry_loader = ABCRegistryResolver()
    logger_factory = registry_loader.resolve_default_factory("LoggingPortABC")
    writer_factory = registry_loader.resolve_default_factory("WriterABC")
    metadata_writer_factory = registry_loader.resolve_default_factory(
        "MetadataWriterABC"
    )
    quality_reporter_factory = registry_loader.resolve_default_factory(
        "QualityReportABC"
    )
    output_writer_factory = registry_loader.resolve_default_factory("OutputWriterABC")
    frame_converter_factory = registry_loader.resolve_default_factory(
        "OutputFrameConverterABC"
    )
    hash_service_factory = registry_loader.resolve_default_factory("HashServiceABC")

    logger = logger_factory()
    writer = writer_factory()
    metadata_writer = metadata_writer_factory()
    quality_reporter = quality_reporter_factory()
    metrics_port = _create_metrics_port()
    converter_id = getattr(
        getattr(config, "output", SimpleNamespace()), "converter", None
    )
    frame_converter = frame_converter_factory(converter_id)

    output_writer = output_writer_factory(
        config=config.determinism,
        qc_config=config.qc,
        writer=writer,
        metadata_writer=metadata_writer,
        quality_reporter=quality_reporter,
        metrics_port=metrics_port,
        converter=frame_converter,
    )
    metadata_builder = _create_metadata_builder()
    validator_factory = _create_validator_factory()
    hash_service = hash_service_factory()

    return PipelineContainer(
        config,
        logger=logger,
        output_writer=output_writer,
        validator_factory=validator_factory,
        metadata_builder=metadata_builder,
        metrics_port=metrics_port,
        hash_service=hash_service,
        provider_registry=provider_registry,
        provider_registry_provider=provider_registry_provider,
    )


def create_default_container_factory() -> Callable[..., Any]:
    """Expose default container factory."""
    return build_default_container
