#!/usr/bin/env python3
"""Generate a committed module-level coverage inventory from coverage XML."""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

from scripts.engineering.qa.file_discovery import discover_files

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_COVERAGE_XML = PROJECT_ROOT / "reports" / "coverage" / "coverage.xml"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "module-coverage-inventory.json"
SOURCE_ROOT = PROJECT_ROOT / "src" / "bioetl"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--coverage-xml", type=Path, default=DEFAULT_COVERAGE_XML)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--snapshot-date", default=None)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_tree_sha256(source_paths: list[Path], repo_root: Path) -> str:
    digest = hashlib.sha256()
    for path in source_paths:
        relative = _repo_relative(path, repo_root)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _repo_relative(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _module_name(source_path: Path, repo_root: Path) -> str:
    relative = source_path.relative_to(repo_root / "src").with_suffix("")
    if relative.name == "__init__":
        relative = relative.parent
    return ".".join(relative.parts)


def _iter_source_modules(repo_root: Path) -> list[Path]:
    source_root = repo_root / "src" / "bioetl"
    return [
        source_root / relative_path
        for relative_path in discover_files(str(source_root.resolve()), ".py")
    ]


def _coverage_filename_to_repo_path(filename: str) -> str | None:
    normalized = filename.replace("\\", "/")
    if normalized.startswith("src/bioetl/"):
        return normalized
    if normalized.startswith("bioetl/"):
        return f"src/{normalized}"
    return None


def _parse_coverage_xml(coverage_xml: Path) -> dict[str, dict[str, int]]:
    if not coverage_xml.exists():
        return {}

    root = ET.parse(coverage_xml).getroot()
    coverage_by_path: dict[str, dict[str, int]] = {}
    for class_node in root.iter("class"):
        filename = class_node.attrib.get("filename", "")
        repo_path = _coverage_filename_to_repo_path(filename)
        if repo_path is None:
            continue

        executable = 0
        covered = 0
        for line_node in class_node.iter("line"):
            executable += 1
            if int(line_node.attrib.get("hits", "0")) > 0:
                covered += 1
        coverage_by_path[repo_path] = {
            "executable_lines": executable,
            "covered_lines": covered,
            "missing_lines": max(executable - covered, 0),
        }
    return coverage_by_path


def _coverage_status(
    *,
    coverage_xml_exists: bool,
    coverage_entry: dict[str, int] | None,
) -> str:
    if not coverage_xml_exists:
        return "coverage_xml_missing"
    if coverage_entry is None:
        return "unmeasured"
    executable_lines = coverage_entry["executable_lines"]
    covered_lines = coverage_entry["covered_lines"]
    missing_lines = coverage_entry["missing_lines"]
    if executable_lines == 0:
        return "no_executable_lines"
    if covered_lines == 0:
        return "uncovered"
    if missing_lines == 0:
        return "fully_covered"
    return "partially_covered"


def _coverage_percent(coverage_entry: dict[str, int] | None) -> float | None:
    if coverage_entry is None:
        return None
    executable_lines = coverage_entry["executable_lines"]
    if executable_lines == 0:
        return None
    return round(100.0 * coverage_entry["covered_lines"] / executable_lines, 2)


def build_module_coverage_inventory(
    *,
    repo_root: Path = PROJECT_ROOT,
    coverage_xml: Path = DEFAULT_COVERAGE_XML,
    snapshot_date: str | None = None,
) -> dict[str, Any]:
    """Build the module-level coverage inventory payload."""
    repo_root = repo_root.resolve()
    coverage_xml = coverage_xml.resolve()
    coverage_xml_exists = coverage_xml.exists()
    coverage_by_path = _parse_coverage_xml(coverage_xml)
    source_paths = _iter_source_modules(repo_root)
    rows: list[dict[str, Any]] = []

    for source_path in source_paths:
        repo_path = _repo_relative(source_path, repo_root)
        coverage_entry = coverage_by_path.get(repo_path)
        status = _coverage_status(
            coverage_xml_exists=coverage_xml_exists,
            coverage_entry=coverage_entry,
        )
        source_text = source_path.read_text(encoding="utf-8")
        rows.append(
            {
                "module": _module_name(source_path, repo_root),
                "path": repo_path,
                "source_lines": len(source_text.splitlines()),
                "coverage_status": status,
                "coverage_percent": _coverage_percent(coverage_entry),
                "executable_lines": (
                    coverage_entry["executable_lines"] if coverage_entry else None
                ),
                "covered_lines": (
                    coverage_entry["covered_lines"] if coverage_entry else None
                ),
                "missing_lines": (
                    coverage_entry["missing_lines"] if coverage_entry else None
                ),
            }
        )

    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["coverage_status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "schema_version": 1,
        "snapshot_date": snapshot_date or date.today().isoformat(),
        "generated_by": "scripts/engineering/qa/report_module_coverage_inventory.py",
        "coverage_xml_path": _repo_relative(coverage_xml, repo_root),
        "coverage_xml_sha256": _sha256(coverage_xml),
        "source_tree_sha256": _source_tree_sha256(source_paths, repo_root),
        "canonical_coverage_lane": "coverage-verify",
        "summary": {
            "source_module_count": len(rows),
            "coverage_xml_present": coverage_xml_exists,
            "status_counts": dict(sorted(status_counts.items())),
        },
        "modules": rows,
    }


def _payload_for_check(args: argparse.Namespace) -> dict[str, Any]:
    snapshot_date = args.snapshot_date
    if args.check and args.json_out.exists() and snapshot_date is None:
        current = json.loads(args.json_out.read_text(encoding="utf-8"))
        snapshot_date = str(current.get("snapshot_date") or date.today().isoformat())
    return build_module_coverage_inventory(
        repo_root=args.repo_root,
        coverage_xml=args.coverage_xml,
        snapshot_date=snapshot_date,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = _payload_for_check(args)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    if args.check:
        if not args.json_out.exists():
            print(f"[module-coverage-inventory] missing artifact: {args.json_out}")
            return 1
        current = args.json_out.read_text(encoding="utf-8")
        if current != rendered:
            print(f"[module-coverage-inventory] stale artifact: {args.json_out}")
            return 1
        print("[module-coverage-inventory] artifact is current")
        return 0

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(rendered, encoding="utf-8")
    print(
        "[module-coverage-inventory] "
        f"modules={payload['summary']['source_module_count']}; json={args.json_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
