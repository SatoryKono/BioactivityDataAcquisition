# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Read/list/cleanup helpers extracted from ``BronzeWriterIOMixin``."""

from __future__ import annotations

import asyncio
import os
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import orjson
import zstandard as zstd

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.bronze.cleanup_support import (
    bronze_tree_lock,
    candidate_is_safe,
    date_dir_name_is_older,
    destructive_cleanup_supported,
    find_old_date_dirs,
    is_owned_artifact,
    iter_safe_child_dirs,
    real_root,
    safe_named_child_dir,
    safe_rmdir,
    safe_unlink,
    scan_dir_entries,
    validate_scope_filter,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort, MetricsPort


@dataclass(frozen=True, slots=True)
class _CleanupCandidate:
    path: Path
    identity: os.stat_result


@dataclass(slots=True)
class _CleanupDatePlan:
    path: Path
    identity: os.stat_result | None
    files: list[_CleanupCandidate]
    removable: bool
    files_skipped: int = 0
    bytes_skipped: int = 0
    files_conflicted: int = 0
    bytes_conflicted: int = 0
    files_failed: int = 0
    bytes_failed: int = 0
    directories_skipped: int = 0
    directories_conflicted: int = 0
    directories_failed: int = 0


class BronzeWriterReadCleanupMixin:
    """Filesystem read/list/cleanup helpers for Bronze storage."""

    base_path: Path = cast(Any, None)  # Any: host attr default (PD3)
    _flat_structure: bool = cast(Any, None)  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _metrics: MetricsPort = cast(Any, None)  # Any: host attr default (PD3)
    _resolve_bronze_path: Callable[[str, str, str, str], str] = cast(Any, None)

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
        on_skip: Callable[[str, str], None] | None = None,
    ) -> list[Path]:
        """Find date directories older than cutoff without following links."""
        return find_old_date_dirs(
            self.base_path,
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
            return self._cleanup_old_files_locked_sync(
                cutoff_str, dry_run, provider, entity
            )
        with bronze_tree_lock(self.base_path, exclusive=True):
            return self._cleanup_old_files_locked_sync(
                cutoff_str, dry_run, provider, entity
            )

    def _cleanup_old_files_locked_sync(
        self,
        cutoff_str: str,
        dry_run: bool,
        provider: str | None,
        entity: str | None,
    ) -> dict[str, int]:
        stats = dict.fromkeys(
            (
                "files_planned",
                "bytes_planned",
                "directories_planned",
                "files_removed",
                "bytes_freed",
                "directories_removed",
                "files_skipped",
                "bytes_skipped",
                "directories_skipped",
                "files_conflicted",
                "bytes_conflicted",
                "directories_conflicted",
                "files_failed",
                "bytes_failed",
                "directories_failed",
            ),
            0,
        )
        root_abs = Path(os.path.abspath(self.base_path))  # noqa: PTH100
        root_real = real_root(self.base_path)

        def on_discovery_skip(path: str, reason: str) -> None:
            self._log_cleanup_skip(path, reason)
            if reason in ("scan_error", "stat_error"):
                stats["directories_failed"] += 1
            elif reason == "missing_scope":
                stats["directories_conflicted"] += 1
            elif reason != "not_a_directory":
                stats["directories_skipped"] += 1

        for date_dir in self._find_old_date_dirs(
            cutoff_str, provider, entity, on_skip=on_discovery_skip
        ):
            plan = self._plan_old_dir_files(date_dir, root_abs, root_real)
            stats["files_planned"] += len(plan.files)
            stats["bytes_planned"] += sum(c.identity.st_size for c in plan.files)
            stats["files_skipped"] += plan.files_skipped
            stats["bytes_skipped"] += plan.bytes_skipped
            stats["files_conflicted"] += plan.files_conflicted
            stats["bytes_conflicted"] += plan.bytes_conflicted
            stats["files_failed"] += plan.files_failed
            stats["bytes_failed"] += plan.bytes_failed
            stats["directories_skipped"] += plan.directories_skipped
            stats["directories_conflicted"] += plan.directories_conflicted
            stats["directories_failed"] += plan.directories_failed
            if plan.removable:
                stats["directories_planned"] += 1
            elif not plan.directories_failed and not plan.directories_conflicted:
                stats["directories_skipped"] += 1
            if dry_run:
                continue
            failed_before = stats["files_failed"]
            conflicted_before = stats["files_conflicted"]

            def on_stage_error(name: str, _error: OSError) -> None:
                stats["directories_failed"] += 1
                self._log_cleanup_skip(str(self.base_path / name), "stage_cleanup_error")

            for candidate in plan.files:
                try:
                    removed = safe_unlink(
                        candidate.path,
                        root_abs,
                        root_real,
                        candidate.identity,
                        on_stage_error=on_stage_error,
                    )
                except OSError:
                    stats["files_failed"] += 1
                    stats["bytes_failed"] += candidate.identity.st_size
                    self._log_cleanup_skip(str(candidate.path), "unlink_error")
                else:
                    if removed:
                        stats["files_removed"] += 1
                        stats["bytes_freed"] += candidate.identity.st_size
                    else:
                        stats["files_conflicted"] += 1
                        stats["bytes_conflicted"] += candidate.identity.st_size
                        self._log_cleanup_skip(str(candidate.path), "unlink_conflict")
            if not plan.removable:
                continue
            if (
                stats["files_failed"] != failed_before
                or stats["files_conflicted"] != conflicted_before
            ):
                stats["directories_skipped"] += 1
                continue
            try:
                removed_dir = safe_rmdir(
                    date_dir,
                    root_abs,
                    root_real,
                    plan.identity,
                    on_stage_error=on_stage_error,
                )
            except OSError:
                stats["directories_failed"] += 1
                self._log_cleanup_skip(str(date_dir), "rmdir_error")
            else:
                if removed_dir:
                    stats["directories_removed"] += 1
                else:
                    stats["directories_conflicted"] += 1
                    self._log_cleanup_skip(str(date_dir), "rmdir_conflict")
        return stats

    def _plan_old_dir_files(
        self, date_dir: Path, root_abs: Path, root_real: Path
    ) -> _CleanupDatePlan:
        """Snapshot exact writer-owned paths without mutating the tree."""
        plan = _CleanupDatePlan(date_dir, None, [], False)
        try:
            identity = date_dir.lstat()
        except OSError:
            plan.directories_failed = 1
            return plan
        if not candidate_is_safe(
            date_dir, root_abs, root_real, identity, directory=True
        ):
            plan.directories_conflicted = 1
            return plan
        plan.identity = identity
        entries = scan_dir_entries(date_dir)
        if entries is None:
            plan.directories_failed = 1
            return plan
        identities: dict[str, os.stat_result] = {}
        for entry in entries:
            try:
                entry.stat(follow_symlinks=False)
                # DirEntry.stat on Windows may report st_dev=st_ino=0.
                identities[entry.name] = (date_dir / entry.name).lstat()
            except OSError:
                plan.files_failed += 1
                self._log_cleanup_skip(entry.path, "stat_error")
        payload_names = {
            name
            for name, identity in identities.items()
            if name.endswith(".jsonl.zst")
            and stat.S_ISREG(identity.st_mode)
            and is_owned_artifact(name, date_name=date_dir.name)
            and (sidecar := identities.get(f"{name}.meta.json")) is not None
            and stat.S_ISREG(sidecar.st_mode)
        }
        rel_date = Path(os.path.abspath(date_dir)).relative_to(root_abs)  # noqa: PTH100
        provider_name, entity_name = (
            ("", "") if self._flat_structure else rel_date.parts[:2]
        )
        for entry in sorted(entries, key=lambda item: item.name):
            candidate_identity = identities.get(entry.name)
            if candidate_identity is None:
                continue
            expected_rel = Path(
                self._resolve_bronze_path(
                    provider_name,
                    entity_name,
                    date_dir.name,
                    entry.name,
                )
            )
            file_path = date_dir / entry.name
            if (
                stat.S_ISDIR(candidate_identity.st_mode)
            ):
                plan.directories_skipped += 1
                self._log_cleanup_skip(entry.path, "unknown_directory")
                continue
            if (
                not stat.S_ISREG(candidate_identity.st_mode)
                or not is_owned_artifact(
                    entry.name, date_name=date_dir.name, payload_names=payload_names
                )
                or expected_rel != rel_date / entry.name
            ):
                plan.files_skipped += 1
                if stat.S_ISREG(candidate_identity.st_mode):
                    plan.bytes_skipped += candidate_identity.st_size
                self._log_cleanup_skip(entry.path, "unknown_artifact")
                continue
            if not candidate_is_safe(file_path, root_abs, root_real, candidate_identity):
                plan.files_conflicted += 1
                plan.bytes_conflicted += candidate_identity.st_size
                self._log_cleanup_skip(entry.path, "candidate_conflict")
                continue
            plan.files.append(_CleanupCandidate(file_path, candidate_identity))
        plan.removable = (
            len(plan.files) == len(entries)
            and not plan.files_failed
            and not plan.files_conflicted
        )
        return plan

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
        result = await asyncio.to_thread(
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
        for key, metric in (
            ("files_skipped", "bioetl_bronze_cleanup_files_skipped_total"),
            ("bytes_skipped", "bioetl_bronze_cleanup_bytes_skipped_total"),
            ("files_conflicted", "bioetl_bronze_cleanup_files_conflicted_total"),
            ("bytes_conflicted", "bioetl_bronze_cleanup_bytes_conflicted_total"),
            ("files_failed", "bioetl_bronze_cleanup_files_failed_total"),
            ("bytes_failed", "bioetl_bronze_cleanup_bytes_failed_total"),
            ("directories_skipped", "bioetl_bronze_cleanup_directories_skipped_total"),
            (
                "directories_conflicted",
                "bioetl_bronze_cleanup_directories_conflicted_total",
            ),
            ("directories_failed", "bioetl_bronze_cleanup_directories_failed_total"),
        ):
            if not dry_run and result[key]:
                self._metrics.increment_counter(
                    metric, result[key], {"operation": "cleanup"}
                )
        return result

    def preview_cleanup(
        self,
        provider: str | None = None,
        entity: str | None = None,
    ) -> JsonDict:  # Any: preview payload has heterogeneous values
        """Preview direct date-partition files with bounded, no-follow traversal."""
        validate_scope_filter(provider, "provider")
        validate_scope_filter(entity, "entity")
        preview_root = self._resolve_bronze_preview_root(provider, entity)
        exists = self.base_path.exists()
        if not exists or (self._flat_structure and (provider or entity)):
            return {
                "path": str(preview_root),
                "file_count": 0,
                "exists": exists and not (provider or entity),
            }
        root_abs = Path(os.path.abspath(self.base_path))  # noqa: PTH100
        root_real = real_root(self.base_path)
        file_count = 0
        scope_exists: bool = bool(exists)
        if self._flat_structure:
            date_parents = [self.base_path]
        else:
            providers = (
                [p]
                if provider
                and (p := safe_named_child_dir(self.base_path, provider, root_real))
                else ([] if provider else iter_safe_child_dirs(self.base_path))
            )
            date_parents = []
            for provider_dir in providers:
                if entity:
                    child = safe_named_child_dir(provider_dir, entity, root_real)
                    if child is not None:
                        date_parents.append(child)
                else:
                    date_parents.extend(iter_safe_child_dirs(provider_dir))
            scope_exists = bool(date_parents) if entity else bool(providers) if provider else exists
        for parent in date_parents:
            for date_dir in iter_safe_child_dirs(parent):
                if not (
                    date_dir_name_is_older(date_dir.name, "9999-12-31")
                    or date_dir.name == "9999-12-31"
                ):
                    continue
                try:
                    date_stat = date_dir.lstat()
                except OSError:
                    continue
                if not candidate_is_safe(
                    date_dir, root_abs, root_real, date_stat, directory=True
                ):
                    continue
                entries = scan_dir_entries(date_dir)
                if entries is None:
                    continue
                for entry in entries:
                    try:
                        entry.stat(follow_symlinks=False)
                        identity = (date_dir / entry.name).lstat()
                    except OSError:
                        continue
                    if stat.S_ISREG(identity.st_mode) and candidate_is_safe(
                        date_dir / entry.name, root_abs, root_real, identity
                    ):
                        file_count += 1
                        if file_count > 100_000:
                            raise ValueError("Bronze preview exceeds 100000 files")

        return {
            "path": str(preview_root),
            "file_count": file_count,
            "exists": scope_exists,
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
