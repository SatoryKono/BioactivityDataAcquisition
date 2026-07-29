"""Strict optional manual metadata for assembled passport pages."""

from __future__ import annotations

from pathlib import Path

import yaml

_ALLOWED = {
    "owner",
    "owner_approved",
    "purpose",
    "business_context",
    "known_limitations",
    "rationale",
    "approved_exceptions",
}


def load_manual_sidecar(path: Path) -> dict[str, object]:
    """Load and validate one sidecar without permitting fact overrides."""
    if not path.is_file():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Manual passport sidecar must be a mapping: {path}")
    unknown = sorted(set(payload) - _ALLOWED)
    if unknown:
        raise ValueError(f"Unknown manual passport keys in {path}: {unknown}")
    if payload.get("owner_approved") is not True:
        raise ValueError(f"Manual passport sidecar is not owner-approved: {path}")
    owner = payload.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError(f"Manual passport sidecar has no owner: {path}")
    return payload
