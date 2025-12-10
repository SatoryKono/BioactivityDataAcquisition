"""
Factory for creating PipelineContainer with default infrastructure implementations.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, cast

from bioetl.application.config.resolution import ConfigPathResolver
from bioetl.application.container import PipelineContainer
from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.domain.clients.base.output.contracts import RunMetadataBuilderProtocol
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
from bioetl.domain.observability import MetricsPortABC
from bioetl.domain.provider_registry import ProviderRegistryABC
from bioetl.domain.validation import ValidatorFactoryABC
from bioetl.infrastructure.clients.base.abc_registry_resolver import ABCRegistryResolver
from bioetl.infrastructure.config.loader import (
    get_pipeline_config,
    get_pipeline_config_from_path,
)
from bioetl.infrastructure.config.sources import get_configs_root
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


def _create_metrics_port() -> MetricsPortABC:
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
    loader_factory = registry_loader.resolve_default_factory("LoaderABC")
    frame_converter_factory = registry_loader.resolve_default_factory(
        "OutputFrameConverterABC"
    )
    hash_service_factory = registry_loader.resolve_default_factory("HashServiceABC")
    timestamp_provider_factory = registry_loader.resolve_default_factory(
        "TimestampProviderABC"
    )
    index_generator_factory = registry_loader.resolve_default_factory(
        "IndexGeneratorABC"
    )

    logger = logger_factory()
    metrics_port = _create_metrics_port()
    converter_id = getattr(config.sink.output, "converter", None)
    frame_converter = frame_converter_factory(converter_id)

    loader = loader_factory(
        config=config.quality.determinism,
        qc_config=config.quality.qc,
        metrics_port=metrics_port,
        converter=frame_converter,
    )
    metadata_builder = _create_metadata_builder()
    validator_factory = _create_validator_factory()
    hash_service = hash_service_factory()
    timestamp_provider = timestamp_provider_factory()
    index_generator = index_generator_factory()

    return PipelineContainer(
        config,
        logger=logger,
        loader=loader,
        validator_factory=validator_factory,
        metadata_builder=metadata_builder,
        metrics_port=metrics_port,
        hash_service=hash_service,
        timestamp_provider=timestamp_provider,
        index_generator=index_generator,
        provider_registry=provider_registry,
        provider_registry_provider=provider_registry_provider,
    )


def create_default_container_factory() -> Callable[..., Any]:
    """Expose default container factory."""
    return build_default_container


def create_config_loader() -> PipelineConfigLoaderProtocol:
    """Return config loader port backed by infrastructure loader.

    Creates a config loader that uses explicit schema contract provider injection.
    The provider is obtained from SimplePipelineContainer and bound to the loader
    functions.

    Returns:
        PipelineConfigLoaderProtocol: Config loader with bound schema provider.
    """
    from bioetl.interfaces.simple_container import SimplePipelineContainer

    container = SimplePipelineContainer()
    container.bootstrap()

    # Get the schema contract provider from the container
    provider = container.schema_contract_provider

    # Create bound functions that pass the provider explicitly
    def get_by_id_with_provider(
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict | None = None,
        env_overrides: dict | None = None,
        base_dir: str | Path | None = None,
    ):
        return get_pipeline_config(
            pipeline_id,
            schema_contract_provider=provider,
            profile=profile,
            cli_overrides=cli_overrides,
            env_overrides=env_overrides,
            base_dir=base_dir,
        )

    def get_from_path_with_provider(
        config_path: str | Path,
        *,
        profile: str | None = None,
        profiles_root: str | Path | None = None,
        cli_overrides: dict | None = None,
        env_overrides: dict | None = None,
    ):
        return get_pipeline_config_from_path(
            config_path,
            schema_contract_provider=provider,
            profile=profile,
            profiles_root=profiles_root,
            cli_overrides=cli_overrides,
            env_overrides=env_overrides,
        )

    return cast(
        PipelineConfigLoaderProtocol,
        SimpleNamespace(
            get_by_id=get_by_id_with_provider,
            get_from_path=get_from_path_with_provider,
        ),
    )


def create_config_path_resolver(
    configs_root: Path | str | None = None,
) -> ConfigPathResolver:
    """Create ConfigPathResolver with default or specified configs root.

    Args:
        configs_root: Root directory for configs. If None, uses infrastructure
            default (BIOETL_CONFIG_DIR env var or 'configs' directory).

    Returns:
        ConfigPathResolver instance.
    """
    effective_root = (
        Path(configs_root) if configs_root is not None else get_configs_root(None)
    )
    return ConfigPathResolver(effective_root)
