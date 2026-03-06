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

    batch_size: int
    relaxed_dq: bool


@runtime_checkable
class SettingsPort(Protocol):
    """Protocol for application settings."""

    env: str
    data_dir: str | Path
    debug: bool
    test_mode: bool
    metrics_enabled: bool
    metrics_port: int
    pipeline: PipelineSettingsPort

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
