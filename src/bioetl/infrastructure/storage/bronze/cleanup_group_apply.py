"""Connect public cleanup plans to durable, attested group operations."""

from __future__ import annotations

import json
import os
from collections.abc import Callable

from .cleanup_core import BronzeRootLease
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


class BronzeGroupCleanup:
    """Apply only the planned objects and resume only eligible owned intents."""

    def __init__(
        self,
        lease: BronzeRootLease,
        cutoff: str,
        flat: bool,
        on_skip: Callable[[str, str], None],
    ) -> None:
        self.journal = GroupJournal(lease)
        self.root = lease.path
        self.cutoff = cutoff
        self.flat = flat
        self.on_skip = on_skip

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
            spec.flat_structure != self.flat
            or (self.flat and (provider is not None or entity is not None))
            or spec.date >= self.cutoff
            or (provider is not None and provider != spec.provider)
            or (entity is not None and entity != spec.entity)
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

    def apply(self, plan: _CleanupDatePlan, stats: dict[str, int]) -> None:
        groups: dict[str, list[_CleanupCandidate]] = {}
        for candidate in plan.files:
            groups.setdefault(candidate.path.name.split(".jsonl", 1)[0], []).append(
                candidate
            )
        for group, candidates in groups.items():
            size = sum(candidate.identity.st_size for candidate in candidates)
            try:
                spec = self._spec(plan, group)
                operation = self.journal.begin(
                    spec,
                    expected_members={c.path.name: c.identity for c in candidates},
                    expected_date=plan.identity,
                )
            except (OSError, ValueError, TypeError) as exc:
                kind = (
                    "conflicted"
                    if isinstance(exc, (GroupJournalConflict, ValueError, TypeError))
                    else "failed"
                )
                stats[f"files_{kind}"] += len(candidates)
                stats[f"bytes_{kind}"] += size
                self.on_skip(str(plan.path / group), f"group_attestation_{kind}")
                continue
            self._recover(
                stats, operation, len(candidates), size, str(plan.path / group)
            )

    def _spec(self, plan: _CleanupDatePlan, group: str) -> GroupSpec:
        relative = plan.path.relative_to(self.root)
        batch = group.removeprefix(f"batch_{plan.path.name}_")
        if self.flat:
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
            provider, entity = metadata.get("provider"), metadata.get("entity")
            if not isinstance(provider, str) or not isinstance(entity, str):
                raise GroupJournalConflict("missing sidecar scope")
        else:
            provider, entity, _date = relative.parts
        return GroupSpec(
            provider, entity, plan.path.name, batch, self.cutoff, self.flat
        )
