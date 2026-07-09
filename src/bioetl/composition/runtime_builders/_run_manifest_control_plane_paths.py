"""Writable data-root and control-plane path helpers for run manifests."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _resolve_data_root(settings) / "output" / "control" / leaf


def _resolve_data_root(settings: Settings) -> Path:
    """Resolve a writable data root for control-plane artifacts."""
    configured_root = getattr(settings, "data_dir", None)
    if configured_root:
        return Path(configured_root)

    candidate = Path("data")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _private_fallback_data_root()
    if not os.access(candidate, os.W_OK):
        return _private_fallback_data_root()
    return candidate


def _private_fallback_data_root() -> Path:
    """Return a user-private fallback data root when the checkout is read-only."""
    preferred = Path.home() / ".cache" / "bioetl-data"
    try:
        return _prepare_private_runtime_dir(preferred)
    except OSError:
        runtime_user = getattr(os, "getuid", lambda: "user")()
        fallback = Path(tempfile.gettempdir()) / f"bioetl-data-{runtime_user}"
        return _prepare_private_runtime_dir(fallback)


def _prepare_private_runtime_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    with suppress(OSError):
        path.chmod(0o700)
    return path
