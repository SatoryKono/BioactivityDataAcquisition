"""Canonical domain-config resolution flow for validated pipeline YAML config."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader

if TYPE_CHECKING:
    from bioetl.domain.config import DQConfig, PipelineConfig
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class DomainConfigMapper(Protocol):
    """Typed mapper seam for translating validated YAML config into domain config."""

    def __call__(
        self,
        yaml_config: PipelineYamlConfig,
        resolved_dq_config: DQConfig | None = None,
    ) -> PipelineConfig: ...


class PipelineConfigDQResolver(Protocol):
    """Typed resolver seam for DQ enrichment of validated pipeline YAML config."""

    def resolve_dq_config(
        self,
        yaml_config: PipelineYamlConfig,
    ) -> DQConfig:
        """Resolve the DQ config that should accompany this YAML pipeline config."""
        ...


class PipelineConfigDQResolverProvider(Protocol):
    """Typed provider seam for creating pipeline DQ resolvers."""

    def __call__(
        self,
        configs_root: Path,
        *,
        relaxed_dq: bool = False,
    ) -> PipelineConfigDQResolver: ...


@dataclass(frozen=True, slots=True)
class DomainConfigResolver:
    """Resolve domain config from validated YAML config plus hierarchical DQ config."""

    configs_root: Path = Path("configs")
    loader_class: PipelineConfigDQResolverProvider = PipelineConfigLoader
    domain_mapper: DomainConfigMapper = yaml_config_to_domain

    def resolve(
        self,
        yaml_config: PipelineYamlConfig,
        *,
        relaxed_dq: bool,
    ) -> PipelineConfig:
        """Resolve domain config from YAML with DQ loader composition."""
        config_loader = self.loader_class(self.configs_root, relaxed_dq=relaxed_dq)
        resolved_dq = config_loader.resolve_dq_config(yaml_config)
        return self.domain_mapper(yaml_config, resolved_dq_config=resolved_dq)


def resolve_domain_pipeline_config(
    yaml_config: PipelineYamlConfig,
    *,
    configs_root: Path = Path("configs"),
    relaxed_dq: bool = False,
    loader_class: PipelineConfigDQResolverProvider = PipelineConfigLoader,
    domain_mapper: DomainConfigMapper = yaml_config_to_domain,
) -> PipelineConfig:
    """Resolve domain config from an already validated YAML pipeline config."""
    resolver = DomainConfigResolver(
        configs_root=configs_root,
        loader_class=loader_class,
        domain_mapper=domain_mapper,
    )
    return resolver.resolve(yaml_config, relaxed_dq=relaxed_dq)


def load_domain_pipeline_config(
    pipeline_name: str,
    *,
    configs_root: Path = Path("configs"),
    relaxed_dq: bool = False,
    yaml_loader: Callable[[str], PipelineYamlConfig] = load_pipeline_config,
    loader_class: PipelineConfigDQResolverProvider = PipelineConfigLoader,
    domain_mapper: DomainConfigMapper = yaml_config_to_domain,
) -> PipelineConfig:
    """Load domain config through the canonical function-based config flow."""
    yaml_config = yaml_loader(pipeline_name)
    return resolve_domain_pipeline_config(
        yaml_config,
        configs_root=configs_root,
        relaxed_dq=relaxed_dq,
        loader_class=loader_class,
        domain_mapper=domain_mapper,
    )


__all__ = [
    "DomainConfigResolver",
    "load_domain_pipeline_config",
    "resolve_domain_pipeline_config",
]
