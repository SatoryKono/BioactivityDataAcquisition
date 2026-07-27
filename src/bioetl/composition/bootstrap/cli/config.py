"""Bootstrap `ConfigService` for CLI configuration commands."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import cast

from bioetl.application.services.config_service import ConfigService
from bioetl.application.services.control_plane.effective_config.service import (
    create_effective_config_service,
)
from bioetl.composition.bootstrap.cli.config_helpers import get_pipeline_yaml_for_dq
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.bootstrap.cli.service_builders import build_cli_config_service
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders.config_access import (
    create_dq_config_loader,
    create_pipeline_config_loader,
    get_settings,
    resolve_configs_root,
)
from bioetl.domain.ports import (
    DomainConfigMapperPort,
    PipelineConfigLoaderPort,
    SettingsLoaderPort,
)
from bioetl.infrastructure.config.converters import yaml_config_to_domain


def create_registered_pipeline_registry(
    registry: PipelineRegistry | None = None,
) -> PipelineRegistry:
    effective_registry = create_registry() if registry is None else registry
    register_all_pipelines(registry=effective_registry)
    return effective_registry


def bootstrap_config_service(
    *,
    registry: PipelineRegistry | None = None,
    configs_root: Path | None = None,
) -> ConfigService:
    resolved_configs_root = resolve_configs_root(configs_root)
    pipeline_config_loader = create_pipeline_config_loader(resolved_configs_root)
    dq_config_loader = create_dq_config_loader(resolved_configs_root)

    from bioetl.application.services.config_dq_service import DQConfigLoaderProtocol

    return build_cli_config_service(
        registry=create_registered_pipeline_registry(registry),
        logger_factory=create_noop_logger,
        settings_loader=cast(SettingsLoaderPort, get_settings),
        pipeline_config_loader=cast(PipelineConfigLoaderPort, pipeline_config_loader),
        domain_config_mapper=cast(DomainConfigMapperPort, yaml_config_to_domain),
        pipeline_yaml_getter=partial(
            get_pipeline_yaml_for_dq, pipeline_config_loader=pipeline_config_loader
        ),
        dq_config_loader=cast(DQConfigLoaderProtocol, dq_config_loader),
        effective_config_service_factory=create_effective_config_service,
    )
