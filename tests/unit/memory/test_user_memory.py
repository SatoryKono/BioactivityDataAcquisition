"""Consent, lifecycle, and isolation tests for repository-owned user memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.access import AccessAction, AccessContext, AccessDeniedError
from memory.records import ActorIdentity, RecordEnvelope, RecordStatus, RecordType
from memory.user_memory import (
    UserMemoryConsent,
    UserMemoryConsentError,
    UserMemoryStore,
)

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
        repo_id=repo_id,
        git_commit="a" * 40,
        branch="main",
        worktree_id="wt-a",
        task_id="task-a",
        actor=ActorIdentity(runtime="test", agent="test-agent"),
        source_refs=("explicit-user-input",),
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
