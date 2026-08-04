# Host attrs/methods provided by concrete composition.
"""Computed storage paths for application settings."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

__all__ = ["StoragePathSettingsMixin"]


class _StoragePathSettingsHost(Protocol):
    """Structural host contract for settings-backed storage paths."""

    data_dir: Path


class StoragePathSettingsMixin:
    """Computed local storage paths derived from ``data_dir``."""

    @property
    def bronze_path(self: _StoragePathSettingsHost) -> Path:
        """Path for Bronze layer storage."""
        return self.data_dir / "output" / "bronze"

    @property
    def silver_path(self: _StoragePathSettingsHost) -> Path:
        """Path for Silver layer storage."""
        return self.data_dir / "output" / "silver"

    @property
    def gold_path(self: _StoragePathSettingsHost) -> Path:
        """Path for Gold layer storage."""
        return self.data_dir / "output" / "gold"

    @property
    def checkpoint_path(self: _StoragePathSettingsHost) -> Path:
        """Path for checkpoint storage."""
        return self.data_dir / "output" / "checkpoints"

    @property
    def quarantine_path(self: _StoragePathSettingsHost) -> Path:
        """Path for quarantine storage."""
        return self.data_dir / "output" / "quarantine"
