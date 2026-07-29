"""CLI for dry-run-first JSON memory schema migration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from memory.migrations import migrate_json_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--target-version", type=int, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply migration; default behavior is a read-only dry-run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the migration CLI."""
    args = _build_parser().parse_args(argv)
    result = migrate_json_file(
        args.path,
        target_version=args.target_version,
        apply=args.apply,
    )
    print(
        json.dumps(
            {
                "path": str(result.path),
                "from_version": result.from_version,
                "to_version": result.to_version,
                "applied": result.applied,
                "changed": result.changed,
                "original_digest": result.original_digest,
                "migrated_digest": result.migrated_digest,
                "preserved_original": (
                    str(result.preserved_original)
                    if result.preserved_original is not None
                    else None
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
