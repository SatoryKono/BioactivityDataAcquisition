"""Unified entry point for ``python -m memory.graph`` commands."""

from __future__ import annotations

import sys

from memory.graph import query, sync

COMMANDS = {
    "sync": sync.main,
    "query": query.main,
}


def _print_help() -> None:
    print(
        "Usage:\n"
        "    python -m memory.graph <command> [args...]\n"
        "    python -m memory.graph --help\n\n"
        "Commands:\n"
        "    sync        Build and optionally sync the deterministic Neo4j repo graph\n"
        "    query       Query deterministic Neo4j memory ownership, neighbors, and analysis shortcuts",
        end="",
    )


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return 0

    cmd, rest = args[0], args[1:]
    handler = COMMANDS.get(cmd)
    if handler is None:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(sorted(COMMANDS))}", file=sys.stderr)
        return 2
    return handler(rest)


if __name__ == "__main__":
    raise SystemExit(main())
