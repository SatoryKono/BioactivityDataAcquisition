"""Consent, lifecycle, and isolation tests for repository-owned user memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.access import AccessAction, AccessContext, AccessDeniedError
from memory.records import (
    ActorIdentity,
    RecordEnvelope,
    RecordScope,
    RecordStatus,
    RecordType,
    TrustLevel,
)
from memory.user_memory import (
    UserMemoryConsent,
    UserMemoryConsentError,
    UserMemoryFreshnessError,
    UserMemoryStore,
)
from memory.scope import RepositoryScope

pytestmark = pytest.mark.unit

_ALL_GRANTS = frozenset(AccessAction)


def _context(*, user_id: str = "user-a", repo_id: str = "repo-a") -> AccessContext:
    return AccessContext(
        principal_id=user_id,
        repo_id=repo_id,
        grants=_ALL_GRANTS,
    )


def _envelope(
    *,
    record_id: str = "preference-1",
    repo_id: str = "repo-a",
) -> RecordEnvelope:
    return RecordEnvelope.create(
        record_id=record_id,
        record_type=RecordType.KNOWLEDGE,
        scope=RecordScope(repo_id, "a" * 40, "main", "wt-a", "task-a"),
        actor=ActorIdentity(runtime="test", agent="test-agent"),
        source_refs=("explicit-user-input",),
        trust=TrustLevel.TRUSTED_REPOSITORY,
        created_at="2026-07-29T00:00:00+00:00",
    )


def _consent(store: UserMemoryStore) -> None:
    store.grant_consent(
        UserMemoryConsent(
            user_id="user-a",
            repo_id="repo-a",
            granted_at="2026-07-29T00:00:00+00:00",
        )
    )


def _scope(
    *,
    repo_id: str = "repo-a",
    git_commit: str = "a" * 40,
    branch: str = "main",
    worktree_id: str = "wt-a",
) -> RepositoryScope:
    return RepositoryScope(
        repo_id=repo_id,
        git_commit=git_commit,
        branch=branch,
        worktree_id=worktree_id,
        task_id="task-a",
    )


def test_user_memory_is_disabled_until_explicit_consent(tmp_path: Path) -> None:
    store = UserMemoryStore(tmp_path)

    with pytest.raises(UserMemoryConsentError, match="explicit consent"):
        store.put(
            _context(),
            owner_id="user-a",
            envelope=_envelope(),
            content={"language": "ru"},
        )


def test_scoped_enumerate_export_correct_tombstone_and_delete(tmp_path: Path) -> None:
    store = UserMemoryStore(tmp_path)
    _consent(store)
    context = _context()
    store.put(
        context,
        owner_id="user-a",
        envelope=_envelope(),
        content={"language": "ru"},
    )

    assert store.enumerate(context, owner_id="user-a") == ["preference-1"]
    assert store.export(
        context,
        owner_id="user-a",
        record_id="preference-1",
        scope=_scope(),
        dirty=False,
    ).content == {"language": "ru"}

    corrected = store.correct(
        context,
        owner_id="user-a",
        record_id="preference-1",
        content={"language": "en"},
    )
    assert corrected.content == {"language": "en"}

    tombstoned = store.tombstone(
        context,
        owner_id="user-a",
        record_id="preference-1",
    )
    assert tombstoned.tombstoned is True
    assert tombstoned.content == {}
    assert tombstoned.envelope.status is RecordStatus.ARCHIVED

    store.delete(context, owner_id="user-a", record_id="preference-1")
    assert store.enumerate(context, owner_id="user-a") == []


def test_cross_user_and_cross_repository_access_is_denied(tmp_path: Path) -> None:
    store = UserMemoryStore(tmp_path)
    _consent(store)
    store.put(
        _context(),
        owner_id="user-a",
        envelope=_envelope(),
        content={"language": "ru"},
    )

    with pytest.raises(AccessDeniedError, match="principal scope mismatch"):
        store.export(
            _context(user_id="user-b"),
            owner_id="user-a",
            record_id="preference-1",
            scope=_scope(),
            dirty=False,
        )

    with pytest.raises(UserMemoryConsentError, match="explicit consent"):
        store.enumerate(
            _context(repo_id="repo-b"),
            owner_id="user-a",
        )


def test_revoked_consent_blocks_subsequent_access_without_deleting(
    tmp_path: Path,
) -> None:
    store = UserMemoryStore(tmp_path)
    _consent(store)
    context = _context()
    store.put(
        context,
        owner_id="user-a",
        envelope=_envelope(),
        content={"language": "ru"},
    )

    store.revoke_consent(context, user_id="user-a")

    with pytest.raises(UserMemoryConsentError, match="consent revoked"):
        store.enumerate(context, owner_id="user-a")


def test_authorized_erasure_remains_available_after_consent_revocation(
    tmp_path: Path,
) -> None:
    store = UserMemoryStore(tmp_path)
    _consent(store)
    context = _context()
    store.put(
        context,
        owner_id="user-a",
        envelope=_envelope(),
        content={"language": "ru"},
    )
    store.revoke_consent(context, user_id="user-a")

    store.delete(context, owner_id="user-a", record_id="preference-1")

    assert not (tmp_path / "users" / "user-a" / "repo-a" / "records").exists()


def test_cross_user_erasure_after_revocation_is_denied(tmp_path: Path) -> None:
    store = UserMemoryStore(tmp_path)
    _consent(store)
    owner_context = _context()
    store.put(
        owner_context,
        owner_id="user-a",
        envelope=_envelope(),
        content={"language": "ru"},
    )
    store.revoke_consent(owner_context, user_id="user-a")

    with pytest.raises(AccessDeniedError, match="principal scope mismatch"):
        store.delete(
            _context(user_id="user-b"),
            owner_id="user-a",
            record_id="preference-1",
        )


@pytest.mark.parametrize(
    ("scope", "dirty", "reason"),
    [
        (_scope(git_commit="b" * 40), False, "commit-mismatch"),
        (_scope(branch="feature"), False, "branch-mismatch"),
        (_scope(worktree_id="wt-b"), False, "worktree-mismatch"),
        (_scope(repo_id="repo-b"), False, "repository-mismatch"),
        (_scope(), True, "dirty-worktree"),
    ],
)
def test_export_rejects_memory_outside_current_checkout(
    tmp_path: Path,
    scope: RepositoryScope,
    dirty: bool,
    reason: str,
) -> None:
    store = UserMemoryStore(tmp_path)
    _consent(store)
    context = _context()
    store.put(
        context,
        owner_id="user-a",
        envelope=_envelope(),
        content={"language": "ru"},
    )

    with pytest.raises(UserMemoryFreshnessError, match=reason):
        store.export(
            context,
            owner_id="user-a",
            record_id="preference-1",
            scope=scope,
            dirty=dirty,
        )


def test_export_allows_explicit_clean_historical_mode(tmp_path: Path) -> None:
    store = UserMemoryStore(tmp_path)
    _consent(store)
    context = _context()
    store.put(
        context,
        owner_id="user-a",
        envelope=_envelope(),
        content={"language": "ru"},
    )

    record = store.export(
        context,
        owner_id="user-a",
        record_id="preference-1",
        scope=_scope(git_commit="b" * 40),
        dirty=False,
        historical_mode=True,
    )

    assert record.content == {"language": "ru"}


@pytest.mark.parametrize("identifier", ["../escape", "/absolute", "", "space value"])
def test_identifiers_cannot_escape_the_scoped_store(
    tmp_path: Path,
    identifier: str,
) -> None:
    store = UserMemoryStore(tmp_path)

    with pytest.raises(ValueError, match="invalid user_id"):
        store.grant_consent(
            UserMemoryConsent(
                user_id=identifier,
                repo_id="repo-a",
                granted_at="2026-07-29T00:00:00+00:00",
            )
        )
