"""Consent-gated repository-owned user memory.

This module controls only records stored by this repository. It does not claim
to enumerate, export, correct, or delete memory retained by model vendors,
hosted IDEs, or other external services.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from memory.access import AccessAction, AccessContext, require_access
from memory.freshness import FreshnessResult, evaluate_freshness
from memory.records import (
    ActorIdentity,
    RecordEnvelope,
    RecordStatus,
    RecordType,
    SecurityClass,
    TrustLevel,
)
from memory.scope import RepositoryScope
from memory.security import assert_safe_for_persistence
from memory.storage import atomic_write_json

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class UserMemoryConsentError(PermissionError):
    """Raised when user-memory processing lacks explicit active consent."""


class UserMemoryFreshnessError(RuntimeError):
    """Raised when a record is not usable in the active repository scope."""

    def __init__(self, result: FreshnessResult) -> None:
        self.result = result
        reasons = ", ".join(result.reasons) or "unknown"
        super().__init__(f"user-memory record is {result.status.value}: {reasons}")


@dataclass(frozen=True, slots=True)
class UserMemoryConsent:
    """Explicit repository-scoped consent for user-memory operations."""

    user_id: str
    repo_id: str
    granted_at: str
    active: bool = True


@dataclass(frozen=True, slots=True)
class UserMemoryRecord:
    """One repository-owned user-memory record."""

    owner_id: str
    envelope: RecordEnvelope
    content: dict[str, Any]
    tombstoned: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible representation."""
        return {
            "owner_id": self.owner_id,
            "envelope": self.envelope.to_dict(),
            "content": self.content,
            "tombstoned": self.tombstoned,
        }


def _validate_identifier(value: str, *, field_name: str) -> str:
    if not _SAFE_ID.fullmatch(value):
        raise ValueError(f"invalid {field_name}")
    return value


def _envelope_from_dict(payload: dict[str, Any]) -> RecordEnvelope:
    actor_payload = payload["actor"]
    return RecordEnvelope(
        record_id=payload["record_id"],
        record_type=RecordType(payload["record_type"]),
        repo_id=payload["repo_id"],
        git_commit=payload["git_commit"],
        branch=payload["branch"],
        worktree_id=payload["worktree_id"],
        task_id=payload["task_id"],
        actor=ActorIdentity(**actor_payload),
        created_at=payload["created_at"],
        source_refs=tuple(payload["source_refs"]),
        source_hashes=dict(payload.get("source_hashes", {})),
        trust=TrustLevel(payload["trust"]),
        security_class=SecurityClass(payload["security_class"]),
        status=RecordStatus(payload["status"]),
        supersedes=tuple(payload.get("supersedes", ())),
        schema_version=payload["schema_version"],
    )


class UserMemoryStore:
    """Filesystem store with explicit consent and per-operation authorization."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def grant_consent(self, consent: UserMemoryConsent) -> None:
        """Persist an explicit repository-scoped consent decision."""
        user_id = _validate_identifier(consent.user_id, field_name="user_id")
        repo_id = _validate_identifier(consent.repo_id, field_name="repo_id")
        atomic_write_json(
            self._consent_path(user_id, repo_id),
            asdict(consent),
        )

    def revoke_consent(self, context: AccessContext, *, user_id: str) -> None:
        """Revoke consent without silently deleting existing records."""
        consent = self._require_consent(user_id, context.repo_id)
        require_access(
            context,
            action=AccessAction.DELETE,
            owner_id=user_id,
            repo_id=context.repo_id,
        )
        self.grant_consent(replace(consent, active=False))

    def put(
        self,
        context: AccessContext,
        *,
        owner_id: str,
        envelope: RecordEnvelope,
        content: dict[str, Any],
    ) -> UserMemoryRecord:
        """Create or replace one consented user-memory record."""
        # NOSONAR - S2583: false positive - envelope.repo_id and context.repo_id are independent strings
        if envelope.repo_id != context.repo_id:
            raise ValueError("record envelope repository does not match caller")
        self._require_consent(owner_id, envelope.repo_id)
        require_access(
            context,
            action=AccessAction.CORRECT,
            owner_id=owner_id,
            repo_id=context.repo_id,
        )
        assert_safe_for_persistence(
            json.dumps(content, sort_keys=True),
            trust=envelope.trust,
        )
        record = UserMemoryRecord(
            owner_id=owner_id,
            envelope=envelope,
            content=dict(content),
        )
        atomic_write_json(
            self._record_path(owner_id, envelope.repo_id, envelope.record_id),
            record.to_dict(),
        )
        return record

    def enumerate(self, context: AccessContext, *, owner_id: str) -> list[str]:
        """List record identifiers inside the caller's user/repository scope."""
        self._require_consent(owner_id, context.repo_id)
        require_access(
            context,
            action=AccessAction.ENUMERATE,
            owner_id=owner_id,
            repo_id=context.repo_id,
        )
        records_dir = self._records_dir(owner_id, context.repo_id)
        if not records_dir.exists():
            return []
        return sorted(path.stem for path in records_dir.glob("*.json"))

    def export(
        self,
        context: AccessContext,
        *,
        owner_id: str,
        record_id: str,
        scope: RepositoryScope,
        dirty: bool,
        historical_mode: bool = False,
    ) -> UserMemoryRecord:
        """Return one scoped record, including its provenance envelope."""
        self._require_consent(owner_id, context.repo_id)
        require_access(
            context,
            action=AccessAction.EXPORT,
            owner_id=owner_id,
            repo_id=context.repo_id,
        )
        record = self._read_record(owner_id, context.repo_id, record_id)
        freshness = evaluate_freshness(
            record.envelope,
            scope,
            dirty=dirty,
            historical_mode=historical_mode,
        )
        if not freshness.usable:
            raise UserMemoryFreshnessError(freshness)
        return record

    def correct(
        self,
        context: AccessContext,
        *,
        owner_id: str,
        record_id: str,
        content: dict[str, Any],
    ) -> UserMemoryRecord:
        """Replace record content while preserving its provenance envelope."""
        self._require_consent(owner_id, context.repo_id)
        require_access(
            context,
            action=AccessAction.CORRECT,
            owner_id=owner_id,
            repo_id=context.repo_id,
        )
        current = self._read_record(owner_id, context.repo_id, record_id)
        assert_safe_for_persistence(
            json.dumps(content, sort_keys=True),
            trust=current.envelope.trust,
        )
        corrected = replace(current, content=dict(content))
        atomic_write_json(
            self._record_path(owner_id, context.repo_id, record_id),
            corrected.to_dict(),
        )
        return corrected

    def tombstone(
        self,
        context: AccessContext,
        *,
        owner_id: str,
        record_id: str,
    ) -> UserMemoryRecord:
        """Mark a record deleted while retaining an auditable envelope."""
        self._require_consent(owner_id, context.repo_id)
        require_access(
            context,
            action=AccessAction.TOMBSTONE,
            owner_id=owner_id,
            repo_id=context.repo_id,
        )
        current = self._read_record(owner_id, context.repo_id, record_id)
        tombstoned = replace(
            current,
            envelope=replace(current.envelope, status=RecordStatus.ARCHIVED),
            content={},
            tombstoned=True,
        )
        atomic_write_json(
            self._record_path(owner_id, context.repo_id, record_id),
            tombstoned.to_dict(),
        )
        return tombstoned

    def delete(
        self,
        context: AccessContext,
        *,
        owner_id: str,
        record_id: str,
    ) -> None:
        """Permanently delete one explicitly scoped repository-owned record."""
        # Revocation stops processing but must not make privacy erasure impossible.
        self._require_consent(owner_id, context.repo_id, require_active=False)
        require_access(
            context,
            action=AccessAction.DELETE,
            owner_id=owner_id,
            repo_id=context.repo_id,
        )
        path = self._record_path(owner_id, context.repo_id, record_id)
        if not path.is_file():
            raise FileNotFoundError("user-memory record not found")
        path.unlink()

    def _require_consent(
        self,
        user_id: str,
        repo_id: str,
        *,
        require_active: bool = True,
    ) -> UserMemoryConsent:
        path = self._consent_path(user_id, repo_id)
        if not path.is_file():
            raise UserMemoryConsentError(
                "repository-owned user memory requires explicit consent"
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        consent = UserMemoryConsent(**payload)
        if require_active and not consent.active:
            raise UserMemoryConsentError("repository-owned user memory consent revoked")
        return consent

    def _read_record(
        self,
        owner_id: str,
        repo_id: str,
        record_id: str,
    ) -> UserMemoryRecord:
        path = self._record_path(owner_id, repo_id, record_id)
        if not path.is_file():
            raise FileNotFoundError("user-memory record not found")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return UserMemoryRecord(
            owner_id=payload["owner_id"],
            envelope=_envelope_from_dict(payload["envelope"]),
            content=dict(payload["content"]),
            tombstoned=bool(payload["tombstoned"]),
        )

    def _scope_dir(self, user_id: str, repo_id: str) -> Path:
        return (
            self._root
            / _validate_identifier(repo_id, field_name="repo_id")
            / (_validate_identifier(user_id, field_name="user_id"))
        )

    def _consent_path(self, user_id: str, repo_id: str) -> Path:
        return self._scope_dir(user_id, repo_id) / "consent.json"

    def _records_dir(self, user_id: str, repo_id: str) -> Path:
        return self._scope_dir(user_id, repo_id) / "records"

    def _record_path(self, user_id: str, repo_id: str, record_id: str) -> Path:
        safe_record_id = _validate_identifier(record_id, field_name="record_id")
        return self._records_dir(user_id, repo_id) / f"{safe_record_id}.json"
