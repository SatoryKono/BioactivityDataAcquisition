"""Bootstrap functions for configuration service.

Contains bootstrap functions for ConfigService.
Used primarily by CLI configuration operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.registry import get_default_registry
from bioetl.infrastructure.config import (
    get_settings,
    load_pipeline_config,
    yaml_config_to_domain,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.application.services import ConfigService

__all__ = [
    "bootstrap_config_service",
]


def bootstrap_config_service() -> ConfigService:
    """Bootstrap ConfigService for CLI configuration operations.

    Creates a ConfigService for configuration access and validation.
    Wires up infrastructure dependencies for configuration loading.

    Returns:
        ConfigService configured for CLI operations.

    Example:
        >>> service = bootstrap_config_service()
        >>> settings = service.get_settings()
        >>> logger.info("environment", env=settings.env)
    """
    from bioetl.application.services import ConfigService

    noop_logger = NoOpLogger()

    # Ensure pipelines are registered for list_pipelines()
    register_all_pipelines()

    return ConfigService(
        logger=noop_logger,
        _settings_loader=get_settings,
        _pipeline_config_loader=load_pipeline_config,
        _domain_config_mapper=yaml_config_to_domain,
        _registry_accessor=get_default_registry,
    )
