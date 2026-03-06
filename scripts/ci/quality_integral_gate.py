#!/usr/bin/env python3
"""CI quality metrics aggregation + integral score gate.

This script computes a compact quality snapshot, writes JSON artifact, and
fails the run when adjusted integral score is below the active quarter target.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from bioetl.infrastructure.quality.debt_scorecard import (
    evaluate_debt_scorecard,
    load_debt_scorecard,
)
from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry
from bioetl.infrastructure.quality.inventory import build_exemption_inventory


@dataclass(frozen=True)
class ArchitectureTestStats:
    """Parsed architecture test counters."""

    tests: int
    failures: int
    errors: int
    skipped: int
    returncode: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute CI quality metrics, write JSON report, and enforce "
            "integral-score merge gate."
        )
    )
    parser.add_argument(
        "--registry",
        default="configs/quality/architecture_metric_exemptions.yaml",
        help="Path to exemption registry YAML.",
    )
    parser.add_argument(
        "--scorecard",
        default="configs/quality/debt_scorecard.yaml",
        help="Path to debt scorecard YAML.",
    )
    parser.add_argument(
        "--src-root",
        default="src/bioetl",
        help="Source root for class LOC scan.",
    )
    parser.add_argument(
        "--architecture-tests",
        default="tests/architecture",
        help="Architecture tests path passed to pytest.",
    )
    parser.add_argument(
        "--vcr-root",
        default="tests/fixtures/vcr",
        help="Root directory containing provider VCR cassettes.",
    )
    parser.add_argument(
        "--coverage-xml",
        default="coverage.xml",
        help="Coverage XML file path (optional).",
    )
    parser.add_argument(
        "--output",
        default="reports/quality/ci-quality-metrics.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=85.0,
        help="Coverage threshold for verified bonus.",
    )
    parser.add_argument(
        "--max-class-loc-target",
        type=int,
        default=300,
        help="Target maximum class LOC.",
    )
    parser.add_argument(
        "--vcr-min-per-provider-target",
        type=int,
        default=20,
        help="Target minimum cassette count per provider.",
    )
    return parser.parse_args()


def _resolve_ruff_cmd() -> list[str]:
    root = Path.cwd()
    local_candidates = [
        root / ".venv" / "Scripts" / "ruff.exe",
        root / ".venv" / "bin" / "ruff",
    ]
    for candidate in local_candidates:
        if candidate.exists():
            return [str(candidate)]
    return [sys.executable, "-m", "ruff"]


def _run_architecture_tests(pytest_path: str) -> ArchitectureTestStats:
    with tempfile.TemporaryDirectory(prefix="quality-arch-") as tmp_dir:
        junit_path = Path(tmp_dir) / "architecture.junit.xml"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            pytest_path,
            "-q",
            "--tb=no",
            f"--junitxml={junit_path}",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"},
        )

        if not junit_path.exists():
            return ArchitectureTestStats(
                tests=0,
                failures=0,
                errors=1,
                skipped=0,
                returncode=result.returncode,
            )

        tree = ET.parse(junit_path)
        root = tree.getroot()
        suites = []
        if root.tag == "testsuite":
            suites = [root]
        elif root.tag == "testsuites":
            suites = [elem for elem in root if elem.tag == "testsuite"]

        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_skipped = 0

        for suite in suites:
            total_tests += int(suite.attrib.get("tests", "0"))
            total_failures += int(suite.attrib.get("failures", "0"))
            total_errors += int(suite.attrib.get("errors", "0"))
            total_skipped += int(suite.attrib.get("skipped", "0"))

        return ArchitectureTestStats(
            tests=total_tests,
            failures=total_failures,
            errors=total_errors,
            skipped=total_skipped,
            returncode=result.returncode,
        )


def _count_total_exemptions(registry_path: Path) -> int:
    inventory = build_exemption_inventory(registry_path)
    return inventory.total_exemptions


def _count_domain_cc_exemptions(registry_path: Path) -> int:
    raw = load_exemptions_registry(registry_path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        return 0

    domain_complexity_count = 0
    domain_function_complexity_count = 0

    domain_complexity_entries = registries.get("domain_complexity", {})
    if isinstance(domain_complexity_entries, dict):
        domain_complexity_count = len(domain_complexity_entries)

    function_complexity_entries = registries.get("function_complexity", {})
    if isinstance(function_complexity_entries, dict):
        for exemption_key in function_complexity_entries:
            if not isinstance(exemption_key, str):
                continue
            if exemption_key.startswith("src/bioetl/domain/"):
                domain_function_complexity_count += 1

    return domain_complexity_count + domain_function_complexity_count


def _max_class_loc(src_root: Path) -> int:
    max_loc = 0
    for py_file in src_root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            start_line = node.lineno
            end_line = node.end_lineno or start_line
            loc = end_line - start_line + 1
            if loc > max_loc:
                max_loc = loc
    return max_loc


def _vcr_provider_counts(vcr_root: Path) -> dict[str, int]:
    if not vcr_root.exists():
        return {}

    counts: dict[str, int] = {}
    for provider_dir in sorted(vcr_root.iterdir()):
        if not provider_dir.is_dir():
            continue
        provider_name = provider_dir.name
        if provider_name == "multi_provider":
            continue
        yaml_count = sum(1 for _ in provider_dir.rglob("*.yaml"))
        counts[provider_name] = yaml_count
    return counts


def _ruff_format_violations() -> int:
    cmd = [*_resolve_ruff_cmd(), "format", "--check", "src", "tests"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return 0
    return sum(
        1
        for line in result.stdout.splitlines()
        if line.strip().startswith("Would reformat:")
    )


def _coverage_percent(coverage_xml_path: Path) -> float | None:
    if not coverage_xml_path.exists():
        return None
    try:
        tree = ET.parse(coverage_xml_path)
        root = tree.getroot()
    except ET.ParseError:
        return None

    raw_line_rate = root.attrib.get("line-rate")
    if raw_line_rate is None:
        return None
    try:
        return round(float(raw_line_rate) * 100.0, 2)
    except ValueError:
        return None


def _quarter_target(
    scorecard: dict[str, object], quarter: str
) -> dict[str, object] | None:
    targets = scorecard.get("quarterly_targets", [])
    if not isinstance(targets, list):
        return None
    for item in targets:
        if isinstance(item, dict) and item.get("quarter") == quarter:
            return item
    return None


def _ci_target_for_quarter(
    scorecard: dict[str, object],
    quarter: str,
    *,
    max_class_loc_target: int,
    vcr_min_per_provider_target: int,
    coverage_threshold_percent: float,
) -> dict[str, object]:
    default_target: dict[str, object] = {
        "architecture_test_failures_max": 0,
        "total_exemptions_max": 145,
        "max_class_loc_max": max_class_loc_target,
        "domain_cc_gt5_exemptions_max": 18,
        "vcr_cassettes_min_per_provider": vcr_min_per_provider_target,
        "ruff_formatting_violations_max": 0,
        "coverage_threshold_percent": coverage_threshold_percent,
    }

    custom_targets = scorecard.get("ci_quality_targets", [])
    if not isinstance(custom_targets, list):
        return default_target

    for item in custom_targets:
        if not isinstance(item, dict):
            continue
        if item.get("quarter") != quarter:
            continue
        merged = dict(default_target)
        merged.update(item)
        return merged
    return default_target


def main() -> int:
    args = _parse_args()
    registry_path = Path(args.registry)
    scorecard_path = Path(args.scorecard)
    src_root = Path(args.src_root)
    vcr_root = Path(args.vcr_root)
    coverage_xml = Path(args.coverage_xml)

    architecture_stats = _run_architecture_tests(args.architecture_tests)
    arch_failures = architecture_stats.failures + architecture_stats.errors

    scorecard = load_debt_scorecard(scorecard_path)
    violations, summary = evaluate_debt_scorecard(
        registry_path=registry_path,
        scorecard_path=scorecard_path,
    )
    if summary is None:
        print("[quality-integral-gate] scorecard evaluation failed")
        for item in violations:
            print(f"  - {item}")
        return 1

    quarter = summary.quarter
    quarter_target = _quarter_target(scorecard, quarter)
    if quarter_target is None:
        print(f"[quality-integral-gate] missing quarterly target for {quarter}")
        return 1

    max_total_exemptions = int(quarter_target["max_total_exemptions"])
    min_integral_score = float(quarter_target["min_integral_score"])

    total_exemptions = _count_total_exemptions(registry_path)
    domain_cc_exemptions = _count_domain_cc_exemptions(registry_path)
    max_class_loc = _max_class_loc(src_root)
    provider_vcr_counts = _vcr_provider_counts(vcr_root)
    min_provider_vcr = min(provider_vcr_counts.values()) if provider_vcr_counts else 0
    ruff_violations = _ruff_format_violations()
    coverage_percent = _coverage_percent(coverage_xml)

    ci_target = _ci_target_for_quarter(
        scorecard,
        quarter,
        max_class_loc_target=args.max_class_loc_target,
        vcr_min_per_provider_target=args.vcr_min_per_provider_target,
        coverage_threshold_percent=args.coverage_threshold,
    )
    coverage_threshold = float(ci_target["coverage_threshold_percent"])

    bonus = 0.0
    if arch_failures == 0:
        bonus += 0.5
    if total_exemptions < max_total_exemptions:
        bonus += 0.5
    if max_class_loc <= args.max_class_loc_target:
        bonus += 1.5
    if coverage_percent is not None and coverage_percent >= coverage_threshold:
        bonus += 0.5

    adjusted_integral_score = round(min(100.0, summary.integral_score + bonus), 2)
    gate_pass = adjusted_integral_score >= min_integral_score

    output = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "quarter": quarter,
        "architecture_tests": asdict(architecture_stats),
        "quarterly_target": {
            "max_total_exemptions": max_total_exemptions,
            "min_integral_score": min_integral_score,
        },
        "ci_metric_targets": ci_target,
        "metrics": {
            "architecture_test_failures": arch_failures,
            "total_exemptions": total_exemptions,
            "max_class_loc": max_class_loc,
            "domain_cc_gt5_exemptions": domain_cc_exemptions,
            "vcr_cassettes_min_per_provider": min_provider_vcr,
            "vcr_cassettes_by_provider": provider_vcr_counts,
            "ruff_formatting_violations": ruff_violations,
            "coverage_percent": coverage_percent,
            "coverage_verified": coverage_percent is not None,
        },
        "integral_score": {
            "base": summary.integral_score,
            "bonus": bonus,
            "adjusted": adjusted_integral_score,
            "min_required": min_integral_score,
            "pass": gate_pass,
        },
        "debt_scorecard": {
            "violations_count": len(violations),
            "violations": violations,
        },
        "metric_comparison": {
            "architecture_test_failures_ok": arch_failures
                                             <= int(ci_target["architecture_test_failures_max"]),
            "total_exemptions_ok": total_exemptions
                                   <= int(ci_target["total_exemptions_max"]),
            "max_class_loc_ok": max_class_loc <= int(ci_target["max_class_loc_max"]),
            "domain_cc_gt5_exemptions_ok": domain_cc_exemptions
                                           <= int(ci_target["domain_cc_gt5_exemptions_max"]),
            "vcr_cassettes_min_per_provider_ok": min_provider_vcr
                                                 >= int(ci_target["vcr_cassettes_min_per_provider"]),
            "ruff_formatting_violations_ok": ruff_violations
                                             <= int(ci_target["ruff_formatting_violations_max"]),
            "coverage_ok": (
                coverage_percent is not None
                and coverage_percent >= float(ci_target["coverage_threshold_percent"])
            ),
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        "[quality-integral-gate] "
        f"quarter={quarter}; arch_failures={arch_failures}; "
        f"total_exemptions={total_exemptions}/{max_total_exemptions}; "
        f"base_score={summary.integral_score}; bonus={bonus}; "
        f"adjusted_score={adjusted_integral_score}; min_required={min_integral_score}"
    )
    print(f"[quality-integral-gate] wrote metrics: {output_path}")

    if not gate_pass:
        print(
            "[quality-integral-gate] FAIL: adjusted integral score below quarter target"
        )
        return 1

    print("[quality-integral-gate] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
