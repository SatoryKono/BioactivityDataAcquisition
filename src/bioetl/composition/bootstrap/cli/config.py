"""Bootstrap `ConfigService` for CLI configuration commands."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.application.services.control_plane.effective_config_service import (
    create_effective_config_service,
)
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.bootstrap.cli.service_builders import build_cli_config_service
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry_api import get_default_registry
from bioetl.domain.config import DQConfig
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
    from bioetl.application.services.config_service import ConfigService
    from bioetl.composition.registry_api import PipelineRegistry


def _pipeline_yaml_for_dq(pipeline_name: str) -> JsonDict:
    config = load_pipeline_config(pipeline_name)
    if hasattr(config, "model_dump"):
        pipeline_payload: JsonDict = config.model_dump()
        return pipeline_payload
    if isinstance(config, Mapping):
        return dict(config)
    raise TypeError("Pipeline YAML config must provide model_dump() or be a mapping")


def _load_dq_config_for_pipeline_with_root(
    pipeline_name: str,
    *,
    configs_root: Path,
) -> DQConfig:
    """Load governed DQ config from the injected configs root."""
    return load_dq_config_for_pipeline(
        pipeline_name,
        configs_root=configs_root,
    )


def bootstrap_config_service(
    *,
    registry: PipelineRegistry | None = None,
    configs_root: Path = Path("configs"),
) -> ConfigService:
    """Assemble the CLI-facing ConfigService with default composition wiring."""
    return build_cli_config_service(
        registry=registry,
        logger_factory=create_noop_logger,
        register_pipelines=register_all_pipelines,
        default_registry_accessor=get_default_registry,
        settings_loader=cast(SettingsLoaderPort, get_settings),
        pipeline_config_loader=load_pipeline_config,
        domain_config_mapper=cast(DomainConfigMapperPort, yaml_config_to_domain),
        pipeline_yaml_getter=_pipeline_yaml_for_dq,
        dq_config_loader=lambda pipeline_name: _load_dq_config_for_pipeline_with_root(
            pipeline_name,
            configs_root=configs_root,
        ),
        effective_config_service_factory=create_effective_config_service,
    )
