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

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
)

_CATEGORY_BASELINES: tuple[dict[str, object], ...] = (
    {
        "id": "layer_compliance",
        "name": "Layer compliance",
        "weight": 0.13,
        "metric_keys": ("layer_violations",),
    },
    {
        "id": "hexagonal_ports_adapters",
        "name": "Hexagonal / Ports & Adapters",
        "weight": 0.11,
        "metric_keys": ("layer_violations", "retained_entrypoint_count"),
    },
    {
        "id": "ddd_invariants",
        "name": "DDD / aggregates / invariants",
        "weight": 0.09,
        "metric_keys": ("source_module_count", "uncovered_module_count"),
    },
    {
        "id": "composition_di",
        "name": "Composition root / DI",
        "weight": 0.10,
        "metric_keys": ("layer_violations", "retained_public_export_facade_count"),
    },
    {
        "id": "module_boundaries_coupling",
        "name": "Module boundaries / coupling",
        "weight": 0.14,
        "metric_keys": (
            "source_module_count",
            "hotspot_family_count",
            "hotspot_budget_warning_count",
            "total_duplicate_clusters",
        ),
    },
    {
        "id": "naming_package_consistency",
        "name": "Naming / package consistency",
        "weight": 0.08,
        "metric_keys": ("retained_entrypoint_count", "twin_pair_count"),
    },
    {
        "id": "test_strategy_testability",
        "name": "Test strategy / testability",
        "weight": 0.12,
        "metric_keys": (
            "unmeasured_module_count",
            "uncovered_module_count",
            "compatibility_test_file_count",
        ),
    },
    {
        "id": "config_contracts_entrypoints",
        "name": "Config / contracts / entrypoints",
        "weight": 0.09,
        "metric_keys": (
            "contract_blocking_issue_count",
            "dq_blocking_issue_count",
            "adr_enforcement_blocking_gap_count",
        ),
    },
    {
        "id": "determinism_replay_observability",
        "name": "Determinism / replay / observability",
        "weight": 0.08,
        "metric_keys": (
            "layer_violations",
            "contract_blocking_issue_count",
            "dashboarded_without_emission_count",
            "dashboarded_without_declaration_count",
            "runtime_cardinality_review_required_count",
            "runtime_cardinality_threshold_violation_count",
        ),
    },
    {
        "id": "debt_burden_evolution_friction",
        "name": "Debt burden / evolution friction",
        "weight": 0.06,
        "metric_keys": (
            "retained_entrypoint_count",
            "repo_wide_untriaged_zero_import_candidate_count",
            "hotspot_budget_warning_count",
            "total_duplicate_clusters",
        ),
    },
)


def _load_json(
    repo_root: Path, rel_path: str
) -> dict[str, Any]:  # Any: JSON can have any value type
    path = repo_root / rel_path
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(
    repo_root: Path, rel_path: str
) -> dict[str, Any]:  # Any: YAML can have any value type
    path = repo_root / rel_path
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _metric_value(metrics: dict[str, object], key: str) -> object:
    return metrics.get(key, "[missing]")


def _metric_int(metrics: dict[str, object], key: str) -> int:
    value = metrics.get(key, 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 1)


def _score_layer_compliance(metrics: dict[str, object]) -> float:
    return _clamp_score(9.5 - 2.5 * _metric_int(metrics, "layer_violations"))


def _score_hexagonal_ports_adapters(metrics: dict[str, object]) -> float:
    return _clamp_score(
        9.2
        - 1.5 * _metric_int(metrics, "layer_violations")
        - 0.05 * _metric_int(metrics, "retained_entrypoint_count")
    )


def _score_ddd_invariants(metrics: dict[str, object]) -> float:
    return _clamp_score(
        9.0
        - 1.5 * _metric_int(metrics, "uncovered_module_count")
        - 0.75 * _metric_int(metrics, "unmeasured_module_count")
    )


def _score_composition_di(metrics: dict[str, object]) -> float:
    return _clamp_score(
        9.0
        - 1.5 * _metric_int(metrics, "layer_violations")
        - 0.25 * _metric_int(metrics, "retained_public_export_facade_count")
    )


def _score_module_boundaries_coupling(metrics: dict[str, object]) -> float:
    return _clamp_score(
        8.8
        - 0.12 * _metric_int(metrics, "hotspot_family_count")
        - 0.12 * _metric_int(metrics, "hotspot_budget_warning_count")
        - 0.01 * _metric_int(metrics, "total_duplicate_clusters")
    )


def _score_naming_package_consistency(metrics: dict[str, object]) -> float:
    return _clamp_score(
        8.8
        - 0.06 * _metric_int(metrics, "retained_entrypoint_count")
        - 0.8 * _metric_int(metrics, "twin_pair_count")
    )


def _score_test_strategy_testability(metrics: dict[str, object]) -> float:
    return _clamp_score(
        8.8
        - 1.5 * _metric_int(metrics, "unmeasured_module_count")
        - 1.0 * _metric_int(metrics, "uncovered_module_count")
        - 0.02 * _metric_int(metrics, "compatibility_test_file_count")
    )


def _score_config_contracts_entrypoints(metrics: dict[str, object]) -> float:
    return _clamp_score(
        9.2
        - 2.0 * _metric_int(metrics, "contract_blocking_issue_count")
        - 2.0 * _metric_int(metrics, "dq_blocking_issue_count")
        - 1.5 * _metric_int(metrics, "adr_enforcement_blocking_gap_count")
    )


def _score_determinism_replay_observability(metrics: dict[str, object]) -> float:
    return _clamp_score(
        9.0
        - 1.5 * _metric_int(metrics, "dashboarded_without_emission_count")
        - 1.5 * _metric_int(metrics, "dashboarded_without_declaration_count")
        - 1.0 * _metric_int(metrics, "runtime_cardinality_review_required_count")
        - 1.0 * _metric_int(metrics, "runtime_cardinality_threshold_violation_count")
        - 0.5 * _metric_int(metrics, "layer_violations")
    )


def _score_debt_burden_evolution_friction(metrics: dict[str, object]) -> float:
    return _clamp_score(
        8.5
        - 0.06 * _metric_int(metrics, "retained_entrypoint_count")
        - 0.5 * _metric_int(metrics, "repo_wide_untriaged_zero_import_candidate_count")
        - 0.08 * _metric_int(metrics, "hotspot_budget_warning_count")
        - 0.01 * _metric_int(metrics, "total_duplicate_clusters")
    )


_CATEGORY_SCORERS = {
    "layer_compliance": _score_layer_compliance,
    "hexagonal_ports_adapters": _score_hexagonal_ports_adapters,
    "ddd_invariants": _score_ddd_invariants,
    "composition_di": _score_composition_di,
    "module_boundaries_coupling": _score_module_boundaries_coupling,
    "naming_package_consistency": _score_naming_package_consistency,
    "test_strategy_testability": _score_test_strategy_testability,
    "config_contracts_entrypoints": _score_config_contracts_entrypoints,
    "determinism_replay_observability": _score_determinism_replay_observability,
    "debt_burden_evolution_friction": _score_debt_burden_evolution_friction,
}


def _score_category(category_id: str, metrics: dict[str, object]) -> float:
    scorer = _CATEGORY_SCORERS[category_id]
    return scorer(metrics)


def _build_categories(metrics: dict[str, object]) -> list[dict[str, object]]:
    categories: list[dict[str, object]] = []
    for item in _CATEGORY_BASELINES:
        weight = float(item["weight"])
        score = _score_category(str(item["id"]), metrics)
        metric_keys = tuple(str(key) for key in item["metric_keys"])
        categories.append(
            {
                "id": item["id"],
                "name": item["name"],
                "weight": weight,
                "score": score,
                "weighted_score": round(weight * score, 4),
                "evidence_metrics": {
                    key: _metric_value(metrics, key) for key in metric_keys
                },
            }
        )
    return categories


def _interpretation(score: float) -> str:
    if score < 5.0:
        return "critical"
    if score < 8.5:
        return "satisfactory_system_refactoring_required"
    return "good_targeted_improvements"


def _load_scorecard_inputs(
    repo_root: Path,
) -> tuple[
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
    dict[str, Any],  # Any: JSON artifacts can have any value type
]:
    return (
        _load_json(
            repo_root,
            "docs/02-architecture/generated/module-dependency-map.json",
        ),
        _load_json(repo_root, "reports/quality/module-coverage-inventory.json"),
        _load_json(repo_root, "reports/quality/compatibility-importer-census.json"),
        _load_json(repo_root, "reports/quality/dead-code-inventory.json"),
        _load_json(repo_root, "reports/quality/contract-registry-diagnostics.json"),
        build_contract_registry_dq_diagnostics(repo_root),
        _load_json(
            repo_root, "reports/observability/runtime_cardinality_inventory.json"
        ),
        _load_json(repo_root, "reports/quality/full-app-duplication-baseline.json"),
        _load_json(repo_root, "reports/quality/hotspot-family-baseline.json"),
        _load_json(repo_root, "reports/quality/test-governance-current.json"),
        build_adr_enforcement_matrix(repo_root=repo_root),
        _load_yaml(repo_root, "configs/quality/debt_scorecard.yaml"),
    )


def _build_source_artifacts(
    dependency_map: dict[str, Any],  # Any: JSON artifact can have any value type
    coverage_inventory: dict[str, Any],  # Any: JSON artifact can have any value type
    compatibility_census: dict[str, Any],  # Any: JSON artifact can have any value type
    dead_code_inventory: dict[str, Any],  # Any: JSON artifact can have any value type
    contract_diagnostics: dict[str, Any],  # Any: JSON artifact can have any value type
    dq_diagnostics: dict[str, Any],  # Any: JSON artifact can have any value type
    observability_inventory: dict[
        str, Any  # Any: JSON artifact can have any value type
    ],  # Any: JSON artifact can have any value type
    duplication_baseline: dict[str, Any],  # Any: JSON artifact can have any value type
    hotspot_baseline: dict[str, Any],  # Any: JSON artifact can have any value type
    test_governance_report: dict[
        str, Any  # Any: JSON artifact can have any value type
    ],  # Any: JSON artifact can have any value type
    adr_enforcement_matrix: dict[
        str, Any  # Any: JSON artifact can have any value type
    ],  # Any: JSON artifact can have any value type
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


def _current_compatibility_debt_metrics(
    debt_budgets: dict[str, Any] | object,  # Any: YAML config can have any value type
) -> dict[str, Any]:  # Any: Extracted metrics can have any value type
    if not isinstance(debt_budgets, dict):
        return {}
    metrics = debt_budgets.get("metrics", {})
    return metrics if isinstance(metrics, dict) else {}


def _build_architecture_quality_metrics(
    dependency_map: dict[str, Any],  # Any: JSON artifact can have any value type
    coverage_inventory: dict[str, Any],  # Any: JSON artifact can have any value type
    compatibility_census: dict[str, Any],  # Any: JSON artifact can have any value type
    dead_code_inventory: dict[str, Any],  # Any: JSON artifact can have any value type
    contract_diagnostics: dict[str, Any],  # Any: JSON artifact can have any value type
    dq_diagnostics: dict[str, Any],  # Any: JSON artifact can have any value type
    observability_inventory: dict[
        str, Any  # Any: JSON artifact can have any value type
    ],  # Any: JSON artifact can have any value type
    duplication_baseline: dict[str, Any],  # Any: JSON artifact can have any value type
    hotspot_baseline: dict[str, Any],  # Any: JSON artifact can have any value type
    test_governance_report: dict[
        str, Any  # Any: JSON artifact can have any value type
    ],  # Any: JSON artifact can have any value type
    adr_enforcement_matrix: dict[
        str, Any  # Any: JSON artifact can have any value type
    ],  # Any: JSON artifact can have any value type
) -> dict[str, object]:
    coverage_summary = coverage_inventory["summary"]
    status_counts = coverage_summary["status_counts"]
    compatibility_summary = compatibility_census["summary"]
    dead_code_summary = dead_code_inventory["summary"]
    duplication_summary = duplication_baseline["summary"]
    hotspot_summary = hotspot_baseline["summary"]
    adr_summary = adr_enforcement_matrix["summary"]
    test_governance_summary = test_governance_report["report"]
    return {
        "layer_violations": len(dependency_map.get("violations", [])),
        "source_module_count": coverage_summary["source_module_count"],
        "unmeasured_module_count": coverage_summary["unmeasured_module_count"],
        "uncovered_module_count": status_counts.get("uncovered", 0),
        "hotspot_family_count": len(coverage_summary["hotspot_family_coverage"]),
        "hotspot_budget_warning_count": hotspot_summary["budget_warnings"],
        "total_duplicate_clusters": duplication_summary["total_duplicate_clusters"],
        "retained_entrypoint_count": compatibility_summary["retained_entrypoint_count"],
        "retained_public_export_facade_count": compatibility_summary[
            "retained_public_export_facade_count"
        ],
        "twin_pair_count": compatibility_summary["twin_pair_count"],
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


def _build_debt_budget_policy(scorecard: dict[str, Any]) -> dict[str, object]:
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
    )
    categories = _build_categories(metrics)
    integral_score = round(
        sum(float(category["weighted_score"]) for category in categories),
        2,
    )
    weights_sum = round(
        sum(float(category["weight"]) for category in categories),
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
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


__all__ = [
    "DEFAULT_OUTPUT",
    "_build_categories",
    "_score_category",
    "build_architecture_quality_scorecard",
    "write_architecture_quality_scorecard",
]
