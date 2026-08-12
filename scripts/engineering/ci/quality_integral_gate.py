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
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

if __package__ in {None, ""}:
    from scripts.engineering.ci._compatibility_telemetry import (  # type: ignore[import-not-found]
        CompatibilitySurfaceSnapshot,
        DebtGovernanceSnapshot,
        collect_debt_governance_snapshot,
        render_debt_governance_section,
    )
else:
    from ._compatibility_telemetry import (
        CompatibilitySurfaceSnapshot,
        DebtGovernanceSnapshot,
        collect_debt_governance_snapshot,
        render_debt_governance_section,
    )

from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    build_architecture_quality_scorecard,
)
from bioetl.infrastructure.quality.debt_scorecard import (
    DebtScorecardResult,
    evaluate_debt_scorecard,
    load_debt_scorecard,
)
from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry
from bioetl.infrastructure.quality.inventory import build_exemption_inventory
from memory.proof import emit_receipt_from_environment


@dataclass(frozen=True)
class ArchitectureTestStats:
    """Parsed architecture test counters."""

    tests: int
    failures: int
    errors: int
    skipped: int
    returncode: int


@dataclass(frozen=True)
class TestHealthClassification:
    """Descriptive test-health classification derived from policy + execution."""

    status: str
    summary: str
    reasons: tuple[str, ...]
    architecture_skip_count: int
    architecture_skip_ratio: float | None
    live_contract_enforced_provider_count: int
    live_contract_pilot_provider_count: int
    live_contract_vcr_only_provider_count: int
    skip_classes: tuple[tuple[str, int], ...]
    staged_rollout_flags: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable view."""
        return {
            "status": self.status,
            "summary": self.summary,
            "reasons": list(self.reasons),
            "architecture_skip_count": self.architecture_skip_count,
            "architecture_skip_ratio": self.architecture_skip_ratio,
            "live_contract_enforced_provider_count": (
                self.live_contract_enforced_provider_count
            ),
            "live_contract_pilot_provider_count": (
                self.live_contract_pilot_provider_count
            ),
            "live_contract_vcr_only_provider_count": (
                self.live_contract_vcr_only_provider_count
            ),
            "skip_classes": dict(self.skip_classes),
            "staged_rollout_flags": list(self.staged_rollout_flags),
        }


@dataclass(frozen=True)
class ContractTestingContext:
    """Normalized contract-testing policy inputs used for health classification."""

    enforced_providers: list[str]
    pilot_providers: list[str]
    vcr_only_providers: list[str]
    network_opt_in_required: bool
    live_api_gate_mode: str


@dataclass(frozen=True)
class QualityGateOutputContext:
    """Compact input bundle for quality gate JSON payload rendering."""

    quarter: str
    architecture_stats: ArchitectureTestStats
    max_total_exemptions: int
    min_integral_score: float
    ci_target: dict[str, object]
    arch_failures: int
    total_exemptions: int
    max_class_loc: int
    domain_cc_exemptions: int
    min_provider_vcr: int
    provider_vcr_counts: dict[str, int]
    ruff_violations: int
    coverage_percent: float | None
    compatibility_surface: CompatibilitySurfaceSnapshot
    debt_governance_surface: DebtGovernanceSnapshot
    architecture_quality_scorecard: Mapping[str, object]
    test_health_payload: dict[str, object]
    bonus: float
    summary: DebtScorecardResult
    adjusted_integral_score: float
    gate_pass: bool
    violations: list[str]


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
        default="reports/coverage/coverage.xml",
        help="Coverage XML file path (optional).",
    )
    parser.add_argument(
        "--test-matrix",
        default="configs/quality/test_matrix.yaml",
        help="Path to the test matrix policy YAML used for descriptive health classification.",
    )
    parser.add_argument(
        "--test-health-taxonomy",
        default="configs/quality/test_health_reporting.yaml",
        help="Path to the canonical test-health reporting taxonomy config.",
    )
    parser.add_argument(
        "--output",
        default="reports/quality/ci-quality-metrics.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--summary-out",
        default="",
        help="Optional path to append a compact markdown summary.",
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
        if candidate.exists() and os.access(candidate, os.X_OK):
            return [str(candidate)]
    return [sys.executable, "-m", "ruff"]


def _architecture_test_cmd(pytest_path: str, junit_path: Path) -> list[str]:
    """Build pytest command for architecture suite execution."""
    return [
        sys.executable,
        "-m",
        "pytest",
        pytest_path,
        "-q",
        "--tb=no",
        f"--junitxml={junit_path}",
    ]


def _missing_architecture_stats(returncode: int) -> ArchitectureTestStats:
    """Return fallback stats when JUnit report was not produced."""
    return ArchitectureTestStats(
        tests=0,
        failures=0,
        errors=1,
        skipped=0,
        returncode=returncode,
    )


def _parse_architecture_junit(
    junit_path: Path, *, returncode: int
) -> ArchitectureTestStats:
    """Parse architecture JUnit XML into stable counters."""
    if not junit_path.exists():
        return _missing_architecture_stats(returncode)
    tree = ET.parse(junit_path)
    root = tree.getroot()
    suites = _junit_suites(root)
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
        returncode=returncode,
    )


def _junit_suites(root: ET.Element) -> list[ET.Element]:
    """Return testsuite nodes from pytest JUnit root element."""
    if root.tag == "testsuite":
        return [root]
    if root.tag == "testsuites":
        return [elem for elem in root if elem.tag == "testsuite"]
    return []


def _run_architecture_tests(pytest_path: str) -> ArchitectureTestStats:
    with tempfile.TemporaryDirectory(prefix="quality-arch-") as tmp_dir:
        junit_path = Path(tmp_dir) / "architecture.junit.xml"
        from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

        cmd = ensure_safe_cli_argv(_architecture_test_cmd(pytest_path, junit_path))
        result = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
            cmd,
            capture_output=True,
            text=True,
            env={k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"},
        )
        return _parse_architecture_junit(
            junit_path,
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
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    cmd = ensure_safe_cli_argv(
        [
            str(token)
            for token in [*_resolve_ruff_cmd(), "format", "--check", "src", "tests"]
        ]
    )
    result = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
        cmd, capture_output=True, text=True
    )
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


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return raw
    return {}


def _build_test_health_payload(
    classification: TestHealthClassification,
    taxonomy: dict[str, object],
) -> dict[str, object]:
    """Attach canonical taxonomy metadata to the computed classification."""
    status_entry = _taxonomy_status_entry(taxonomy, classification.status)
    short_label = _taxonomy_string(
        status_entry.get("short_label"), classification.status
    )
    definition = _taxonomy_string(
        status_entry.get("definition"), classification.summary
    )
    merge_semantics = _taxonomy_string(
        status_entry.get("merge_semantics"), "informational"
    )
    skip_classes_detail = _skip_classes_detail(classification, taxonomy)

    return {
        **classification.as_dict(),
        "skip_classes_detail": skip_classes_detail,
        "classification_mode": taxonomy.get("classification_mode", "informational"),
        "merge_blocking_source": taxonomy.get(
            "merge_blocking_source", "ci_pass_fail_and_quality_gate"
        ),
        "merge_blocking_note": taxonomy.get("merge_blocking_note", ""),
        "short_label": short_label,
        "definition": definition,
        "merge_semantics": merge_semantics,
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _taxonomy_status_entry(
    taxonomy: dict[str, object], status: str
) -> dict[str, object]:
    statuses = taxonomy.get("statuses", {})
    if not isinstance(statuses, dict):
        return {}
    raw_entry = statuses.get(status, {})
    return raw_entry if isinstance(raw_entry, dict) else {}


def _taxonomy_string(value: object, fallback: str) -> str:
    return value if isinstance(value, str) else fallback


def _skip_classes_detail(
    classification: TestHealthClassification,
    taxonomy: dict[str, object],
) -> list[dict[str, object]]:
    skip_classes_taxonomy = taxonomy.get("skip_classes", {})
    if not isinstance(skip_classes_taxonomy, dict):
        return []
    details: list[dict[str, object]] = []
    for skip_class, count in classification.skip_classes:
        raw_entry = skip_classes_taxonomy.get(skip_class, {})
        entry = raw_entry if isinstance(raw_entry, dict) else {}
        details.append(
            {
                "id": skip_class,
                "count": count,
                "short_label": _taxonomy_string(entry.get("short_label"), skip_class),
                "definition": _taxonomy_string(entry.get("definition"), skip_class),
            }
        )
    return details


def _fixture_governance_rollout_flags(test_matrix: dict[str, object]) -> list[str]:
    fixture_governance = test_matrix.get("fixture_governance", {})
    if not isinstance(fixture_governance, dict):
        return []
    rollout = fixture_governance.get("rollout", {})
    if not isinstance(rollout, dict):
        return []
    flags: list[str] = []
    for key, value in sorted(rollout.items()):
        if isinstance(value, str) and value != "enforced":
            flags.append(f"fixture_governance.{key}={value}")
    return flags


def _mutation_testing_rollout_flags(test_matrix: dict[str, object]) -> list[str]:
    mutation_testing = test_matrix.get("mutation_testing", {})
    if not isinstance(mutation_testing, dict):
        return []
    flags: list[str] = []
    ci_gate_mode = mutation_testing.get("ci_gate_mode")
    if isinstance(ci_gate_mode, str) and ci_gate_mode != "full":
        flags.append(f"mutation_testing.ci_gate_mode={ci_gate_mode}")
    targets = mutation_testing.get("targets", {})
    if not isinstance(targets, dict):
        return flags
    for target_name, target_payload in sorted(targets.items()):
        if not isinstance(target_payload, dict):
            continue
        if target_payload.get("enforced") is False:
            flags.append(f"mutation_testing.targets.{target_name}=staged")
    return flags


def _staged_rollout_flags(test_matrix: dict[str, object]) -> tuple[str, ...]:
    flags = _fixture_governance_rollout_flags(
        test_matrix
    ) + _mutation_testing_rollout_flags(test_matrix)
    return tuple(flags)


def _not_run_lane_entries(test_matrix: dict[str, object]) -> tuple[dict[str, str], ...]:
    confidence = test_matrix.get("test_health_confidence", {})
    if not isinstance(confidence, dict):
        return ()
    entries = confidence.get("lane_absence_skip_classes", {})
    if not isinstance(entries, list):
        return ()

    normalized: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        lane = entry.get("lane")
        skip_class = entry.get("skip_class")
        reason = entry.get("reason")
        if not isinstance(lane, str) or not lane:
            continue
        if not isinstance(skip_class, str) or not skip_class:
            continue
        normalized.append(
            {
                "lane": lane,
                "skip_class": skip_class,
                "reason": (
                    reason
                    if isinstance(reason, str) and reason
                    else f"current quality-gate run does not execute the canonical {lane} lane"
                ),
            }
        )
    return tuple(normalized)


def _build_skip_classes(
    architecture_stats: ArchitectureTestStats,
    *,
    network_opt_in_required: bool,
    live_api_gate_mode: str,
    pilot_providers: list[str],
    vcr_only_providers: list[str],
    not_run_lane_entries: tuple[dict[str, str], ...],
) -> tuple[tuple[str, int], ...]:
    """Return stable grouped skip/conditional-confidence buckets."""
    classes: list[tuple[str, int]] = []
    if architecture_stats.skipped > 0:
        classes.append(("architecture_suite_skips", architecture_stats.skipped))
    if network_opt_in_required:
        classes.append(("live_network_opt_in_gate", 1))
    if live_api_gate_mode and live_api_gate_mode != "always":
        classes.append(("live_api_gate_mode_non_always", 1))
    if pilot_providers:
        classes.append(("pilot_provider_count", len(pilot_providers)))
    if vcr_only_providers:
        classes.append(("vcr_only_provider_count", len(vcr_only_providers)))
    for entry in not_run_lane_entries:
        classes.append((entry["skip_class"], 1))
    return tuple(classes)


def _blocking_confidence_reasons(
    architecture_stats: ArchitectureTestStats,
    contract_context: ContractTestingContext,
    not_run_lane_entries: tuple[dict[str, str], ...],
) -> list[str]:
    reasons: list[str] = []
    if architecture_stats.skipped > 0:
        reasons.append(
            f"architecture suite carries {architecture_stats.skipped} skip(s); "
            "architecture skip budget is zero"
        )
    if contract_context.vcr_only_providers:
        reasons.append(
            "live minimum baseline excludes "
            f"{len(contract_context.vcr_only_providers)} VCR-only provider(s)"
        )
    if contract_context.pilot_providers:
        reasons.append(
            "live minimum baseline includes "
            f"{len(contract_context.pilot_providers)} pilot provider(s)"
        )
    reasons.extend(entry["reason"] for entry in not_run_lane_entries)
    return reasons


def _classify_test_health(
    architecture_stats: ArchitectureTestStats,
    test_matrix: dict[str, object],
    *,
    suite_green: bool,
) -> TestHealthClassification:
    total_executed = architecture_stats.tests
    skip_ratio: float | None = None
    if total_executed > 0:
        skip_ratio = round(architecture_stats.skipped / total_executed, 4)
    contract_context = _contract_testing_context(test_matrix)
    staged_flags = _staged_rollout_flags(test_matrix)
    not_run_lane_entries = _not_run_lane_entries(test_matrix)
    skip_classes = _build_skip_classes(
        architecture_stats,
        network_opt_in_required=contract_context.network_opt_in_required,
        live_api_gate_mode=contract_context.live_api_gate_mode,
        pilot_providers=contract_context.pilot_providers,
        vcr_only_providers=contract_context.vcr_only_providers,
        not_run_lane_entries=not_run_lane_entries,
    )
    if not suite_green:
        return TestHealthClassification(
            status="non_green",
            summary=(
                "Suite is not green, so descriptive confidence classes remain "
                "secondary to active failures."
            ),
            reasons=("merge-blocking failures remain present",),
            architecture_skip_count=architecture_stats.skipped,
            architecture_skip_ratio=skip_ratio,
            live_contract_enforced_provider_count=len(
                contract_context.enforced_providers
            ),
            live_contract_pilot_provider_count=len(contract_context.pilot_providers),
            live_contract_vcr_only_provider_count=len(
                contract_context.vcr_only_providers
            ),
            skip_classes=skip_classes,
            staged_rollout_flags=staged_flags,
        )
    blocking_confidence_reasons = _blocking_confidence_reasons(
        architecture_stats,
        contract_context,
        not_run_lane_entries,
    )
    if blocking_confidence_reasons:
        return TestHealthClassification(
            status="non_green",
            summary=(
                "Suite passed, but required confidence evidence is missing or "
                "explicitly outside the zero-debt baseline."
            ),
            reasons=tuple(blocking_confidence_reasons),
            architecture_skip_count=architecture_stats.skipped,
            architecture_skip_ratio=skip_ratio,
            live_contract_enforced_provider_count=len(
                contract_context.enforced_providers
            ),
            live_contract_pilot_provider_count=len(contract_context.pilot_providers),
            live_contract_vcr_only_provider_count=len(
                contract_context.vcr_only_providers
            ),
            skip_classes=skip_classes,
            staged_rollout_flags=staged_flags,
        )

    environment_reasons = _environment_limited_reasons(
        architecture_stats,
        contract_context,
        not_run_lane_entries,
    )
    if environment_reasons:
        return TestHealthClassification(
            status="environment_limited_green",
            summary=(
                "Green status is environment-limited because parts of the "
                "confidence surface remain skip- or environment-gated."
            ),
            reasons=tuple(environment_reasons),
            architecture_skip_count=architecture_stats.skipped,
            architecture_skip_ratio=skip_ratio,
            live_contract_enforced_provider_count=len(
                contract_context.enforced_providers
            ),
            live_contract_pilot_provider_count=len(contract_context.pilot_providers),
            live_contract_vcr_only_provider_count=len(
                contract_context.vcr_only_providers
            ),
            skip_classes=skip_classes,
            staged_rollout_flags=staged_flags,
        )

    if staged_flags:
        return TestHealthClassification(
            status="staged_green",
            summary=(
                "Green status is staged because at least one shared confidence "
                "surface is not yet fully enforced."
            ),
            reasons=staged_flags,
            architecture_skip_count=architecture_stats.skipped,
            architecture_skip_ratio=skip_ratio,
            live_contract_enforced_provider_count=len(
                contract_context.enforced_providers
            ),
            live_contract_pilot_provider_count=len(contract_context.pilot_providers),
            live_contract_vcr_only_provider_count=len(
                contract_context.vcr_only_providers
            ),
            skip_classes=skip_classes,
            staged_rollout_flags=staged_flags,
        )

    return TestHealthClassification(
        status="fully_exercised_green",
        summary=(
            "Green status reflects a fully exercised confidence surface with no "
            "detected staged or environment-gated limitations."
        ),
        reasons=(),
        architecture_skip_count=architecture_stats.skipped,
        architecture_skip_ratio=skip_ratio,
        live_contract_enforced_provider_count=len(contract_context.enforced_providers),
        live_contract_pilot_provider_count=len(contract_context.pilot_providers),
        live_contract_vcr_only_provider_count=len(contract_context.vcr_only_providers),
        skip_classes=skip_classes,
        staged_rollout_flags=staged_flags,
    )


def _contract_testing_context(
    test_matrix: dict[str, object],
) -> ContractTestingContext:
    contract_testing = test_matrix.get("contract_testing", {})
    if not isinstance(contract_testing, dict):
        return ContractTestingContext([], [], [], False, "")
    live_api_gate_mode = contract_testing.get("live_api_gate_mode")
    baseline = contract_testing.get("live_api_minimum_baseline", {})
    baseline_mapping = baseline if isinstance(baseline, dict) else {}
    return ContractTestingContext(
        enforced_providers=_string_list(baseline_mapping.get("enforced_providers")),
        pilot_providers=_string_list(baseline_mapping.get("pilot_providers")),
        vcr_only_providers=_string_list(baseline_mapping.get("vcr_only_providers")),
        network_opt_in_required=bool(
            contract_testing.get("network_opt_in_required", False)
        ),
        live_api_gate_mode=(
            live_api_gate_mode if isinstance(live_api_gate_mode, str) else ""
        ),
    )


def _environment_limited_reasons(
    architecture_stats: ArchitectureTestStats,
    contract_context: ContractTestingContext,
    not_run_lane_entries: tuple[dict[str, str], ...],
) -> list[str]:
    del architecture_stats, not_run_lane_entries
    reasons: list[str] = []
    if contract_context.network_opt_in_required:
        reasons.append("live contract execution is network opt-in gated")
    if (
        contract_context.live_api_gate_mode
        and contract_context.live_api_gate_mode != "always"
    ):
        reasons.append(f"live API gate mode is {contract_context.live_api_gate_mode}")
    return reasons


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


def _require_int(mapping: dict[str, object], key: str) -> int:
    value = mapping[key]
    if isinstance(value, bool):
        raise TypeError(f"{key} must not be boolean")
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    raise TypeError(f"{key} must be numeric-compatible, got {type(value)!r}")


def _require_float(mapping: dict[str, object], key: str) -> float:
    value = mapping[key]
    if isinstance(value, bool):
        raise TypeError(f"{key} must not be boolean")
    if isinstance(value, int | float | str):
        return float(value)
    raise TypeError(f"{key} must be float-compatible, got {type(value)!r}")


def _bonus_score(
    *,
    arch_failures: int,
    total_exemptions: int,
    max_total_exemptions: int,
    max_class_loc: int,
    max_class_loc_target: int,
    coverage_percent: float | None,
    coverage_threshold: float,
) -> float:
    """Compute deterministic bonus added to the base integral score."""
    bonus = 0.0
    if arch_failures == 0:
        bonus += 0.5
    if total_exemptions < max_total_exemptions:
        bonus += 0.5
    if max_class_loc <= max_class_loc_target:
        bonus += 1.5
    if coverage_percent is not None and coverage_percent >= coverage_threshold:
        bonus += 0.5
    return bonus


def _metric_comparison(
    *,
    ci_target: dict[str, object],
    arch_failures: int,
    total_exemptions: int,
    max_class_loc: int,
    domain_cc_exemptions: int,
    min_provider_vcr: int,
    ruff_violations: int,
    coverage_percent: float | None,
) -> dict[str, bool]:
    """Build metric-to-target comparison payload."""
    return {
        "architecture_test_failures_ok": arch_failures
        <= _require_int(ci_target, "architecture_test_failures_max"),
        "total_exemptions_ok": total_exemptions
        <= _require_int(ci_target, "total_exemptions_max"),
        "max_class_loc_ok": max_class_loc
        <= _require_int(ci_target, "max_class_loc_max"),
        "domain_cc_gt5_exemptions_ok": domain_cc_exemptions
        <= _require_int(ci_target, "domain_cc_gt5_exemptions_max"),
        "vcr_cassettes_min_per_provider_ok": min_provider_vcr
        >= _require_int(ci_target, "vcr_cassettes_min_per_provider"),
        "ruff_formatting_violations_ok": ruff_violations
        <= _require_int(ci_target, "ruff_formatting_violations_max"),
        "coverage_ok": (
            coverage_percent is not None
            and coverage_percent
            >= _require_float(ci_target, "coverage_threshold_percent")
        ),
    }


def _quality_gate_output(payload: QualityGateOutputContext) -> dict[str, object]:
    """Build JSON payload emitted by the quality gate."""
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "quarter": payload.quarter,
        "architecture_tests": asdict(payload.architecture_stats),
        "quarterly_target": {
            "max_total_exemptions": payload.max_total_exemptions,
            "min_integral_score": payload.min_integral_score,
        },
        "ci_metric_targets": payload.ci_target,
        "metrics": {
            "architecture_test_failures": payload.arch_failures,
            "total_exemptions": payload.total_exemptions,
            "max_class_loc": payload.max_class_loc,
            "domain_cc_gt5_exemptions": payload.domain_cc_exemptions,
            "vcr_cassettes_min_per_provider": payload.min_provider_vcr,
            "vcr_cassettes_by_provider": payload.provider_vcr_counts,
            "ruff_formatting_violations": payload.ruff_violations,
            "coverage_percent": payload.coverage_percent,
            "coverage_verified": payload.coverage_percent is not None,
        },
        "compatibility_surface": payload.compatibility_surface.as_dict(),
        "debt_governance_surface": payload.debt_governance_surface.as_dict(),
        "architecture_quality_scorecard": payload.architecture_quality_scorecard,
        "test_health": payload.test_health_payload,
        "integral_score": {
            "base": payload.summary.integral_score,
            "bonus": payload.bonus,
            "adjusted": payload.adjusted_integral_score,
            "min_required": payload.min_integral_score,
            "pass": payload.gate_pass,
        },
        "debt_scorecard": {
            "violations_count": len(payload.violations),
            "violations": payload.violations,
        },
        "metric_comparison": _metric_comparison(
            ci_target=payload.ci_target,
            arch_failures=payload.arch_failures,
            total_exemptions=payload.total_exemptions,
            max_class_loc=payload.max_class_loc,
            domain_cc_exemptions=payload.domain_cc_exemptions,
            min_provider_vcr=payload.min_provider_vcr,
            ruff_violations=payload.ruff_violations,
            coverage_percent=payload.coverage_percent,
        ),
    }


def _summary_lines(
    *,
    quarter: str,
    adjusted_integral_score: float,
    min_integral_score: float,
    arch_failures: int,
    test_health: TestHealthClassification,
    test_health_payload: dict[str, object],
    total_exemptions: int,
    compatibility_surface: CompatibilitySurfaceSnapshot,
    debt_governance_surface: DebtGovernanceSnapshot,
) -> list[str]:
    """Build compact markdown summary lines."""
    del compatibility_surface
    skip_classes_detail_raw = test_health_payload["skip_classes_detail"]
    skip_classes_detail = (
        skip_classes_detail_raw if isinstance(skip_classes_detail_raw, list) else []
    )
    skip_classes_rendered = (
        ", ".join(
            f"{item['short_label']}={item['count']}" for item in skip_classes_detail
        )
        if skip_classes_detail
        else "none"
    )
    staged_flags_rendered = (
        ", ".join(test_health.staged_rollout_flags)
        if test_health.staged_rollout_flags
        else "none"
    )
    return [
        "## CI Quality Metrics Snapshot",
        f"- quarter: `{quarter}`",
        f"- adjusted_integral_score: `{adjusted_integral_score}`",
        f"- min_required: `{min_integral_score}`",
        f"- architecture_test_failures: `{arch_failures}`",
        f"- test_health_status: `{test_health.status}`",
        f"- test_health_label: `{test_health_payload['short_label']}`",
        f"- test_health_summary: {test_health.summary}",
        f"- test_health_definition: {test_health_payload['definition']}",
        f"- test_health_merge_semantics: `{test_health_payload['merge_semantics']}`",
        (
            "- test_health_merge_blocking_source: `"
            + str(test_health_payload["merge_blocking_source"])
            + "`"
        ),
        f"- architecture_skipped: `{test_health.architecture_skip_count}`",
        f"- test_health_skip_classes: `{skip_classes_rendered}`",
        f"- staged_rollout_flags: `{staged_flags_rendered}`",
        f"- total_exemptions: `{total_exemptions}`",
        render_debt_governance_section(
            debt_governance_surface,
            heading="## Debt Governance Surface Snapshot",
        ),
    ]


def _write_output(path: Path, output: dict[str, object]) -> None:
    """Write JSON quality gate payload."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _append_summary(path: Path, summary_lines: list[str]) -> None:
    """Append markdown summary to the requested file."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(summary_lines) + "\n")


def main() -> int:
    args = _parse_args()
    registry_path = Path(args.registry)
    scorecard_path = Path(args.scorecard)
    src_root = Path(args.src_root)
    vcr_root = Path(args.vcr_root)
    coverage_xml = Path(args.coverage_xml)
    test_matrix_path = Path(args.test_matrix)
    test_health_taxonomy_path = Path(args.test_health_taxonomy)

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

    max_total_exemptions = _require_int(quarter_target, "max_total_exemptions")
    min_integral_score = _require_float(quarter_target, "min_integral_score")

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
    coverage_threshold = _require_float(ci_target, "coverage_threshold_percent")
    debt_governance_surface = collect_debt_governance_snapshot()
    compatibility_surface = debt_governance_surface.compatibility_surface
    architecture_quality_scorecard = build_architecture_quality_scorecard(
        repo_root=Path.cwd()
    )
    test_matrix = _load_yaml_mapping(test_matrix_path)
    test_health_taxonomy = _load_yaml_mapping(test_health_taxonomy_path)

    bonus = _bonus_score(
        arch_failures=arch_failures,
        total_exemptions=total_exemptions,
        max_total_exemptions=max_total_exemptions,
        max_class_loc=max_class_loc,
        max_class_loc_target=args.max_class_loc_target,
        coverage_percent=coverage_percent,
        coverage_threshold=coverage_threshold,
    )
    adjusted_integral_score = round(min(100.0, summary.integral_score + bonus), 2)
    gate_pass = adjusted_integral_score >= min_integral_score
    test_health = _classify_test_health(
        architecture_stats,
        test_matrix,
        suite_green=gate_pass and arch_failures == 0,
    )
    test_health_payload = _build_test_health_payload(test_health, test_health_taxonomy)

    output = _quality_gate_output(
        QualityGateOutputContext(
            quarter=quarter,
            architecture_stats=architecture_stats,
            max_total_exemptions=max_total_exemptions,
            min_integral_score=min_integral_score,
            ci_target=ci_target,
            arch_failures=arch_failures,
            total_exemptions=total_exemptions,
            max_class_loc=max_class_loc,
            domain_cc_exemptions=domain_cc_exemptions,
            min_provider_vcr=min_provider_vcr,
            provider_vcr_counts=provider_vcr_counts,
            ruff_violations=ruff_violations,
            coverage_percent=coverage_percent,
            compatibility_surface=compatibility_surface,
            debt_governance_surface=debt_governance_surface,
            architecture_quality_scorecard=architecture_quality_scorecard,
            test_health_payload=test_health_payload,
            bonus=bonus,
            summary=summary,
            adjusted_integral_score=adjusted_integral_score,
            gate_pass=gate_pass,
            violations=violations,
        )
    )

    output_path = Path(args.output)
    _write_output(output_path, output)
    emit_receipt_from_environment(
        repo_root=Path.cwd(),
        producer="quality_integral_gate",
        evidence_kind="quality",
        command="python -m scripts.engineering.ci.quality_integral_gate",
        status="pass" if gate_pass else "fail",
        exit_code=0 if gate_pass else 1,
        output_path=output_path,
    )

    if args.summary_out:
        _append_summary(
            Path(args.summary_out),
            _summary_lines(
                quarter=quarter,
                adjusted_integral_score=adjusted_integral_score,
                min_integral_score=min_integral_score,
                arch_failures=arch_failures,
                test_health=test_health,
                test_health_payload=test_health_payload,
                total_exemptions=total_exemptions,
                compatibility_surface=compatibility_surface,
                debt_governance_surface=debt_governance_surface,
            ),
        )

    print(
        "[quality-integral-gate] "
        f"quarter={quarter}; arch_failures={arch_failures}; "
        f"total_exemptions={total_exemptions}/{max_total_exemptions}; "
        f"base_score={summary.integral_score}; bonus={bonus}; "
        f"adjusted_score={adjusted_integral_score}; min_required={min_integral_score}"
    )
    print(
        "[quality-integral-gate] "
        "compatibility_surface="
        f"curated={compatibility_surface.curated_inventory_rows}; "
        f"measured={compatibility_surface.measured_tracked_modules}; "
        f"measured_only={compatibility_surface.measured_only_modules}; "
        f"compat_shims={compatibility_surface.compat_shim_modules}; "
        f"mixed={compatibility_surface.mixed_modules}; "
        f"retained={compatibility_surface.retained_entrypoints}; "
        f"public={compatibility_surface.public_entrypoints}"
    )
    print(
        "[quality-integral-gate] "
        "debt_governance="
        f"uuid_seams={debt_governance_surface.runtime_uuid.runtime_uuid_seam_count}; "
        "replay_critical_uuid="
        f"{debt_governance_surface.runtime_uuid.replay_critical_uuid_seam_count}; "
        f"triaged_dead_code={debt_governance_surface.retirement.triaged_entry_count}; "
        "untriaged_zero_import="
        f"{debt_governance_surface.retirement.repo_wide_untriaged_zero_import_candidate_count}; "
        "compatibility_tests="
        f"{debt_governance_surface.test_governance.compatibility_test_files}"
    )
    print(
        "[quality-integral-gate] "
        f"test_health={test_health.status}; "
        f"test_health_semantics={test_health_payload['merge_semantics']}; "
        f"arch_skipped={test_health.architecture_skip_count}; "
        f"skip_classes={len(test_health.skip_classes)}; "
        f"live_enforced={test_health.live_contract_enforced_provider_count}; "
        f"live_pilot={test_health.live_contract_pilot_provider_count}; "
        f"live_vcr_only={test_health.live_contract_vcr_only_provider_count}; "
        f"staged_flags={len(test_health.staged_rollout_flags)}"
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
