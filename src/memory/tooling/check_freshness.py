"""Fail-closed freshness gate for repository-owned memory surfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from memory.resources import discover_repo_root
from memory.tooling.review_curated import review_curated_notes
from memory.validation import validate_memory_scaffold


def check_memory_freshness(repo_root: Path) -> dict[str, Any]:
    """Return deterministic checks for canonical, curated, graph, and MCP memory."""
    memory_root = repo_root / "src" / "memory"
    scaffold_issues = validate_memory_scaffold()
    curated = review_curated_notes(memory_root / "curated")
    checks: list[dict[str, Any]] = [
        {
            "surface": "project-catalog",
            "ok": not scaffold_issues,
            "details": [f"{issue.path}: {issue.message}" for issue in scaffold_issues],
        },
        {
            "surface": "curated-memory",
            "ok": curated["summary"]["stale_count"] == 0,
            "details": curated["summary"],
        },
    ]

    graph_details: list[str] = []
    for name in ("ontology.yaml", "mappings.yaml"):
        path = memory_root / "graph" / name
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                graph_details.append(f"{path}: root must be a mapping")
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            graph_details.append(f"{path}: {exc}")
    checks.append(
        {"surface": "knowledge-graph", "ok": not graph_details, "details": graph_details}
    )

    seed = repo_root / "docs/00-project/ai/memory/mcp-memory.json"
    seed_details: list[str] = []
    try:
        payload = json.loads(seed.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not {"entities", "relations"} <= payload.keys():
            seed_details.append("seed must contain entities and relations")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        seed_details.append(str(exc))
    checks.append(
        {"surface": "mcp-seed", "ok": not seed_details, "details": seed_details}
    )
    return {"ok": all(check["ok"] for check in checks), "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    repo_root = args.repo_root or discover_repo_root()
    if repo_root is None:
        parser.error("repository root not found")
    report = check_memory_freshness(repo_root.resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for check in report["checks"]:
            print(f"{check['surface']}: {'PASS' if check['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
