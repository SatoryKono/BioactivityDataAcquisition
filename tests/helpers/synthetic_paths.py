"""Deterministic synthetic paths for test-only artifact references."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path("/tmp/bioetl-test-artifacts")


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "artifact"


def synthetic_test_root(label: str) -> Path:
    """Return a stable absolute synthetic root path without creating temp dirs.

    Callers often derive ``file://`` URIs via ``Path.as_uri()`` at import time.
    On Windows, ``Path('/tmp/...')`` is drive-relative and therefore not a valid
    URI source until it is resolved to an absolute path.
    """
    return (_ROOT / _slug(label)).resolve()
