# Host attrs/methods provided by concrete composition.
"""Health check and preview operations mixin for StorageBundle."""

from __future__ import annotations

from collections.abc import Awaitable
from pathlib import Path
from typing import Any, TYPE_CHECKING, cast

from bioetl.composition.factories.storage._blocking import run_storage_blocking
from bioetl.domain.types import HealthStatus, JsonDict

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageBundleHealthMixin"]


class StorageBundleHealthMixin:
    """Mixin providing health check, preview, and lifecycle operations."""

    # ARCH-CR2-06: typed host attributes (set by StorageBundle.__init__).
    bronze: BronzeWriter
    silver: SilverWriter
    gold: GoldWriter

    async def aclose(self) -> None:
        """Close resources.

        Implements aclose() required by StorageLifecyclePort.
        """
        for audit in self._iter_unique_audit_ports():
            aclose = getattr(audit, "aclose", None)
            if callable(aclose):
                awaitable = aclose()
                if isinstance(awaitable, Awaitable):
                    await awaitable

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
        return await run_storage_blocking(self._check_storage_health_sync)

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

        Implements StorageMaintenancePort.preview_cleanup().
        Used by CLI dry-run mode to show users what data would be affected.

        Args:
            silver_table: Silver table name (e.g., 'chembl.activity')
            gold_table: Optional Gold table name

        Returns:
            Dict with layer info including paths and file counts.
        """
        silver_preview = self._preview_layer(self.silver, silver_table)
        gold_preview = (
            self._preview_layer(self.gold, gold_table) if gold_table else None
        )
        result: JsonDict = {  # preview payload values are heterogeneous
            "silver": silver_preview,
            "gold": None,
            "total_files": 0,
        }

        if gold_preview is not None:
            result["gold"] = gold_preview

        result["total_files"] = silver_preview["file_count"] + (
            gold_preview["file_count"] if gold_preview else 0
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
        preview_method = getattr(writer, "preview_cleanup", None)
        if callable(preview_method):
            preview_result = cast(JsonDict, preview_method(table_name))
            if self._is_layer_preview_payload(preview_result):
                return preview_result

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
    def _is_layer_preview_payload(value: object) -> bool:
        """Check whether a preview payload has the expected layer shape."""
        if not isinstance(value, dict):
            return False
        path = value.get("path")
        file_count = value.get("file_count")
        exists = value.get("exists")
        return (
            isinstance(path, str)
            and isinstance(file_count, int)
            and isinstance(exists, bool)
        )

    def _iter_unique_audit_ports(self) -> list[object]:
        """Return explicit per-writer audit ports without double-closing shared ones."""
        seen: set[int] = set()
        audits: list[object] = []
        for writer in (self.bronze, self.silver, self.gold):
            audit = self._get_explicit_writer_audit(writer)
            if audit is None:
                continue
            audit_id = id(audit)
            if audit_id in seen:
                continue
            seen.add(audit_id)
            audits.append(audit)
        return audits

    @staticmethod
    def _get_explicit_writer_audit(writer: object) -> object | None:
        """Return a writer's explicitly assigned audit port when present."""
        try:
            writer_dict = vars(writer)
        except TypeError:
            return None
        return writer_dict.get("_audit")

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
