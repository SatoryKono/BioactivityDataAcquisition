"""Bootstrap `ConfigService` for CLI configuration commands."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.application.services.control_plane.effective_config_service import create_effective_config_service
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.bootstrap.cli.service_builders import build_cli_config_service
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry_api import get_default_registry
from bioetl.domain.config import DQConfig
from bioetl.domain.ports import DomainConfigMapperPort, SettingsLoaderPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.dq_contract_config_loader import load_dq_config_for_pipeline
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config_from_root

__all__ = ["bootstrap_config_service", "create_pipeline_config_loader"]

if TYPE_CHECKING:
    from bioetl.application.services.config_service import ConfigService
    from bioetl.composition.registry_api import PipelineRegistry


def create_pipeline_config_loader(configs_root: Path) -> Callable[[str], object]:
    return lambda pipeline_name: load_pipeline_config_from_root(
        pipeline_name, configs_root=configs_root
    )


def _pipeline_yaml_for_dq(pipeline_name: str, *, pipeline_config_loader: Callable[[str], object]) -> JsonDict:
    config = pipeline_config_loader(pipeline_name)
    if hasattr(config, "model_dump"):
        return config.model_dump()
    if isinstance(config, Mapping):
        return dict(config)
    raise TypeError("Pipeline YAML config must provide model_dump() or be a mapping")


def bootstrap_config_service(*, registry: PipelineRegistry | None = None, configs_root: Path | None = None) -> ConfigService:
    """Assemble the CLI-facing ConfigService with default composition wiring."""
    resolved_configs_root = resolve_configs_root(configs_root)
    pipeline_config_loader = create_pipeline_config_loader(resolved_configs_root)
    return build_cli_config_service(
        registry=registry,
        logger_factory=create_noop_logger,
        register_pipelines=register_all_pipelines,
        default_registry_accessor=get_default_registry,
        settings_loader=cast(SettingsLoaderPort, get_settings),
        pipeline_config_loader=pipeline_config_loader,
        domain_config_mapper=cast(DomainConfigMapperPort, yaml_config_to_domain),
        pipeline_yaml_getter=lambda pipeline_name: _pipeline_yaml_for_dq(pipeline_name, pipeline_config_loader=pipeline_config_loader),
        dq_config_loader=lambda pipeline_name: cast(DQConfig, load_dq_config_for_pipeline(pipeline_name, configs_root=resolved_configs_root)),
        effective_config_service_factory=create_effective_config_service,
    )
