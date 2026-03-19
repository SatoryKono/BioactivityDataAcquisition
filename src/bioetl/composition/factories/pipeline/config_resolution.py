"""Domain-config resolution helpers for pipeline construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline.construction_types import (
    DomainConfigMapper,
)
from bioetl.infrastructure.config import yaml_config_to_domain
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class DomainConfigResolver:
    """Resolve domain config with hierarchical DQ integration."""

    configs_root: Path = Path("configs")
    loader_class: type[PipelineConfigLoader] = PipelineConfigLoader
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
