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


def common_directory(root: Path) -> Path:
    """Verify a checkout or linked-worktree marker and its backlink."""
    root = _physical(root)
    marker = root / ".git"
    _physical(marker)
    if marker.is_dir():
        return marker
    text = marker.read_text(encoding="utf-8-sig").strip()
    if not text.startswith("gitdir: "):
        raise ValueError("Invalid native MCP Git marker")
    gitdir = Path(text[8:])
    gitdir = _physical((gitdir if gitdir.is_absolute() else root / gitdir).resolve(strict=True))
    backlink = Path((gitdir / "gitdir").read_text(encoding="utf-8-sig").strip())
    if not backlink.is_absolute():
        backlink = gitdir / backlink
    if backlink.resolve(strict=True) != marker:
        raise ValueError("Native MCP worktree backlink mismatch")
    common = Path((gitdir / "commondir").read_text(encoding="utf-8-sig").strip())
    return _physical((common if common.is_absolute() else gitdir / common).resolve(strict=True))


def apply_local_routes(
    servers: dict[str, dict[str, Any]], workspace: Path, *, manifest: Path | None = None
) -> dict[str, dict[str, Any]]:
    """Return reviewed stdio overrides; malformed or foreign bindings fail closed."""
    explicit = os.environ.get("BIOETL_CODEX_ROUTES_FILE")
    path = manifest or Path(explicit or Path.home() / ".config/pc-agent/codex-routes.json")
    if not path.exists():
        if explicit or manifest:
            raise ValueError("Configured native MCP route manifest is absent")
        return servers
    _physical(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"schema", "git_common", "entries"} or data["schema"] != 1:
        raise ValueError("Invalid native MCP route manifest")
    expected = _physical(Path(data["git_common"]))
    try:
        actual = common_directory(workspace)
    except FileNotFoundError:
        if explicit or manifest:
            raise
        return servers  # A default host binding does not own a new/foreign repo.
    if actual != expected:
        if explicit or manifest:
            raise ValueError("Native MCP route belongs to another repository")
        return servers
    result = deepcopy(servers)
    if not isinstance(data["entries"], dict):
        raise ValueError("Invalid native MCP route entries")
    for name, entry in data["entries"].items():
        if name == "ref" or not isinstance(entry, dict) or set(entry) != {"command", "args"}:
            raise ValueError("Native MCP route must be credential-free stdio without cwd")
        if not isinstance(entry["command"], str) or not entry["command"].strip():
            raise ValueError("Invalid native MCP executable")
        if not isinstance(entry["args"], list) or not all(isinstance(x, str) for x in entry["args"]):
            raise ValueError("Invalid native MCP arguments")
        # Profiles may omit optional catalogue members. Never add an extra server.
        if name not in servers:
            continue
        flags = {k: deepcopy(v) for k, v in servers[name].items() if k in {
            "enabled", "disabled", "enabled_tools", "disabled_tools", "tools", "startup_timeout_sec", "tool_timeout_sec"
        }}
        result[name] = {**deepcopy(entry), **flags}
    return result
