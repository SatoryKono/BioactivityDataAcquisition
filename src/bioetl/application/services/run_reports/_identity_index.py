"""Bounded identity peek for persisted run-report index rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple


class IdentityIndexPreview(NamedTuple):
    """Bounded identity peek for run-report index rows."""

    status: str | None
    started_at: str | None
    completed_at: str | None
    workflow_id: str | None
    workflow_run_id: str | None


def _optional_identity_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def read_identity_preview(path: Path) -> IdentityIndexPreview:
    """Read identity fields from a run-report JSON file."""
    empty = IdentityIndexPreview(None, None, None, None, None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty
    identity = payload.get("identity") if isinstance(payload, dict) else None
    if not isinstance(identity, dict):
        return empty
    return IdentityIndexPreview(
        status=_optional_identity_text(identity.get("status")),
        started_at=_optional_identity_text(identity.get("started_at")),
        completed_at=_optional_identity_text(identity.get("completed_at")),
        workflow_id=_optional_identity_text(identity.get("workflow_id")),
        workflow_run_id=_optional_identity_text(identity.get("workflow_run_id")),
    )
