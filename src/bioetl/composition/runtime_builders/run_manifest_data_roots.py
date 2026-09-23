"""Resolve run-manifest data roots and expose compatibility path helpers."""

from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Callable
from contextlib import suppress
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

DataRootMode = Literal["explicit", "repo_default", "private_cache", "tmp"]

__all__ = [
    "DataRootMode",
    "build_planned_artifacts",
    "control_plane_root",
    "is_explicit_data_root_configured",
    "resolve_data_root",
    "resolve_data_root_mode",
    "resolve_data_root_with_mode",
]


def compat_attr(module: str, name: str, *args: object, **kwargs: object) -> object:
    return getattr(import_module(module), name)(*args, **kwargs)


def control_plane_root(*args: object, **kwargs: object) -> object:
    return compat_attr(
        "bioetl.composition.control_plane_paths",
        "control_plane_root",
        *args,
        **kwargs,
    )


def build_planned_artifacts(*args: object, **kwargs: object) -> object:
    return compat_attr(
        "bioetl.composition.runtime_builders._run_manifest_planned_artifacts",
        "build_planned_artifacts",
        *args,
        **kwargs,
    )


def is_explicit_data_root_configured(settings: Settings) -> bool:
    """Return ``True`` when settings declare an explicit non-empty data root."""
    configured_root = getattr(settings, "data_dir", None)
    return bool(str(configured_root or "").strip())


def resolve_data_root_mode(settings: Settings) -> DataRootMode:
    """Classify which data-root strategy would be used in the current runtime.

    Shares the single resolution path with ``resolve_data_root``.
    """
    return resolve_data_root_with_mode(settings)[1]


def resolve_data_root(settings: Settings) -> Path:
    """Resolve the writable data root used by run-manifest builders."""
    return resolve_data_root_with_mode(settings)[0]


def resolve_data_root_with_mode(settings: Settings) -> tuple[Path, DataRootMode]:
    """Single source of truth for data-root path and mode selection."""
    configured_root = getattr(settings, "data_dir", None)
    if configured_root and str(configured_root).strip():
        return Path(configured_root), "explicit"

    candidate = Path("data")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _private_fallback_data_root_with_mode()
    if not os.access(candidate, os.W_OK):
        return _private_fallback_data_root_with_mode()
    return candidate, "repo_default"


def _private_fallback_data_root() -> Path:
    """Named seam for the user-private fallback data root (test monkeypatch)."""
    preferred = Path.home() / ".cache" / "bioetl-data"
    try:
        return _prepare_private_runtime_dir(preferred)
    except OSError:
        runtime_user = getattr(os, "getuid", lambda: "user")()
        fallback = Path(tempfile.gettempdir()) / f"bioetl-data-{runtime_user}"
        return _prepare_private_runtime_dir(fallback)


def _private_fallback_data_root_with_mode() -> tuple[Path, DataRootMode]:
    """Return private fallback path via the monkeypatchable seam + mode class."""
    path = _private_fallback_data_root()
    preferred = Path.home() / ".cache" / "bioetl-data"
    try:
        if path.resolve() == preferred.resolve():
            return path, "private_cache"
    except OSError:
        pass
    return path, "tmp"


def _prepare_private_runtime_dir(path: Path) -> Path:
    """Create a private runtime directory; POSIX rejects non-owner modes."""
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    with suppress(OSError):
        path.chmod(0o700)
    _assert_private_runtime_dir(path)
    return path


def _assert_private_runtime_dir(path: Path) -> None:
    """Fail closed when the private runtime directory is not owner-private."""
    if not path.is_dir():
        raise OSError(f"private runtime path is not a directory: {path}")
    try:
        st = path.stat()
    except OSError as exc:
        raise OSError(f"unable to stat private runtime path: {path}") from exc
    getuid = cast("Callable[[], int] | None", getattr(os, "getuid", None))
    if getuid is not None:
        try:
            uid = getuid()
        except (TypeError, ValueError, OSError):
            uid = None
        else:
            if st.st_uid != uid:
                raise OSError(
                    f"private runtime path is not owned by current user: {path}"
                )

    if os.name == "nt":
        return

    mode = stat.S_IMODE(st.st_mode)
    if mode & 0o077:
        with suppress(OSError):
            path.chmod(0o700)
            st = path.stat()
            mode = stat.S_IMODE(st.st_mode)
        if mode & 0o077:
            raise OSError(
                f"private runtime path is not owner-private (mode={oct(mode)}): {path}"
            )
