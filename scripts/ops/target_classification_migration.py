"""Prepare, promote or roll back paired target tables under maintenance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationPaths,
    prepare_target_migration,
    promote_target_migration,
    rollback_target_migration,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "promote", "rollback"))
    parser.add_argument(
        "--plan",
        type=Path,
        required=True,
        help="JSON: explicit paths and frozen legacy_include_fields",
    )
    args = parser.parse_args()
    document = json.loads(args.plan.read_bytes())
    paths = TargetMigrationPaths(
        **{key: Path(value) for key, value in document["paths"].items()}
    )
    if args.action == "prepare":
        state = prepare_target_migration(
            paths,
            legacy_include_fields=tuple(document["legacy_include_fields"]),
        )
    elif args.action == "promote":
        state = promote_target_migration(paths)
    else:
        state = rollback_target_migration(paths)
    print(
        json.dumps(
            {"phase": state["phase"], "journal": str(paths.backup / "journal.json")}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
