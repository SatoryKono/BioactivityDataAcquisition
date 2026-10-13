# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Read/list/cleanup helpers extracted from ``BronzeWriterIOMixin``."""

from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import orjson
import zstandard as zstd

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.bronze.cleanup_core import BronzeRootLease
from bioetl.infrastructure.storage.bronze.cleanup_metrics import (
    emit_cleanup_outcome_metrics,
)
from bioetl.infrastructure.storage.bronze.cleanup_planner import (
    BronzeCleanupPlannerMixin,
    _CleanupDatePlan,
)
from bioetl.infrastructure.storage.bronze.cleanup_preview_mixin import (
    BronzeCleanupPreviewMixin,
)
from bioetl.infrastructure.storage.bronze.cleanup_support import (
    bronze_tree_lock,
    date_dir_name_is_older,
    destructive_cleanup_supported,
    find_old_date_dirs,
    real_root,
    safe_rmdir,
    safe_unlink,
    validate_scope_filter,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort, MetricsPort


async def _drain_cleanup_worker(task: asyncio.Task[dict[str, int]]) -> None:
    """Wait through repeated cancellation before releasing the caller."""
    while not task.done():
        try:
            await asyncio.shield(task)
        except BaseException as exc:
            if isinstance(exc, asyncio.CancelledError):
                current = asyncio.current_task()
                if current is not None:
                    current.uncancel()
            elif not task.done():
                raise


class BronzeWriterReadMixin:
    """Filesystem read and batch listing helpers for Bronze storage."""

    base_path: Path = cast(Any, None)  # Any: host attr default (PD3)
    _flat_structure: bool = cast(Any, None)  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)

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

    def _batch_search_path(
        self, provider: str, entity: str, date: datetime | None
    ) -> Path | None:
        if self._flat_structure and not provider and not entity:
            return (
                self.base_path / date.strftime("%Y-%m-%d") if date else self.base_path
            )
        if not provider or not entity:
            return None
        path = self.base_path / provider / entity
        return path / date.strftime("%Y-%m-%d") if date else path

    def _list_batches_sync(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """Sync body for list_batches with blocking Path I/O."""
        search_path = self._batch_search_path(provider, entity, date)
        if search_path is None or not search_path.exists():
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


class BronzeWriterReadCleanupMixin(
    BronzeWriterReadMixin, BronzeCleanupPlannerMixin, BronzeCleanupPreviewMixin
):
    """Apply and report nonmutating Bronze cleanup plans."""

    _metrics: MetricsPort = cast(Any, None)  # Any: host attr default (PD3)
    _resolve_bronze_path: Callable[[str, str, str, str], str] = cast(
        Any, None
    )  # Any: host method default (PD3)

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
        on_skip: Callable[[str, str], None] | None = None,
        base_path: Path | None = None,
    ) -> list[Path]:
        """Find date directories older than cutoff without following links."""
        return find_old_date_dirs(
            base_path if base_path is not None else self.base_path,
            flat_structure=self._flat_structure,
            cutoff_str=cutoff_str,
            provider=provider,
            entity=entity,
            on_skip=on_skip or self._log_cleanup_skip,
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
        cancel_requested: threading.Event | None = None,
    ) -> dict[str, int]:
        """Plan once and apply the same candidates under the writer/cleaner lock."""
        if not dry_run and not destructive_cleanup_supported():
            raise NotImplementedError(
                "Bronze destructive cleanup is unsupported on this platform/FS"
            )
        if dry_run:
            return self._cleanup_old_files_locked_sync(
                cutoff_str, dry_run, provider, entity
            )
        if not self.base_path.exists():
            return self._empty_cleanup_stats()
        with bronze_tree_lock(self.base_path, exclusive=True) as locked_root:
            if cancel_requested is not None and cancel_requested.is_set():
                return self._empty_cleanup_stats()
            return self._cleanup_old_files_locked_sync(
                cutoff_str, dry_run, provider, entity, locked_root
            )

    def _cleanup_old_files_locked_sync(
        self,
        cutoff_str: str,
        dry_run: bool,
        provider: str | None,
        entity: str | None,
        locked_root: BronzeRootLease | None = None,
    ) -> dict[str, int]:
        stats = self._empty_cleanup_stats()
        root_abs = (
            locked_root.path
            if locked_root is not None
            else Path(os.path.abspath(self.base_path))  # noqa: PTH100
        )
        root_real = (
            locked_root.path if locked_root is not None else real_root(self.base_path)
        )

        def on_discovery_skip(path: str, reason: str) -> None:
            self._log_cleanup_skip(path, reason)
            if reason in ("scan_error", "stat_error"):
                stats["directories_failed"] += 1
            elif reason == "missing_scope":
                stats["directories_conflicted"] += 1
            elif reason != "not_a_directory":
                stats["directories_skipped"] += 1

        for date_dir in self._find_old_date_dirs(
            cutoff_str,
            provider,
            entity,
            on_skip=on_discovery_skip,
            base_path=locked_root.path if locked_root is not None else None,
        ):
            plan = self._plan_old_dir_files(
                date_dir,
                root_abs,
                root_real,
                root_fd=locked_root.fd if locked_root is not None else None,
            )
            self._record_cleanup_plan(stats, plan)
            if not dry_run:
                self._apply_cleanup_plan(
                    stats,
                    plan,
                    root_abs,
                    root_real,
                    locked_root.fd if locked_root is not None else None,
                )
        return stats

    def _apply_cleanup_plan(
        self,
        stats: dict[str, int],
        plan: _CleanupDatePlan,
        root_abs: Path,
        root_real: Path,
        root_fd: int | None,
    ) -> None:
        """Apply the exact planned inodes and retain partial-result accounting."""
        failed_before = stats["files_failed"]
        conflicted_before = stats["files_conflicted"]

        def on_stage_error(name: str, _error: OSError) -> None:
            stats["directories_failed"] += 1
            self._log_cleanup_skip(str(self.base_path / name), "stage_cleanup_error")

        self._apply_planned_files(
            stats, plan, root_abs, root_real, root_fd, on_stage_error
        )
        if not plan.removable:
            return
        if (
            stats["files_failed"] != failed_before
            or stats["files_conflicted"] != conflicted_before
        ):
            stats["directories_skipped"] += 1
            return
        self._apply_planned_directory(
            stats, plan, root_abs, root_real, root_fd, on_stage_error
        )

    def _apply_planned_files(
        self,
        stats: dict[str, int],
        plan: _CleanupDatePlan,
        root_abs: Path,
        root_real: Path,
        root_fd: int | None,
        on_stage_error: Callable[[str, OSError], None],
    ) -> None:
        failed_groups: set[str] = set()
        for candidate in plan.files:
            group = candidate.path.name.split(".jsonl", 1)[0]
            if group in failed_groups:
                stats["files_skipped"] += 1
                stats["bytes_skipped"] += candidate.identity.st_size
                self._log_cleanup_skip(str(candidate.path), "associated_member_failed")
                continue
            try:
                removed = safe_unlink(
                    candidate.path,
                    root_abs,
                    root_real,
                    candidate.identity,
                    on_stage_error=on_stage_error,
                    root_fd=root_fd,
                )
            except OSError:
                failed_groups.add(group)
                stats["files_failed"] += 1
                stats["bytes_failed"] += candidate.identity.st_size
                self._log_cleanup_skip(str(candidate.path), "unlink_error")
            else:
                if removed:
                    stats["files_removed"] += 1
                    stats["bytes_freed"] += candidate.identity.st_size
                else:
                    failed_groups.add(group)
                    stats["files_conflicted"] += 1
                    stats["bytes_conflicted"] += candidate.identity.st_size
                    self._log_cleanup_skip(str(candidate.path), "unlink_conflict")

    def _apply_planned_directory(
        self,
        stats: dict[str, int],
        plan: _CleanupDatePlan,
        root_abs: Path,
        root_real: Path,
        root_fd: int | None,
        on_stage_error: Callable[[str, OSError], None],
    ) -> None:
        try:
            removed_dir = safe_rmdir(
                plan.path,
                root_abs,
                root_real,
                plan.identity,
                on_stage_error=on_stage_error,
                root_fd=root_fd,
            )
        except OSError:
            stats["directories_failed"] += 1
            self._log_cleanup_skip(str(plan.path), "rmdir_error")
        else:
            if removed_dir:
                stats["directories_removed"] += 1
            else:
                stats["directories_conflicted"] += 1
                self._log_cleanup_skip(str(plan.path), "rmdir_conflict")

    async def cleanup_bronze(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Implement ``BronzeStoragePort`` cleanup through the shared helper."""
        return await self.cleanup_old_files(cutoff_date, dry_run=dry_run)

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
        cancel_requested = threading.Event()
        worker = asyncio.create_task(
            asyncio.to_thread(
                self._cleanup_old_files_sync,
                cutoff_str,
                dry_run,
                provider,
                entity,
                cancel_requested,
            )
        )
        try:
            result = await asyncio.shield(worker)
        except asyncio.CancelledError:
            cancel_requested.set()
            # A cancelled caller must not leave an unobserved destructive thread.
            await _drain_cleanup_worker(worker)
            raise

        self._logger.info(
            "bronze_cleanup_complete",
            cutoff=cutoff_str,
            dry_run=dry_run,
            **result,
        )
        if not dry_run and result["files_removed"] > 0:
            cleanup_labels = {"operation": "cleanup"}
            self._metrics.increment_counter(
                "bioetl_bronze_files_removed_total",
                result["files_removed"],
                cleanup_labels,
            )
            self._metrics.increment_counter(
                "bioetl_bronze_bytes_freed_total",
                result["bytes_freed"],
                cleanup_labels,
            )
        if not dry_run:
            emit_cleanup_outcome_metrics(self._metrics, result)
        return result
