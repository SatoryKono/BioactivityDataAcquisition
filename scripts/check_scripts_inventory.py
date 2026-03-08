#!/usr/bin/env python3
"""Generate and validate scripts inventory metadata.

This tool inventories script entrypoints in:
- scripts/**
- src/tools/**

It classifies each script by discovered call-sites and can:
- update a committed manifest (`--update`)
- verify drift against a manifest (`--check`)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

SCRIPT_EXTENSIONS: Final[tuple[str, ...]] = (".py", ".sh", ".ps1", ".cmd", ".bat")
SCRIPT_ROOTS: Final[tuple[str, ...]] = ("scripts", "src/tools")
SEARCH_ROOTS: Final[tuple[str, ...]] = (
    "AGENTS.md",
    ".codex/skills",
    ".github/workflows",
    "pyproject.toml",
    "Makefile",
    "makefile",
    "docs",
    "tests",
    "scripts",
    "src/tools",
)
MANIFEST_DEFAULT: Final[str] = "reports/quality/scripts_inventory_manifest.json"
SCHEMA_VERSION: Final[str] = "1.0"


@dataclass(frozen=True)
class RefEvidence:
    """Reference evidence item for a script."""

    path: str
    line: int
    text: str
    source_group: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_scripts(root: Path) -> list[Path]:
    scripts: list[Path] = []
    for rel_root in SCRIPT_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        for file_path in base.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in SCRIPT_EXTENSIONS:
                continue
            scripts.append(file_path)
    return sorted(set(scripts))


def _iter_search_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in SEARCH_ROOTS:
        path = root / rel
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            if ".git" in file_path.parts:
                continue
            files.append(file_path)
    return files


def _source_group(rel_path: str) -> str:
    if rel_path.startswith(".github/workflows/"):
        return "ci"
    if rel_path.startswith(".codex/skills/"):
        return "skills"
    if rel_path in {"Makefile", "makefile", "pyproject.toml"}:
        return "build"
    if rel_path.startswith("tests/"):
        return "tests"
    if rel_path.startswith("docs/"):
        return "docs"
    if rel_path == "AGENTS.md":
        return "agents"
    if rel_path.startswith("scripts/") or rel_path.startswith("src/tools/"):
        return "scripts"
    return "other"


def _discover_refs(root: Path, scripts: list[Path]) -> dict[str, list[RefEvidence]]:
    rel_scripts = [path.relative_to(root).as_posix() for path in scripts]
    refs: dict[str, list[RefEvidence]] = {item: [] for item in rel_scripts}
    search_files = _iter_search_files(root)
    pattern = re.compile("|".join(re.escape(item) for item in rel_scripts))

    for file_path in search_files:
        rel = file_path.relative_to(root).as_posix()
        try:
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            for match in pattern.finditer(line):
                script_rel = match.group(0)
                if rel == script_rel:
                    continue
                refs[script_rel].append(
                    RefEvidence(
                        path=rel,
                        line=line_no,
                        text=line.strip()[:200],
                        source_group=_source_group(rel),
                    )
                )
    return refs


def _dedupe_refs(refs: list[RefEvidence]) -> list[RefEvidence]:
    seen: set[tuple[str, int, str]] = set()
    result: list[RefEvidence] = []
    for item in refs:
        key = (item.path, item.line, item.text)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _status_for(script_rel: str, refs: list[RefEvidence]) -> str:
    if not refs:
        return "legacy" if ("_tmp" in script_rel or "debug_" in script_rel) else "orphan"

    groups = {item.source_group for item in refs}
    if groups & {"ci", "build", "skills", "tests", "scripts", "agents"}:
        return "active"
    if groups == {"docs"}:
        return "unknown"
    return "unknown"


def _agent_usage(refs: list[RefEvidence]) -> list[str]:
    usages: set[str] = set()
    for item in refs:
        if not item.path.startswith(".codex/skills/"):
            continue
        parts = item.path.split("/")
        if len(parts) >= 4:
            usages.add(parts[2])
    return sorted(usages)


def _build_inventory(root: Path) -> dict[str, object]:
    scripts = _iter_scripts(root)
    refs_map = _discover_refs(root, scripts)
    rows: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()

    for script in scripts:
        script_rel = script.relative_to(root).as_posix()
        refs = _dedupe_refs(refs_map[script_rel])
        status = _status_for(script_rel, refs)
        status_counts[status] += 1
        for group in {item.source_group for item in refs}:
            group_counts[group] += 1

        rows.append(
            {
                "path": script_rel,
                "type": script.suffix.lstrip("."),
                "status": status,
                "agent_usage": _agent_usage(refs),
                "reference_count": len(refs),
                "references": [
                    {
                        "path": item.path,
                        "line": item.line,
                        "source_group": item.source_group,
                        "text": item.text,
                    }
                    for item in refs[:8]
                ],
            }
        )

    rows.sort(key=lambda item: str(item["path"]))
    summary = {
        "total_scripts": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "reference_group_coverage": dict(sorted(group_counts.items())),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "scripts": rows,
    }


def _stable_manifest(data: dict[str, object]) -> dict[str, object]:
    normalized = dict(data)
    normalized.pop("generated_at", None)
    return normalized


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _check(manifest_path: Path, actual: dict[str, object]) -> int:
    if not manifest_path.exists():
        print(f"[FAIL] Manifest not found: {manifest_path}")
        print("Run with --update to create baseline manifest.")
        return 1

    expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    if _stable_manifest(expected) == _stable_manifest(actual):
        print(f"[OK] Scripts inventory is in sync: {manifest_path}")
        return 0

    print(f"[FAIL] Scripts inventory drift detected: {manifest_path}")
    print("Run with --update to refresh manifest.")
    return 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scripts inventory drift checker")
    parser.add_argument(
        "--manifest",
        default=MANIFEST_DEFAULT,
        help="Path to inventory manifest JSON",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print generated inventory JSON to stdout",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write/update manifest file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate current inventory against manifest file",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = _project_root()
    manifest_path = root / args.manifest
    payload = _build_inventory(root)

    if args.update:
        _write_manifest(manifest_path, payload)
        print(f"[OK] Updated scripts inventory manifest: {manifest_path}")

    if args.check:
        result = _check(manifest_path, payload)
        if result != 0:
            return result

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        summary = payload["summary"]
        print(
            "[INFO] scripts={total} active={active} unknown={unknown} orphan={orphan} legacy={legacy}".format(
                total=summary["total_scripts"],
                active=summary["status_counts"].get("active", 0),
                unknown=summary["status_counts"].get("unknown", 0),
                orphan=summary["status_counts"].get("orphan", 0),
                legacy=summary["status_counts"].get("legacy", 0),
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
