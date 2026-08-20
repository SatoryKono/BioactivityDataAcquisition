#!/usr/bin/env python3
"""Aggregate debt-reduction fail-fast gates across quality artifacts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    build_architecture_quality_scorecard,
)
from bioetl.infrastructure.quality.debt_scorecard import (
    evaluate_debt_scorecard,
    load_debt_scorecard,
)
from scripts.engineering.ci.validate_registry_dq_refs import (
    build_diagnostics_payload as build_contract_registry_dq_diagnostics,
)
from scripts.engineering.qa import (
    report_adr_enforcement_matrix,
    report_architecture_debt_remote_main_baseline,
    report_hotspot_family_baseline,
    report_observability_metric_inventory,
)
from scripts.engineering.qa.report_config_surface_backlog import (
    build_backlog,
)
from scripts.engineering.qa.report_module_coverage_inventory import (
    _refresh_existing_inventory_source_tree,
)
from memory.proof import emit_receipt_from_environment

DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "debt-governance-gates.json"
)
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "debt-governance-gates.md"
RELEASE_REVIEW_MAX_AGE_DAYS = 21
# Canonical inputs that invalidate committed debt-governance-gates artifacts.
# When any of these change, operators/CI must re-run:
#   python -m scripts.engineering.qa report-debt-governance-gates --update
# Prefer `python -m scripts.engineering.qa.refresh_governance_artifacts` which
# regenerates gates last (#7465).
DEBT_GATE_INPUT_ARTIFACTS: tuple[str, ...] = (
    "configs/quality/debt_scorecard.yaml",
    "configs/quality/scripts_inventory_manifest.json",
    "reports/quality/architecture-quality-scorecard.json",
    "reports/quality/hotspot-family-baseline.json",
    "reports/quality/module-coverage-inventory.json",
    "reports/quality/config-surface-backlog.json",
    "reports/quality/architecture-debt-remote-main-baseline.json",
    "reports/quality/adr-enforcement-matrix.json",
    "reports/quality/compatibility-importer-census.json",
    "reports/quality/flaky-test-burndown-review.json",
    "reports/quality/dead-code-inventory.json",
)
DEBT_SCORECARD_PATH = "configs/quality/debt_scorecard.yaml"
FLAKY_TEST_REVIEW_PATH = "reports/quality/flaky-test-burndown-review.json"
# Quality / observability artifact path identities (python:S1192).
HOTSPOT_FAMILY_BASELINE_JSON = "reports/quality/hotspot-family-baseline.json"
ARCHITECTURE_DEBT_REMOTE_MAIN_BASELINE_JSON = (
    "reports/quality/architecture-debt-remote-main-baseline.json"
)
RUNTIME_CARDINALITY_INVENTORY_JSON = (
    "reports/observability/runtime_cardinality_inventory.json"
)
RUNTIME_CARDINALITY_REVIEW_JSON = (
    "reports/observability/runtime_cardinality_review.json"
)
MODULE_COVERAGE_INVENTORY_JSON = "reports/quality/module-coverage-inventory.json"
COMPATIBILITY_IMPORTER_CENSUS_JSON = (
    "reports/quality/compatibility-importer-census.json"
)
CONFIG_DISCREPANCY_BASELINE_JSON = "reports/quality/config-discrepancy-baseline.json"
TEST_GOVERNANCE_CURRENT_JSON = "reports/quality/test-governance-current.json"
RUNTIME_UUID_SEAMS_YAML = "configs/quality/runtime_uuid_seams.yaml"
ADR_ENFORCEMENT_MATRIX_JSON = "reports/quality/adr-enforcement-matrix.json"
SCRIPTS_INVENTORY_MANIFEST_JSON = "configs/quality/scripts_inventory_manifest.json"
BUDGET_KEY_NAMES = frozenset(
    {
        "budget",
        "max",
        "max_count",
        "max_loc",
        "max_lines",
        "max_value",
        "limit",
        "threshold",
        "cap",
    }
)
UNTRIAGED_FLAKY_STATUSES = frozenset({"", "needs-triage", "unknown", "untriaged"})


@dataclass(frozen=True)
class Gate:
    """Normalized debt-governance gate row."""

    name: str
    status: str
    metric: str
    current: object
    limit: object
    source_artifact: str
    remediation: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(PROJECT_ROOT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument(
        "--changed-from-ref",
        help=(
            "Optional git base ref for changed-path gating. When set, the report "
            "computes repo-relative changed files from <ref>...HEAD and enables "
            "touched-surface governance gates."
        ),
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--update", action="store_true")
    return parser.parse_args(argv)


def _load_json(repo_root: Path, rel_path: str) -> dict[str, Any]:
    path = repo_root / rel_path
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_input_with_preflight(
    repo_root: Path,
    rel_path: str,
    *,
    gate_name: str,
) -> tuple[dict[str, Any], Gate]:
    """Load one required JSON input without crashing the evidence rollup."""
    path = repo_root / rel_path
    current: str
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        current = "missing"
    except json.JSONDecodeError:
        current = "invalid_json"
    except OSError:
        current = "unreadable"
    else:
        if isinstance(payload, dict):
            return payload, Gate(
                name=gate_name,
                status="pass",
                metric="required_json_input",
                current="available_valid_object",
                limit="available_valid_object",
                source_artifact=rel_path,
                remediation="No action required.",
            )
        current = "invalid_top_level_type"

    return {}, Gate(
        name=gate_name,
        status="fail",
        metric="required_json_input",
        current=current,
        limit="available_valid_object",
        source_artifact=rel_path,
        remediation=(
            "Run the canonical producer for this input and publish the generated "
            "artifact before rerunning debt-governance gates."
        ),
    )


def _load_yaml(repo_root: Path, rel_path: str) -> dict[str, Any]:
    payload = yaml.safe_load((repo_root / rel_path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_yaml_from_git_ref(
    repo_root: Path,
    ref: str,
    rel_path: str,
) -> dict[str, Any] | None:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    result = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
        ensure_safe_cli_argv(
            ["git", "-C", repo_root.as_posix(), "show", f"{ref}:{rel_path}"]
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return None
    payload = yaml.safe_load(result.stdout)
    return payload if isinstance(payload, dict) else {}


# Implementation seams are kept in focused sibling modules. Imports remain
# here so existing callers of this historical module path retain compatibility.
from scripts.engineering.qa.debt_governance_gate_evaluators import (
    _count,
    _is_budget_key,
    _collect_budget_numbers,
    _budget_growth_increases,
    _debt_scorecard_budget_no_growth_gate,
    _flaky_untriaged_entries,
    _hard_limit_gate,
    _warn_limit_gate,
    _artifact_matches,
    _payload_without_volatile_fields,
    _artifact_matches_builder,
    _hotspot_family_baseline_artifact_matches_builder,
    _remote_main_baseline_artifact_matches_builder,
    _unavailable_required_remote_baseline_artifacts,
    _parse_generated_at,
    _release_review_freshness_gate,
    _release_gate_status,
    _module_coverage_source_tree_hash_gate,
    _module_coverage_scorecard_coherence_gate,
    _compatibility_scorecard_coherence_gate,
    _module_coverage_aggregate_residual_limits,
    _collect_changed_paths,
    _string_paths_from,
    _paths_from_emitter_lists,
    _emitter_paths_from_fields,
    _collect_metric_change_trigger_paths,
    _matching_touched_metric_paths,
    _observability_touched_metric_inventory_gate,
    _observability_touched_metric_review_gate,
    _debt_scorecard_gates,
    _module_coverage_residual_gates,
    _hotspot_and_compatibility_gates,
    _dead_code_and_contract_gates,
    _config_discrepancy_gates,
    _family_duplication_current,
    _full_app_family_duplication_gates,
    _full_app_duplication_gates,
    _script_zero_reference_counts,
    _supporting_scripts_gates,
    _test_governance_and_flaky_gates,
    _runtime_uuid_gates,
    _observability_cardinality_list_gates,
    _observability_review_and_touch_gates,
    _remote_main_baseline_gate,
    _config_surface_backlog_matches_builder,
    _in_test_mode,
    _collect_stale_artifacts,
)
from scripts.engineering.qa.debt_governance_gate_report import (
    _check_artifacts,
    render_markdown,
)


def _gate_status_counts(gates: list[Gate]) -> dict[str, int]:
    """Count pass/warn/fail gate statuses."""
    return {
        "pass": sum(1 for gate in gates if gate.status == "pass"),
        "warn": sum(1 for gate in gates if gate.status == "warn"),
        "fail": sum(1 for gate in gates if gate.status == "fail"),
    }


def build_payload(
    *,
    repo_root: Path = PROJECT_ROOT,
    changed_from_ref: str | None = None,
) -> dict[str, object]:
    """Build normalized debt-governance gate payload."""
    repo_root = repo_root.resolve()
    flaky_review, flaky_review_preflight_gate = _load_json_input_with_preflight(
        repo_root,
        FLAKY_TEST_REVIEW_PATH,
        gate_name="flaky_test_review_input_preflight",
    )

    architecture_scorecard = _load_json(
        repo_root,
        "reports/quality/architecture-quality-scorecard.json",
    )
    module_coverage = _load_json(repo_root, MODULE_COVERAGE_INVENTORY_JSON)
    module_coverage_policy = _load_yaml(
        repo_root, "configs/quality/module_coverage_gates.yaml"
    )
    hotspot_family = _load_json(repo_root, HOTSPOT_FAMILY_BASELINE_JSON)
    compatibility = _load_json(repo_root, COMPATIBILITY_IMPORTER_CENSUS_JSON)
    dead_code = _load_json(repo_root, "reports/quality/dead-code-inventory.json")
    contract_matrix = _load_json(
        repo_root, "reports/quality/contract-coverage-matrix.json"
    )
    contract_diagnostics = _load_json(
        repo_root, "reports/quality/contract-registry-diagnostics.json"
    )
    dq_diagnostics = build_contract_registry_dq_diagnostics(repo_root)
    config_discrepancy = _load_json(repo_root, CONFIG_DISCREPANCY_BASELINE_JSON)
    test_governance = _load_json(repo_root, TEST_GOVERNANCE_CURRENT_JSON)
    runtime_cardinality = _load_json(repo_root, RUNTIME_CARDINALITY_INVENTORY_JSON)
    observability_governance = _load_yaml(
        repo_root,
        "configs/quality/observability_metric_governance.yaml",
    )
    runtime_review = _load_json(repo_root, RUNTIME_CARDINALITY_REVIEW_JSON)
    runtime_uuid = _load_yaml(repo_root, RUNTIME_UUID_SEAMS_YAML)
    adr_matrix = _load_json(repo_root, ADR_ENFORCEMENT_MATRIX_JSON)
    remote_baseline = _load_json(
        repo_root,
        ARCHITECTURE_DEBT_REMOTE_MAIN_BASELINE_JSON,
    )
    changed_paths = _collect_changed_paths(
        repo_root,
        changed_from_ref=changed_from_ref,
    )
    scorecard = load_debt_scorecard()

    coverage_summary = module_coverage["summary"]
    coverage_status_counts = coverage_summary["status_counts"]
    module_coverage_hash_gate = _module_coverage_source_tree_hash_gate(
        module_coverage,
        repo_root=repo_root,
    )
    remote_main_baseline_gate = _remote_main_baseline_gate(remote_baseline)

    gates: list[Gate] = []
    gates.extend(_debt_scorecard_gates())
    gates.append(flaky_review_preflight_gate)
    gates.append(
        _debt_scorecard_budget_no_growth_gate(
            repo_root=repo_root,
            changed_from_ref=changed_from_ref,
        )
    )
    gates.append(module_coverage_hash_gate)
    gates.append(
        _module_coverage_scorecard_coherence_gate(
            architecture_scorecard,
            module_coverage,
        )
    )
    gates.extend(
        _module_coverage_residual_gates(
            coverage_summary=coverage_summary,
            status_counts=coverage_status_counts,
            aggregate_residual_limits=_module_coverage_aggregate_residual_limits(
                module_coverage_policy
            ),
        )
    )
    gates.extend(
        _hotspot_and_compatibility_gates(
            hotspot_family=hotspot_family,
            compatibility=compatibility,
            architecture_scorecard=architecture_scorecard,
        )
    )
    gates.extend(
        _dead_code_and_contract_gates(
            dead_code=dead_code,
            contract_matrix=contract_matrix,
            contract_diagnostics=contract_diagnostics,
            dq_diagnostics=dq_diagnostics,
        )
    )
    gates.extend(_config_discrepancy_gates(config_discrepancy))
    gates.extend(_full_app_duplication_gates(repo_root=repo_root, scorecard=scorecard))
    gates.extend(_supporting_scripts_gates(repo_root=repo_root, scorecard=scorecard))
    gates.extend(
        _test_governance_and_flaky_gates(
            test_governance=test_governance,
            flaky_review=flaky_review,
        )
    )
    gates.extend(_runtime_uuid_gates(runtime_uuid))
    gates.extend(_observability_cardinality_list_gates(runtime_cardinality))
    gates.extend(
        _observability_review_and_touch_gates(
            runtime_cardinality=runtime_cardinality,
            runtime_review=runtime_review,
            observability_governance=observability_governance,
            changed_paths=changed_paths,
            repo_root=repo_root,
        )
    )
    gates.append(
        _hard_limit_gate(
            name="adr_enforcement_blocking_gaps",
            metric="blocking_gap_count",
            current=adr_matrix["summary"]["blocking_gap_count"],
            limit=0,
            source_artifact=ADR_ENFORCEMENT_MATRIX_JSON,
            remediation=(
                "Add enforcement owner tests/scripts or reviewed manual exception "
                "markers for accepted ADRs."
            ),
        )
    )
    gates.append(remote_main_baseline_gate)

    stale_artifacts = _collect_stale_artifacts(
        repo_root=repo_root,
        module_coverage_hash_gate=module_coverage_hash_gate,
        remote_main_baseline_gate=remote_main_baseline_gate,
    )
    stale_count = sum(1 for stale in stale_artifacts.values() if stale)
    stale_names = sorted(name for name, is_stale in stale_artifacts.items() if is_stale)
    gates.append(
        Gate(
            name="generated_artifact_drift",
            status="pass" if stale_count == 0 else "fail",
            metric="stale_artifact_count",
            current={"count": stale_count, "artifacts": stale_names},
            limit=0,
            source_artifact="reports/quality/*.json",
            remediation=(
                "Regenerate stale quality artifacts with their canonical QA commands: "
                + (", ".join(stale_names) if stale_names else "none")
            ),
        )
    )

    status_counts = _gate_status_counts(gates)
    failing_gates = [gate.name for gate in gates if gate.status == "fail"]
    warning_gates = [gate.name for gate in gates if gate.status == "warn"]
    return {
        "schema_version": 1,
        "generated_by": "scripts.engineering.qa.report_debt_governance_gates",
        "linked_issue_refresh_policy": "#7465",
        "input_artifacts": list(DEBT_GATE_INPUT_ARTIFACTS),
        "refresh_commands": [
            "python -m scripts.engineering.qa.refresh_governance_artifacts",
            "python -m scripts.engineering.qa report-debt-governance-gates --update",
            "python -m scripts.engineering.qa report-debt-governance-gates --check",
        ],
        "summary": {
            "gate_count": len(gates),
            "pass_count": status_counts["pass"],
            "warn_count": status_counts["warn"],
            "fail_count": status_counts["fail"],
            "release_gate_status": _release_gate_status(status_counts),
            "architecture_quality_scorecard_integral_score": architecture_scorecard[
                "integral_score"
            ],
            "architecture_quality_scorecard_interpretation": architecture_scorecard[
                "interpretation"
            ],
            "failing_gates": failing_gates,
            "warning_gates": warning_gates,
        },
        "status_counts": status_counts,
        "stale_artifacts": stale_artifacts,
        "gates": [gate.as_dict() for gate in gates],
    }


def main(argv: list[str] | None = None) -> int:
    """Compatibility entrypoint for `python -m scripts.engineering.qa report-debt-governance-gates`."""
    from scripts.engineering.qa.debt_governance_gate_report import main as _gate_main

    return _gate_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
