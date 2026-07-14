"""Versioning and reproducibility utilities for pipeline metadata.

Provides functions to compute:
- Git commit hash for reproducibility tracking
- Config hash for change detection
- Pipeline version from config or package

These utilities support PipelineMetadata population as per RULES.md §2.3.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess  # nosec B404
from dataclasses import dataclass
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.normalization import serialize_json_canonical

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

_FULL_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_RUNTIME_PATH_CLS = type(Path())
_REPO_ROOT = Path(__file__).resolve().parents[4]

__all__ = [
    "CodeRevisionProvenance",
    "compute_config_hash",
    "get_code_revision_provenance",
    "get_dependency_lock_hash",
    "get_git_commit",
    "get_pipeline_version",
]


@dataclass(frozen=True, slots=True)
class CodeRevisionProvenance:
    """Resolved source revision anchors for replay/debug provenance."""

    git_commit: str | None
    source_revision_state: str
    dependency_lock_hash: str | None = None


def _iter_windows_git_fallback_executables() -> tuple[str, ...]:
    """Return explicit Windows git executable paths discovered from PATH."""
    candidates: list[str] = []
    seen: set[str] = set()
    for path_entry in os.get_exec_path():
        candidate = (Path(path_entry) / "git.exe").resolve()
        candidate_str = str(candidate)
        if candidate.is_file() and candidate_str not in seen:
            seen.add(candidate_str)
            candidates.append(candidate_str)
    return tuple(candidates)


def _should_try_windows_git_fallback(
    result: subprocess.CompletedProcess[str] | None,
    *,
    accepted_returncodes: tuple[int, ...],
) -> bool:
    """Return whether a Windows-specific git executable fallback is warranted."""
    if os.name != "nt":
        return False
    if result is None:
        return True
    if result.returncode in accepted_returncodes:
        return False
    # Preserve ordinary git/repo failures as-is; only recover from shim/process
    # failures that indicate the launcher itself is unreliable.
    return result.returncode not in {1, 128}


def _run_git_command(
    *arguments: str,
    accepted_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str] | None:
    """Run one git command, retrying explicit Windows executables when needed."""
    last_result: subprocess.CompletedProcess[str] | None = None
    try:
        last_result = subprocess.run(  # nosec B603 B607
            ["git", *arguments],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        last_result = None
    if not _should_try_windows_git_fallback(
        last_result,
        accepted_returncodes=accepted_returncodes,
    ):
        return last_result
    for executable in _iter_windows_git_fallback_executables():
        try:
            candidate_result = subprocess.run(  # nosec B603
                [executable, *arguments],
                cwd=_REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            continue
        if candidate_result.returncode in accepted_returncodes:
            return candidate_result
        last_result = candidate_result
    return last_result


@lru_cache(maxsize=1)
def get_git_commit() -> str | None:
    """Get the current git commit hash.

    Returns the full git commit hash of HEAD.
    Returns None if:
    - Not in a git repository
    - Git is not installed
    - Any other git error occurs

    Results are cached for the process lifetime since the commit
    doesn't change during execution.

    Returns:
        Full git commit hash (e.g., a 40-character SHA-1) or None.

    Example:
        >>> commit = get_git_commit()
        >>> commit  # full HEAD SHA or None
    """
    result = _run_git_command("rev-parse", "HEAD")
    if result is None or result.returncode != 0:
        return None
    commit = result.stdout.strip().lower()
    return commit if _FULL_GIT_SHA_RE.fullmatch(commit) else None


@lru_cache(maxsize=1)
def get_dependency_lock_hash() -> str | None:
    """Return the content hash for the active dependency lockfile, if present."""
    cwd = _RUNTIME_PATH_CLS.cwd()
    for directory in (cwd, *cwd.parents):
        for lockfile_name in ("uv.lock", "poetry.lock"):
            lockfile = directory / lockfile_name
            if lockfile.is_file():
                digest = hashlib.sha256(lockfile.read_bytes()).hexdigest()
                return f"sha256:{digest}"
    return None


def _get_repo_dependency_lock_hash() -> str | None:
    """Return the checkout lockfile hash for provenance when cwd is external."""
    for lockfile_name in ("uv.lock", "poetry.lock"):
        lockfile = _REPO_ROOT / lockfile_name
        if lockfile.is_file():
            digest = hashlib.sha256(lockfile.read_bytes()).hexdigest()
            return f"sha256:{digest}"
    for lockfile_name in ("uv.lock", "poetry.lock"):
        result = _run_git_command("show", f"HEAD:{lockfile_name}")
        if result is None or result.returncode != 0:
            continue
        digest = hashlib.sha256(result.stdout.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
    return None


@lru_cache(maxsize=1)
def get_code_revision_provenance() -> CodeRevisionProvenance:
    """Return git commit plus coarse source revision state for manifests."""
    commit = get_git_commit()
    dependency_lock_hash = get_dependency_lock_hash()
    if dependency_lock_hash is None and commit is not None:
        dependency_lock_hash = _get_repo_dependency_lock_hash()
    if commit is None:
        return CodeRevisionProvenance(
            git_commit=None,
            source_revision_state="git_unavailable",
            dependency_lock_hash=dependency_lock_hash,
        )
    result = _run_git_command(
        "diff-index",
        "--quiet",
        "HEAD",
        "--",
        accepted_returncodes=(0, 1),
    )
    if result is None:
        return CodeRevisionProvenance(
            git_commit=commit,
            source_revision_state="dirty_state_unknown",
            dependency_lock_hash=dependency_lock_hash,
        )
    if result.returncode == 0:
        state = "clean"
    elif result.returncode == 1:
        state = "dirty"
    else:
        state = "dirty_state_unknown"
    return CodeRevisionProvenance(
        git_commit=commit,
        source_revision_state=state,
        dependency_lock_hash=dependency_lock_hash,
    )


def _normalize_for_hash(obj: object) -> object:
    """Normalize object for deterministic hashing.

    Converts:
    - Lists to sorted lists (for sets represented as lists)
    - Dicts to sorted key-value pairs
    - None to null string
    - Other values as-is

    Args:
        obj: Object to normalize.

    Returns:
        Normalized object suitable for deterministic JSON serialization.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _normalize_for_hash(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_normalize_for_hash(item) for item in obj]
    if isinstance(obj, tuple):
        return [_normalize_for_hash(item) for item in obj]
    return obj


def compute_config_hash(
    config: PipelineYamlConfig | dict[str, object],
) -> str:
    """Compute SHA256 hash of pipeline configuration.

    Creates a deterministic hash of the configuration for change detection.
    The hash is computed from a normalized JSON representation to ensure
    consistency regardless of dict ordering or whitespace.

    Args:
        config: Pipeline configuration (PipelineYamlConfig or dict).

    Returns:
        SHA256 hash string (64 characters).

    Example:
        >>> config = load_pipeline_config("chembl_activity")
        >>> hash_value = compute_config_hash(config)
        >>> hash_value  # '3a7bd3e2...'
    """
    # Convert Pydantic model to dict if needed
    if hasattr(config, "model_dump"):
        config_dict = config.model_dump(mode="json", exclude_none=True)
    elif hasattr(config, "dict"):
        # Legacy Pydantic v1 support
        config_dict = config.dict(exclude_none=True)
    else:
        config_dict = dict(config)

    # Normalize for deterministic serialization
    normalized = _normalize_for_hash(config_dict)
    if not isinstance(normalized, dict | list):
        raise TypeError("Pipeline config normalization must produce JSON-like data")

    # Reuse the same canonical JSON contract as the run-manifest fingerprint.
    json_str = serialize_json_canonical(normalized)

    # Compute SHA256 hash
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def get_pipeline_version(
    config: PipelineYamlConfig | dict[str, object] | None = None,
) -> str:
    """Get pipeline version from config or fallback to package version.

    Priority:
    1. config.version if available
    2. bioetl package version
    3. "unknown" as last resort

    Args:
        config: Optional pipeline configuration.

    Returns:
        Version string (e.g., '1.0.0' or package version).

    Example:
        >>> version = get_pipeline_version(config)
        >>> version  # '1.0.0'
    """
    # Try to get version from config
    if config is not None:
        # Handle Pydantic model
        if hasattr(config, "version") and config.version:
            return str(config.version)
        # Handle dict
        if isinstance(config, dict) and config.get("version"):
            return str(config["version"])

    # Fallback to bioetl package version
    try:
        return pkg_version("bioetl")
    except (PackageNotFoundError, RuntimeError, ValueError, TypeError):
        return "unknown"
