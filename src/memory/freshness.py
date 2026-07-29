"""Commit-, branch-, worktree-, and repository-aware memory invalidation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from memory.records import RecordEnvelope
from memory.scope import RepositoryScope


class FreshnessStatus(StrEnum):
    """Outcome of binding a record to the active checkout."""

    CURRENT = "current"
    HISTORICAL = "historical"
    STALE = "stale"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class FreshnessResult:
    """Bounded explanation of one scope comparison."""

    status: FreshnessStatus
    reasons: tuple[str, ...]

    @property
    def usable(self) -> bool:
        """Whether normal retrieval may consume this record."""
        return self.status in {FreshnessStatus.CURRENT, FreshnessStatus.HISTORICAL}


def evaluate_freshness(
    envelope: RecordEnvelope,
    scope: RepositoryScope,
    *,
    dirty: bool,
    historical_mode: bool = False,
) -> FreshnessResult:
    """Fail closed across repository/worktree boundaries and stale commits."""
    rejected: list[str] = []
    stale: list[str] = []
    if envelope.repo_id != scope.repo_id:
        rejected.append("repository-mismatch")
    if envelope.worktree_id != scope.worktree_id:
        rejected.append("worktree-mismatch")
    if rejected:
        return FreshnessResult(FreshnessStatus.REJECTED, tuple(rejected))
    if envelope.branch != scope.branch:
        stale.append("branch-mismatch")
    if envelope.git_commit != scope.git_commit:
        stale.append("commit-mismatch")
    if dirty:
        stale.append("dirty-worktree")
    if not stale:
        return FreshnessResult(FreshnessStatus.CURRENT, ())
    if historical_mode and not dirty:
        return FreshnessResult(FreshnessStatus.HISTORICAL, tuple(stale))
    return FreshnessResult(FreshnessStatus.STALE, tuple(stale))
