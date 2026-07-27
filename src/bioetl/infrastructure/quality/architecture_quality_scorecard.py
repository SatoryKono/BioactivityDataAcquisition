"""Deterministic architecture quality scorecard aggregation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from scripts.engineering.ci.validate_registry_dq_refs import (
    build_diagnostics_payload as build_contract_registry_dq_diagnostics,
)
from scripts.engineering.qa.report_adr_enforcement_matrix import (
    build_payload as build_adr_enforcement_matrix,
)

from bioetl.infrastructure.quality.architecture_quality_scoring import (
    _build_categories,
    _interpretation,
    _score_category,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
)


# Scorecard inputs are heterogeneous JSON/YAML mappings (artifact payloads).
JsonMap = dict[str, Any]


def _load_json(repo_root: Path, rel_path: str) -> JsonMap:
    """Load one JSON object used by the scorecard."""
    path = repo_root / rel_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{rel_path} must contain a JSON object")
    return payload


def _as_float(value: object) -> float:
    """Validate a numeric scorecard value before aggregation."""
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError(f"scorecard metric must be numeric, got {type(value)!r}")


def _load_yaml(repo_root: Path, rel_path: str) -> JsonMap:
    """Load one YAML mapping used by the scorecard."""
    path = repo_root / rel_path
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_scorecard_inputs(repo_root: Path) -> tuple[JsonMap, ...]:
    return (
        _load_json(repo_root, "docs/02-architecture/generated/module-dependency-map.json"),
        _load_json(repo_root, "reports/quality/module-coverage-inventory.json"),
        _load_json(repo_root, "reports/quality/compatibility-importer-census.json"),
        _load_json(repo_root, "reports/quality/dead-code-inventory.json"),
        _load_json(repo_root, "reports/quality/contract-registry-diagnostics.json"),
        build_contract_registry_dq_diagnostics(repo_root),
        _load_json(repo_root, "reports/observability/runtime_cardinality_inventory.json"),
        _load_json(repo_root, "reports/quality/full-app-duplication-baseline.json"),
        _load_json(repo_root, "reports/quality/hotspot-family-baseline.json"),
        _load_json(repo_root, "reports/quality/test-governance-current.json"),
        build_adr_enforcement_matrix(repo_root=repo_root),
        _load_yaml(repo_root, "configs/quality/debt_scorecard.yaml"),
    )


def _build_source_artifacts(
    dependency_map: JsonMap,
    coverage_inventory: JsonMap,
    compatibility_census: JsonMap,
    dead_code_inventory: JsonMap,
    contract_diagnostics: JsonMap,
    dq_diagnostics: JsonMap,
    observability_inventory: JsonMap,
    duplication_baseline: JsonMap,
    hotspot_baseline: JsonMap,
    test_governance_report: JsonMap,
    adr_enforcement_matrix: JsonMap,
) -> dict[str, object]:
    return {
        "dependency_map": {
            "path": "docs/02-architecture/generated/module-dependency-map.json",
            "source_fingerprint": dependency_map["summary"].get("source_fingerprint"),
        },
        "module_coverage_inventory": {
            "path": "reports/quality/module-coverage-inventory.json",
            "source_tree_sha256": coverage_inventory["source_tree_sha256"],
            "coverage_xml_sha256": coverage_inventory["coverage_xml_sha256"],
        },
        "compatibility_importer_census": {
            "path": "reports/quality/compatibility-importer-census.json",
            "snapshot_date": compatibility_census["snapshot_date"],
        },
        "dead_code_inventory": {
            "path": "reports/quality/dead-code-inventory.json",
            "snapshot_date": dead_code_inventory["snapshot_date"],
        },
        "contract_registry_diagnostics": {
            "path": "reports/quality/contract-registry-diagnostics.json",
            "valid": contract_diagnostics["valid"],
        },
        "contract_registry_dq_diagnostics": {
            "path": (
                "scripts/engineering/ci/validate_registry_dq_refs.py"
                "::build_diagnostics_payload"
            ),
            "source_check": "python -m scripts.engineering.ci validate-dq-consistency",
            "valid": dq_diagnostics["valid"],
            "blocking_issue_count": dq_diagnostics["blocking_issue_count"],
        },
        "observability_runtime_cardinality_inventory": {
            "path": "reports/observability/runtime_cardinality_inventory.json",
            "dashboarded_without_emission_count": len(
                observability_inventory.get("dashboarded_without_emission", [])
            ),
            "dashboarded_without_declaration_count": len(
                observability_inventory.get("dashboarded_without_declaration", [])
            ),
        },
        "duplication_baseline": {
            "path": "reports/quality/full-app-duplication-baseline.json",
            "snapshot_date": duplication_baseline["summary"]["snapshot_date"],
            "total_duplicate_clusters": duplication_baseline["summary"][
                "total_duplicate_clusters"
            ],
        },
        "hotspot_family_baseline": {
            "path": "reports/quality/hotspot-family-baseline.json",
            "snapshot_date": hotspot_baseline["summary"]["snapshot_date"],
            "budget_warnings": hotspot_baseline["summary"]["budget_warnings"],
        },
        "test_governance_report": {
            "path": "reports/quality/test-governance-current.json",
            "compatibility_test_files": test_governance_report["report"][
                "compatibility_test_files"
            ],
        },
        "adr_enforcement_matrix": {
            "path": (
                "scripts/engineering/qa/report_adr_enforcement_matrix.py::build_payload"
            ),
            "generated_artifact": "reports/quality/adr-enforcement-matrix.json",
            "accepted_adr_count": adr_enforcement_matrix["summary"][
                "accepted_adr_count"
            ],
            "blocking_gap_count": adr_enforcement_matrix["summary"][
                "blocking_gap_count"
            ],
        },
    }


def _current_compatibility_debt_metrics(debt_budgets: object) -> JsonMap:
    if not isinstance(debt_budgets, dict):
        return {}
    metrics = debt_budgets.get("metrics", {})
    return metrics if isinstance(metrics, dict) else {}


def _scorecard_metric_count(
    scorecard: JsonMap, section_name: str, metric_name: str
) -> int:
    section = scorecard.get(section_name, {})
    if not isinstance(section, dict):
        return 0
    metrics = section.get("metrics", {})
    if not isinstance(metrics, dict):
        return 0
    policy = metrics.get(metric_name, {})
    if not isinstance(policy, dict):
        return 0
    value = policy.get("current_count", 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _build_compatibility_quality_metrics(
    compatibility_summary: JsonMap, scorecard: JsonMap
) -> dict[str, object]:
    retained_entrypoint_count = int(compatibility_summary["retained_entrypoint_count"])
    retained_public_export_facade_count = int(
        compatibility_summary["retained_public_export_facade_count"]
    )
    reviewed_entrypoint_count = _scorecard_metric_count(
        scorecard, "sanctioned_public_entrypoint_governance", "public_entrypoint_count"
    )
    reviewed_public_export_facade_count = _scorecard_metric_count(
        scorecard,
        "sanctioned_public_entrypoint_governance",
        "public_export_facade_count",
    )
    conflict_count = max(
        int(compatibility_summary.get(
            "retained_public_export_facades_with_duplicate_exports", 0
        )),
        int(compatibility_summary.get(
            "retained_public_export_facades_with_resolution_conflicts", 0
        )),
        int(compatibility_summary.get(
            "retained_public_export_facades_with_wrapper_contract_drift", 0
        )),
    )
    return {
        "retained_entrypoint_count": retained_entrypoint_count,
        "retained_public_export_facade_count": retained_public_export_facade_count,
        "transition_compat_count": _scorecard_metric_count(
            scorecard, "compatibility_debt_metrics", "transition_compat_count"
        ),
        "sunset_compat_count": _scorecard_metric_count(
            scorecard, "compatibility_debt_metrics", "sunset_compat_count"
        ),
        "expired_compat_count": _scorecard_metric_count(
            scorecard, "compatibility_debt_metrics", "expired_compat_count"
        ),
        "public_entrypoint_growth_count": max(
            0, retained_entrypoint_count - reviewed_entrypoint_count
        ),
        "public_export_facade_growth_count": max(
            0, retained_public_export_facade_count - reviewed_public_export_facade_count
        ),
        "public_export_facade_conflict_count": conflict_count,
        "twin_pair_count": compatibility_summary["twin_pair_count"],
    }


def _build_architecture_quality_metrics(
    dependency_map: JsonMap,
    coverage_inventory: JsonMap,
    compatibility_census: JsonMap,
    dead_code_inventory: JsonMap,
    contract_diagnostics: JsonMap,
    dq_diagnostics: JsonMap,
    observability_inventory: JsonMap,
    duplication_baseline: JsonMap,
    hotspot_baseline: JsonMap,
    test_governance_report: JsonMap,
    adr_enforcement_matrix: JsonMap,
    scorecard: JsonMap,
) -> dict[str, object]:
    coverage_summary = coverage_inventory["summary"]
    status_counts = coverage_summary["status_counts"]
    compatibility_summary = compatibility_census["summary"]
    dead_code_summary = dead_code_inventory["summary"]
    duplication_summary = duplication_baseline["summary"]
    hotspot_summary = hotspot_baseline["summary"]
    adr_summary = adr_enforcement_matrix["summary"]
    test_governance_summary = test_governance_report["report"]
    compatibility_metrics = _build_compatibility_quality_metrics(
        compatibility_summary,
        scorecard,
    )
    return {
        "layer_violations": len(dependency_map.get("violations", [])),
        "source_module_count": coverage_summary["source_module_count"],
        "unmeasured_module_count": coverage_summary["unmeasured_module_count"],
        "uncovered_module_count": status_counts.get("uncovered", 0),
        "hotspot_family_count": len(coverage_summary["hotspot_family_coverage"]),
        "hotspot_budget_warning_count": hotspot_summary["budget_warnings"],
        "total_duplicate_clusters": duplication_summary["total_duplicate_clusters"],
        **compatibility_metrics,
        "compatibility_test_file_count": test_governance_summary[
            "compatibility_test_files"
        ],
        "repo_wide_untriaged_zero_import_candidate_count": dead_code_summary[
            "repo_wide_untriaged_zero_import_candidate_count"
        ],
        "contract_blocking_issue_count": contract_diagnostics["blocking_issue_count"],
        "dq_blocking_issue_count": dq_diagnostics["blocking_issue_count"],
        "dashboarded_without_emission_count": len(
            observability_inventory.get("dashboarded_without_emission", [])
        ),
        "dashboarded_without_declaration_count": len(
            observability_inventory.get("dashboarded_without_declaration", [])
        ),
        "runtime_cardinality_review_required_count": len(
            observability_inventory.get("runtime_cardinality_review_required", [])
        ),
        "runtime_cardinality_threshold_violation_count": len(
            observability_inventory.get("runtime_cardinality_threshold_violations", [])
        ),
        "accepted_adr_count": adr_summary["accepted_adr_count"],
        "adr_enforcement_blocking_gap_count": adr_summary["blocking_gap_count"],
        "adr_enforcement_manual_exception_count": adr_summary["manual_exception_count"],
    }


def _build_debt_budget_policy(scorecard: JsonMap) -> dict[str, object]:
    debt_budgets = scorecard.get("compatibility_debt_metrics", {})
    return {
        "budget_growth_allowed": False,
        "compatibility_debt_metrics_source": (
            "configs/quality/debt_scorecard.yaml#compatibility_debt_metrics"
        ),
        "current_compatibility_debt_metrics": _current_compatibility_debt_metrics(
            debt_budgets
        ),
    }


def build_architecture_quality_scorecard(
    *,
    repo_root: Path = PROJECT_ROOT,
) -> dict[str, object]:
    """Build the deterministic architecture quality scorecard payload."""
    repo_root = repo_root.resolve()
    (
        dependency_map,
        coverage_inventory,
        compatibility_census,
        dead_code_inventory,
        contract_diagnostics,
        dq_diagnostics,
        observability_inventory,
        duplication_baseline,
        hotspot_baseline,
        test_governance_report,
        adr_enforcement_matrix,
        scorecard,
    ) = _load_scorecard_inputs(repo_root)

    metrics = _build_architecture_quality_metrics(
        dependency_map,
        coverage_inventory,
        compatibility_census,
        dead_code_inventory,
        contract_diagnostics,
        dq_diagnostics,
        observability_inventory,
        duplication_baseline,
        hotspot_baseline,
        test_governance_report,
        adr_enforcement_matrix,
        scorecard,
    )
    categories = _build_categories(metrics)
    integral_score = round(
        sum(
            [_as_float(category["weighted_score"]) for category in categories],
            0.0,
        ),
        2,
    )
    weights_sum = round(
        sum([_as_float(category["weight"]) for category in categories], 0.0),
        2,
    )
    source_artifacts = _build_source_artifacts(
        dependency_map,
        coverage_inventory,
        compatibility_census,
        dead_code_inventory,
        contract_diagnostics,
        dq_diagnostics,
        observability_inventory,
        duplication_baseline,
        hotspot_baseline,
        test_governance_report,
        adr_enforcement_matrix,
    )

    return {
        "schema_version": 1,
        "generated_by": "bioetl.infrastructure.quality.architecture_quality_scorecard",
        "source_artifacts": source_artifacts,
        "weights_sum": weights_sum,
        "integral_score": integral_score,
        "interpretation": _interpretation(integral_score),
        "categories": categories,
        "metrics": metrics,
        "debt_budget_policy": _build_debt_budget_policy(scorecard),
    }


def write_architecture_quality_scorecard(
    path: Path = DEFAULT_OUTPUT,
    *,
    repo_root: Path = PROJECT_ROOT,
) -> dict[str, object]:
    """Write and return the deterministic architecture quality scorecard."""
    payload = build_architecture_quality_scorecard(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


__all__ = [
    "DEFAULT_OUTPUT",
    "_build_categories",
    "_score_category",
    "build_architecture_quality_scorecard",
    "write_architecture_quality_scorecard",
]
