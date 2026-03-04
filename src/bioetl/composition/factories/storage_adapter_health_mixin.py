"""Health check and preview operations mixin for StorageAdapter."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus, JsonDict

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapterHealthMixin"]


class StorageAdapterHealthMixin:
    """Mixin providing health check, preview, and lifecycle operations."""

    bronze: BronzeWriter
    silver: SilverWriter
    gold: GoldWriter

    async def aclose(self) -> None:
        """Close resources.

        Implements aclose() required by StoragePort protocol.
        """
        pass  # Writers don't need explicit cleanup

    async def health_check(self) -> HealthStatus:
        """Check storage accessibility and write capability.

        Validates Bronze, Silver, and Gold directories are writable by
        attempting to create and delete a temporary file in each layer.

        Returns:
            HealthStatus:
            - HEALTHY: All layers accessible and writable
            - DEGRADED: Partial access (1-2 layers have issues)
            - UNHEALTHY: Critical storage failure (all layers unavailable)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._check_storage_health_sync)

    def _check_storage_health_sync(self) -> HealthStatus:
        """Synchronous storage health check implementation.

        Checks if each layer's base directory is writable.
        """
        layers = [
            ("bronze", Path(self.bronze.base_path)),
            ("silver", Path(self.silver.base_path)),
            ("gold", Path(self.gold.base_path)),
        ]

        issues = 0
        for _layer_name, base_path in layers:
            if not self._check_directory_writable(base_path):
                issues += 1

        if issues == 0:
            return HealthStatus.HEALTHY
        elif issues < len(layers):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> JsonDict:  # Any: factory wiring; concrete types resolved at runtime
        """Preview what would be cleared without actual deletion.

        Implements StoragePort.preview_cleanup().
        Used by CLI dry-run mode to show users what data would be affected.

        Args:
            silver_table: Silver table name (e.g., 'chembl.activity')
            gold_table: Optional Gold table name

        Returns:
            Dict with layer info including paths and file counts.
        """
        result: JsonDict = {  # preview payload values are heterogeneous
            "silver": self._preview_layer(self.silver, silver_table),
            "gold": None,
            "total_files": 0,
        }

        if gold_table:
            result["gold"] = self._preview_layer(self.gold, gold_table)

        result["total_files"] = result["silver"]["file_count"] + (
            result["gold"]["file_count"] if result["gold"] else 0
        )
        return result

    def _preview_layer(
        self,
        writer: SilverWriter | GoldWriter,
        table_name: str,
    ) -> JsonDict:  # Any: factory wiring; concrete types resolved at runtime
        """Count files in a layer without deletion.

        Args:
            writer: Delta or Gold writer instance
            table_name: Table name to preview

        Returns:
            Dict with path, file_count, and exists status.
        """
        path = writer.get_table_path(table_name)
        file_count = 0
        exists = path.exists()

        if exists:
            file_count = sum(1 for f in path.rglob("*") if f.is_file())

        return {
            "path": str(path),
            "file_count": file_count,
            "exists": exists,
        }

    @staticmethod
    def _check_directory_writable(dir_path: Path | str) -> bool:
        """Check if a directory is writable.

        Args:
            dir_path: Directory path to check (accepts Path or str).

        Returns:
            True if directory is writable, False otherwise.
        """
        try:
            path = Path(dir_path) if isinstance(dir_path, str) else dir_path
            path.mkdir(parents=True, exist_ok=True)
            temp_file = path / ".health_check_probe"
            temp_file.touch()
            temp_file.unlink()
            return True
        except (OSError, PermissionError):
            return False
