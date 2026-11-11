"""Local, non-executing guards for structured filesystem operations.

This is an internal command-wrapper contract, not a vendor lifecycle event.
Arbitrary child processes require a separate OS/tool boundary.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Literal

Status = Literal["PASS", "FAIL", "ERROR", "SKIP"]
_WORKTREE_LOCATION = "worktree.location"
WINDOWS_RESERVED = frozenset(
    ["nul", "con", "prn", "aux"]
    + [f"com{i}" for i in range(1, 10)]
    + [f"lpt{i}" for i in range(1, 10)]
)


@dataclass(frozen=True)
class Decision:
    """A decision is evidence about an operation, never execution of it."""

    status: Status
    code: str
    message: str
    canonical_path: str | None = None


@dataclass(frozen=True)
class WorktreePermit:
    """In-process path evidence to recheck immediately before creating a tree."""

    requested: Path
    canonical: Path
    ancestors: tuple[tuple[str, int, int], ...]


def allowed_worktree_root() -> Path:
    """Map the fixed Windows workspace into its WSL filesystem view."""
    return Path("D:/github" if os.name == "nt" else "/mnt/d/github")


def _is_env_name(name: str) -> bool:
    """Keep case-insensitive Windows names and the existing *.env guard."""
    name = name.split(":", 1)[0].rstrip(" .").casefold()
    return name == ".env" or name.startswith(".env.") or name.endswith(".env")


def is_env_target(raw: str) -> bool:
    """Check both lexical spelling and symlink/junction-resolved components."""
    lexical = raw.replace("\\", "/").split("/")
    return any(_is_env_name(part) for part in lexical) or any(
        _is_env_name(part) for part in Path(raw).resolve().parts
    )


def _ancestor_identity(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Directory identity ignores unrelated sibling edits by parallel agents."""
    identities = []
    for parent in path.parents:
        if parent.exists():
            info = parent.stat()
            identities.append((str(parent), info.st_dev, info.st_ino))
    return tuple(identities)


def prepare_worktree(raw: str, *, allowed_root: Path | None = None) -> WorktreePermit:
    """Validate destination and existing ancestors without creating anything."""
    root = (allowed_root or allowed_worktree_root()).resolve()
    if not root.is_dir():
        raise OSError("allowed workspace is unavailable")
    parent = root / "BioactivityDataAcquisition-worktrees"
    requested = Path(raw)
    if not requested.is_absolute():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", raw):
            raise ValueError("relative destination must be a task slug")
        requested = parent / raw
    canonical = requested.resolve()
    if not canonical.is_relative_to(root) or not canonical.is_relative_to(
        parent.resolve()
    ):
        raise ValueError("destination resolves outside the approved worktree directory")
    if canonical.parent != parent.resolve() or canonical.exists():
        raise ValueError("destination must be a new task directory")
    if any(
        part.casefold().split(".")[0] in WINDOWS_RESERVED for part in canonical.parts
    ):
        raise ValueError("reserved Windows path component")
    return WorktreePermit(requested, canonical, _ancestor_identity(requested))


def revalidate_worktree(
    permit: WorktreePermit, *, allowed_root: Path | None = None
) -> Decision:
    """Refuse changed path identity; the caller must still control the operation."""
    try:
        current = prepare_worktree(str(permit.requested), allowed_root=allowed_root)
        if current != permit:
            return Decision(
                "FAIL", "worktree.race", "destination or ancestor identity changed"
            )
        return Decision(
            "PASS",
            _WORKTREE_LOCATION,
            "destination revalidated",
            str(current.canonical),
        )
    except ValueError:
        return Decision(
            "FAIL", _WORKTREE_LOCATION, "destination is no longer admissible"
        )
    except (OSError, RuntimeError):
        return Decision(
            "ERROR", "worktree.unavailable", "path identity could not be verified"
        )


def evaluate_request(request: Any, *, allowed_root: Path | None = None) -> Decision:
    """Deny protected mutations; request data cannot grant its own approval."""
    if not isinstance(request, dict) or set(request) - {
        "operation",
        "path",
        "destination",
    }:
        return Decision(
            "ERROR",
            "request.schema",
            "unsupported fields; self-granted approvals are not accepted",
        )
    operation = request.get("operation")
    if not isinstance(operation, str):
        return Decision("ERROR", "request.operation", "operation must be a string")
    if operation == "worktree_create":
        return _evaluate_worktree(request.get("destination"), allowed_root)
    if operation not in {"read", "write", "create", "delete", "rename", "move"}:
        return Decision(
            "ERROR", "request.operation", "unknown operation; no command was executed"
        )
    return _evaluate_file_operation(operation, request)


def _evaluate_file_operation(operation: str, request: dict[str, Any]) -> Decision:
    """Check every write endpoint, including rename sources and targets."""
    paths = [request.get("path")]
    if operation in {"rename", "move"}:
        paths.append(request.get("destination"))
    validated: list[str] = []
    for path in paths:
        if not isinstance(path, str) or not path.strip() or "\x00" in path:
            return Decision("ERROR", "request.path", "all operation paths are required")
        validated.append(path)
    if operation == "read":
        return Decision("PASS", "env.read", "reads are permitted")
    try:
        if any(is_env_target(path) for path in validated):
            return Decision(
                "FAIL",
                "env.protected",
                "protected mutation requires user approval outside this guard",
            )
        if any(Path(path).resolve().is_dir() for path in validated):
            return Decision(
                "FAIL",
                "path.directory_review",
                "directory mutations require host review of contained environment files",
            )
    except (OSError, RuntimeError, ValueError):
        return Decision("ERROR", "path.unavailable", "path resolution failed")
    return Decision(
        "PASS", "path.unprotected", "no protected environment path detected"
    )


def _evaluate_worktree(raw: Any, allowed_root: Path | None) -> Decision:
    """Convert path-validation failures into non-secret-bearing decisions."""
    if not isinstance(raw, str) or not raw.strip():
        return Decision("ERROR", "request.destination", "destination is required")
    try:
        permit = prepare_worktree(raw, allowed_root=allowed_root)
    except ValueError:
        return Decision("FAIL", _WORKTREE_LOCATION, "destination is not admissible")
    except (OSError, RuntimeError):
        return Decision("ERROR", "worktree.unavailable", "path resolution failed")
    return revalidate_worktree(permit, allowed_root=allowed_root)


def main(argv: list[str] | None = None) -> int:
    """Read one bounded JSON request from stdin; never invoke an operation."""
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(65537)
        request = json.loads(raw) if len(raw) <= 65536 else None
    except (OSError, ValueError, RecursionError):
        request = None
    result = evaluate_request(request)
    print(json.dumps(asdict(result)))
    return {"PASS": 0, "FAIL": 1, "ERROR": 2, "SKIP": 3}[result.status]
