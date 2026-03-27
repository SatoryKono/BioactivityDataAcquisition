"""Bootstrap `ConfigService` for CLI configuration commands."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

from bioetl.application.services import ConfigService
from bioetl.application.services.config_dq_service import ConfigDQService
from bioetl.application.services.effective_config_service import (
    create_effective_config_service,
)
from bioetl.composition import get_default_registry
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.domain.ports import DomainConfigMapperPort, SettingsLoaderPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.dq_contract_config_loader import (
    load_dq_config_for_pipeline,
)
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

__all__ = ["bootstrap_config_service"]

if TYPE_CHECKING:
    from bioetl.composition import PipelineRegistry


def _pipeline_yaml_for_dq(pipeline_name: str) -> JsonDict:
    config = load_pipeline_config(pipeline_name)
    if hasattr(config, "model_dump"):
        return config.model_dump()
    if isinstance(config, Mapping):
        return dict(config)
    raise TypeError("Pipeline YAML config must provide model_dump() or be a mapping")


def bootstrap_config_service(
    *,
    registry: PipelineRegistry | None = None,
) -> ConfigService:
    """Assemble the CLI-facing ConfigService with default composition wiring."""
    logger = create_noop_logger()
    effective_registry = registry
    if effective_registry is None:
        register_all_pipelines()
        effective_registry = get_default_registry()

    dq_service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=_pipeline_yaml_for_dq,
        _dq_config_loader=load_dq_config_for_pipeline,
        _effective_config_service=create_effective_config_service(),
    )
    return ConfigService(
        logger=logger,
        _settings_loader=cast(SettingsLoaderPort, get_settings),
        _pipeline_config_loader=load_pipeline_config,
        _domain_config_mapper=cast(DomainConfigMapperPort, yaml_config_to_domain),
        _registry_accessor=lambda: effective_registry,
        _dq_service=dq_service,
    )
