# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Read/list/cleanup helpers extracted from ``BronzeWriterIOMixin``."""

from __future__ import annotations

import asyncio
import contextvars
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import orjson
import zstandard as zstd

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.bronze.cleanup_core import BronzeRootLease
from bioetl.infrastructure.storage.bronze.cleanup_group_apply import (
    BronzeGroupCleanup,
    cleanup_roots,
    execute_cleanup_plan,
    group_cleanup_for_lock,
)
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
    root_components_safe,
    safe_rmdir,
    validate_scope_filter,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort, MetricsPort


_CLEANUP_EXECUTOR = ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="bronze-cleanup"
)


async def _drain_cleanup_worker(task: asyncio.Future[dict[str, int]]) -> None:
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
        if not self.base_path.exists():
            return self._empty_cleanup_stats()
        if dry_run:
            # Shared lock may resolve writer aliases; linked cleanup roots refuse.
            if not root_components_safe(self.base_path):
                return self._empty_cleanup_stats()
            # Shared lock when available; attestation still runs read-only.
            with bronze_tree_lock(self.base_path, exclusive=False) as locked_root:
                return self._cleanup_old_files_locked_sync(
                    cutoff_str, dry_run, provider, entity, locked_root
                )
        with bronze_tree_lock(
            self.base_path, exclusive=True, allow_group_recovery=True
        ) as locked_root:
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
        group_cleanup = group_cleanup_for_lock(
            locked_root, cutoff_str, self._flat_structure, self._log_cleanup_skip
        )
        if (
            group_cleanup is not None
            and not dry_run
            and not group_cleanup.resume(stats, provider, entity)
        ):
            return stats
        root_abs, root_real = cleanup_roots(locked_root, self.base_path)
        root_fd = locked_root.fd if locked_root is not None else None
        for date_dir in self._find_old_date_dirs(
            cutoff_str,
            provider,
            entity,
            on_skip=partial(self._record_cleanup_discovery_skip, stats),
            base_path=locked_root.path if locked_root is not None else None,
        ):
            plan = self._plan_old_dir_files(
                date_dir, root_abs, root_real, root_fd=root_fd
            )
            self._record_cleanup_plan(stats, plan)
            execute_cleanup_plan(
                self, dry_run, stats, plan, root_abs, root_real, root_fd, group_cleanup
            )
        return stats

    def _record_cleanup_discovery_skip(
        self, stats: dict[str, int], path: str, reason: str
    ) -> None:
        self._log_cleanup_skip(path, reason)
        if reason in ("scan_error", "stat_error"):
            stats["directories_failed"] += 1
        elif reason == "missing_scope":
            stats["directories_conflicted"] += 1
        elif reason not in ("not_a_directory", "reserved_maintenance"):
            stats["directories_skipped"] += 1

    def _apply_cleanup_plan(
        self,
        stats: dict[str, int],
        plan: _CleanupDatePlan,
        root_abs: Path,
        root_real: Path,
        root_fd: int | None,
        group_cleanup: BronzeGroupCleanup | None,
    ) -> None:
        """Apply the exact planned inodes and retain partial-result accounting."""
        failed_before = stats["files_failed"]
        conflicted_before = stats["files_conflicted"]
        stage_failed_before = stats["directories_failed"]
        stage_conflicted_before = stats["directories_conflicted"]

        def on_stage_error(name: str, _error: OSError) -> None:
            stats["directories_failed"] += 1
            self._log_cleanup_skip(str(self.base_path / name), "stage_cleanup_error")

        if group_cleanup is None:
            raise NotImplementedError(
                "destructive cleanup requires a pinned group journal"
            )
        group_cleanup.apply(plan, stats)
        if not plan.removable:
            return
        if (
            stats["files_failed"] != failed_before
            or stats["files_conflicted"] != conflicted_before
            or stats["directories_failed"] != stage_failed_before
            or stats["directories_conflicted"] != stage_conflicted_before
        ):
            stats["directories_skipped"] += 1
            return
        self._apply_planned_directory(
            stats, plan, root_abs, root_real, root_fd, on_stage_error
        )

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
        worker = asyncio.get_running_loop().run_in_executor(
            _CLEANUP_EXECUTOR,
            partial(
                contextvars.copy_context().run,
                self._cleanup_old_files_sync,
                cutoff_str,
                dry_run,
                provider,
                entity,
                cancel_requested,
            ),
        )
        try:
            result = await asyncio.shield(worker)
        except asyncio.CancelledError:
            cancel_requested.set()
            # A cancelled caller must not leave an unobserved destructive thread.
            await _drain_cleanup_worker(worker)
            if not worker.cancelled() and worker.exception() is None:
                self._emit_cleanup_result(cutoff_str, dry_run, worker.result())
            raise

        self._emit_cleanup_result(cutoff_str, dry_run, result)
        return result

    def _emit_cleanup_result(
        self, cutoff_str: str, dry_run: bool, result: dict[str, int]
    ) -> None:
        """Account for completed work even when its caller was cancelled."""
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
