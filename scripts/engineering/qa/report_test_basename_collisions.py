"""Generate the tracked test-file basename collision inventory (QM-08)."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path
from scripts.engineering.qa._tracked_glob import tracked_files

DEFAULT_OUTPUT = Path("reports/quality/test-basename-collision-inventory.json")


class BasenameInventory(TypedDict):
    duplicate_basename_count: int
    duplicate_basenames: dict[str, list[str]]


def build_inventory(root: Path) -> BasenameInventory:
    """Group existing indexed tests/**/*.py named test_*, with no lane exclusions."""
    root = root.resolve()
    groups: dict[str, list[str]] = defaultdict(list)
    for path in tracked_files(root, "tests/**/*.py"):
        if path.name.startswith("test_"):
            groups[path.name].append(path.relative_to(root).as_posix())
    duplicates = {
        name: sorted(paths) for name, paths in sorted(groups.items()) if len(paths) > 1
    }
    return {
        "duplicate_basename_count": len(duplicates),
        "duplicate_basenames": duplicates,
    }


def _write_atomic(path: Path, payload: bytes) -> None:
    """Replace only our output, and preserve its bytes/mtime when already current."""
    if path.is_file() and path.read_bytes() == payload:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)
    root = resolve_output_path(args.root, root=REPO_ROOT).resolve()
    output = resolve_output_path(args.json_out, root=root)
    rendered = (
        json.dumps(build_inventory(root), indent=2, sort_keys=True) + "\n"
    ).encode()
    if args.check:
        if not output.is_file() or output.read_bytes() != rendered:
            print(f"Basename inventory stale or missing: {output}; run --update")
            return 1
        print("Basename inventory is current")
        return 0
    _write_atomic(output, rendered)
    print(f"Wrote basename inventory: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
