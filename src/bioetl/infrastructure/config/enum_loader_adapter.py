"""Adapter implementing EnumLoaderPort for infrastructure layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.domain.config.enum_loader import EnumLoaderPort

__all__ = ["FileSystemEnumLoader"]


class FileSystemEnumLoader(EnumLoaderPort):
    """Infrastructure adapter for loading enums from filesystem."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize enum loader with optional base path.

        Args:
            base_path: Base path for enum files. If None, uses project root.
        """
        self.base_path = base_path

    def load_chembl_enums(
        self,
    ) -> dict[str, Any]:  # Any: Dynamic YAML content structure
        """Load ChEMBL enum configurations from filesystem."""
        from bioetl.infrastructure.config.enum_file_loader import (
            load_chembl_enums_from_file,
        )

        if self.base_path is None:
            return load_chembl_enums_from_file()
        else:
            return load_chembl_enums_from_file(
                self.base_path / "configs" / "enums" / "chembl.yaml"
            )
