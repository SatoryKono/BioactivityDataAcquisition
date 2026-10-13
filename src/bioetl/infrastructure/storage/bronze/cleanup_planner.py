"""Nonmutating Bronze cleanup plan and exact artifact association."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .cleanup_support import candidate_is_safe, is_owned_artifact, scan_dir_entries


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


@dataclass(frozen=True, slots=True)
class _CleanupPlanScope:
    root_abs: Path
    root_real: Path
    rel_date: Path
    provider_name: str
    entity_name: str
    payload_names: set[str]
    root_fd: int | None = None


class BronzeCleanupPlannerMixin:
    """Plan writer-owned candidates without filesystem mutation."""

    _flat_structure: bool
    _resolve_bronze_path: Callable[[str, str, str, str], str]

    def _log_cleanup_skip(self, path: str, reason: str) -> None:
        raise NotImplementedError

    @staticmethod
    def _empty_cleanup_stats() -> dict[str, int]:
        return dict.fromkeys(
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

    @staticmethod
    def _record_cleanup_plan(stats: dict[str, int], plan: _CleanupDatePlan) -> None:
        """Add one nonmutating plan to the public result counters."""
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

    def _plan_old_dir_files(
        self,
        date_dir: Path,
        root_abs: Path,
        root_real: Path,
        root_fd: int | None = None,
    ) -> _CleanupDatePlan:
        """Snapshot exact writer-owned paths without mutating the tree."""
        plan = _CleanupDatePlan(date_dir, None, [], False)
        try:
            identity = date_dir.lstat()
        except OSError:
            plan.directories_failed = 1
            return plan
        if not candidate_is_safe(
            date_dir, root_abs, root_real, identity, directory=True, root_fd=root_fd
        ):
            plan.directories_conflicted = 1
            return plan
        plan.identity = identity
        entries = scan_dir_entries(date_dir)
        if entries is None:
            plan.directories_failed = 1
            return plan
        identities = self._snapshot_cleanup_identities(date_dir, entries, plan)
        payload_names = self._associated_payload_names(identities, date_dir.name)
        rel_date = Path(os.path.abspath(date_dir)).relative_to(root_abs)  # noqa: PTH100
        provider_name, entity_name = (
            ("", "") if self._flat_structure else rel_date.parts[:2]
        )
        scope = _CleanupPlanScope(
            root_abs,
            root_real,
            rel_date,
            provider_name,
            entity_name,
            payload_names,
            root_fd,
        )
        # Writer names sort copy, payload, then lineage sidecar. A failed
        # member therefore cannot leave a retained payload without its sidecar.
        for entry in sorted(entries, key=lambda item: item.name):
            candidate_identity = identities.get(entry.name)
            if candidate_identity is None:
                continue
            self._plan_cleanup_entry(plan, entry, candidate_identity, scope)
        plan.removable = (
            len(plan.files) == len(entries)
            and not plan.files_failed
            and not plan.files_conflicted
        )
        return plan

    def _snapshot_cleanup_identities(
        self,
        date_dir: Path,
        entries: list[os.DirEntry[str]],
        plan: _CleanupDatePlan,
    ) -> dict[str, os.stat_result]:
        """Retain stat failures while obtaining portable entry identities."""
        identities: dict[str, os.stat_result] = {}
        for entry in entries:
            try:
                entry.stat(follow_symlinks=False)
                # DirEntry.stat on Windows may report st_dev=st_ino=0.
                identities[entry.name] = (date_dir / entry.name).lstat()
            except OSError:
                plan.files_failed += 1
                self._log_cleanup_skip(entry.path, "stat_error")
        return identities

    @staticmethod
    def _associated_payload_names(
        identities: dict[str, os.stat_result], date_name: str
    ) -> set[str]:
        """Require an exact payload/sidecar pair before classifying copies."""
        return {
            name
            for name, identity in identities.items()
            if name.endswith(".jsonl.zst")
            and stat.S_ISREG(identity.st_mode)
            and is_owned_artifact(name, date_name=date_name)
            and (sidecar := identities.get(f"{name}.meta.json")) is not None
            and stat.S_ISREG(sidecar.st_mode)
        }

    def _plan_cleanup_entry(
        self,
        plan: _CleanupDatePlan,
        entry: os.DirEntry[str],
        identity: os.stat_result,
        scope: _CleanupPlanScope,
    ) -> None:
        expected_rel = Path(
            self._resolve_bronze_path(
                scope.provider_name, scope.entity_name, plan.path.name, entry.name
            )
        )
        file_path = plan.path / entry.name
        if stat.S_ISDIR(identity.st_mode):
            plan.directories_skipped += 1
            self._log_cleanup_skip(entry.path, "unknown_directory")
            return
        if (
            not stat.S_ISREG(identity.st_mode)
            or not is_owned_artifact(
                entry.name,
                date_name=plan.path.name,
                payload_names=scope.payload_names,
            )
            or expected_rel != scope.rel_date / entry.name
        ):
            plan.files_skipped += 1
            if stat.S_ISREG(identity.st_mode):
                plan.bytes_skipped += identity.st_size
            self._log_cleanup_skip(entry.path, "unknown_artifact")
            return
        if not candidate_is_safe(
            file_path,
            scope.root_abs,
            scope.root_real,
            identity,
            root_fd=scope.root_fd,
        ):
            plan.files_conflicted += 1
            plan.bytes_conflicted += identity.st_size
            self._log_cleanup_skip(entry.path, "candidate_conflict")
            return
        plan.files.append(_CleanupCandidate(file_path, identity))
