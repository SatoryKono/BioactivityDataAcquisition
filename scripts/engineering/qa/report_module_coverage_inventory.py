#!/usr/bin/env python3
"""Generate a committed module-level coverage inventory from coverage XML."""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

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
    parser.add_argument(
        "--allow-missing-coverage-xml",
        action="store_true",
        help=(
            "Permit source-tree-only inventory checks when reports/coverage/coverage.xml "
            "has not been produced by the coverage-verify lane."
        ),
    )
    return parser.parse_args(argv)


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class _SourceModuleSnapshot:
    """Source-tree facts read once for row generation and drift hashing."""

    path: Path
    repo_path: str
    source_lines: int


def _read_source_module_snapshots(
    source_paths: list[Path],
    repo_root: Path,
) -> tuple[list[_SourceModuleSnapshot], str]:
    """Read source modules once and return row facts plus tree digest."""
    digest = hashlib.sha256()
    snapshots: list[_SourceModuleSnapshot] = []
    for path in source_paths:
        relative = _repo_relative(path, repo_root)
        raw_source = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(raw_source)
        digest.update(b"\0")
        snapshots.append(
            _SourceModuleSnapshot(
                path=path,
                repo_path=relative,
                source_lines=len(raw_source.decode("utf-8").splitlines()),
            )
        )
    return snapshots, digest.hexdigest()


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


def compute_source_tree_sha256(
    *,
    repo_root: Path = PROJECT_ROOT,
) -> str:
    """Return the committed source-tree digest without rebuilding full coverage rows."""
    repo_root = repo_root.resolve()
    source_paths = _iter_source_modules(repo_root)
    _, source_tree_sha256 = _read_source_module_snapshots(
        source_paths,
        repo_root,
    )
    return source_tree_sha256


def _coverage_source_roots(
    root: ET.Element,
    *,
    repo_root: Path,
    coverage_xml: Path,
) -> tuple[Path, ...]:
    source_roots: list[Path] = []
    sources_node = root.find("sources")
    if sources_node is None:
        return ()
    for source_node in sources_node.findall("source"):
        raw_value = str(source_node.text or "").strip()
        if not raw_value:
            continue
        source_path = Path(raw_value)
        if not source_path.is_absolute():
            repo_candidate = (repo_root / source_path).resolve()
            xml_candidate = (coverage_xml.parent / source_path).resolve()
            source_path = repo_candidate if repo_candidate.exists() else xml_candidate
        else:
            source_path = source_path.resolve()
        source_roots.append(source_path)
    return tuple(source_roots)


def _coverage_filename_to_repo_path(
    filename: str,
    *,
    repo_root: Path,
    source_roots: tuple[Path, ...],
) -> str | None:
    normalized = filename.replace("\\", "/")
    if normalized.startswith("src/bioetl/"):
        return normalized
    if normalized.startswith("bioetl/"):
        return f"src/{normalized}"
    for source_root in source_roots:
        candidate = (source_root / normalized).resolve()
        if not candidate.exists():
            continue
        try:
            return candidate.relative_to(repo_root).as_posix()
        except ValueError:
            continue
    return None


def _parse_coverage_xml(
    coverage_xml: Path,
    *,
    repo_root: Path,
) -> dict[str, dict[str, int]]:
    if not coverage_xml.exists():
        return {}

    root = ET.parse(coverage_xml).getroot()
    source_roots = _coverage_source_roots(
        root,
        repo_root=repo_root,
        coverage_xml=coverage_xml,
    )
    coverage_by_path: dict[str, dict[str, int]] = {}
    for class_node in root.iter("class"):
        filename = class_node.attrib.get("filename", "")
        repo_path = _coverage_filename_to_repo_path(
            filename,
            repo_root=repo_root,
            source_roots=source_roots,
        )
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


def _load_hotspot_family_prefixes(repo_root: Path) -> dict[str, tuple[str, ...]]:
    scorecard_path = repo_root / "configs" / "quality" / "debt_scorecard.yaml"
    payload = yaml.safe_load(scorecard_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    ratchets = payload.get("hotspot_family_ratchets", {})
    assert isinstance(ratchets, dict)
    families = ratchets.get("families", [])
    assert isinstance(families, list)
    family_prefixes: dict[str, tuple[str, ...]] = {}
    for family in families:
        if not isinstance(family, dict):
            continue
        name = family.get("name")
        prefixes = family.get("path_prefixes", [])
        if not isinstance(name, str) or not isinstance(prefixes, list):
            continue
        normalized_prefixes = tuple(
            prefix for prefix in prefixes if isinstance(prefix, str) and prefix
        )
        if normalized_prefixes:
            family_prefixes[name] = normalized_prefixes
    return family_prefixes


def _load_hotspot_family_thresholds(
    repo_root: Path,
) -> dict[str, dict[str, Any]]:
    scorecard_path = repo_root / "configs" / "quality" / "debt_scorecard.yaml"
    payload = yaml.safe_load(scorecard_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    threshold_payload = payload.get("hotspot_family_coverage_thresholds", {})
    assert isinstance(threshold_payload, dict)
    families = threshold_payload.get("families", {})
    assert isinstance(families, dict)
    thresholds: dict[str, dict[str, Any]] = {}
    for family_name, row in families.items():
        if not isinstance(family_name, str) or not isinstance(row, dict):
            continue
        numeric_thresholds = {
            key: value for key, value in row.items() if isinstance(value, int | float)
        }
        allowlisted_paths = tuple(
            str(path)
            for path in row.get("allowlisted_unmeasured_paths", [])
            if isinstance(path, str) and path
        )
        thresholds[family_name] = {
            **numeric_thresholds,
            "allowlisted_unmeasured_paths": allowlisted_paths,
        }
    return thresholds


def _status_is_measured(status: str) -> bool:
    return status in {
        "no_executable_lines",
        "uncovered",
        "fully_covered",
        "partially_covered",
    }


def _build_hotspot_family_coverage(
    rows: list[dict[str, Any]],
    *,
    repo_root: Path,
) -> dict[str, dict[str, Any]]:
    families = _load_hotspot_family_prefixes(repo_root)
    thresholds = _load_hotspot_family_thresholds(repo_root)
    family_coverage: dict[str, dict[str, Any]] = {}
    for family_name, prefixes in families.items():
        family_rows = [
            row
            for row in rows
            if any(str(row["path"]).startswith(prefix) for prefix in prefixes)
        ]
        measured_module_count = sum(
            1 for row in family_rows if _status_is_measured(str(row["coverage_status"]))
        )
        covered_module_count = sum(
            1
            for row in family_rows
            if str(row["coverage_status"]) in {"partially_covered", "fully_covered"}
        )
        unmeasured_module_count = sum(
            1 for row in family_rows if str(row["coverage_status"]) == "unmeasured"
        )
        family_thresholds = thresholds.get(family_name, {})
        allowlisted_unmeasured_paths = {
            str(path)
            for path in family_thresholds.get("allowlisted_unmeasured_paths", ())
            if isinstance(path, str)
        }
        allowlisted_unmeasured_modules = [
            str(row["path"])
            for row in family_rows
            if str(row["coverage_status"]) == "unmeasured"
            and str(row["path"]) in allowlisted_unmeasured_paths
        ]
        unexpected_unmeasured_modules = [
            str(row["path"])
            for row in family_rows
            if str(row["coverage_status"]) == "unmeasured"
            and str(row["path"]) not in allowlisted_unmeasured_paths
        ]
        executable_lines_total = sum(
            int(row["executable_lines"] or 0) for row in family_rows
        )
        covered_lines_total = sum(int(row["covered_lines"] or 0) for row in family_rows)
        coverage_percents = [
            float(row["coverage_percent"])
            for row in family_rows
            if row["coverage_percent"] is not None
        ]
        status_counts: dict[str, int] = {}
        for row in family_rows:
            status = str(row["coverage_status"])
            status_counts[status] = status_counts.get(status, 0) + 1
        covered_line_percent = (
            round(100.0 * covered_lines_total / executable_lines_total, 2)
            if executable_lines_total
            else None
        )
        threshold_status = "pass"
        if measured_module_count < int(
            family_thresholds.get("min_measured_module_count", measured_module_count)
        ):
            threshold_status = "fail"
        if len(unexpected_unmeasured_modules) > int(
            family_thresholds.get(
                "max_unmeasured_module_count",
                len(unexpected_unmeasured_modules),
            )
        ):
            threshold_status = "fail"
        if covered_module_count < int(
            family_thresholds.get("min_covered_module_count", covered_module_count)
        ):
            threshold_status = "fail"
        min_covered_line_percent = family_thresholds.get("min_covered_line_percent")
        if (
            isinstance(min_covered_line_percent, int | float)
            and covered_line_percent is not None
            and covered_line_percent < float(min_covered_line_percent)
        ):
            threshold_status = "fail"
        family_coverage[family_name] = {
            "module_count": len(family_rows),
            "measured_module_count": measured_module_count,
            "covered_module_count": covered_module_count,
            "unmeasured_module_count": unmeasured_module_count,
            "allowlisted_unmeasured_module_count": len(allowlisted_unmeasured_modules),
            "unexpected_unmeasured_module_count": len(unexpected_unmeasured_modules),
            "allowlisted_unmeasured_modules": sorted(allowlisted_unmeasured_modules),
            "unexpected_unmeasured_modules": sorted(unexpected_unmeasured_modules),
            "covered_line_percent": covered_line_percent,
            "measured_percent": (
                round(100.0 * measured_module_count / len(family_rows), 2)
                if family_rows
                else 100.0
            ),
            "coverage_percent_min": (
                round(min(coverage_percents), 2) if coverage_percents else None
            ),
            "coverage_percent_avg": (
                round(sum(coverage_percents) / len(coverage_percents), 2)
                if coverage_percents
                else None
            ),
            "status_counts": dict(sorted(status_counts.items())),
            "thresholds": family_thresholds,
            "threshold_status": threshold_status,
        }
    return family_coverage


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
    coverage_by_path = _parse_coverage_xml(coverage_xml, repo_root=repo_root)
    source_paths = _iter_source_modules(repo_root)
    source_snapshots, source_tree_sha256 = _read_source_module_snapshots(
        source_paths,
        repo_root,
    )
    rows: list[dict[str, Any]] = []

    for source_snapshot in source_snapshots:
        coverage_entry = coverage_by_path.get(source_snapshot.repo_path)
        status = _coverage_status(
            coverage_xml_exists=coverage_xml_exists,
            coverage_entry=coverage_entry,
        )
        rows.append(
            {
                "module": _module_name(source_snapshot.path, repo_root),
                "path": source_snapshot.repo_path,
                "source_lines": source_snapshot.source_lines,
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

    hotspot_family_coverage = _build_hotspot_family_coverage(rows, repo_root=repo_root)
    unmeasured_modules = [
        {
            "module": str(row["module"]),
            "path": str(row["path"]),
            "reason": "coverage_xml_has_no_class_entry",
        }
        for row in rows
        if str(row["coverage_status"]) == "unmeasured"
    ]

    return {
        "schema_version": 1,
        "snapshot_date": snapshot_date or date.today().isoformat(),
        "generated_by": "scripts/engineering/qa/report_module_coverage_inventory.py",
        "coverage_xml_path": _repo_relative(coverage_xml, repo_root),
        "coverage_xml_sha256": _sha256(coverage_xml),
        "measurement_mode": (
            "coverage_xml" if coverage_xml_exists else "source_tree_only"
        ),
        "source_tree_sha256": source_tree_sha256,
        "canonical_coverage_lane": "coverage-verify",
        "summary": {
            "source_module_count": len(rows),
            "coverage_xml_present": coverage_xml_exists,
            "status_counts": dict(sorted(status_counts.items())),
            "unmeasured_module_count": len(unmeasured_modules),
            "unmeasured_modules": unmeasured_modules,
            "hotspot_family_coverage": hotspot_family_coverage,
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

    if not args.coverage_xml.exists() and not args.allow_missing_coverage_xml:
        print(f"[module-coverage-inventory] missing coverage XML: {args.coverage_xml}")
        print(
            "[module-coverage-inventory] run the coverage-verify lane first, "
            "or pass --allow-missing-coverage-xml for source-tree-only drift checks"
        )
        return 1

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
