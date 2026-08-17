"""Canonical process-independent runtime/report source identity primitives."""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

RUNTIME_SOURCE_ID_ENV = "BIOETL_RUNTIME_SOURCE_ID"
RUNTIME_SOURCE_ID_LABEL = "io.bioetl.dashboard-source-id"
RUNTIME_SOURCE_ID_SCHEMA = "bioetl-dashboard-source-v1"

IDENTITY_SOURCE_RUNTIME_ROOT = "runtime_root"
IDENTITY_SOURCE_PROCESS_ENVIRONMENT = "process_environment"
IDENTITY_SOURCE_REPOSITORY_ENVIRONMENT = "repository_environment"
IDENTITY_SOURCE_CONTAINER_ENVIRONMENT = "container_environment"
IDENTITY_SOURCE_CONTAINER_LABEL = "container_label"
IDENTITY_SOURCE_NONE = "none"

IDENTITY_RESOLUTION_RESOLVED = "resolved"
IDENTITY_RESOLUTION_MISSING = "missing"
IDENTITY_RESOLUTION_INVALID = "invalid"

IDENTITY_STATE_MISSING = "missing"
IDENTITY_STATE_INVALID = "invalid"
IDENTITY_STATE_FOREIGN = "foreign"
IDENTITY_STATE_ALIGNED = "aligned"

_SOURCE_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_DRIVE_PATTERN = re.compile(r"^([A-Za-z]):(?:/(.*))?$")
_WSL_UNC_PATTERN = re.compile(
    r"^//(?:wsl\$|wsl\.localhost)/[^/]+(/.*)$",
    flags=re.IGNORECASE,
)
_DOCKER_DESKTOP_DRIVE_PATTERN = re.compile(
    r"^/(?:run/desktop/mnt/host|host_mnt)/([A-Za-z])(?:/(.*))?$",
    flags=re.IGNORECASE,
)
_DOCKER_DESKTOP_WSL_PATTERN = re.compile(
    r"^/(?:run/desktop/mnt/host|host_mnt)/wsl(?:/(.*))?$",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class RuntimeSourceIdentityResolutionResult:
    """One precedence-bound identity resolution without secret-bearing data."""

    value: str | None
    source: str
    status: str
    conflicts: tuple[str, ...] = ()
    invalid_sources: tuple[str, ...] = ()

    @property
    def is_resolved(self) -> bool:
        return self.status == IDENTITY_RESOLUTION_RESOLVED and self.value is not None

    @property
    def state(self) -> str:
        """Return the canonical externally reportable resolution state."""
        if self.status == IDENTITY_RESOLUTION_MISSING:
            return IDENTITY_STATE_MISSING
        if self.status == IDENTITY_RESOLUTION_INVALID or self.invalid_sources:
            return IDENTITY_STATE_INVALID
        if self.conflicts:
            return IDENTITY_STATE_FOREIGN
        return IDENTITY_STATE_ALIGNED

    @property
    def is_consistent(self) -> bool:
        return self.is_resolved and self.state == IDENTITY_STATE_ALIGNED

    def as_dict(self) -> dict[str, object]:
        """Return bounded JSON diagnostics (origins and digest only)."""
        return {
            "value": self.value,
            "source": self.source,
            "status": self.status,
            "state": self.state,
            "conflicts": list(self.conflicts),
            "invalid_sources": list(self.invalid_sources),
        }


@dataclass(frozen=True)
class RuntimeSourceIdentityComparisonResult:
    """Comparison state for one expected/actual source identity pair."""

    state: str
    expected: str | None
    actual: str | None

    @property
    def is_aligned(self) -> bool:
        return self.state == IDENTITY_STATE_ALIGNED


def normalize_source_id(value: object | None) -> str | None:
    """Return a canonical lowercase source digest, or ``None`` when invalid."""
    text = str(value or "").strip().lower()
    return text if _SOURCE_ID_PATTERN.fullmatch(text) else None


def _clean_path_text(path: str | Path) -> str:
    value = str(path).strip().strip('"').replace("\\", "/")
    while "//" in value and not value.startswith("//"):
        value = value.replace("//", "/")
    return value


def _is_absolute_runtime_path(value: str) -> bool:
    return bool(
        value.startswith("/")
        or value.startswith("//")
        or _WINDOWS_DRIVE_PATTERN.match(value)
    )


def _drive_path_to_mnt(value: str) -> str | None:
    """Translate Windows and Docker Desktop drive paths to ``/mnt``."""
    for pattern in (_WINDOWS_DRIVE_PATTERN, _DOCKER_DESKTOP_DRIVE_PATTERN):
        match = pattern.match(value)
        if match is None:
            continue
        drive, suffix = match.groups()
        normalized = f"/mnt/{drive.lower()}"
        return f"{normalized}/{suffix.lstrip('/')}" if suffix else normalized
    return None


def _normalize_wsl_runtime_path(value: str) -> str:
    """Translate WSL UNC and Docker Desktop WSL spellings to local paths."""
    wsl_unc_match = _WSL_UNC_PATTERN.match(value)
    if wsl_unc_match:
        return wsl_unc_match.group(1)
    desktop_wsl_match = _DOCKER_DESKTOP_WSL_PATTERN.match(value)
    if desktop_wsl_match:
        suffix = desktop_wsl_match.group(1) or ""
        return f"/mnt/wsl/{suffix.lstrip('/')}"
    return value


def normalize_runtime_path(path: str | Path, *, root: str | Path) -> str:
    """Normalize Windows, WSL, and Docker Desktop paths for comparison."""
    value = _clean_path_text(path)
    if not value:
        return ""

    value = _normalize_wsl_runtime_path(value)
    drive_path = _drive_path_to_mnt(value)
    if drive_path is not None:
        return posixpath.normpath(drive_path).casefold()

    if not _is_absolute_runtime_path(value):
        root_text = _clean_path_text(root)
        value = f"{root_text.rstrip('/')}/{value}"
        return normalize_runtime_path(value, root=root)

    normalized = posixpath.normpath(value)
    if re.match(r"^/mnt/[a-z](?:/|$)", normalized, flags=re.IGNORECASE):
        return normalized.casefold()
    return normalized


def _non_windows_runtime_path_to_local_path(value: str) -> Path | None:
    """Translate one Windows-origin runtime spelling on POSIX hosts."""
    drive_path = _drive_path_to_mnt(value)
    if drive_path is not None:
        return Path(drive_path)
    wsl_path = _normalize_wsl_runtime_path(value)
    return Path(wsl_path) if wsl_path != value else None


def runtime_path_to_local_path(path: str | Path, *, root: str | Path) -> Path:
    """Return the locally readable form of one host/runtime path spelling."""
    value = _clean_path_text(path)
    if not value:
        return Path(root)
    if os.name != "nt":
        translated = _non_windows_runtime_path_to_local_path(value)
        if translated is not None:
            return translated
    candidate = Path(value).expanduser()
    return candidate if candidate.is_absolute() else (Path(root) / candidate).resolve()


def compute_runtime_source_id(
    *,
    runtime_root: str | Path,
    mounts: Mapping[str, str | Path],
    schema_version: str = RUNTIME_SOURCE_ID_SCHEMA,
) -> str | None:
    """Compute the deterministic identity for a runtime root and mount set."""
    schema = str(schema_version).strip()
    normalized_root = normalize_runtime_path(runtime_root, root=runtime_root)
    normalized_mounts = {
        str(target): normalize_runtime_path(source, root=runtime_root)
        for target, source in sorted(mounts.items(), key=lambda item: str(item[0]))
        if str(target).strip() and str(source).strip()
    }
    if not schema or not normalized_root or not normalized_mounts:
        return None
    payload = {
        "schema_version": schema,
        "repository_root": normalized_root,
        "mounts": normalized_mounts,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _mapping_value(mapping: Mapping[str, object] | None, name: str) -> object | None:
    return mapping.get(name) if mapping is not None else None


def resolve_runtime_source_identity(
    *,
    computed_identity: object | None = None,
    process_environment: Mapping[str, object] | None = None,
    repository_environment: Mapping[str, object] | None = None,
    container_environment: Mapping[str, object] | None = None,
    container_labels: Mapping[str, object] | None = None,
    environment_name: str = RUNTIME_SOURCE_ID_ENV,
    label_name: str = RUNTIME_SOURCE_ID_LABEL,
) -> RuntimeSourceIdentityResolutionResult:
    """Resolve one identity using the canonical fail-closed precedence.

    Precedence is computed runtime root, process environment, repository env
    loader, container environment, then container label.  A present but invalid
    highest-precedence value is not bypassed.  Lower-precedence disagreements
    are retained as bounded diagnostics for consumers that compare multiple
    independently observed surfaces.
    """
    candidates = (
        (IDENTITY_SOURCE_RUNTIME_ROOT, computed_identity),
        (
            IDENTITY_SOURCE_PROCESS_ENVIRONMENT,
            _mapping_value(process_environment, environment_name),
        ),
        (
            IDENTITY_SOURCE_REPOSITORY_ENVIRONMENT,
            _mapping_value(repository_environment, environment_name),
        ),
        (
            IDENTITY_SOURCE_CONTAINER_ENVIRONMENT,
            _mapping_value(container_environment, environment_name),
        ),
        (
            IDENTITY_SOURCE_CONTAINER_LABEL,
            _mapping_value(container_labels, label_name),
        ),
    )
    selected_value: str | None = None
    selected_source = IDENTITY_SOURCE_NONE
    selected_status = IDENTITY_RESOLUTION_MISSING
    conflicts: list[str] = []
    invalid_sources: list[str] = []

    for source, raw_value in candidates:
        raw_text = str(raw_value or "").strip()
        if not raw_text:
            continue
        normalized = normalize_source_id(raw_text)
        if selected_source == IDENTITY_SOURCE_NONE:
            selected_source = source
            if normalized is None:
                selected_status = IDENTITY_RESOLUTION_INVALID
                invalid_sources.append(source)
                break
            selected_value = normalized
            selected_status = IDENTITY_RESOLUTION_RESOLVED
            continue
        if normalized is None:
            invalid_sources.append(source)
        elif normalized != selected_value:
            conflicts.append(source)

    return RuntimeSourceIdentityResolutionResult(
        value=selected_value,
        source=selected_source,
        status=selected_status,
        conflicts=tuple(conflicts),
        invalid_sources=tuple(invalid_sources),
    )


def compare_runtime_source_identity(
    *,
    expected: object | None,
    actual: object | None,
) -> RuntimeSourceIdentityComparisonResult:
    """Classify an independently observed source identity."""
    expected_text = str(expected or "").strip()
    actual_text = str(actual or "").strip()
    normalized_expected = normalize_source_id(expected_text)
    normalized_actual = normalize_source_id(actual_text)
    if not expected_text or not actual_text:
        return RuntimeSourceIdentityComparisonResult(
            state=IDENTITY_STATE_MISSING,
            expected=normalized_expected,
            actual=normalized_actual,
        )
    if normalized_expected is None or normalized_actual is None:
        return RuntimeSourceIdentityComparisonResult(
            state=IDENTITY_STATE_INVALID,
            expected=normalized_expected,
            actual=normalized_actual,
        )
    if normalized_expected != normalized_actual:
        return RuntimeSourceIdentityComparisonResult(
            state=IDENTITY_STATE_FOREIGN,
            expected=normalized_expected,
            actual=normalized_actual,
        )
    return RuntimeSourceIdentityComparisonResult(
        state=IDENTITY_STATE_ALIGNED,
        expected=normalized_expected,
        actual=normalized_actual,
    )


def _repository_env_paths(
    *,
    root: Path,
    process_environment: Mapping[str, object],
) -> tuple[Path, ...]:
    """Resolve repository env paths without mutating process state."""
    configured_env = str(process_environment.get("BIOETL_ENV_FILE") or "").strip()
    env_path = Path(configured_env) if configured_env else root / ".env"
    if not env_path.is_absolute():
        env_path = root / env_path
    paths = [env_path]
    if str(process_environment.get("BIOETL_SKIP_ENV_LOCAL") or "0").strip() != "1":
        paths.append(root / ".env.local")
    return tuple(paths)


def _normalize_repository_env_value(value: str) -> str:
    """Apply canonical repository-env quote and inline-comment semantics."""
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] in {"'", '"'} and stripped[-1] == stripped[0]:
        return stripped[1:-1]
    return re.sub(r"\s+#.*$", "", stripped).rstrip()


def _parse_repository_env_line(
    raw: str,
    *,
    allowed: set[str],
) -> tuple[str, str] | None:
    """Return one whitelisted env assignment, or ``None`` when ignored."""
    stripped = raw.strip()
    if not stripped:
        return None
    if stripped.startswith("#"):
        return None
    if "=" not in raw:
        return None
    key, value = raw.split("=", 1)
    key = key.strip()
    if key not in allowed:
        return None
    return key, _normalize_repository_env_value(value)


def load_repository_source_environment(
    root: str | Path,
    *,
    names: Iterable[str],
    process_environment: Mapping[str, object] | None = None,
) -> dict[str, str]:
    """Read only whitelisted source settings through repository-env semantics.

    The function never mutates process state and never returns unrelated or
    secret-bearing values.  ``.env.local`` overrides ``.env`` exactly as the
    canonical shell loader does.  A custom ``BIOETL_ENV_FILE`` is honored when
    the caller supplies it through ``process_environment``.
    """
    root_path = Path(root)
    allowed = {str(name) for name in names if str(name)}
    process = process_environment or {}

    values: dict[str, str] = {}
    for path in _repository_env_paths(
        root=root_path,
        process_environment=process,
    ):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_repository_env_line(raw, allowed=allowed)
            if parsed is None:
                continue
            key, value = parsed
            values[key] = value
    return values
