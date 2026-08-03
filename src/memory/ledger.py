"""Append-only, content-free audit ledger for persistent memory mutations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from memory.records import ActorIdentity
from memory.storage import StorageConflictError, append_jsonl


@dataclass(frozen=True, slots=True)
class MutationEvent:
    """Attributable mutation metadata without persisted record content."""

    event_id: str
    operation: str
    record_id: str
    repo_id: str
    git_commit: str
    branch: str
    worktree_id: str
    task_id: str
    actor: ActorIdentity
    occurred_at: str
    reason: str
    previous_digest: str | None
    new_digest: str | None
    supersedes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.operation not in {
            "create",
            "update",
            "supersede",
            "archive",
            "delete",
        }:
            raise ValueError("unsupported mutation operation")
        if not self.reason.strip():
            raise ValueError("mutation reason is required")
        if self.operation == "create" and self.new_digest is None:
            raise ValueError("create requires new_digest")
        if self.operation == "delete" and self.previous_digest is None:
            raise ValueError("delete requires previous_digest")

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic content-free representation."""
        payload = asdict(self)
        payload["actor"] = asdict(self.actor)
        payload["supersedes"] = list(self.supersedes)
        return payload

    @property
    def event_digest(self) -> str:
        """Digest the full audit metadata."""
        encoded = json.dumps(
            self.to_dict(), separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class MutationLedger:
    """Append-only ledger with bounded queries by record identity."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, event: MutationEvent) -> str:
        """Append an event and reject reused event identities."""
        try:
            append_jsonl(
                self._path,
                {**event.to_dict(), "event_digest": event.event_digest},
                reject_if=lambda row: row.get("event_id") == event.event_id,
                conflict_message="mutation event already exists",
            )
        except StorageConflictError as exc:
            raise ValueError("mutation event already exists") from exc
        return event.event_digest

    def history(self, record_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return bounded chronological metadata for one record."""
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        rows = [row for row in self._rows() if row.get("record_id") == record_id]
        return rows[-limit:]

    def _rows(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("mutation ledger rows must be objects")
            digest = row.get("event_digest")
            content = {
                key: value for key, value in row.items() if key != "event_digest"
            }
            encoded = json.dumps(content, separators=(",", ":"), sort_keys=True).encode(
                "utf-8"
            )
            if digest != hashlib.sha256(encoded).hexdigest():
                raise ValueError("mutation ledger digest mismatch")
            rows.append(row)
        return rows
