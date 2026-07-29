"""Freshness and commit-mismatch behavior for every envelope-backed store."""

from __future__ import annotations

from memory.freshness import FreshnessStatus, evaluate_freshness
from memory.records import ActorIdentity, RecordEnvelope, RecordType
from memory.scope import RepositoryScope


def _envelope(**overrides: str) -> RecordEnvelope:
    values = {
        "repo_id": "bioetl",
        "git_commit": "a" * 40,
        "branch": "main",
        "worktree_id": "tree-a",
    }
    values.update(overrides)
    return RecordEnvelope.create(
        record_id="record",
        record_type=RecordType.KNOWLEDGE,
        task_id="task",
        actor=ActorIdentity(runtime="test", agent="test"),
        source_refs=("source",),
        created_at="2026-07-29T00:00:00+00:00",
        **values,
    )


def _scope(**overrides: str) -> RepositoryScope:
    values = {
        "repo_id": "bioetl",
        "git_commit": "a" * 40,
        "branch": "main",
        "worktree_id": "tree-a",
        "task_id": "task",
    }
    values.update(overrides)
    return RepositoryScope(**values)


def test_current_clean_record_is_usable() -> None:
    result = evaluate_freshness(_envelope(), _scope(), dirty=False)
    assert result.status is FreshnessStatus.CURRENT
    assert result.usable


def test_commit_branch_and_dirty_checkout_are_stale() -> None:
    commit = evaluate_freshness(
        _envelope(), _scope(git_commit="b" * 40), dirty=False
    )
    branch = evaluate_freshness(
        _envelope(), _scope(branch="feature"), dirty=False
    )
    dirty = evaluate_freshness(_envelope(), _scope(), dirty=True)
    assert commit.reasons == ("commit-mismatch",)
    assert branch.reasons == ("branch-mismatch",)
    assert dirty.reasons == ("dirty-worktree",)
    assert not commit.usable and not branch.usable and not dirty.usable


def test_wrong_repository_or_worktree_is_rejected() -> None:
    repo = evaluate_freshness(_envelope(), _scope(repo_id="fork"), dirty=False)
    tree = evaluate_freshness(
        _envelope(), _scope(worktree_id="tree-b"), dirty=False
    )
    assert repo.status is FreshnessStatus.REJECTED
    assert tree.status is FreshnessStatus.REJECTED


def test_explicit_historical_mode_never_accepts_dirty_checkout() -> None:
    historical = evaluate_freshness(
        _envelope(), _scope(git_commit="b" * 40), dirty=False, historical_mode=True
    )
    dirty = evaluate_freshness(
        _envelope(), _scope(git_commit="b" * 40), dirty=True, historical_mode=True
    )
    assert historical.status is FreshnessStatus.HISTORICAL
    assert dirty.status is FreshnessStatus.STALE
