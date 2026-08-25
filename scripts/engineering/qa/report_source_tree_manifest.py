#!/usr/bin/env python3
"""Write or check the unified source-tree manifest (S6 / #9602)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.engineering.common.repo_paths import resolve_output_path
from scripts.engineering.qa.report_module_coverage_inventory import (
    compute_source_tree_sha256,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "source-tree-manifest.json"


def build_manifest(*, repo_root: Path = PROJECT_ROOT) -> dict[str, object]:
    digest = compute_source_tree_sha256(repo_root=repo_root)
    return {
        "schema_version": 1,
        "linked_issue": "9602",
        "source_tree_sha256": digest,
        "generated_from_manifest": True,
    }


def write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = resolve_output_path(args.output)
    live = build_manifest()
    if args.check:
        if not output.exists():
            print(f"missing source-tree manifest: {output}", file=sys.stderr)
            return 1
        committed = json.loads(output.read_text(encoding="utf-8"))
        if committed.get("source_tree_sha256") != live["source_tree_sha256"]:
            print(
                "source-tree-manifest.json source_tree_sha256 is stale; "
                "run python -m scripts.engineering.qa report-source-tree-manifest",
                file=sys.stderr,
            )
            return 1
        print(f"source-tree manifest ok: {live['source_tree_sha256']}")
        return 0
    write_manifest(output, live)
    print(f"wrote {output} source_tree_sha256={live['source_tree_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
