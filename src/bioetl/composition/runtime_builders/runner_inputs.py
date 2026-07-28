"""Shared runtime input models for runner composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

@dataclass(frozen=True, slots=True)
class RunnerInputs:
    settings: Settings
    yaml_config: PipelineYamlConfig
    observability: ObservabilityBundle
    runtime_config: RuntimeConfig
    filter_config: InputFilterConfig | None
    cached_bronze: CachedBronzeContext

__all__ = ["RunnerInputs"]
