"""Data model and source identity primitives for RAG validation."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from memory.rag.chunking import content_hash

FULL_BUILD_SCOPE = "full"
WORKFLOW_BUILD_SCOPE = "workflow"
SUPPORTED_BUILD_SCOPES = frozenset({FULL_BUILD_SCOPE, WORKFLOW_BUILD_SCOPE})
VIRTUAL_FRAGMENT_SOURCE = ".devin/wiki.json"
VIRTUAL_FRAGMENT_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
GIT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True, slots=True)
class RagValidationIssue:
    """One deterministic RAG manifest contract violation."""

    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable representation."""
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True, slots=True)
class RagValidationReport:
    """Machine-readable result of validating one RAG manifest pair."""

    issues: tuple[RagValidationIssue, ...]
    build_scope: str | None
    eligible_source_count: int
    indexed_source_count: int
    chunk_count: int
    missing_path_count: int
    stale_chunk_count: int
    source_surface_sha256: str | None

    @property
    def ok(self) -> bool:
        """Return whether the pair satisfies every requested contract."""
        return not self.issues

    def as_dict(self) -> dict[str, Any]:
        """Return a stable JSON-serializable validation payload."""
        return {
            "build_scope": self.build_scope,
            "chunk_count": self.chunk_count,
            "eligible_source_count": self.eligible_source_count,
            "indexed_source_count": self.indexed_source_count,
            "issues": [issue.as_dict() for issue in self.issues],
            "missing_path_count": self.missing_path_count,
            "ok": self.ok,
            "source_surface_sha256": self.source_surface_sha256,
            "stale_chunk_count": self.stale_chunk_count,
        }


class RagManifestValidationError(ValueError):
    """Raised when a RAG manifest pair fails semantic validation."""

    def __init__(self, report: RagValidationReport) -> None:
        self.report = report
        codes = ", ".join(sorted({issue.code for issue in report.issues}))
        issue_preview = "; ".join(
            f"{issue.code}@{issue.path}" for issue in report.issues[:5]
        )
        details = f" ({issue_preview})" if issue_preview else ""
        super().__init__(
            f"RAG manifest validation failed: {codes or 'unknown error'}{details}"
        )


def normalize_rag_source_path(
    source_path: str,
    *,
    allow_virtual_fragment: bool,
) -> str:
    """Normalize a safe repository-relative RAG source path."""
    if not source_path or "\x00" in source_path or "\\" in source_path:
        raise ValueError("source path must be a non-empty POSIX path")

    base_path, separator, fragment = source_path.partition("#")
    if separator:
        if not allow_virtual_fragment or base_path != VIRTUAL_FRAGMENT_SOURCE:
            raise ValueError("virtual fragments are only allowed for .devin/wiki.json")
        if "#" in fragment or not VIRTUAL_FRAGMENT_PATTERN.fullmatch(fragment):
            raise ValueError("virtual source fragment must be a canonical slug")

    pure_path = PurePosixPath(base_path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ValueError("source path must stay inside the repository")
    if not pure_path.parts or any(":" in part for part in pure_path.parts):
        raise ValueError("source path is not repository-relative")
    normalized = pure_path.as_posix()
    if normalized in {"", "."} or normalized != base_path:
        raise ValueError("source path must use canonical POSIX normalization")
    return normalized


def calculate_source_surface_sha256(
    root: Path,
    source_paths: list[str] | tuple[str, ...] | set[str],
) -> str:
    """Hash the ordered repository-relative source path/content identities."""
    identities: list[dict[str, str]] = []
    resolved_root = root.resolve()
    for source_path in sorted(set(source_paths)):
        normalized = normalize_rag_source_path(
            source_path,
            allow_virtual_fragment=False,
        )
        resolved_path = (resolved_root / normalized).resolve()
        if not resolved_path.is_relative_to(resolved_root):
            raise ValueError(f"source path escapes repository root: {source_path}")
        if not resolved_path.is_file():
            raise FileNotFoundError(f"RAG source does not exist: {normalized}")
        identities.append(
            {
                "content_hash": content_hash(resolved_path.read_text(encoding="utf-8")),
                "source_path": normalized,
            }
        )
    return calculate_source_identities_sha256(identities)


def calculate_source_identities_sha256(
    identities: list[dict[str, str]],
) -> str:
    """Hash already-captured source path/content identities."""
    canonical = json.dumps(
        sorted(identities, key=lambda identity: identity["source_path"]),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _run_git(
    root: Path, arguments: list[str]
) -> subprocess.CompletedProcess[str] | None:
    if not (root / ".git").exists():
        return None
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def capture_rag_git_identity(root: Path) -> dict[str, str | None]:
    """Capture the repository HEAD and tracked working-tree state."""
    head_result = _run_git(root, ["rev-parse", "HEAD"])
    status_result = _run_git(root, ["status", "--porcelain", "--untracked-files=no"])
    git_head_sha = (
        head_result.stdout.strip()
        if head_result is not None and head_result.returncode == 0
        else None
    )
    if status_result is None or status_result.returncode != 0:
        working_tree_state = "unavailable"
    else:
        working_tree_state = "dirty" if status_result.stdout.strip() else "clean"
    return {
        "git_head_sha": git_head_sha,
        "working_tree_state": working_tree_state,
    }


def capture_rag_source_identity(
    root: Path,
    source_paths: list[str] | tuple[str, ...] | set[str],
) -> dict[str, str | None]:
    """Capture Git and content identity for a generated RAG source surface."""
    return {
        **capture_rag_git_identity(root),
        "source_surface_sha256": calculate_source_surface_sha256(root, source_paths),
    }
