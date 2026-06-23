#!/usr/bin/env python3
"""CI gate for deterministic Neo4j memory ontology invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.memory.sync import build_snapshot, snapshot_invariant_issues


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate deterministic Neo4j memory snapshot invariants.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_ROOT,
        help="Project root directory.",
    )
    parser.add_argument(
        "--verified-at",
        type=str,
        default="2026-04-09",
        help="Stable verification date for deterministic snapshots in CI.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    snapshot = build_snapshot(args.root.resolve(), verified_at=args.verified_at)
    issues = snapshot_invariant_issues(snapshot)
    payload = {
        "snapshot": snapshot.stats(),
        "issues": issues,
    }
    print(json.dumps(payload, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
