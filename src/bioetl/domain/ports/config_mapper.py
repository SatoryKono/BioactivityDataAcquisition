"""YAML-to-domain config mapper contract."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.config.pipeline import PipelineConfig
    from bioetl.domain.quality.dq_config import DQConfig

    PipelineYamlConfig = object


@runtime_checkable
class DomainConfigMapper(Protocol):
    """Callable contract for mapping YAML config to domain config."""

    def __call__(
        self,
        yaml_config: PipelineYamlConfig,
        resolved_dq_config: DQConfig | None = None,
    ) -> PipelineConfig:
        """Map YAML config to domain PipelineConfig."""
        ...
