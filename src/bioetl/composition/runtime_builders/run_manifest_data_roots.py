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
from dataclasses import dataclass

from bioetl.application.services.run_reports.source_identity import (
    RUNTIME_SOURCE_ID_ENV,
    resolve_runtime_source_identity,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    load_repository_source_environment,
)
from bioetl.domain.control_plane.run_evidence_location import (
    canonicalize_relative_data_root,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

DataRootMode = Literal["explicit", "repo_default", "private_cache", "tmp"]

__all__ = [
    "DataRootMode",
    "EvidenceLocationBindingContext",
    "build_planned_artifacts",
    "control_plane_root",
    "is_explicit_data_root_configured",
    "relative_data_root_under_alias",
    "resolve_dashboard_data_alias_base",
    "resolve_data_root",
    "resolve_data_root_mode",
    "resolve_data_root_with_mode",
    "resolve_registration_runtime_source_id",
]

_DASHBOARD_DATA_ROOT_ENV = "BIOETL_DASHBOARD_DATA_ROOT"


@dataclass(frozen=True, slots=True)
class EvidenceLocationBindingContext:
    """Trusted write root + alias binding for one publisher call."""

    write_data_root: Path
    alias_base: Path
    root_alias: str
    relative_data_root: str
    runtime_source_id: str | None
    report_root: Path | None
    skip_reason: str | None = None

    @property
    def registration_allowed(self) -> bool:
        """False when binding cannot publish a ``dashboard_data`` locator."""
        return self.skip_reason is None and self.runtime_source_id is not None


def resolve_dashboard_data_alias_base(*, write_data_root: Path) -> Path | None:
    """Resolve the trusted ``dashboard_data`` alias base at composition edge."""
    raw = os.environ.get(_DASHBOARD_DATA_ROOT_ENV, "").strip()
    return Path(raw).expanduser().resolve(strict=False) if raw else None


def relative_data_root_under_alias(
    *, write_data_root: Path, alias_base: Path
) -> str | None:
    """Return the canonical write-root path relative to its trusted alias."""
    try:
        relative = (
            Path(write_data_root)
            .resolve(strict=False)
            .relative_to(Path(alias_base).resolve(strict=False))
        )
    except ValueError:
        return None
    text = relative.as_posix()
    return "." if text in {"", "."} else canonicalize_relative_data_root(text)


def resolve_registration_runtime_source_id(settings: Settings) -> str | None:
    """Resolve the bind/runtime source digest at the composition boundary."""
    configured = getattr(settings, "runtime_source_id", None)
    process_environment = (
        {RUNTIME_SOURCE_ID_ENV: str(configured).strip()}
        if configured is not None and str(configured).strip()
        else {}
    )
    if not process_environment:
        env_value = os.environ.get(RUNTIME_SOURCE_ID_ENV, "").strip()
        if env_value:
            process_environment[RUNTIME_SOURCE_ID_ENV] = env_value
    repository_environment = load_repository_source_environment(
        _repository_root(),
        names=(RUNTIME_SOURCE_ID_ENV,),
        process_environment=process_environment,
    )
    resolution = resolve_runtime_source_identity(
        process_environment=process_environment,
        repository_environment=repository_environment,
    )
    return resolution.value if resolution.is_resolved else None


def _repository_root() -> Path:
    """Return the repository root for repository-local runtime identity inputs."""
    return Path(__file__).resolve().parents[4]


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
        "bioetl.composition.runtime_builders.run_manifest_support",
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
