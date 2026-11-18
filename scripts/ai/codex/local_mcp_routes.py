"""Apply explicit, credential-free native transport bindings to local Codex output.

Portable manifests never consume this surface. The user-owned manifest is
selected for one physical Git common directory; adapters retain the inherited
session cwd and perform their own per-request authorization.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


def _physical(path: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("Native MCP route requires a physical absolute path")
    if path.resolve(strict=True) != path:
        raise ValueError("Native MCP route traverses a link")
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise ValueError("Native MCP route traverses a reparse point")
    return path


def _read_git_path(marker: Path, parent: Path, prefix: str = "") -> Path:
    limit = 8192
    with _physical(marker).open(encoding="utf-8-sig") as stream:
        raw = stream.read(limit + 1)
    text = raw.strip()
    if len(raw) > limit or not text.startswith(prefix) or not text[len(prefix) :]:
        raise ValueError("Invalid native MCP Git marker")
    return Path(os.path.abspath(parent / text[len(prefix) :]))


def common_directory(root: Path, *, expected: Path) -> Path | None:
    """Verify a checkout or worktree bound to the registered Git directory."""
    root = _physical(root)
    marker = _physical(root / ".git")
    if marker.is_dir():
        return marker if marker == expected else None
    gitdir = _read_git_path(marker, root, prefix="gitdir: ")
    if gitdir.parent != expected / "worktrees":
        return None
    if _read_git_path(gitdir / "gitdir", gitdir) != marker:
        raise ValueError("Native MCP worktree backlink mismatch")
    common = _read_git_path(gitdir / "commondir", gitdir)
    return expected if common == expected else None


def _validate_route_entry(name: str, entry: Any) -> None:
    if (
        name == "ref"
        or not isinstance(entry, dict)
        or set(entry) != {"command", "args"}
    ):
        raise ValueError("Native MCP route must be credential-free stdio without cwd")
    if not isinstance(entry["command"], str) or not entry["command"].strip():
        raise ValueError("Invalid native MCP executable")
    if not isinstance(entry["args"], list) or not all(
        isinstance(x, str) for x in entry["args"]
    ):
        raise ValueError("Invalid native MCP arguments")


def _repository_binding_matches(
    expected: Path, workspace: Path, *, strict: bool
) -> bool:
    try:
        actual = common_directory(workspace, expected=expected)
    except FileNotFoundError:
        if strict:
            raise
        return False  # A default host binding does not own a new/foreign repo.
    if actual != expected:
        if strict:
            raise ValueError("Native MCP route belongs to another repository")
        return False
    return True


def select_local_routes_manifest(manifest: Path | None = None) -> tuple[Path, bool]:
    """Use the caller path, then the explicit environment path, then the default."""
    explicit = os.environ.get("BIOETL_CODEX_ROUTES_FILE")
    path = manifest or Path(
        explicit or Path.home() / ".config/pc-agent/codex-routes.json"
    )
    return path, manifest is not None or bool(explicit)


def apply_local_routes(
    servers: dict[str, dict[str, Any]], workspace: Path, *, manifest: Path | None = None
) -> dict[str, dict[str, Any]]:
    """Return reviewed stdio overrides; malformed or foreign bindings fail closed."""
    path, explicit = select_local_routes_manifest(manifest)
    if not path.exists():
        if explicit:
            raise ValueError("Configured native MCP route manifest is absent")
        return servers
    _physical(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"schema", "git_common", "entries"} or data["schema"] != 1:
        raise ValueError("Invalid native MCP route manifest")
    try:
        expected = _physical(Path(data["git_common"]))
    except FileNotFoundError:
        if explicit:
            raise
        return servers  # A removed checkout cannot own the default host route.
    if not _repository_binding_matches(expected, workspace, strict=explicit):
        return servers
    result = deepcopy(servers)
    if not isinstance(data["entries"], dict):
        raise ValueError("Invalid native MCP route entries")
    for name, entry in data["entries"].items():
        _validate_route_entry(name, entry)
        # Profiles may omit optional catalogue members. Never add an extra server.
        if name not in servers:
            continue
        flags = {
            k: deepcopy(v)
            for k, v in servers[name].items()
            if k
            in {
                "enabled",
                "disabled",
                "enabled_tools",
                "disabled_tools",
                "tools",
                "startup_timeout_sec",
                "tool_timeout_sec",
            }
        }
        result[name] = {**deepcopy(entry), **flags}
    return result
