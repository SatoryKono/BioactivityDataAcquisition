"""Data-root and artifact path helpers for run-manifest builders."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from bioetl.domain.control_plane import RunArtifactRef

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


DataRootMode = Literal["explicit", "repo_default", "private_cache", "tmp"]


def is_explicit_data_root_configured(settings: Settings) -> bool:
    """Return ``True`` when settings declare an explicit non-empty data root."""
    configured_root = getattr(settings, "data_dir", None)
    return bool(str(configured_root or "").strip())


def resolve_data_root_mode(settings: Settings) -> DataRootMode:
    """Classify which data-root strategy would be used in the current runtime."""
    if is_explicit_data_root_configured(settings):
        return "explicit"

    candidate = Path("data")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _private_fallback_data_root_mode()
    if not os.access(candidate, os.W_OK):
        return _private_fallback_data_root_mode()
    return "repo_default"


def build_planned_artifacts(
    *,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned layer roots for the manifest control-plane snapshot."""
    output_root = _resolve_data_root(settings) / "output"
    return (
        RunArtifactRef(
            layer="bronze", path=str(output_root / "bronze" / provider / entity)
        ),
        RunArtifactRef(
            layer="silver", path=str(output_root / "silver" / provider / entity)
        ),
        RunArtifactRef(
            layer="gold", path=str(output_root / "gold" / provider / entity)
        ),
    )


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


def _private_fallback_data_root_mode() -> DataRootMode:
    """Classify which private fallback would be used when checkout is read-only."""
    preferred = Path.home() / ".cache" / "bioetl-data"
    try:
        _prepare_private_runtime_dir(preferred)
    except OSError:
        return "tmp"
    return "private_cache"


def _prepare_private_runtime_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    with suppress(OSError):
        path.chmod(0o700)
    return path
