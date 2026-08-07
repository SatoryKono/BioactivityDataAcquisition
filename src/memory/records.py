"""Vendor-neutral record envelope for persistent AI memory artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class RecordType(StrEnum):
    """Supported memory record roles."""

    EVIDENCE = "evidence"
    WORKING = "working"
    KNOWLEDGE = "knowledge"
    DECISION = "decision"


class TrustLevel(StrEnum):
    """Trust assigned to the record's least-trusted input."""

    TRUSTED_REPOSITORY = "trusted_repository"
    REVIEWED_EXTERNAL = "reviewed_external"
    UNTRUSTED = "untrusted"


class SecurityClass(StrEnum):
    """Repository-owned memory data classification."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"  # pragma: allowlist secret


class RecordStatus(StrEnum):
    """Lifecycle state of a memory record."""

    ACTIVE = "active"
    STALE = "stale"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class ActorIdentity:
    """Runtime identity responsible for producing a record."""

    runtime: str
    agent: str
    model: str | None = None


@dataclass(frozen=True, slots=True)
class RecordEnvelope:
    """Common identity, provenance, and lifecycle metadata."""

    record_id: str
    record_type: RecordType
    repo_id: str
    git_commit: str
    branch: str
    worktree_id: str
    task_id: str
    actor: ActorIdentity
    created_at: str
    source_refs: tuple[str, ...]
    source_hashes: dict[str, str] = field(default_factory=dict)
    trust: TrustLevel = TrustLevel.UNTRUSTED
    security_class: SecurityClass = SecurityClass.INTERNAL
    status: RecordStatus = RecordStatus.ACTIVE
    supersedes: tuple[str, ...] = ()
    schema_version: int = 1

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        record_type: RecordType,
        repo_id: str,
        git_commit: str,
        branch: str,
        worktree_id: str,
        task_id: str,
        actor: ActorIdentity,
        source_refs: tuple[str, ...],
        source_hashes: dict[str, str] | None = None,
        trust: TrustLevel = TrustLevel.UNTRUSTED,
        security_class: SecurityClass = SecurityClass.INTERNAL,
        status: RecordStatus = RecordStatus.ACTIVE,
        supersedes: tuple[str, ...] = (),
        created_at: str | None = None,
    ) -> RecordEnvelope:
        """Create an envelope with a canonical UTC timestamp.
        
        NOSONAR - S107: 15 parameters are intentional for comprehensive record envelope creation;
        each parameter represents a distinct domain field required for memory records.
        """
        return cls(
            record_id=record_id,
            record_type=record_type,
            repo_id=repo_id,
            git_commit=git_commit,
            branch=branch,
            worktree_id=worktree_id,
            task_id=task_id,
            actor=actor,
            created_at=created_at or datetime.now(UTC).isoformat(),
            source_refs=source_refs,
            source_hashes=source_hashes or {},
            trust=trust,
            security_class=security_class,
            status=status,
            supersedes=supersedes,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible canonical representation."""
        payload = asdict(self)
        payload["record_type"] = self.record_type.value
        payload["trust"] = self.trust.value
        payload["security_class"] = self.security_class.value
        payload["status"] = self.status.value
        payload["source_refs"] = list(self.source_refs)
        payload["supersedes"] = list(self.supersedes)
        return payload

    @property
    def content_digest(self) -> str:
        """Return a stable digest of the complete envelope."""
        encoded = json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
