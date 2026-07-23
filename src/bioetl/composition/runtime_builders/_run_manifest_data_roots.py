"""Data-root mode policy helpers for run-manifest builders."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from importlib import import_module
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


DataRootMode = Literal["explicit", "repo_default", "private_cache", "tmp"]

__all__ = [
    "DataRootMode",
    "build_planned_artifacts",
    "control_plane_root",
    "is_explicit_data_root_configured",
    "resolve_data_root_mode",
]


def control_plane_root(*args: object, **kwargs: object) -> object:
    """Compatibility wrapper for the control-plane path leaf helper."""
    return (
        import_module(
            "bioetl.composition.runtime_builders._run_manifest_control_plane_paths"
        )
    ).control_plane_root(*args, **kwargs)


def build_planned_artifacts(*args: object, **kwargs: object) -> object:
    """Compatibility wrapper for the planned-artifact path leaf helper."""
    return (
        import_module(
            "bioetl.composition.runtime_builders._run_manifest_planned_artifacts"
        )
    ).build_planned_artifacts(*args, **kwargs)


def __getattr__(name: str) -> object:  # pragma: no cover
    """Lazily expose legacy path helpers without static facade fan-in."""
    if TYPE_CHECKING:
        raise AttributeError
    if name == "control_plane_root":
        return getattr(
            import_module(
                "bioetl.composition.runtime_builders._run_manifest_control_plane_paths"
            ),
            name,
        )
    if name == "build_planned_artifacts":
        return getattr(
            import_module(
                "bioetl.composition.runtime_builders._run_manifest_planned_artifacts"
            ),
            name,
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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


def _resolve_data_root(settings: Settings) -> Path:
    """Resolve a writable data root for legacy run-manifest facade callers."""
    configured_root = getattr(settings, "data_dir", None)
    if configured_root and str(configured_root).strip():
        return Path(configured_root)

    candidate = Path("data")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _private_fallback_data_root()
    if not os.access(candidate, os.W_OK):
        return _private_fallback_data_root()
    return candidate


def _private_fallback_data_root_mode() -> DataRootMode:
    """Classify which private fallback would be used when checkout is read-only."""
    preferred = Path.home() / ".cache" / "bioetl-data"
    try:
        _prepare_private_runtime_dir(preferred)
    except OSError:
        return "tmp"
    return "private_cache"


def _private_fallback_data_root() -> Path:
    """Return a user-private fallback data root for legacy facade callers."""
    preferred = Path.home() / ".cache" / "bioetl-data"
    try:
        return _prepare_private_runtime_dir(preferred)
    except OSError:
        runtime_user = getattr(os, "getuid", lambda: "user")()
        fallback = Path(tempfile.gettempdir()) / f"bioetl-data-{runtime_user}"
        return _prepare_private_runtime_dir(fallback)


def _prepare_private_runtime_dir(path: Path) -> Path:
    """Create a private runtime directory and normalize its permissions."""
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    with suppress(OSError):
        path.chmod(0o700)
    return path


def _artifact_path_string(path: PurePath) -> str:
    """Return portable artifact paths with normalized separators."""
    return path.as_posix()
