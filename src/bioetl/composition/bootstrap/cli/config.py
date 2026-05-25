"""Bootstrap `ConfigService` for CLI configuration commands."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import cast

from bioetl.application.services.config_service import ConfigService
from bioetl.application.services.control_plane.effective_config_service import (
    create_effective_config_service,
)
from bioetl.composition.bootstrap.cli.config_helpers import get_pipeline_yaml_for_dq
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.bootstrap.cli.service_builders import build_cli_config_service
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import DomainConfigMapperPort, SettingsLoaderPort
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.dq_contract_config_loader import (
    load_dq_config_for_pipeline,
)
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)

__all__ = [
    "bootstrap_config_service",
    "create_pipeline_config_loader",
    "create_registered_pipeline_registry",
]


def create_pipeline_config_loader(configs_root: Path) -> Callable[[str], object]:
    return lambda pipeline_name: load_pipeline_config_from_root(
        pipeline_name, configs_root=configs_root
    )


def create_registered_pipeline_registry(
    registry: PipelineRegistry | None = None,
) -> PipelineRegistry:
    """Create or populate an explicit pipeline registry for CLI composition."""
    effective_registry = registry if registry is not None else create_registry()
    register_all_pipelines(registry=effective_registry)
    return effective_registry


def bootstrap_config_service(
    *,
    registry: PipelineRegistry | None = None,
    configs_root: Path | None = None,
) -> ConfigService:
    """Assemble the CLI-facing ConfigService with default composition wiring."""
    resolved_configs_root = resolve_configs_root(configs_root)
    pipeline_config_loader = create_pipeline_config_loader(resolved_configs_root)
    effective_registry = create_registered_pipeline_registry(registry)
    return build_cli_config_service(
        registry=effective_registry,
        logger_factory=create_noop_logger,
        settings_loader=cast(SettingsLoaderPort, get_settings),
        pipeline_config_loader=pipeline_config_loader,
        domain_config_mapper=cast(DomainConfigMapperPort, yaml_config_to_domain),
        pipeline_yaml_getter=partial(
            get_pipeline_yaml_for_dq,
            pipeline_config_loader=pipeline_config_loader,
        ),
        dq_config_loader=partial(
            load_dq_config_for_pipeline,
            configs_root=resolved_configs_root,
        ),
        effective_config_service_factory=create_effective_config_service,
    )
