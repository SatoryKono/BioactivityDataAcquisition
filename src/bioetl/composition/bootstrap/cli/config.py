"""Bootstrap functions for configuration CLI operations.

Contains bootstrap functions for ConfigService.
Used primarily by CLI configuration operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.services import ConfigService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry import create_registry
from bioetl.domain.ports import DomainConfigMapperPort, SettingsLoaderPort
from bioetl.infrastructure.config import (
    get_settings,
    yaml_config_to_domain,
)
from bioetl.infrastructure.config_load_api import load_pipeline_config

__all__ = ["bootstrap_config_service"]

if TYPE_CHECKING:
    from bioetl.composition.registry import PipelineRegistry


def get_default_registry() -> PipelineRegistry:
    """Compatibility helper returning an explicit registered registry."""
    registry = create_registry()
    register_all_pipelines(registry=registry)
    return registry


def bootstrap_config_service(
    *,
    registry: PipelineRegistry | None = None,
) -> ConfigService:
    """Bootstrap ConfigService for CLI configuration operations.

    Creates a ConfigService for configuration access and validation.
    Wires up infrastructure dependencies for configuration loading.

    Args:
        registry: Optional explicit registry. When omitted, a fresh registered
            registry is built for this service instance.

    Returns:
        ConfigService configured for CLI operations.

    Example:
        >>> service = bootstrap_config_service()
        >>> settings = service.get_settings()
        >>> logger.info("environment", env=settings.env)
    """
    noop_logger = create_noop_logger()
    effective_registry = registry if registry is not None else get_default_registry()

    return ConfigService(
        logger=noop_logger,
        _settings_loader=cast(SettingsLoaderPort, get_settings),
        _pipeline_config_loader=load_pipeline_config,
        _domain_config_mapper=cast(DomainConfigMapperPort, yaml_config_to_domain),
        _registry_accessor=lambda: effective_registry,
    )
