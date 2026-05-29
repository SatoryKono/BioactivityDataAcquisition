"""Shared identity helpers for append-only control-plane ledgers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256

__all__ = ["build_ledger_idempotency_key"]


def build_ledger_idempotency_key(
    payload: Mapping[str, object],
    *,
    fields: Sequence[str],
) -> str:
    """Build a stable key for one logical control-plane ledger event."""
    semantic_payload = {field_name: payload.get(field_name) for field_name in fields}
    serialized = json.dumps(
        semantic_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"sha256:{sha256(serialized.encode('utf-8')).hexdigest()}"
