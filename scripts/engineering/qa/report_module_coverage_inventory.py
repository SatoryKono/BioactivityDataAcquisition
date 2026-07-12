#!/usr/bin/env python3
"""Generate a committed module-level coverage inventory from coverage XML."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import time
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
DEFAULT_GATES_CONFIG = (
    PROJECT_ROOT / "configs" / "quality" / "module_coverage_gates.yaml"
)
SOURCE_ROOT = PROJECT_ROOT / "src" / "bioetl"
ENFORCEMENT_MODES = frozenset({"off", "warn", "block-regression", "block-all"})
COVERAGE_STATUSES = (
    "coverage_xml_missing",
    "fully_covered",
    "no_executable_lines",
    "partially_covered",
    "uncovered",
    "unmeasured",
)
# Shared-drive worktrees can return one transient digest immediately after local
# edits; prefer a repeated digest before declaring the source-tree hash current.
DEFAULT_SOURCE_TREE_STABILIZATION_ATTEMPTS = 5
DEFAULT_SOURCE_TREE_STABILIZATION_SLEEP_SECONDS = 0.1
MOUNTED_SOURCE_TREE_STABILIZATION_ATTEMPTS = 12
MOUNTED_SOURCE_TREE_STABILIZATION_SLEEP_SECONDS = 0.25


def _write_text_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--coverage-xml", type=Path, default=DEFAULT_COVERAGE_XML)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--snapshot-date", default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--refresh-from-coverage-xml",
        action="store_true",
        help=(
            "Rebuild an existing committed inventory from --coverage-xml. "
            "Use only in the canonical coverage-verify lane after producing fresh XML; "
            "local drift checks preserve existing rows and refresh only source_tree_sha256."
        ),
    )
    parser.add_argument(
        "--allow-missing-coverage-xml",
        action="store_true",
        help=(
            "Permit source-tree-only inventory checks when reports/coverage/coverage.xml "
            "has not been produced by the coverage-verify lane."
        ),
    )
    parser.add_argument(
        "--enforce-module-thresholds",
        choices=sorted(ENFORCEMENT_MODES),
        default="off",
        help=(
            "Enforce per-module coverage tiers and/or regressions. "
            "block-regression fails when line coverage decreases vs baseline; "
            "block-all also fails tier threshold gaps."
        ),
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help=(
            "Alias for --enforce-module-thresholds=block-regression when enforcement is off."
        ),
    )
    parser.add_argument(
        "--baseline-json",
        type=Path,
        default=None,
        help=(
            "Committed inventory baseline for regression checks "
            "(defaults to --json-out when enforcing regressions)."
        ),
    )
    parser.add_argument(
        "--gates-config",
        type=Path,
        default=DEFAULT_GATES_CONFIG,
        help="YAML policy for tier thresholds, exemptions, and enforcement modes.",
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
    declaration_only: bool


def _module_is_declaration_only(source_text: str) -> bool:
    """Return True when a module contains only declarations/type-only scaffolding."""
    try:
        module = ast.parse(source_text)
    except SyntaxError:
        return False
    return all(_statement_is_declaration_only(node) for node in module.body)


def _statement_is_declaration_only(node: ast.stmt) -> bool:
    """Identify statements that do not contribute runtime behavior worth covering."""
    if isinstance(node, ast.Expr):
        return isinstance(getattr(node, "value", None), ast.Constant) and isinstance(
            getattr(node.value, "value", None), str
        )
    if isinstance(node, (ast.Import, ast.ImportFrom, ast.Pass)):
        return True
    if isinstance(node, ast.AnnAssign):
        return True
    if isinstance(node, ast.Assign):
        return _assign_targets_are_declaration_only(node.targets)
    if isinstance(node, ast.If):
        return _if_is_type_checking_only(node)
    if isinstance(node, ast.ClassDef):
        return all(_statement_is_declaration_only(child) for child in node.body)
    return False


def _assign_targets_are_declaration_only(targets: list[ast.expr]) -> bool:
    """Allow sentinel export/slot assignments in declaration-only modules."""
    allowed_names = {"__all__", "__slots__"}
    return all(
        isinstance(target, ast.Name) and target.id in allowed_names
        for target in targets
    )


def _if_is_type_checking_only(node: ast.If) -> bool:
    """Return True when an if-block is guarded only by TYPE_CHECKING."""
    test = node.test
    is_type_checking_guard = isinstance(test, ast.Name) and test.id == "TYPE_CHECKING"
    if not is_type_checking_guard:
        return False
    return all(
        _statement_is_declaration_only(child) for child in node.body + node.orelse
    )


def _read_source_module_snapshots(
    source_paths: list[Path],
    repo_root: Path,
) -> tuple[list[_SourceModuleSnapshot], str]:
    """Read source modules once and return row facts plus tree digest."""
    digest = hashlib.sha256()
    snapshots: list[_SourceModuleSnapshot] = []
    for path in source_paths:
        if not path.exists():
            continue
        relative = _repo_relative(path, repo_root)
        try:
            raw_source = path.read_bytes()
        except FileNotFoundError:
            # Shared-drive worktrees can briefly report a stale path as present and
            # then fail on open a few milliseconds later. Skip the vanished file so
            # the inventory reflects the readable source tree instead of flaking.
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(raw_source)
        digest.update(b"\0")
        source_text = raw_source.decode("utf-8")
        snapshots.append(
            _SourceModuleSnapshot(
                path=path,
                repo_path=relative,
                source_lines=len(source_text.splitlines()),
                declaration_only=_module_is_declaration_only(source_text),
            )
        )
    return snapshots, digest.hexdigest()


def _read_source_module_content_digest(
    source_paths: list[Path],
    repo_root: Path,
) -> str:
    """Hash current source-tree paths and file contents."""
    digest = hashlib.sha256()
    for path in source_paths:
        if not path.exists():
            continue
        relative = _repo_relative(path, repo_root)
        try:
            raw_source = path.read_bytes()
        except FileNotFoundError:
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(raw_source)
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
        for relative_path in sorted(discover_files(str(source_root.resolve()), ".py"))
    ]


def _source_tree_stabilization_profile(
    repo_root: Path,
) -> tuple[int, float]:
    """Use longer read windows on mounted/shared-drive worktrees."""
    normalized_root = str(repo_root.resolve()).replace("\\", "/").lower()
    if "/mnt/" in normalized_root or "g-drive" in normalized_root:
        return (
            MOUNTED_SOURCE_TREE_STABILIZATION_ATTEMPTS,
            MOUNTED_SOURCE_TREE_STABILIZATION_SLEEP_SECONDS,
        )
    return (
        DEFAULT_SOURCE_TREE_STABILIZATION_ATTEMPTS,
        DEFAULT_SOURCE_TREE_STABILIZATION_SLEEP_SECONDS,
    )


def _read_stable_source_module_snapshots(
    repo_root: Path,
    *,
    max_attempts: int | None = None,
    sleep_seconds: float | None = None,
) -> tuple[list[_SourceModuleSnapshot], str]:
    """Retry source-tree reads until two consecutive snapshots agree."""
    profile_attempts, profile_sleep = _source_tree_stabilization_profile(repo_root)
    attempts = max_attempts if max_attempts is not None else profile_attempts
    pause_seconds = sleep_seconds if sleep_seconds is not None else profile_sleep
    best_digest: str | None = None
    best_paths: tuple[str, ...] = ()
    best_snapshots: list[_SourceModuleSnapshot] | None = None
    peak_module_count = 0
    stable_at_peak_reads = 0
    previous_digest: str | None = None
    previous_paths: tuple[str, ...] | None = None

    for attempt in range(attempts):
        source_paths = _iter_source_modules(repo_root)
        snapshots, digest = _read_source_module_snapshots(
            source_paths,
            repo_root,
        )
        repo_paths = tuple(snapshot.repo_path for snapshot in snapshots)
        if best_snapshots is None or len(repo_paths) > len(best_paths):
            best_digest = digest
            best_paths = repo_paths
            best_snapshots = snapshots
        if len(repo_paths) > peak_module_count:
            peak_module_count = len(repo_paths)
            stable_at_peak_reads = 0
        elif (
            previous_digest is not None
            and digest == previous_digest
            and repo_paths == previous_paths
            and len(repo_paths) == peak_module_count
        ):
            stable_at_peak_reads += 1
            if stable_at_peak_reads >= 1:
                return snapshots, digest
        else:
            stable_at_peak_reads = 0
        previous_digest = digest
        previous_paths = repo_paths
        if attempt + 1 < attempts:
            time.sleep(pause_seconds)

    if best_snapshots is None or best_digest is None:
        return [], hashlib.sha256().hexdigest()
    return best_snapshots, best_digest


def compute_source_tree_sha256(
    *,
    repo_root: Path = PROJECT_ROOT,
) -> str:
    """Return the current source-tree digest for verification paths.

    The digest intentionally uses repo-relative paths and file contents only.
    Shared-drive metadata such as ``mtime_ns`` can drift without a source
    change and must not affect release-governance freshness.
    """
    repo_root = repo_root.resolve()
    _, source_tree_sha256 = _read_stable_source_module_snapshots(repo_root)
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


def _coverage_status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    status_counts = dict.fromkeys(COVERAGE_STATUSES, 0)
    for row in rows:
        status = str(row["coverage_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    return dict(sorted(status_counts.items()))


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
        status_counts = _coverage_status_counts(family_rows)
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
            "status_counts": status_counts,
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
    source_snapshots, source_tree_sha256 = _read_stable_source_module_snapshots(
        repo_root,
    )
    rows: list[dict[str, Any]] = []

    for source_snapshot in source_snapshots:
        coverage_entry = coverage_by_path.get(source_snapshot.repo_path)
        if (
            coverage_entry is None
            and coverage_xml_exists
            and source_snapshot.declaration_only
        ):
            coverage_entry = {
                "executable_lines": 0,
                "covered_lines": 0,
                "missing_lines": 0,
            }
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

    status_counts = _coverage_status_counts(rows)

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
    uncovered_modules = [
        {
            "module": str(row["module"]),
            "path": str(row["path"]),
            "reason": "coverage_xml_reports_zero_executed_lines",
        }
        for row in rows
        if str(row["coverage_status"]) == "uncovered"
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
            "status_counts": status_counts,
            "unmeasured_module_count": len(unmeasured_modules),
            "unmeasured_modules": unmeasured_modules,
            "uncovered_module_count": len(uncovered_modules),
            "uncovered_modules": uncovered_modules,
            "hotspot_family_coverage": hotspot_family_coverage,
        },
        "modules": rows,
        "rows": rows,
    }


def _load_module_coverage_gates(repo_root: Path, gates_config: Path) -> dict[str, Any]:
    path = gates_config if gates_config.is_absolute() else repo_root / gates_config
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid module coverage gates config: {path}")
    return payload


def _resolve_enforcement_mode(args: argparse.Namespace) -> str:
    mode = str(args.enforce_module_thresholds)
    if mode == "off" and args.fail_on_regression:
        return "block-regression"
    return mode


def _exempt_paths(gates: dict[str, Any]) -> frozenset[str]:
    exemptions = gates.get("exemptions", [])
    if not isinstance(exemptions, list):
        return frozenset()
    paths: set[str] = set()
    for entry in exemptions:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if isinstance(path, str) and path:
            paths.add(path)
    return frozenset(paths)


def _resolve_module_tier(
    repo_path: str,
    *,
    gates: dict[str, Any],
) -> tuple[str, float]:
    tiers = gates.get("tiers", {})
    if not isinstance(tiers, dict):
        return "default_module", 85.0
    order = gates.get("tier_resolution_order", [])
    if not isinstance(order, list):
        order = list(tiers.keys())
    for tier_name in order:
        if not isinstance(tier_name, str):
            continue
        tier = tiers.get(tier_name, {})
        if not isinstance(tier, dict):
            continue
        prefixes = tier.get("path_prefixes", [])
        if not isinstance(prefixes, list):
            prefixes = []
        if any(
            repo_path.startswith(prefix)
            for prefix in prefixes
            if isinstance(prefix, str)
        ):
            line_min = tier.get("line_min_percent", 85)
            if isinstance(line_min, int | float):
                return tier_name, float(line_min)
    default = tiers.get("default_module", {})
    if isinstance(default, dict):
        line_min = default.get("line_min_percent", 85)
        if isinstance(line_min, int | float):
            return "default_module", float(line_min)
    return "default_module", 85.0


def _baseline_coverage_by_path(baseline_payload: dict[str, Any]) -> dict[str, float]:
    baseline_rows = baseline_payload.get("modules", [])
    if not isinstance(baseline_rows, list):
        return {}
    baseline: dict[str, float] = {}
    for row in baseline_rows:
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        coverage_percent = row.get("coverage_percent")
        if isinstance(path, str) and isinstance(coverage_percent, int | float):
            baseline[path] = float(coverage_percent)
    return baseline


@dataclass(frozen=True, slots=True)
class _ModuleCoverageViolation:
    path: str
    kind: str
    tier: str
    current_percent: float | None
    baseline_percent: float | None
    required_percent: float | None
    message: str


def evaluate_module_coverage_gates(
    payload: dict[str, Any],
    *,
    baseline_payload: dict[str, Any],
    gates: dict[str, Any],
    enforcement_mode: str,
) -> list[_ModuleCoverageViolation]:
    """Return tier/regression violations for the supplied inventory payload."""
    if enforcement_mode == "off":
        return []

    rows = payload.get("modules", [])
    if not isinstance(rows, list):
        return []

    exempt = _exempt_paths(gates)
    regression_cfg = gates.get("regression", {})
    min_delta = 0.01
    if isinstance(regression_cfg, dict):
        raw_delta = regression_cfg.get("min_delta_points", min_delta)
        if isinstance(raw_delta, int | float):
            min_delta = float(raw_delta)

    enforcement_cfg = gates.get("enforcement", {})
    tier_mode = "warn"
    ranked_target_tier_mode = "warn"
    if isinstance(enforcement_cfg, dict):
        raw_tier_mode = enforcement_cfg.get("tier_violation_mode", tier_mode)
        if isinstance(raw_tier_mode, str):
            tier_mode = raw_tier_mode
        raw_ranked_target_tier_mode = enforcement_cfg.get(
            "ranked_target_tier_violation_mode",
            ranked_target_tier_mode,
        )
        if isinstance(raw_ranked_target_tier_mode, str):
            ranked_target_tier_mode = raw_ranked_target_tier_mode

    ranked_target_paths: set[str] = set()
    coverage_tail_cfg = gates.get("coverage_tail", {})
    if isinstance(coverage_tail_cfg, dict):
        ranked_targets = coverage_tail_cfg.get("ranked_targets", [])
        if isinstance(ranked_targets, list):
            for row in ranked_targets:
                if not isinstance(row, dict):
                    continue
                path = row.get("path")
                if isinstance(path, str) and path:
                    ranked_target_paths.add(path)

    baseline_by_path = _baseline_coverage_by_path(baseline_payload)
    violations: list[_ModuleCoverageViolation] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path", ""))
        if not path or path in exempt:
            continue
        status = str(row.get("coverage_status", ""))
        if status not in {"partially_covered", "fully_covered"}:
            continue
        current = row.get("coverage_percent")
        current_percent = float(current) if isinstance(current, int | float) else None
        if current_percent is None:
            continue

        baseline_percent = baseline_by_path.get(path)
        if (
            baseline_percent is not None
            and current_percent + min_delta < baseline_percent
        ):
            violations.append(
                _ModuleCoverageViolation(
                    path=path,
                    kind="regression",
                    tier="regression",
                    current_percent=current_percent,
                    baseline_percent=baseline_percent,
                    required_percent=baseline_percent,
                    message=(
                        f"{path}: coverage regressed "
                        f"{baseline_percent:.2f}% -> {current_percent:.2f}%"
                    ),
                )
            )

        tier_name, required_percent = _resolve_module_tier(path, gates=gates)
        if current_percent + min_delta < required_percent:
            violations.append(
                _ModuleCoverageViolation(
                    path=path,
                    kind="tier",
                    tier=tier_name,
                    current_percent=current_percent,
                    baseline_percent=baseline_percent,
                    required_percent=required_percent,
                    message=(
                        f"{path}: {tier_name} tier requires >= {required_percent:.2f}% "
                        f"(current {current_percent:.2f}%)"
                    ),
                )
            )

    if enforcement_mode == "block-regression":
        return [
            violation
            for violation in violations
            if violation.kind == "regression"
            or (
                violation.kind == "tier"
                and violation.path in ranked_target_paths
                and ranked_target_tier_mode == "block"
            )
        ]
    if enforcement_mode == "warn" and tier_mode != "warn":
        return violations
    return violations


def _report_gate_violations(
    violations: list[_ModuleCoverageViolation],
    *,
    enforcement_mode: str,
) -> int:
    if not violations:
        print("[module-coverage-inventory] module coverage gates: pass")
        return 0

    regressions = [v for v in violations if v.kind == "regression"]
    tiers = [v for v in violations if v.kind == "tier"]
    print(
        "[module-coverage-inventory] module coverage gates: "
        f"mode={enforcement_mode}; regressions={len(regressions)}; tier_gaps={len(tiers)}"
    )
    for violation in violations[:25]:
        print(f"  - {violation.message}")
    if len(violations) > 25:
        print(f"  - ... and {len(violations) - 25} more")

    if enforcement_mode == "block-regression" and regressions:
        return 1
    if enforcement_mode == "block-all" and (regressions or tiers):
        return 1
    return 0


def _source_tree_only_row(
    source_snapshot: _SourceModuleSnapshot, repo_root: Path
) -> dict[str, Any]:
    return {
        "module": _module_name(source_snapshot.path, repo_root),
        "path": source_snapshot.repo_path,
        "source_lines": source_snapshot.source_lines,
        "coverage_status": "no_executable_lines",
        "coverage_percent": None,
        "executable_lines": 0,
        "covered_lines": 0,
        "missing_lines": 0,
    }


def _refresh_existing_inventory_source_tree(
    payload: dict[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    source_snapshots, source_tree_sha256 = _read_stable_source_module_snapshots(
        repo_root
    )
    rows = payload.get("modules", [])
    rows_by_path = {
        str(row.get("path")): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }

    refreshed_rows: list[dict[str, Any]] = []
    for source_snapshot in source_snapshots:
        existing = rows_by_path.get(source_snapshot.repo_path)
        row = (
            dict(existing)
            if existing is not None
            else _source_tree_only_row(source_snapshot, repo_root)
        )
        row["module"] = _module_name(source_snapshot.path, repo_root)
        row["path"] = source_snapshot.repo_path
        row["source_lines"] = source_snapshot.source_lines
        refreshed_rows.append(row)

    status_counts = _coverage_status_counts(refreshed_rows)
    unmeasured_modules = [
        {
            "module": str(row["module"]),
            "path": str(row["path"]),
            "reason": "coverage_xml_has_no_class_entry",
        }
        for row in refreshed_rows
        if str(row["coverage_status"]) == "unmeasured"
    ]
    uncovered_modules = [
        {
            "module": str(row["module"]),
            "path": str(row["path"]),
            "reason": "coverage_xml_reports_zero_executed_lines",
        }
        for row in refreshed_rows
        if str(row["coverage_status"]) == "uncovered"
    ]

    refreshed = dict(payload)
    summary = dict(refreshed.get("summary", {}))
    summary.update(
        {
            "source_module_count": len(refreshed_rows),
            "status_counts": status_counts,
            "unmeasured_module_count": len(unmeasured_modules),
            "unmeasured_modules": unmeasured_modules,
            "uncovered_module_count": len(uncovered_modules),
            "uncovered_modules": uncovered_modules,
            "hotspot_family_coverage": _build_hotspot_family_coverage(
                refreshed_rows,
                repo_root=repo_root,
            ),
        }
    )
    refreshed["modules"] = refreshed_rows
    refreshed["rows"] = refreshed_rows
    refreshed["summary"] = summary
    refreshed["source_tree_sha256"] = source_tree_sha256
    return refreshed


def _payload_for_check(args: argparse.Namespace) -> dict[str, Any]:
    if args.json_out.exists() and not args.refresh_from_coverage_xml:
        current = json.loads(args.json_out.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            raise ValueError(f"Invalid module coverage inventory: {args.json_out}")
        return _refresh_existing_inventory_source_tree(
            current, repo_root=args.repo_root
        )

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
    repo_root = args.repo_root.resolve()
    enforcement_mode = _resolve_enforcement_mode(args)

    if not args.coverage_xml.exists() and not args.allow_missing_coverage_xml:
        print(f"[module-coverage-inventory] missing coverage XML: {args.coverage_xml}")
        print(
            "[module-coverage-inventory] run the coverage-verify lane first, "
            "or pass --allow-missing-coverage-xml for source-tree-only drift checks"
        )
        return 1

    payload = _payload_for_check(args)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    gate_exit = 0
    if enforcement_mode != "off":
        baseline_path = args.baseline_json or args.json_out
        if not baseline_path.exists():
            print(
                f"[module-coverage-inventory] missing baseline inventory: {baseline_path}"
            )
            return 1
        baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
        gates = _load_module_coverage_gates(repo_root, args.gates_config)
        violations = evaluate_module_coverage_gates(
            payload,
            baseline_payload=baseline_payload,
            gates=gates,
            enforcement_mode=enforcement_mode,
        )
        gate_exit = _report_gate_violations(
            violations,
            enforcement_mode=enforcement_mode,
        )

    if args.check:
        if not args.json_out.exists():
            print(f"[module-coverage-inventory] missing artifact: {args.json_out}")
            return 1
        current = args.json_out.read_text(encoding="utf-8")
        if current != rendered:
            print(f"[module-coverage-inventory] stale artifact: {args.json_out}")
            return 1
        print("[module-coverage-inventory] artifact is current")
        return gate_exit

    _write_text_atomically(args.json_out, rendered)
    print(
        "[module-coverage-inventory] "
        f"modules={payload['summary']['source_module_count']}; json={args.json_out}"
    )
    return gate_exit


if __name__ == "__main__":
    raise SystemExit(main())
