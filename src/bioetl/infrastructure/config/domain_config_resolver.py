"""Canonical domain-config resolution flow for validated pipeline YAML config."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.ports import DomainConfigMapperPort
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config,
    load_pipeline_config_from_root,
)
from bioetl.infrastructure.config.pipeline_dq_resolution import (
    DQConfigResolver,
    resolve_pipeline_dq_config,
)

DomainConfigMapper = DomainConfigMapperPort
_DEFAULT_DOMAIN_MAPPER = cast(DomainConfigMapper, yaml_config_to_domain)

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class PipelineConfigDQResolverProvider(Protocol):
    """Typed provider seam for creating pipeline DQ resolvers."""

    def __call__(
        self,
        configs_root: Path,
        *,
        relaxed_dq: bool = False,
    ) -> DQConfigResolver: ...


@dataclass(frozen=True, slots=True)
class DomainConfigResolver:
    """Resolve domain config from validated YAML config plus hierarchical DQ config."""

    configs_root: Path = field(default_factory=resolve_configs_root)
    dq_resolver_provider: PipelineConfigDQResolverProvider = DQConfigLoader
    domain_mapper: DomainConfigMapper = _DEFAULT_DOMAIN_MAPPER

    def resolve(
        self,
        yaml_config: PipelineYamlConfig,
        *,
        relaxed_dq: bool,
    ) -> PipelineConfig:
        """Resolve domain config from YAML with DQ loader composition."""
        dq_resolver = self.dq_resolver_provider(
            self.configs_root,
            relaxed_dq=relaxed_dq,
        )
        resolved_dq = resolve_pipeline_dq_config(
            yaml_config,
            dq_loader=dq_resolver,
        )
        return self.domain_mapper(yaml_config, resolved_dq_config=resolved_dq)


def resolve_domain_pipeline_config(
    yaml_config: PipelineYamlConfig,
    *,
    configs_root: Path | None = None,
    relaxed_dq: bool = False,
    dq_resolver_provider: PipelineConfigDQResolverProvider = DQConfigLoader,
    domain_mapper: DomainConfigMapper = _DEFAULT_DOMAIN_MAPPER,
) -> PipelineConfig:
    """Resolve domain config from an already validated YAML pipeline config."""
    resolver = DomainConfigResolver(
        configs_root=resolve_configs_root(configs_root),
        dq_resolver_provider=dq_resolver_provider,
        domain_mapper=domain_mapper,
    )
    return resolver.resolve(yaml_config, relaxed_dq=relaxed_dq)


def load_domain_pipeline_config(
    pipeline_name: str,
    *,
    configs_root: Path | None = None,
    relaxed_dq: bool = False,
    yaml_loader: Callable[[str], PipelineYamlConfig] = load_pipeline_config,
    dq_resolver_provider: PipelineConfigDQResolverProvider = DQConfigLoader,
    domain_mapper: DomainConfigMapper = _DEFAULT_DOMAIN_MAPPER,
) -> PipelineConfig:
    """Load domain config through the canonical function-based config flow."""
    root = resolve_configs_root(configs_root)
    if yaml_loader is load_pipeline_config:
        yaml_config = load_pipeline_config_from_root(pipeline_name, configs_root=root)
    else:
        yaml_config = yaml_loader(pipeline_name)
    return resolve_domain_pipeline_config(
        yaml_config,
        configs_root=root,
        relaxed_dq=relaxed_dq,
        dq_resolver_provider=dq_resolver_provider,
        domain_mapper=domain_mapper,
    )


__all__ = [
    "DomainConfigMapper",
    "DomainConfigResolver",
    "load_domain_pipeline_config",
    "resolve_domain_pipeline_config",
]
