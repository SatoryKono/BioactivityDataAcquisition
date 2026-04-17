#!/usr/bin/env python3
"""Discover and run canonical scripts by group."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

GROUP_ROOTS: dict[str, str] = {
    "ci": "engineering/ci",
    "dev": "engineering/dev",
    "qa": "engineering/qa",
    "docs": "docs",
    "schema": "schema",
    "data": "ops/data",
    "repo": "engineering/repo",
    "ops": "ops",
    "diagnostics": "engineering/diagnostics",
    "migrations": "ops/migrations",
    "diagrams": "diagrams",
}
CANONICAL_GROUPS: tuple[str, ...] = tuple(GROUP_ROOTS)


def _scripts_root() -> Path:
    return Path(__file__).resolve().parent


def _iter_group_scripts(group: str) -> list[Path]:
    rel_root = GROUP_ROOTS[group]
    root = _scripts_root() / rel_root
    if not root.exists():
        return []

    items: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".sh", ".ps1", ".cmd", ".bat"}:
            continue
        items.append(path)
    return sorted(items)


def _print_list() -> int:
    root = _scripts_root()
    for group in CANONICAL_GROUPS:
        scripts = _iter_group_scripts(group)
        print(f"[{group}] {len(scripts)}")
        for path in scripts:
            print(f"  - {path.relative_to(root).as_posix()}")
    return 0


def _print_find(pattern: str) -> int:
    root = _scripts_root()
    needle = pattern.lower()
    found = 0
    for group in CANONICAL_GROUPS:
        for path in _iter_group_scripts(group):
            rel = path.relative_to(root).as_posix()
            if needle in rel.lower():
                print(rel)
                found += 1
    return 0 if found > 0 else 1


def _exec_script(group: str, script_name: str, script_args: list[str]) -> int:
    group_root = _scripts_root() / group
    if not group_root.exists():
        print(f"Group not found: {group}", file=sys.stderr)
        return 2

    candidates = sorted(group_root.rglob(script_name))
    if not candidates:
        print(
            f"Script not found in group '{group}': {script_name}",
            file=sys.stderr,
        )
        return 2

    target = candidates[0]
    cmd: list[str]
    if target.suffix == ".py":
        cmd = [sys.executable, str(target), *script_args]
    elif target.suffix in {".sh"}:
        cmd = ["bash", str(target), *script_args]
    else:
        cmd = [str(target), *script_args]

    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonical scripts launcher")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List canonical scripts by group")

    find_parser = sub.add_parser("find", help="Find scripts by substring")
    find_parser.add_argument("pattern")

    exec_parser = sub.add_parser("exec", help="Execute a canonical script")
    exec_parser.add_argument("group", choices=CANONICAL_GROUPS)
    exec_parser.add_argument("script")
    exec_parser.add_argument("script_args", nargs=argparse.REMAINDER)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    if args.command == "list":
        return _print_list()
    if args.command == "find":
        return _print_find(args.pattern)
    if args.command == "exec":
        script_args = list(args.script_args)
        if script_args and script_args[0] == "--":
            script_args = script_args[1:]
        return _exec_script(args.group, args.script, script_args)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
