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


def _count(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return len(value)
    if isinstance(value, tuple):
        return len(value)
    if value is None:
        return 0
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"Unsupported count value: {value!r}")


def _is_budget_key(key: str) -> bool:
    lowered = key.lower()
    return (
        lowered in BUDGET_KEY_NAMES
        or lowered.startswith("max_")
        or lowered.endswith("_budget")
        or lowered.endswith("_cap")
        or lowered.endswith("_limit")
        or lowered.endswith("_threshold")
    )


def _collect_budget_numbers(
    payload: object,
    *,
    prefix: tuple[str, ...] = (),
) -> dict[str, int | float]:
    numbers: dict[str, int | float] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            next_prefix = (*prefix, key_text)
            if (
                _is_budget_key(key_text)
                and isinstance(value, int | float)
                and not isinstance(value, bool)
            ):
                numbers[".".join(next_prefix)] = value
            elif isinstance(value, dict | list):
                numbers.update(_collect_budget_numbers(value, prefix=next_prefix))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            if isinstance(value, dict | list):
                numbers.update(
                    _collect_budget_numbers(value, prefix=(*prefix, str(index)))
                )
    return numbers


def _budget_growth_increases(
    *,
    baseline_payload: dict[str, Any],
    current_payload: dict[str, Any],
) -> dict[str, dict[str, int | float | None]]:
    baseline = _collect_budget_numbers(baseline_payload)
    current = _collect_budget_numbers(current_payload)
    increases: dict[str, dict[str, int | float | None]] = {}
    for path, current_value in sorted(current.items()):
        baseline_value = baseline.get(path)
        if baseline_value is None:
            if current_value > 0:
                increases[path] = {"from": None, "to": current_value}
            continue
        if current_value > baseline_value:
            increases[path] = {"from": baseline_value, "to": current_value}
    return increases


def _debt_scorecard_budget_no_growth_gate(
    *,
    repo_root: Path,
    changed_from_ref: str | None,
) -> Gate:
    if not changed_from_ref:
        return Gate(
            name="debt_scorecard_budget_no_growth",
            status="pass",
            metric="budget_increase_count",
            current="not_evaluated_without_changed_from_ref",
            limit=0,
            source_artifact=DEBT_SCORECARD_PATH,
            remediation=(
                "Run with --changed-from-ref in CI so scorecard budgets cannot grow."
            ),
        )

    baseline_payload = _load_yaml_from_git_ref(
        repo_root,
        changed_from_ref,
        DEBT_SCORECARD_PATH,
    )
    if baseline_payload is None:
        return Gate(
            name="debt_scorecard_budget_no_growth",
            status="fail",
            metric="budget_increase_count",
            current="baseline_unavailable",
            limit=0,
            source_artifact=DEBT_SCORECARD_PATH,
            remediation=("Fetch the changed-from ref and rerun debt-governance gates."),
        )

    increases = _budget_growth_increases(
        baseline_payload=baseline_payload,
        current_payload=_load_yaml(repo_root, DEBT_SCORECARD_PATH),
    )
    return Gate(
        name="debt_scorecard_budget_no_growth",
        status="pass" if not increases else "fail",
        metric="budget_increase_count",
        current=increases if increases else 0,
        limit=0,
        source_artifact=DEBT_SCORECARD_PATH,
        remediation=(
            "Lower or revert increased scorecard budgets; debt budgets must be "
            "flat or decreasing."
        ),
    )


def _flaky_untriaged_entries(review: dict[str, Any]) -> list[object]:
    entries = review.get("reviewed_flaky_tests", [])
    if not isinstance(entries, list):
        return [{"error": "reviewed_flaky_tests_not_a_list"}]
    untriaged: list[object] = []
    for entry in entries:
        if not isinstance(entry, dict):
            untriaged.append(entry)
            continue
        status = str(entry.get("triage_status", "")).strip().lower()
        if status in UNTRIAGED_FLAKY_STATUSES:
            untriaged.append(entry)
    return untriaged


def _hard_limit_gate(
    *,
    name: str,
    metric: str,
    current: object,
    limit: object,
    source_artifact: str,
    remediation: str,
) -> Gate:
    status = "pass" if _count(current) <= _count(limit) else "fail"
    return Gate(
        name=name,
        status=status,
        metric=metric,
        current=current,
        limit=limit,
        source_artifact=source_artifact,
        remediation=remediation,
    )


def _warn_limit_gate(
    *,
    name: str,
    metric: str,
    current: object,
    limit: object,
    source_artifact: str,
    remediation: str,
) -> Gate:
    status = "pass" if _count(current) <= _count(limit) else "warn"
    return Gate(
        name=name,
        status=status,
        metric=metric,
        current=current,
        limit=limit,
        source_artifact=source_artifact,
        remediation=remediation,
    )


def _artifact_matches(
    *,
    repo_root: Path,
    rel_path: str,
    live_payload: dict[str, object],
) -> bool:
    try:
        committed = _load_json(repo_root, rel_path)
    except FileNotFoundError:
        return False
    return committed == live_payload


def _payload_without_volatile_fields(
    payload: dict[str, object],
    *,
    drop_keys: frozenset[str],
) -> dict[str, object]:
    """Return a shallow copy without volatile metadata keys."""
    return {key: value for key, value in payload.items() if key not in drop_keys}


def _artifact_matches_builder(
    *,
    repo_root: Path,
    rel_path: str,
    payload_builder: Callable[[], dict[str, object]],
) -> bool:
    """Return False when a live artifact builder cannot be evaluated locally."""
    try:
        live_payload = payload_builder()
    except Exception:
        return False
    if not isinstance(live_payload, dict):
        return False
    return _artifact_matches(
        repo_root=repo_root,
        rel_path=rel_path,
        live_payload=live_payload,
    )


def _hotspot_family_baseline_artifact_matches_builder(*, repo_root: Path) -> bool:
    """Verify both hotspot-family artifacts against a fresh live source census."""
    try:
        live_payload, live_markdown = report_hotspot_family_baseline.build_artifacts()
        live_json = json.dumps(live_payload, ensure_ascii=False, indent=2) + "\n"
        committed_json = (repo_root / HOTSPOT_FAMILY_BASELINE_JSON).read_text(
            encoding="utf-8"
        )
        committed_markdown = (
            repo_root / "reports/quality/hotspot-family-baseline.md"
        ).read_text(encoding="utf-8")
    except Exception:
        return False
    return committed_json == live_json and committed_markdown == live_markdown


def _remote_main_baseline_artifact_matches_builder(*, repo_root: Path) -> bool | None:
    try:
        live_payload = report_architecture_debt_remote_main_baseline.build_payload(
            repo_root=repo_root
        )
        committed = _load_json(repo_root, ARCHITECTURE_DEBT_REMOTE_MAIN_BASELINE_JSON)
    except subprocess.CalledProcessError:
        return None
    except RuntimeError as exc:
        if "Could not resolve" in str(exc):
            return None
        return False
    except Exception:
        return False
    return (
        report_architecture_debt_remote_main_baseline.payloads_semantically_equivalent(
            committed, live_payload
        )
    )


def _unavailable_required_remote_baseline_artifacts(
    remote_baseline: dict[str, Any],
) -> list[dict[str, Any]]:
    remote_artifacts = remote_baseline["artifacts"]
    required_remote_baseline_paths = set(
        report_architecture_debt_remote_main_baseline.REQUIRED_BASELINE_ARTIFACTS
    )
    return [
        row
        for row in remote_artifacts
        if isinstance(row, dict)
        and row.get("path") in required_remote_baseline_paths
        and row.get("required_on_remote", row.get("required", True))
        and isinstance(row.get("summary"), dict)
        and not row["summary"].get("available")
    ]


def _parse_generated_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _release_review_freshness_gate(
    runtime_review: dict[str, Any],
    *,
    now: datetime | None = None,
) -> Gate:
    generated_at = _parse_generated_at(runtime_review.get("generated_at"))
    if generated_at is None:
        return Gate(
            name="observability_release_review_freshness",
            status="fail",
            metric="generated_at_age_days",
            current="missing_or_invalid",
            limit=RELEASE_REVIEW_MAX_AGE_DAYS,
            source_artifact=RUNTIME_CARDINALITY_REVIEW_JSON,
            remediation="Regenerate live runtime cardinality review evidence.",
        )

    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    age_days = (current_time - generated_at).days
    return Gate(
        name="observability_release_review_freshness",
        status=("pass" if 0 <= age_days <= RELEASE_REVIEW_MAX_AGE_DAYS else "fail"),
        metric="generated_at_age_days",
        current=age_days,
        limit=RELEASE_REVIEW_MAX_AGE_DAYS,
        source_artifact=RUNTIME_CARDINALITY_REVIEW_JSON,
        remediation="Regenerate live runtime cardinality review evidence.",
    )


def _release_gate_status(status_counts: dict[str, int]) -> str:
    """Return the release-gate status implied by normalized fail-fast gates."""
    if status_counts["fail"] > 0:
        return "failing"
    if status_counts["warn"] > 0:
        return "warning"
    return "passing"


def _module_coverage_source_tree_hash_gate(
    module_coverage: dict[str, Any],
    *,
    repo_root: Path,
) -> Gate:
    expected_hash = str(module_coverage.get("source_tree_sha256") or "")
    refreshed_inventory = _refresh_existing_inventory_source_tree(
        module_coverage,
        repo_root=repo_root,
    )
    current_hash = str(refreshed_inventory.get("source_tree_sha256") or "")
    is_current = bool(expected_hash) and expected_hash == current_hash
    return Gate(
        name="module_coverage_source_tree_hash_current",
        status="pass" if is_current else "fail",
        metric="source_tree_sha256",
        current=current_hash,
        limit=expected_hash or "missing",
        source_artifact=MODULE_COVERAGE_INVENTORY_JSON,
        remediation=(
            "Regenerate module coverage inventory before release gate closeout."
        ),
    )


def _module_coverage_scorecard_coherence_gate(
    architecture_scorecard: dict[str, Any],
    module_coverage: dict[str, Any],
) -> Gate:
    """Verify module-coverage metrics agree across scorecard and inventory."""
    coverage_summary = module_coverage.get("summary", {})
    scorecard_metrics = architecture_scorecard.get("metrics", {})
    source_artifacts = architecture_scorecard.get("source_artifacts", {})
    coverage_source = source_artifacts.get("module_coverage_inventory", {})

    expected = {
        "source_module_count": coverage_summary.get("source_module_count"),
        "unmeasured_module_count": coverage_summary.get("unmeasured_module_count"),
        "uncovered_module_count": coverage_summary.get("uncovered_module_count"),
        "source_tree_sha256": module_coverage.get("source_tree_sha256"),
    }
    current = {
        "source_module_count": scorecard_metrics.get("source_module_count"),
        "unmeasured_module_count": scorecard_metrics.get("unmeasured_module_count"),
        "uncovered_module_count": scorecard_metrics.get("uncovered_module_count"),
        "source_tree_sha256": coverage_source.get("source_tree_sha256"),
    }
    aligned = all(current.get(key) == expected.get(key) for key in expected)
    return Gate(
        name="module_coverage_scorecard_coherence",
        status="pass" if aligned else "fail",
        metric="module_coverage_scorecard_alignment",
        current=current,
        limit=expected,
        source_artifact=(
            "reports/quality/module-coverage-inventory.json + "
            "reports/quality/architecture-quality-scorecard.json"
        ),
        remediation=(
            "Refresh architecture-quality scorecard and module coverage inventory "
            "until counts and source-tree hash match."
        ),
    )


def _compatibility_scorecard_coherence_gate(
    architecture_scorecard: dict[str, Any],
    compatibility: dict[str, Any],
) -> Gate:
    """Verify sanctioned compatibility metrics agree across scorecard and census."""
    compatibility_summary = compatibility.get("summary", {})
    scorecard_metrics = architecture_scorecard.get("metrics", {})
    expected = {
        "retained_entrypoint_count": compatibility_summary.get(
            "retained_entrypoint_count"
        ),
        "retained_public_export_facade_count": compatibility_summary.get(
            "retained_public_export_facade_count"
        ),
        "twin_pair_count": compatibility_summary.get("twin_pair_count"),
    }
    current = {
        "retained_entrypoint_count": scorecard_metrics.get("retained_entrypoint_count"),
        "retained_public_export_facade_count": scorecard_metrics.get(
            "retained_public_export_facade_count"
        ),
        "twin_pair_count": scorecard_metrics.get("twin_pair_count"),
    }
    aligned = all(current.get(key) == expected.get(key) for key in expected)
    return Gate(
        name="compatibility_scorecard_coherence",
        status="pass" if aligned else "fail",
        metric="compatibility_scorecard_alignment",
        current=current,
        limit=expected,
        source_artifact=(
            "reports/quality/compatibility-importer-census.json + "
            "reports/quality/architecture-quality-scorecard.json"
        ),
        remediation=(
            "Refresh compatibility importer census and architecture-quality "
            "scorecard until sanctioned compatibility metrics match."
        ),
    )


def _module_coverage_aggregate_residual_limits(
    policy: dict[str, Any],
) -> dict[str, int] | None:
    ratchets = policy.get("aggregate_residual_ratchets")
    if not isinstance(ratchets, dict):
        return None
    unmeasured = ratchets.get("unmeasured_module_count")
    uncovered = ratchets.get("uncovered_module_count")
    if not isinstance(unmeasured, dict) or not isinstance(uncovered, dict):
        return None
    unmeasured_limit = unmeasured.get("max_count")
    uncovered_limit = uncovered.get("max_count")
    if not isinstance(unmeasured_limit, int) or not isinstance(uncovered_limit, int):
        return None
    return {
        "unmeasured_module_count": unmeasured_limit,
        "uncovered_module_count": uncovered_limit,
    }


def _collect_changed_paths(
    repo_root: Path, *, changed_from_ref: str | None
) -> set[str]:
    if not changed_from_ref:
        return set()
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    # Ref is operator-supplied git rev; refuse shell metacharacters.
    ref = str(changed_from_ref)
    if any(ch in ref for ch in ";&|><`$(){} \n\r"):
        raise ValueError(f"refusing unsafe git ref for path collection: {ref!r}")
    result = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
        ensure_safe_cli_argv(
            [
                "git",
                "-C",
                repo_root.as_posix(),
                "diff",
                "--name-only",
                f"{ref}...HEAD",
            ]
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _string_paths_from(values: object) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(path) for path in values if isinstance(path, str) and path.strip()}


def _paths_from_emitter_lists(field_mapping: object) -> set[str]:
    if not isinstance(field_mapping, dict):
        return set()
    paths: set[str] = set()
    for emitters in field_mapping.values():
        if not isinstance(emitters, list):
            continue
        for emitter_path in emitters:
            if isinstance(emitter_path, str) and emitter_path.strip():
                paths.add(emitter_path)
    return paths


def _emitter_paths_from_fields(
    runtime_cardinality: dict[str, Any],
    field_names: object,
) -> set[str]:
    trigger_paths: set[str] = set()
    if not isinstance(field_names, list):
        return trigger_paths
    for field_name in field_names:
        if not isinstance(field_name, str):
            continue
        trigger_paths.update(
            _paths_from_emitter_lists(runtime_cardinality.get(field_name, {}))
        )
    return trigger_paths


def _collect_metric_change_trigger_paths(
    runtime_cardinality: dict[str, Any],
    observability_governance: dict[str, Any],
) -> set[str]:
    runtime_review = observability_governance.get("runtime_cardinality_review", {})
    if not isinstance(runtime_review, dict):
        return set()
    live_evidence = runtime_review.get("live_evidence", {})
    if not isinstance(live_evidence, dict):
        return set()
    change_gate = live_evidence.get("touched_metric_change_gate", {})
    if not isinstance(change_gate, dict):
        return set()

    trigger_paths = _string_paths_from(
        change_gate.get("changed_path_trigger_static_paths", [])
    )
    trigger_paths.update(
        _string_paths_from(change_gate.get("changed_path_trigger_prefixes", []))
    )
    trigger_paths.update(
        _emitter_paths_from_fields(
            runtime_cardinality, change_gate.get("changed_path_trigger_fields", [])
        )
    )
    return trigger_paths


def _matching_touched_metric_paths(
    *,
    changed_paths: set[str],
    trigger_paths: set[str],
) -> list[str]:
    relevant_paths: set[str] = set()
    normalized_triggers = {
        trigger_path.replace("\\", "/")
        for trigger_path in trigger_paths
        if trigger_path.strip()
    }
    for changed_path in changed_paths:
        normalized_changed = changed_path.replace("\\", "/")
        for trigger_path in normalized_triggers:
            if normalized_changed == trigger_path:
                relevant_paths.add(changed_path)
                break
            if trigger_path.endswith("/") and normalized_changed.startswith(
                trigger_path
            ):
                relevant_paths.add(changed_path)
                break
    return sorted(relevant_paths)


def _observability_touched_metric_inventory_gate(
    runtime_cardinality: dict[str, Any],
    *,
    changed_paths: set[str],
    trigger_paths: set[str],
    repo_root: Path,
    current_inventory: dict[str, Any] | None = None,
) -> Gate:
    relevant_paths = _matching_touched_metric_paths(
        changed_paths=changed_paths,
        trigger_paths=trigger_paths,
    )
    if not relevant_paths:
        return Gate(
            name="observability_touched_metric_inventory_freshness",
            status="pass",
            metric="changed_metric_surface_count",
            current=0,
            limit=0,
            source_artifact=RUNTIME_CARDINALITY_INVENTORY_JSON,
            remediation=(
                "Refresh runtime cardinality inventory evidence before merging "
                "metric, dashboard, or alert-rule changes."
            ),
        )

    if current_inventory is None:
        try:
            current_inventory = (
                report_observability_metric_inventory.collect_metric_inventory(
                    repo_root
                )
            )
        except Exception:
            current_inventory = None

    inventory_is_current = (
        isinstance(current_inventory, dict) and runtime_cardinality == current_inventory
    )
    return Gate(
        name="observability_touched_metric_inventory_freshness",
        status="pass" if inventory_is_current else "fail",
        metric="inventory_matches_current_static_report",
        current=inventory_is_current,
        limit=True,
        source_artifact=RUNTIME_CARDINALITY_INVENTORY_JSON,
        remediation=(
            "Regenerate reports/observability/runtime_cardinality_inventory.json "
            "before merging metric, dashboard, or alert-rule changes."
        ),
    )


def _observability_touched_metric_review_gate(
    runtime_review: dict[str, Any],
    *,
    changed_paths: set[str],
    trigger_paths: set[str],
    now: datetime | None = None,
) -> Gate:
    relevant_paths = _matching_touched_metric_paths(
        changed_paths=changed_paths,
        trigger_paths=trigger_paths,
    )
    if not relevant_paths:
        return Gate(
            name="observability_touched_metric_review_freshness",
            status="pass",
            metric="changed_metric_surface_count",
            current=0,
            limit=0,
            source_artifact=RUNTIME_CARDINALITY_REVIEW_JSON,
            remediation=(
                "Refresh live runtime cardinality review evidence before merging "
                "metric, dashboard, or alert-rule changes."
            ),
        )

    freshness_gate = _release_review_freshness_gate(runtime_review, now=now)
    review_status = str(runtime_review.get("status", "missing"))
    healthy_review = freshness_gate.status == "pass" and review_status == "passed"
    return Gate(
        name="observability_touched_metric_review_freshness",
        status="pass" if healthy_review else "fail",
        metric="changed_metric_surface_count",
        current=len(relevant_paths),
        limit=0,
        source_artifact=RUNTIME_CARDINALITY_REVIEW_JSON,
        remediation=(
            "Refresh live runtime cardinality review evidence before merging "
            "metric, dashboard, or alert-rule changes."
        ),
    )


def _debt_scorecard_gates() -> list[Gate]:
    violations, summary = evaluate_debt_scorecard()
    violation_count = len(violations)
    gates = [
        _hard_limit_gate(
            name="debt_scorecard_budget_violations",
            metric="violation_count",
            current=violation_count,
            limit=0,
            source_artifact=DEBT_SCORECARD_PATH,
            remediation=(
                "Reduce exemptions or ratchet budgets downward; debt budgets must not grow."
            ),
        )
    ]
    scorecard = load_debt_scorecard()
    compatibility_metrics = scorecard.get("compatibility_debt_metrics", {})
    if isinstance(compatibility_metrics, dict):
        metrics = compatibility_metrics.get("metrics", {})
    else:
        metrics = {}
    if not isinstance(metrics, dict):
        metrics = {}
    retained = metrics.get("retained_public_entrypoint_burden", {})
    retained_limit = retained.get("max_count", 0) if isinstance(retained, dict) else 0
    retained_current = (
        retained.get("current_count", 0) if isinstance(retained, dict) else 0
    )
    gates.append(
        _hard_limit_gate(
            name="retained_public_entrypoint_burden",
            metric="current_count",
            current=retained_current,
            limit=retained_limit,
            source_artifact="configs/quality/debt_scorecard.yaml#compatibility_debt_metrics",
            remediation=(
                "Remove retained public entrypoints or lower callers before tightening max_count."
            ),
        )
    )
    gates.append(
        Gate(
            name="debt_budget_growth_policy",
            status="pass" if summary is not None and violation_count == 0 else "fail",
            metric="budget_growth_allowed",
            current=False,
            limit=False,
            source_artifact=DEBT_SCORECARD_PATH,
            remediation="Keep scorecard ratchets non-increasing and fix validation violations.",
        )
    )
    return gates


def _module_coverage_residual_gates(
    *,
    coverage_summary: dict[str, Any],
    status_counts: dict[str, Any],
    aggregate_residual_limits: dict[str, int] | None,
) -> list[Gate]:
    """Build residual unmeasured/uncovered module coverage gates."""
    if aggregate_residual_limits is None:
        return [
            _warn_limit_gate(
                name="module_coverage_unmeasured_modules",
                metric="unmeasured_module_count",
                current=coverage_summary["unmeasured_module_count"],
                limit=0,
                source_artifact=MODULE_COVERAGE_INVENTORY_JSON,
                remediation=(
                    "Refresh coverage evidence and add coverage owner tests "
                    "for unmeasured modules."
                ),
            ),
            _warn_limit_gate(
                name="module_coverage_uncovered_modules",
                metric="uncovered_module_count",
                current=status_counts.get("uncovered", 0),
                limit=0,
                source_artifact=MODULE_COVERAGE_INVENTORY_JSON,
                remediation="Add coverage or classify modules before closeout.",
            ),
        ]
    return [
        _hard_limit_gate(
            name="module_coverage_unmeasured_modules",
            metric="unmeasured_module_count",
            current=coverage_summary["unmeasured_module_count"],
            limit=aggregate_residual_limits["unmeasured_module_count"],
            source_artifact=(
                "configs/quality/module_coverage_gates.yaml#aggregate_residual_ratchets"
            ),
            remediation=(
                "Keep reviewed unmeasured-module residual at or below the "
                "committed no-growth ratchet."
            ),
        ),
        _hard_limit_gate(
            name="module_coverage_uncovered_modules",
            metric="uncovered_module_count",
            current=status_counts.get("uncovered", 0),
            limit=aggregate_residual_limits["uncovered_module_count"],
            source_artifact=(
                "configs/quality/module_coverage_gates.yaml#aggregate_residual_ratchets"
            ),
            remediation=(
                "Keep reviewed uncovered-module residual at or below the "
                "committed no-growth ratchet."
            ),
        ),
    ]


def _hotspot_and_compatibility_gates(
    *,
    hotspot_family: dict[str, Any],
    compatibility: dict[str, Any],
    architecture_scorecard: dict[str, Any],
) -> list[Gate]:
    """Build hotspot-family and compatibility importer gates."""
    hotspot_summary = hotspot_family["summary"]
    budget_warnings = int(hotspot_summary.get("budget_warnings", 0))
    compatibility_summary = compatibility["summary"]
    return [
        Gate(
            name="hotspot_family_baseline_budget_warnings",
            status="fail" if budget_warnings else "pass",
            metric="budget_warnings",
            current=budget_warnings,
            limit=0,
            source_artifact=HOTSPOT_FAMILY_BASELINE_JSON,
            remediation=(
                "Reduce hotspot-family metrics to stay at or below reviewed budgets."
            ),
        ),
        _hard_limit_gate(
            name="compatibility_twin_pairs",
            metric="twin_pair_count",
            current=compatibility_summary["twin_pair_count"],
            limit=0,
            source_artifact=COMPATIBILITY_IMPORTER_CENSUS_JSON,
            remediation=(
                "Retire twin modules or add explicit reviewed governance before closeout."
            ),
        ),
        _hard_limit_gate(
            name="retained_public_export_facade_growth",
            metric="retained_public_export_facade_count",
            current=compatibility_summary["retained_public_export_facade_count"],
            limit=architecture_scorecard["metrics"][
                "retained_public_export_facade_count"
            ],
            source_artifact=COMPATIBILITY_IMPORTER_CENSUS_JSON,
            remediation=(
                "Remove facade exports or update the scorecard only after "
                "approved reduction evidence."
            ),
        ),
        _compatibility_scorecard_coherence_gate(
            architecture_scorecard,
            compatibility,
        ),
    ]


def _dead_code_and_contract_gates(
    *,
    dead_code: dict[str, Any],
    contract_matrix: dict[str, Any],
    contract_diagnostics: dict[str, Any],
    dq_diagnostics: dict[str, Any],
) -> list[Gate]:
    """Build dead-code and contract-registry residual gates."""
    dead_code_summary = dead_code["summary"]
    return [
        _hard_limit_gate(
            name="dead_code_untriaged_zero_import_candidates",
            metric="repo_wide_untriaged_zero_import_candidate_count",
            current=dead_code_summary[
                "repo_wide_untriaged_zero_import_candidate_count"
            ],
            limit=0,
            source_artifact="reports/quality/dead-code-inventory.json",
            remediation=(
                "Classify zero-import candidates and attach owner tests before closeout."
            ),
        ),
        _hard_limit_gate(
            name="contract_coverage_missing_gold_enabled",
            metric="missing_gold_enabled_count",
            current=contract_matrix["missing_gold_enabled_count"],
            limit=0,
            source_artifact="reports/quality/contract-coverage-matrix.json",
            remediation=(
                "Add missing Gold contracts or mark Gold runtime disabled explicitly."
            ),
        ),
        _hard_limit_gate(
            name="contract_registry_blocking_drift",
            metric="blocking_issue_count",
            current=contract_diagnostics["blocking_issue_count"],
            limit=0,
            source_artifact="reports/quality/contract-registry-diagnostics.json",
            remediation="Fix contract registry blocking diagnostics.",
        ),
        _hard_limit_gate(
            name="dq_contract_registry_blocking_drift",
            metric="blocking_issue_count",
            current=dq_diagnostics["blocking_issue_count"],
            limit=0,
            source_artifact=(
                "scripts/engineering/ci/validate_registry_dq_refs.py::"
                "build_diagnostics_payload"
            ),
            remediation="Fix DQ contract diagnostics before closeout.",
        ),
    ]


def _config_discrepancy_gates(config_discrepancy: dict[str, Any]) -> list[Gate]:
    """Build config-discrepancy residual gates."""
    config_metrics = config_discrepancy["metrics"]
    return [
        _hard_limit_gate(
            name="config_discrepancy_inconsistent_parameters",
            metric="inconsistent_parameter_count",
            current=config_metrics["inconsistent_parameter_count"],
            limit=0,
            source_artifact=CONFIG_DISCREPANCY_BASELINE_JSON,
            remediation=(
                "Resolve config parameter drift or update sanctioned partial "
                "classifications."
            ),
        ),
        _hard_limit_gate(
            name="config_discrepancy_raw_inconsistent_parameters",
            metric="raw_inconsistent_parameter_count",
            current=config_metrics["raw_inconsistent_parameter_count"],
            limit=0,
            source_artifact=CONFIG_DISCREPANCY_BASELINE_JSON,
            remediation="Regenerate the config matrix only after resolving raw drift.",
        ),
    ]


def _family_duplication_current(
    *,
    targets: dict[str, int],
    path_prefix: str,
) -> int:
    """Max duplicate count for targets under ``path_prefix``."""
    prefix = path_prefix.rstrip("/")
    return max(count for target, count in targets.items() if target.startswith(prefix))


def _full_app_family_duplication_gates(
    *,
    families: object,
    targets: dict[str, int],
    baseline_artifact: str,
) -> list[Gate]:
    """Build per-family full-app duplication ratchet gates."""
    gates: list[Gate] = []
    if not isinstance(families, list):
        return gates
    for family in families:
        if not isinstance(family, dict):
            continue
        metrics = family.get("metrics", {})
        duplication = (
            metrics.get("duplication_clusters", {}) if isinstance(metrics, dict) else {}
        )
        max_count = (
            duplication.get("max_count") if isinstance(duplication, dict) else None
        )
        path_prefix = family.get("path_prefix")
        if not isinstance(max_count, int) or not isinstance(path_prefix, str):
            continue
        gates.append(
            _hard_limit_gate(
                name=f"full_app_duplication_{family.get('name')}",
                metric="duplication_clusters",
                current=_family_duplication_current(
                    targets=targets, path_prefix=path_prefix
                ),
                limit=max_count,
                source_artifact=baseline_artifact,
                remediation=(
                    "Reduce duplicate clusters and regenerate the full-app "
                    "duplication baseline without raising scorecard budgets."
                ),
            )
        )
    return gates


def _full_app_duplication_gates(
    *,
    repo_root: Path,
    scorecard: dict[str, Any],
) -> list[Gate]:
    """Build full-app duplication ratchet gates from the debt scorecard."""
    gates: list[Gate] = []
    full_app_policy = scorecard.get("full_app_duplication_ratchets", {})
    if not isinstance(full_app_policy, dict):
        return gates
    artifact_policy = full_app_policy.get("artifact_policy", {})
    baseline_artifact = (
        artifact_policy.get("baseline_artifact")
        if isinstance(artifact_policy, dict)
        else None
    )
    if not isinstance(baseline_artifact, str):
        return gates
    full_app_baseline = _load_json(repo_root, baseline_artifact)
    targets = {
        str(row["target"]): int(row["duplicate_count"])
        for row in full_app_baseline.get("targets", [])
        if isinstance(row, dict) and isinstance(row.get("target"), str)
    }
    gates.extend(
        _full_app_family_duplication_gates(
            families=full_app_policy.get("families", []),
            targets=targets,
            baseline_artifact=baseline_artifact,
        )
    )
    summary_metrics = full_app_policy.get("summary_metrics", {})
    total_budget = (
        summary_metrics.get("total_duplicate_clusters", {})
        if isinstance(summary_metrics, dict)
        else {}
    )
    if isinstance(total_budget, dict) and isinstance(
        total_budget.get("max_count"), int
    ):
        summary = full_app_baseline.get("summary", {})
        current_total = (
            int(summary["total_duplicate_clusters"])
            if isinstance(summary, dict)
            else -1
        )
        gates.append(
            _hard_limit_gate(
                name="full_app_duplication_total_clusters",
                metric="total_duplicate_clusters",
                current=current_total,
                limit=int(total_budget["max_count"]),
                source_artifact=baseline_artifact,
                remediation=(
                    "Burn down full-app duplicate clusters and refresh the "
                    "reviewed baseline."
                ),
            )
        )
    return gates


def _script_zero_reference_counts(
    script_rows: object,
) -> tuple[int, int]:
    """Count zero-reference and untriaged zero-reference supporting scripts."""
    if not isinstance(script_rows, list):
        return 0, 0
    zero_ref_count = sum(
        1
        for row in script_rows
        if isinstance(row, dict) and row.get("reference_count") == 0
    )
    untriaged_count = sum(
        1
        for row in script_rows
        if isinstance(row, dict)
        and row.get("reference_count") == 0
        and (
            not row.get("owner")
            or not row.get("lifecycle_decision")
            or not row.get("review_by")
            or not row.get("next_step")
        )
    )
    return zero_ref_count, untriaged_count


def _supporting_scripts_gates(
    *,
    repo_root: Path,
    scorecard: dict[str, Any],
) -> list[Gate]:
    """Build supporting-scripts governance gates from the debt scorecard."""
    gates: list[Gate] = []
    scripts_policy = scorecard.get("supporting_scripts_governance", {})
    if not isinstance(scripts_policy, dict):
        return gates
    scripts_metrics = scripts_policy.get("metrics", {})
    if not isinstance(scripts_metrics, dict):
        return gates
    scripts_manifest = _load_json(repo_root, SCRIPTS_INVENTORY_MANIFEST_JSON)
    zero_ref_count, untriaged_count = _script_zero_reference_counts(
        scripts_manifest.get("scripts", [])
    )
    zero_ref_budget = scripts_metrics.get("zero_reference_supporting_script_count", {})
    untriaged_budget = scripts_metrics.get(
        "untriaged_zero_reference_supporting_script_count", {}
    )
    if isinstance(zero_ref_budget, dict) and isinstance(
        zero_ref_budget.get("max_count"), int
    ):
        gates.append(
            _hard_limit_gate(
                name="supporting_scripts_zero_reference_count",
                metric="zero_reference_supporting_script_count",
                current=zero_ref_count,
                limit=int(zero_ref_budget["max_count"]),
                source_artifact=SCRIPTS_INVENTORY_MANIFEST_JSON,
                remediation=(
                    "Triage or remove zero-reference supporting scripts; "
                    "budgets must not grow."
                ),
            )
        )
    if isinstance(untriaged_budget, dict) and isinstance(
        untriaged_budget.get("max_count"), int
    ):
        gates.append(
            _hard_limit_gate(
                name="supporting_scripts_untriaged_zero_reference_count",
                metric="untriaged_zero_reference_supporting_script_count",
                current=untriaged_count,
                limit=int(untriaged_budget["max_count"]),
                source_artifact=SCRIPTS_INVENTORY_MANIFEST_JSON,
                remediation=(
                    "Add owner/removal metadata for every zero-reference "
                    "supporting script."
                ),
            )
        )
    return gates


def _test_governance_and_flaky_gates(
    *,
    test_governance: dict[str, Any],
    flaky_review: dict[str, Any],
) -> list[Gate]:
    """Build test-governance and flaky-test residual gates."""
    test_report = test_governance["report"]
    flaky_summary = flaky_review.get("summary", {})
    total_flaky = (
        int(flaky_summary.get("total_flaky", 0))
        if isinstance(flaky_summary, dict)
        else 0
    )
    return [
        _hard_limit_gate(
            name="test_governance_budget_violations",
            metric="budget_violations",
            current=len(test_governance["budget_violations"]),
            limit=0,
            source_artifact=TEST_GOVERNANCE_CURRENT_JSON,
            remediation="Fix test governance budget violations before closeout.",
        ),
        _hard_limit_gate(
            name="test_governance_uuid4_call_sites",
            metric="uuid4_call_sites",
            current=test_report["uuid4_call_sites"],
            limit=0,
            source_artifact=TEST_GOVERNANCE_CURRENT_JSON,
            remediation=(
                "Replace uuid4 tests with deterministic factories or explicit IDs."
            ),
        ),
        _hard_limit_gate(
            name="flaky_test_total_count",
            metric="total_flaky",
            current=total_flaky,
            limit=0,
            source_artifact=FLAKY_TEST_REVIEW_PATH,
            remediation=(
                "Stabilize or explicitly quarantine flaky tests; default test "
                "paths must remain deterministic."
            ),
        ),
        _hard_limit_gate(
            name="flaky_test_untriaged_count",
            metric="untriaged_flaky_tests",
            current=len(_flaky_untriaged_entries(flaky_review)),
            limit=0,
            source_artifact=FLAKY_TEST_REVIEW_PATH,
            remediation=(
                "Every flaky candidate must have owner, triage status, and "
                "deterministic remediation metadata."
            ),
        ),
    ]


def _runtime_uuid_gates(runtime_uuid: dict[str, Any]) -> list[Gate]:
    """Build production uuid4 seam residual gates."""
    runtime_uuid_policy = runtime_uuid.get("policy", {})
    runtime_uuid_seams = runtime_uuid.get("seams", [])
    return [
        _hard_limit_gate(
            name="production_uuid4_seams",
            metric="seams",
            current=len(runtime_uuid_seams)
            if isinstance(runtime_uuid_seams, list)
            else 0,
            limit=0,
            source_artifact=RUNTIME_UUID_SEAMS_YAML,
            remediation=(
                "Remove production uuid4 seams; replay identity must be explicit "
                "or deterministic."
            ),
        ),
        _hard_limit_gate(
            name="production_uuid4_budget",
            metric="production_uuid4_budget",
            current=runtime_uuid_policy.get("production_uuid4_budget"),
            limit=0,
            source_artifact=RUNTIME_UUID_SEAMS_YAML,
            remediation="Keep production UUID4 budget at zero.",
        ),
    ]


def _observability_cardinality_list_gates(
    runtime_cardinality: dict[str, Any],
) -> list[Gate]:
    """Build residual list-count gates from runtime cardinality inventory."""
    specs = (
        (
            "observability_dashboarded_without_declaration",
            "dashboarded_without_declaration",
            "Declare dashboarded metrics or remove stale dashboard references.",
        ),
        (
            "observability_dashboarded_without_emission",
            "dashboarded_without_emission",
            "Add runtime emission for dashboarded metrics or remove dashboard references.",
        ),
        (
            "observability_alerted_without_emission",
            "alerted_without_emission",
            "Add runtime emission for alerted metrics or retire stale alert rules.",
        ),
        (
            "observability_unused_declared_metrics",
            "unused_declared_metrics",
            "Emit, retire, or explicitly allowlist unused declared metrics.",
        ),
        (
            "observability_runtime_cardinality_review_required",
            "runtime_cardinality_review_required",
            "Review high-cardinality metrics and record approved thresholds.",
        ),
        (
            "observability_runtime_cardinality_threshold_violations",
            "runtime_cardinality_threshold_violations",
            "Reduce label cardinality or explicitly approve bounded thresholds.",
        ),
    )
    return [
        _hard_limit_gate(
            name=name,
            metric=metric,
            current=len(runtime_cardinality[metric]),
            limit=0,
            source_artifact=RUNTIME_CARDINALITY_INVENTORY_JSON,
            remediation=remediation,
        )
        for name, metric, remediation in specs
    ]


def _observability_review_and_touch_gates(
    *,
    runtime_cardinality: dict[str, Any],
    runtime_review: dict[str, Any],
    observability_governance: dict[str, Any],
    changed_paths: set[str],
    repo_root: Path,
) -> list[Gate]:
    """Build release-review and metric-touch observability gates."""
    degraded_reasons = runtime_review.get("degraded_reasons", [])
    metric_change_trigger_paths = _collect_metric_change_trigger_paths(
        runtime_cardinality,
        observability_governance,
    )
    return [
        Gate(
            name="observability_release_review_status",
            status=(
                "pass"
                if runtime_review.get("status") == "passed" and not degraded_reasons
                else "fail"
            ),
            metric="status",
            current=runtime_review.get("status"),
            limit="passed",
            source_artifact=RUNTIME_CARDINALITY_REVIEW_JSON,
            remediation=(
                "Run live observability cardinality review without degraded "
                "release evidence."
            ),
        ),
        _release_review_freshness_gate(runtime_review),
        _observability_touched_metric_inventory_gate(
            runtime_cardinality,
            changed_paths=changed_paths,
            trigger_paths=metric_change_trigger_paths,
            repo_root=repo_root,
        ),
        _observability_touched_metric_review_gate(
            runtime_review,
            changed_paths=changed_paths,
            trigger_paths=metric_change_trigger_paths,
        ),
    ]


def _remote_main_baseline_gate(remote_baseline: dict[str, Any]) -> Gate:
    """Build remote-main architecture debt baseline gate."""
    unavailable_remote_artifacts = _unavailable_required_remote_baseline_artifacts(
        remote_baseline
    )
    return Gate(
        name="remote_main_architecture_debt_baseline",
        status=(
            "pass"
            if remote_baseline["evidence_source"] == "remote_main_git_tree"
            and remote_baseline["local_tracking_ref_matches_remote"]
            and not unavailable_remote_artifacts
            else "fail"
        ),
        metric="baseline_artifact_fingerprint",
        current=remote_baseline.get("baseline_artifact_fingerprint")
        or report_architecture_debt_remote_main_baseline.baseline_artifact_fingerprint(
            remote_baseline
        ),
        limit="clean remote-main artifact blobs",
        source_artifact=ARCHITECTURE_DEBT_REMOTE_MAIN_BASELINE_JSON,
        remediation=(
            "Fetch origin/main and regenerate the remote-main architecture debt baseline."
        ),
    )


def _config_surface_backlog_matches_builder(*, repo_root: Path) -> bool:
    """Compare config-surface backlog ignoring volatile snapshot_date."""
    try:
        live_payload = build_backlog()
        committed = _load_json(repo_root, "reports/quality/config-surface-backlog.json")
    except Exception:
        return False
    if not isinstance(live_payload, dict) or not isinstance(committed, dict):
        return False
    drop = frozenset({"snapshot_date"})
    return _payload_without_volatile_fields(
        committed, drop_keys=drop
    ) == _payload_without_volatile_fields(live_payload, drop_keys=drop)


def _in_test_mode() -> bool:
    """Return True when running under pytest."""
    return "pytest" in sys.modules or bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _collect_stale_artifacts(
    *,
    repo_root: Path,
    module_coverage_hash_gate: Gate,
    remote_main_baseline_gate: Gate,
) -> dict[str, bool]:
    """Detect stale quality artifacts relative to their builders."""
    if _in_test_mode():
        return {
            "module_coverage_inventory": False,
            "architecture_quality_scorecard": False,
            "hotspot_family_baseline": not _hotspot_family_baseline_artifact_matches_builder(
                repo_root=repo_root
            ),
            "config_surface_backlog": not _config_surface_backlog_matches_builder(
                repo_root=repo_root,
            ),
            "adr_enforcement_matrix": False,
            "remote_main_baseline": False,
            "dq_contract_registry_diagnostics": False,
        }
    remote_main_builder_match = _remote_main_baseline_artifact_matches_builder(
        repo_root=repo_root
    )
    remote_main_baseline_stale = (
        remote_main_builder_match is not True
        if remote_main_builder_match is not None
        else remote_main_baseline_gate.status != "pass"
    )
    return {
        "module_coverage_inventory": module_coverage_hash_gate.status != "pass",
        "architecture_quality_scorecard": not _artifact_matches_builder(
            repo_root=repo_root,
            rel_path="reports/quality/architecture-quality-scorecard.json",
            payload_builder=lambda: build_architecture_quality_scorecard(
                repo_root=repo_root
            ),
        ),
        "hotspot_family_baseline": not _hotspot_family_baseline_artifact_matches_builder(
            repo_root=repo_root
        ),
        "config_surface_backlog": not _config_surface_backlog_matches_builder(
            repo_root=repo_root,
        ),
        "adr_enforcement_matrix": not _artifact_matches_builder(
            repo_root=repo_root,
            rel_path=ADR_ENFORCEMENT_MATRIX_JSON,
            payload_builder=lambda: report_adr_enforcement_matrix.build_payload(
                repo_root=repo_root
            ),
        ),
        "remote_main_baseline": remote_main_baseline_stale,
        "dq_contract_registry_diagnostics": False,
    }


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


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    assert isinstance(summary, dict)
    gates = payload["gates"]
    assert isinstance(gates, list)
    lines = [
        "# Debt Governance Gates",
        "",
        "> Generated by `python -m scripts.engineering.qa report-debt-governance-gates`.",
        "",
        f"- gate_count: {summary['gate_count']}",
        f"- pass_count: {summary['pass_count']}",
        f"- warn_count: {summary['warn_count']}",
        f"- fail_count: {summary['fail_count']}",
        f"- release_gate_status: `{summary['release_gate_status']}`",
        "- architecture_quality_scorecard_integral_score: "
        f"`{summary['architecture_quality_scorecard_integral_score']}`",
        "- architecture_quality_scorecard_interpretation: "
        f"`{summary['architecture_quality_scorecard_interpretation']}`",
        "",
        "| gate | status | metric | current | limit | source |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for gate in gates:
        assert isinstance(gate, dict)
        lines.append(
            "| `{name}` | `{status}` | `{metric}` | `{current}` | `{limit}` | `{source}` |".format(
                name=gate["name"],
                status=gate["status"],
                metric=gate["metric"],
                current=gate["current"],
                limit=gate["limit"],
                source=gate["source_artifact"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def _write_artifacts(
    payload: dict[str, object],
    *,
    json_out: Path,
    md_out: Path,
    root: Path | None = None,
) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    base = root if root is not None else REPO_ROOT
    json_out = resolve_output_path(json_out, root=base)
    md_out = resolve_output_path(md_out, root=base)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(  # NOSONAR - path confined by resolve_output_path
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(
        render_markdown(payload), encoding="utf-8"
    )  # NOSONAR - path confined by resolve_output_path


def _artifact_staleness_errors(
    payload: dict[str, object],
    *,
    json_out: Path,
    md_out: Path,
) -> list[str]:
    """Return errors when committed debt-governance artifacts drift from payload."""
    errors: list[str] = []
    expected_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(payload)
    if (
        not json_out.exists()
        or json_out.read_text(encoding="utf-8")  # NOSONAR - path confined
        != expected_json
    ):
        errors.append(f"Debt governance gate JSON artifact is stale: {json_out}")
    if (
        not md_out.exists()
        or md_out.read_text(encoding="utf-8")  # NOSONAR - path confined
        != expected_md
    ):
        errors.append(f"Debt governance gate Markdown artifact is stale: {md_out}")
    return errors


def _failing_gate_errors(
    summary: dict[str, object], payload: dict[str, object]
) -> list[str]:
    """Return human-readable errors for currently failing debt-governance gates."""
    fail_count = int(summary["fail_count"])
    if fail_count <= 0:
        return []
    errors: list[str] = []
    failing = summary.get("failing_gates") or []
    detail = ", ".join(str(name) for name in failing) if failing else "unknown"
    errors.append(f"Debt governance gates have {fail_count} failing gate(s): {detail}")
    gates = payload.get("gates")
    if not isinstance(gates, list):
        return errors
    for gate in gates:
        if not isinstance(gate, dict) or gate.get("status") != "fail":
            continue
        name = gate.get("name")
        current = gate.get("current")
        remediation = gate.get("remediation")
        errors.append(f"  - {name}: current={current!r}; {remediation}")
    return errors


def _check_artifacts(
    payload: dict[str, object],
    *,
    json_out: Path,
    md_out: Path,
    compare_artifacts: bool = True,
    root: Path | None = None,
) -> list[str]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    base = root if root is not None else REPO_ROOT
    json_out = resolve_output_path(json_out, root=base)
    md_out = resolve_output_path(md_out, root=base)
    errors: list[str] = []
    if compare_artifacts:
        errors.extend(
            _artifact_staleness_errors(payload, json_out=json_out, md_out=md_out)
        )
    summary = payload["summary"]
    assert isinstance(summary, dict)
    errors.extend(_failing_gate_errors(summary, payload))
    return errors


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    payload = build_payload(
        repo_root=repo_root,
        changed_from_ref=args.changed_from_ref,
    )
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)

    if args.check:
        errors = _check_artifacts(
            payload,
            json_out=json_out,
            md_out=md_out,
            compare_artifacts=args.changed_from_ref is None,
            root=repo_root,
        )
        emit_receipt_from_environment(
            repo_root=repo_root,
            producer="debt_governance_gates",
            evidence_kind="debt",
            command="python -m scripts.engineering.qa report-debt-governance-gates",
            status="fail" if errors else "pass",
            exit_code=1 if errors else 0,
            output_path=json_out,
        )
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        return 0

    if args.update:
        _write_artifacts(payload, json_out=json_out, md_out=md_out, root=repo_root)
        emit_receipt_from_environment(
            repo_root=repo_root,
            producer="debt_governance_gates",
            evidence_kind="debt",
            command="python -m scripts.engineering.qa report-debt-governance-gates",
            status="pass",
            exit_code=0,
            output_path=json_out,
        )
        return 0

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
