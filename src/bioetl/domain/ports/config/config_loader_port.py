"""Configuration loader port protocols for dependency inversion.

Defines contracts for loading settings, pipeline configs, and domain mapping.
Migrated from application/services/config_service.py per RF-040 (ARCH-008).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.config import PipelineConfig

if TYPE_CHECKING:
    from bioetl.domain.ports.config.config_port import (
        PipelineYamlConfigPort,
        SettingsPort,
    )

__all__ = [
    "DomainConfigMapperPort",
    "PipelineConfigLoaderPort",
    "SettingsLoaderPort",
]


@runtime_checkable
class SettingsLoaderPort(Protocol):
    """Protocol for loading application settings."""

    def __call__(self) -> SettingsPort:
        """Load settings."""
        ...


@runtime_checkable
class PipelineConfigLoaderPort(Protocol):
    """Protocol for loading pipeline YAML configuration."""

    def __call__(self, pipeline_name: str) -> PipelineYamlConfigPort:
        """Load pipeline configuration."""
        ...


@runtime_checkable
class DomainConfigMapperPort(Protocol):
    """Protocol for mapping YAML configuration to domain configuration."""

    def __call__(self, yaml_config: PipelineYamlConfigPort) -> PipelineConfig:
        """Map YAML config to domain config."""
        ...
