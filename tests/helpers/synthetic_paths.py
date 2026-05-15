"""Deterministic synthetic paths for test-only artifact references."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path("/tmp/bioetl-test-artifacts")


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "artifact"


def synthetic_test_root(label: str) -> Path:
    """Return a stable synthetic root path without creating real temp dirs."""
    return _ROOT / _slug(label)
