"""Stable idempotency-key helpers for control-plane ledger entries."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256


def build_control_plane_idempotency_key(
    payload: Mapping[str, object],
    *,
    fields: tuple[str, ...],
) -> str:
    """Build a deterministic key from the declared semantic payload fields."""
    semantic_payload = {field_name: payload.get(field_name) for field_name in fields}
    serialized = json.dumps(
        semantic_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"sha256:{sha256(serialized.encode('utf-8')).hexdigest()}"


__all__ = ["build_control_plane_idempotency_key"]
