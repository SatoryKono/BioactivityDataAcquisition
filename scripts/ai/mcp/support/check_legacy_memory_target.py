"""Refuse owner-managed graph paths before a standalone memory wrapper starts."""

import sys
from pathlib import Path


def main():
    root, requested = map(Path, sys.argv[1:])
    cache = root.resolve(strict=True) / ".cache" / "mcp-memory"
    target = requested.expanduser().resolve()
    try:
        relative = target.relative_to(cache)
    except ValueError:
        sys.stderr.write("MCP memory target must be inside its worktree cache.\n")
        return 78
    if relative.parts and relative.parts[0].casefold() == "project-service-v1":
        sys.stderr.write("Owner-managed MCP memory requires its registered adapter.\n")
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
