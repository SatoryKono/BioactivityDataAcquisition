"""Configuration port protocols for dependency inversion.

Defines contracts for application settings and pipeline YAML configuration.
Migrated from application/services/config_service.py per RF-040 (ARCH-008).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from bioetl.domain.types import JsonDict

__all__ = [
    "PipelineSettingsPort",
    "PipelineYamlConfigPort",
    "SettingsPort",
]


@runtime_checkable
class PipelineSettingsPort(Protocol):
    """Protocol for pipeline-specific settings."""

    @property
    def batch_size(self) -> int:
        """Configured batch size."""
        ...

    @property
    def relaxed_dq(self) -> bool:
        """Whether relaxed data-quality mode is enabled."""
        ...


@runtime_checkable
class SettingsPort(Protocol):
    """Protocol for application settings."""

    @property
    def env(self) -> str:
        """Deployment environment."""
        ...

    @property
    def data_dir(self) -> str | Path:
        """Base data directory."""
        ...

    @property
    def debug(self) -> bool:
        """Whether debug mode is enabled."""
        ...

    @property
    def test_mode(self) -> bool:
        """Whether test mode is enabled."""
        ...

    @property
    def metrics_enabled(self) -> bool:
        """Whether metrics are enabled."""
        ...

    @property
    def metrics_port(self) -> int:
        """Metrics port number."""
        ...

    @property
    def pipeline(self) -> PipelineSettingsPort:
        """Pipeline-specific settings."""
        ...

    @property
    def bronze_path(self) -> str | Path:
        """Path for Bronze layer storage."""
        ...

    @property
    def silver_path(self) -> str | Path:
        """Path for Silver layer storage."""
        ...

    @property
    def gold_path(self) -> str | Path:
        """Path for Gold layer storage."""
        ...

    @property
    def checkpoint_path(self) -> str | Path:
        """Path for checkpoint storage."""
        ...

    @property
    def quarantine_path(self) -> str | Path:
        """Path for quarantine storage."""
        ...

    def model_dump(self) -> JsonDict:  # Any: YAML config has heterogeneous values
        """Convert settings to dictionary.

        Returns:
            Model data as dictionary.
        """
        ...


@runtime_checkable
class PipelineYamlConfigPort(Protocol):
    """Protocol for pipeline YAML configuration."""

    provider: str
    entity_type: str
    silver_table: str
    gold_table: str | None

    def model_dump(self) -> JsonDict:  # Any: YAML config has heterogeneous values
        """Convert configuration to dictionary.

        Returns:
            Model data as dictionary.
        """
        ...
