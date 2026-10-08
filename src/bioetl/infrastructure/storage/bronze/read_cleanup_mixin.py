# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Read/list/cleanup helpers extracted from ``BronzeWriterIOMixin``."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import orjson
import zstandard as zstd

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.bronze.cleanup_support import (
    date_dir_name_is_older,
    find_old_date_dirs,
    is_owned_artifact,
    real_root,
    safe_rmdir,
    safe_unlink,
    scan_dir_entries,
    validate_scope_filter,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort


class BronzeWriterReadCleanupMixin:
    """Filesystem read/list/cleanup helpers for Bronze storage."""

    base_path: Path = cast(Any, None)  # Any: host attr default (PD3)
    _flat_structure: bool = cast(Any, None)  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _metrics: MetricsPort = cast(Any, None)  # Any: host attr default (PD3)

    async def read_bronze(
        self, path: str
    ) -> AsyncIterator[JsonDict]:  # Any: record/metadata values are heterogeneous
        """Read and decompress Bronze file (for testing/debugging)."""
        full_path = self.base_path / path

        def _read_and_decompress() -> bytes:
            with open(full_path, "rb") as f:
                compressed_data = f.read()
            decompressor = zstd.ZstdDecompressor()
            with decompressor.stream_reader(compressed_data) as reader:
                data: bytes = reader.read()
                return data

        # ARCH-CR2-01: keep blocking FS/decompress off the event loop.
        decompressed_data = await asyncio.to_thread(_read_and_decompress)
        # JSONL boundaries are LF bytes; Unicode separators may occur in strings.
        for line in decompressed_data.split(b"\n"):
            if line.strip():
                yield orjson.loads(line)

    def _list_batches_sync(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """Sync body for list_batches with blocking Path I/O."""
        if self._flat_structure and not provider and not entity:
            search_path = (
                self.base_path / date.strftime("%Y-%m-%d") if date else self.base_path
            )
        else:
            if not provider or not entity:
                return []
            prefix = f"{provider}/{entity}/"
            if date:
                prefix = f"{prefix}{date.strftime('%Y-%m-%d')}/"
            search_path = self.base_path / prefix

        if not search_path.exists():
            return []

        pattern = "batch_*.jsonl.zst" if date else "**/*.jsonl.zst"
        files = list(search_path.glob(pattern))
        return sorted(p.relative_to(self.base_path).as_posix() for p in files)

    async def list_batches(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """List all batch files for a given provider/entity."""
        result = await asyncio.to_thread(
            self._list_batches_sync, provider, entity, date
        )
        self._logger.debug(
            "bronze_list_batches",
            provider=provider,
            entity=entity,
            batch_count=len(result),
        )
        return result

    def _log_cleanup_skip(self, path: str, reason: str) -> None:
        """Emit a diagnostic for a skipped cleanup candidate."""
        self._logger.warning(
            "bronze_cleanup_skip",
            path=path,
            reason=reason,
        )

    def _find_old_date_dirs(
        self,
        cutoff_str: str,
        provider: str | None = None,
        entity: str | None = None,
    ) -> list[Path]:
        """Find date directories older than cutoff without following links."""
        return find_old_date_dirs(
            self.base_path,
            flat_structure=self._flat_structure,
            cutoff_str=cutoff_str,
            provider=provider,
            entity=entity,
            on_skip=self._log_cleanup_skip,
            on_flat_filter=lambda: self._logger.warning(
                "bronze_cleanup_flat_scope_filter",
                provider=provider,
                entity=entity,
            ),
        )

    def _is_old_date_dir(self, path: Path, cutoff_str: str) -> bool:
        """Check if path is a canonical date directory older than cutoff."""
        return date_dir_name_is_older(path.name, cutoff_str)

    def _cleanup_old_files_sync(
        self,
        cutoff_str: str,
        dry_run: bool,
        provider: str | None,
        entity: str | None,
    ) -> tuple[int, int, int, int, int]:
        """Sync body for cleanup_old_files with blocking Path I/O."""
        files = bytes_total = dirs = skipped_files = skipped_dirs = 0
        root_real = real_root(self.base_path)

        for date_dir in self._find_old_date_dirs(cutoff_str, provider, entity):
            removed_files, removed_bytes, skipped = self._remove_old_dir_files(
                date_dir=date_dir,
                dry_run=dry_run,
                root_real=root_real,
            )
            files += removed_files
            bytes_total += removed_bytes
            skipped_files += skipped
            if dry_run:
                if skipped == 0:
                    dirs += 1
                else:
                    skipped_dirs += 1
            elif safe_rmdir(date_dir, root_real):
                dirs += 1
            else:
                skipped_dirs += 1
                self._log_cleanup_skip(str(date_dir), "rmdir_refused")

        return files, bytes_total, dirs, skipped_files, skipped_dirs

    def _remove_old_dir_files(
        self,
        *,
        date_dir: Path,
        dry_run: bool,
        root_real: Path,
    ) -> tuple[int, int, int]:
        """Remove owned Bronze artifacts from one old date directory."""
        files_removed = 0
        bytes_removed = 0
        files_skipped = 0
        entries = scan_dir_entries(date_dir)
        if entries is None:
            return 0, 0, 1
        for entry in entries:
            file_path = Path(entry.path)
            try:
                is_file = entry.is_file(follow_symlinks=False)
            except OSError:
                is_file = False
            if not is_file or not is_owned_artifact(entry.name):
                self._log_cleanup_skip(entry.path, "unknown_artifact")
                files_skipped += 1
                continue
            size = entry.stat(follow_symlinks=False).st_size
            if dry_run:
                files_removed += 1
                bytes_removed += size
                continue
            if safe_unlink(file_path, root_real):
                files_removed += 1
                bytes_removed += size
            else:
                self._log_cleanup_skip(entry.path, "unlink_refused")
                files_skipped += 1
        return files_removed, bytes_removed, files_skipped

    async def cleanup_old_files(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> dict[str, int]:
        """Remove Bronze files older than cutoff date."""
        validate_scope_filter(provider, "provider")
        validate_scope_filter(entity, "entity")
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        (
            files,
            bytes_total,
            dirs,
            skipped_files,
            skipped_dirs,
        ) = await asyncio.to_thread(
            self._cleanup_old_files_sync,
            cutoff_str,
            dry_run,
            provider,
            entity,
        )

        self._logger.info(
            "bronze_cleanup_complete",
            cutoff=cutoff_str,
            dry_run=dry_run,
            files_removed=files,
            bytes_freed=bytes_total,
            dirs_removed=dirs,
            files_skipped=skipped_files,
            dirs_skipped=skipped_dirs,
        )
        if not dry_run and files > 0:
            cleanup_labels = {"operation": "cleanup"}
            self._metrics.increment_counter(
                "bioetl_bronze_files_removed_total",
                files,
                cleanup_labels,
            )
            self._metrics.increment_counter(
                "bioetl_bronze_bytes_freed_total",
                bytes_total,
                cleanup_labels,
            )
        return {
            "files_removed": files,
            "bytes_freed": bytes_total,
            "directories_removed": dirs,
            "files_skipped": skipped_files,
            "directories_skipped": skipped_dirs,
        }

    def preview_cleanup(
        self,
        provider: str | None = None,
        entity: str | None = None,
    ) -> JsonDict:  # Any: preview payload has heterogeneous values
        """Preview Bronze cleanup scope without deleting files."""
        preview_root = self._resolve_bronze_preview_root(provider, entity)
        exists = preview_root.exists()
        file_count = (
            sum(1 for file_path in preview_root.rglob("*") if file_path.is_file())
            if exists
            else 0
        )

        return {
            "path": str(preview_root),
            "file_count": file_count,
            "exists": exists,
        }

    def _resolve_bronze_preview_root(
        self,
        provider: str | None,
        entity: str | None,
    ) -> Path:
        """Resolve Bronze preview root for optional provider/entity filters."""
        if self._flat_structure:
            return self.base_path
        if provider and entity:
            return self.base_path / provider / entity
        if provider:
            return self.base_path / provider
        return self.base_path
