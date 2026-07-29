# Host attrs/methods provided by concrete composition.
"""Computed storage paths for application settings."""

from __future__ import annotations

from pathlib import Path
from typing import cast

__all__ = ["StoragePathSettingsMixin"]


class StoragePathSettingsMixin:
    """Computed local storage paths derived from ``data_dir``."""

    @property
    def bronze_path(self) -> Path:
        """Path for Bronze layer storage."""
        return cast(Path, getattr(self, "data_dir")) / "output" / "bronze"

    @property
    def silver_path(self) -> Path:
        """Path for Silver layer storage."""
        return cast(Path, getattr(self, "data_dir")) / "output" / "silver"

    @property
    def gold_path(self) -> Path:
        """Path for Gold layer storage."""
        return cast(Path, getattr(self, "data_dir")) / "output" / "gold"

    @property
    def checkpoint_path(self) -> Path:
        """Path for checkpoint storage."""
        return cast(Path, getattr(self, "data_dir")) / "output" / "checkpoints"

    @property
    def quarantine_path(self) -> Path:
        """Path for quarantine storage."""
        return cast(Path, getattr(self, "data_dir")) / "output" / "quarantine"
