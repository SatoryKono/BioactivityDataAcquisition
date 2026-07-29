# Host attrs/methods provided by concrete composition.
"""Computed storage paths for application settings."""

from __future__ import annotations

from pathlib import Path

__all__ = ["StoragePathSettingsMixin"]


class StoragePathSettingsMixin:
    """Computed local storage paths derived from ``data_dir``."""

    data_dir: Path

    @property
    def bronze_path(self) -> Path:
        """Path for Bronze layer storage."""
        return self.data_dir / "output" / "bronze"

    @property
    def silver_path(self) -> Path:
        """Path for Silver layer storage."""
        return self.data_dir / "output" / "silver"

    @property
    def gold_path(self) -> Path:
        """Path for Gold layer storage."""
        return self.data_dir / "output" / "gold"

    @property
    def checkpoint_path(self) -> Path:
        """Path for checkpoint storage."""
        return self.data_dir / "output" / "checkpoints"

    @property
    def quarantine_path(self) -> Path:
        """Path for quarantine storage."""
        return self.data_dir / "output" / "quarantine"
