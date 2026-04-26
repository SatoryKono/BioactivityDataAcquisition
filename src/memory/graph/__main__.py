"""Unified entry point for ``python -m memory.graph`` commands."""

from __future__ import annotations

import sys

from memory.graph import query, sync

COMMANDS = {
    "sync": sync.main,
    "query": query.main,
}


def _print_help() -> None:
    pass


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return 0

    cmd, rest = args[0], args[1:]
    handler = COMMANDS.get(cmd)
    if handler is None:
        return 2
    return handler(rest)


if __name__ == "__main__":
    raise SystemExit(main())
