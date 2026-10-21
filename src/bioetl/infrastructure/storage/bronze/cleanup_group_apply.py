"""Connect public cleanup plans to durable, attested group operations."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from .cleanup_core import BronzeRootLease, valid_bronze_scope_name
from .cleanup_group_journal import GroupJournal
from .cleanup_group_schema import (
    _FILE_FLAGS,
    _MAX_SIDECAR,
    GroupJournalConflict,
    GroupRecoveryResult,
    GroupSpec,
    _unique_pairs,
)
from .cleanup_planner import _CleanupCandidate, _CleanupDatePlan


class _CleanupPlanHost(Protocol):
    """Minimal host surface used by execute_cleanup_plan apply dispatch."""

    def _apply_cleanup_plan(
        self,
        stats: dict[str, int],
        plan: _CleanupDatePlan,
        root_abs: Path,
        root_real: Path,
        root_fd: int | None,
        group_cleanup: BronzeGroupCleanup | None,
    ) -> None: ...


class BronzeGroupCleanup:
    """Apply only the planned objects and resume only eligible owned intents."""

    def __init__(
        self,
        lease: BronzeRootLease,
        cutoff: str,
        flat: bool,
        on_skip: Callable[[str, str], None],
        root_identity: tuple[str, str] | None = None,
    ) -> None:
        self.journal = GroupJournal(lease)
        self.root = lease.path
        self.cutoff = cutoff
        self.flat = flat
        self.on_skip = on_skip
        self.root_identity = root_identity

    def _scope_allowed(self, provider: str, entity: str) -> bool:
        """Use only configured ownership or an independent hierarchical path."""
        if self.root_identity is None:
            return not self.flat
        return (
            isinstance(self.root_identity, tuple)
            and len(self.root_identity) == 2
            and all(
                isinstance(value, str) and valid_bronze_scope_name(value)
                for value in self.root_identity
            )
            and self.root_identity == (provider, entity)
        )

    @staticmethod
    def _record_progress(
        stats: dict[str, int], result: GroupRecoveryResult | OSError
    ) -> None:
        stats["files_removed"] += getattr(result, "removed", 0)
        stats["bytes_freed"] += getattr(result, "removed_bytes", 0)

    def resume(
        self, stats: dict[str, int], provider: str | None, entity: str | None
    ) -> bool:
        """Never widen the caller's retention or provider/entity scope on retry."""
        try:
            pending = self.journal.pending()
        except OSError:
            stats["directories_conflicted"] += 1
            self.on_skip(str(self.root), "invalid_pending_group")
            return False
        if any(
            self._outside_requested_scope(spec, provider, entity)
            for _operation, spec, _count, _size in pending
        ):
            stats["directories_skipped"] += 1
            self.on_skip(str(self.root), "pending_group_outside_requested_scope")
            return False
        for operation, spec, count, size in pending:
            stats["files_planned"] += count
            stats["bytes_planned"] += size
            if not self._recover(
                stats, operation, count, size, str(spec.relative_date())
            ):
                return False
        return True

    def _outside_requested_scope(
        self, spec: GroupSpec, provider: str | None, entity: str | None
    ) -> bool:
        """Recheck layout, configured owner, retention and explicit retry filters."""
        if spec.flat_structure != self.flat or not self._scope_allowed(
            spec.provider, spec.entity
        ):
            return True
        if self.flat and (provider is not None or entity is not None):
            return True
        return spec.date >= self.cutoff or _requested_owner_mismatch(
            spec, provider, entity
        )

    def _recover(
        self, stats: dict[str, int], operation: str, count: int, size: int, path: str
    ) -> bool:
        try:
            result = self.journal.recover_with_result(operation)
        except OSError as exc:
            self._record_progress(stats, exc)
            kind = "conflicted" if isinstance(exc, GroupJournalConflict) else "failed"
            stats[f"files_{kind}"] += max(0, count - getattr(exc, "removed", 0))
            stats[f"bytes_{kind}"] += max(0, size - getattr(exc, "removed_bytes", 0))
            stats[f"directories_{kind}"] += 1
            self.on_skip(path, f"group_recovery_{kind}")
            return False
        self._record_progress(stats, result)
        return True

    def _grouped_candidates(
        self, plan: _CleanupDatePlan
    ) -> dict[str, list[_CleanupCandidate]]:
        groups: dict[str, list[_CleanupCandidate]] = {}
        for candidate in plan.files:
            groups.setdefault(candidate.path.name.split(".jsonl", 1)[0], []).append(
                candidate
            )
        return groups

    def _reject_group(
        self,
        stats: dict[str, int],
        plan: _CleanupDatePlan,
        group: str,
        candidates: list[_CleanupCandidate],
        size: int,
        exc: BaseException,
        *,
        dry_run: bool,
    ) -> None:
        kind = (
            "conflicted"
            if isinstance(exc, (GroupJournalConflict, ValueError, TypeError))
            else "failed"
        )
        if dry_run:
            stats["files_planned"] = max(0, stats["files_planned"] - len(candidates))
            stats["bytes_planned"] = max(0, stats["bytes_planned"] - size)
            if plan.removable and stats["directories_planned"] > 0:
                stats["directories_planned"] -= 1
                plan.removable = False
                stats["directories_skipped"] += 1
        stats[f"files_{kind}"] += len(candidates)
        stats[f"bytes_{kind}"] += size
        self.on_skip(str(plan.path / group), f"group_attestation_{kind}")

    def attest_plan(self, plan: _CleanupDatePlan, stats: dict[str, int]) -> None:
        """Apply the same ownership attestation used by destructive cleanup."""
        for group, candidates in self._grouped_candidates(plan).items():
            size = sum(candidate.identity.st_size for candidate in candidates)
            try:
                spec = self._spec(plan, group)
                self.journal.validate_group_for_plan(
                    spec,
                    expected_members={c.path.name: c.identity for c in candidates},
                    expected_date=plan.identity,
                )
            except (OSError, ValueError, TypeError) as exc:
                self._reject_group(
                    stats, plan, group, candidates, size, exc, dry_run=True
                )

    def apply(self, plan: _CleanupDatePlan, stats: dict[str, int]) -> None:
        for group, candidates in self._grouped_candidates(plan).items():
            size = sum(candidate.identity.st_size for candidate in candidates)
            try:
                spec = self._spec(plan, group)
                operation = self.journal.begin(
                    spec,
                    expected_members={c.path.name: c.identity for c in candidates},
                    expected_date=plan.identity,
                )
            except (OSError, ValueError, TypeError) as exc:
                self._reject_group(
                    stats, plan, group, candidates, size, exc, dry_run=False
                )
                continue
            self._recover(
                stats, operation, len(candidates), size, str(plan.path / group)
            )

    def _spec(self, plan: _CleanupDatePlan, group: str) -> GroupSpec:
        relative = plan.path.relative_to(self.root)
        batch = group.removeprefix(f"batch_{plan.path.name}_")
        if self.flat:
            if self.root_identity is None or not self._scope_allowed(
                *self.root_identity
            ):
                raise GroupJournalConflict("missing configured Bronze root identity")
            provider, entity = self.root_identity
            # The bounded read is under the pinned date handle; begin then
            # verifies the complete sidecar, hashes, and original planned inode.
            with self.journal._date(relative.as_posix()) as (date_fd, _chain):
                fd = os.open(
                    f"{group}.jsonl.zst.meta.json", _FILE_FLAGS, dir_fd=date_fd
                )
                try:
                    raw = os.read(fd, _MAX_SIDECAR + 1)
                finally:
                    os.close(fd)
            if len(raw) > _MAX_SIDECAR:
                raise GroupJournalConflict("oversized sidecar")
            metadata = json.loads(raw, object_pairs_hook=_unique_pairs)
            if not isinstance(metadata, dict):
                raise GroupJournalConflict("invalid sidecar scope")
            if (metadata.get("provider"), metadata.get("entity")) != (provider, entity):
                raise GroupJournalConflict(
                    "sidecar differs from configured root identity"
                )
        else:
            provider, entity, _date = relative.parts
            if not self._scope_allowed(provider, entity):
                raise GroupJournalConflict("path differs from configured root identity")
        return GroupSpec(
            provider, entity, plan.path.name, batch, self.cutoff, self.flat
        )


def group_cleanup_for_lock(
    locked_root: BronzeRootLease | None,
    cutoff_str: str,
    flat: bool,
    on_skip: Callable[[str, str], None],
    root_identity: tuple[str, str] | None = None,
) -> BronzeGroupCleanup | None:
    """Build a journal-backed group cleaner only when the root fd is pinned."""
    if locked_root is None or locked_root.fd is None:
        return None
    return BronzeGroupCleanup(locked_root, cutoff_str, flat, on_skip, root_identity)


def cleanup_roots(
    locked_root: BronzeRootLease | None, base_path: Path
) -> tuple[Path, Path]:
    """Return absolute and real roots for planning under an optional lease."""
    if locked_root is not None:
        return locked_root.path, locked_root.path
    return (
        Path(os.path.abspath(base_path)),  # noqa: PTH100
        Path(os.path.realpath(base_path)),
    )


def execute_cleanup_plan(
    host: _CleanupPlanHost,
    dry_run: bool,
    stats: dict[str, int],
    plan: _CleanupDatePlan,
    root_abs: Path,
    root_real: Path,
    root_fd: int | None,
    group_cleanup: BronzeGroupCleanup | None,
) -> None:
    """Attest dry-run plans or apply destructive cleanup through the host."""
    if dry_run:
        if group_cleanup is not None:
            group_cleanup.attest_plan(plan, stats)
        return
    host._apply_cleanup_plan(stats, plan, root_abs, root_real, root_fd, group_cleanup)


def _requested_owner_mismatch(
    spec: GroupSpec, provider: str | None, entity: str | None
) -> bool:
    return (provider is not None and provider != spec.provider) or (
        entity is not None and entity != spec.entity
    )
