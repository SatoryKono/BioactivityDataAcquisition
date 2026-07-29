"""Repository, worktree, and task namespace identity."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_COMPONENT_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")
_GIT_TIMEOUT_SECONDS = 5.0


def safe_component(value: str) -> str:
    """Convert an identity value into one bounded path component."""
    component = _COMPONENT_PATTERN.sub("-", value.strip()).strip(".-").lower()
    if not component:
        raise ValueError("namespace component must not be empty")
    if component in {".", ".."}:
        raise ValueError("relative namespace components are forbidden")
    return component[:96]


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    return completed.stdout.strip()


@dataclass(frozen=True, slots=True)
class RepositoryScope:
    """Version-bound identity for a repository task workspace."""

    repo_id: str
    git_commit: str
    branch: str
    worktree_id: str
    task_id: str

    @classmethod
    def discover(cls, repo_root: Path, *, task_id: str) -> RepositoryScope:
        """Discover identity without network access."""
        root = Path(_git(repo_root, "rev-parse", "--show-toplevel")).resolve()
        commit = _git(root, "rev-parse", "HEAD")
        branch = _git(root, "branch", "--show-current") or "detached"
        try:
            remote = _git(root, "remote", "get-url", "origin")
        except subprocess.CalledProcessError:
            remote = root.name
        repo_id = safe_component(remote.removesuffix(".git").rsplit("/", 1)[-1])
        worktree_digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
        return cls(
            repo_id=repo_id,
            git_commit=commit,
            branch=branch,
            worktree_id=worktree_digest,
            task_id=task_id,
        )

    def namespace_path(self, storage_root: Path) -> Path:
        """Resolve the task namespace under a caller-owned storage root."""
        identity = "\0".join(
            (self.repo_id, self.worktree_id, self.branch, self.task_id)
        ).encode("utf-8")
        identity_digest = hashlib.sha256(identity).hexdigest()[:16]
        return (
            storage_root
            / safe_component(self.repo_id)
            / safe_component(self.worktree_id)
            / safe_component(self.branch)
            / identity_digest
            / safe_component(self.task_id)
        )
