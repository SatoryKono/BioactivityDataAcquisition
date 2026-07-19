"""Scoring policy for the deterministic architecture quality scorecard."""

from __future__ import annotations

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
        "metric_keys": (
            "layer_violations",
            "transition_compat_count",
            "expired_compat_count",
        ),
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
        "metric_keys": (
            "layer_violations",
            "public_entrypoint_growth_count",
            "public_export_facade_growth_count",
            "public_export_facade_conflict_count",
        ),
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
        "metric_keys": ("expired_compat_count", "twin_pair_count"),
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
            "transition_compat_count",
            "sunset_compat_count",
            "expired_compat_count",
            "public_entrypoint_growth_count",
            "public_export_facade_growth_count",
            "public_export_facade_conflict_count",
            "repo_wide_untriaged_zero_import_candidate_count",
            "hotspot_budget_warning_count",
            "total_duplicate_clusters",
        ),
    },
)


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
        - 0.5 * _metric_int(metrics, "transition_compat_count")
        - 1.0 * _metric_int(metrics, "expired_compat_count")
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
        - 0.5 * _metric_int(metrics, "public_entrypoint_growth_count")
        - 0.75 * _metric_int(metrics, "public_export_facade_growth_count")
        - 1.0 * _metric_int(metrics, "public_export_facade_conflict_count")
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
        - 0.8 * _metric_int(metrics, "expired_compat_count")
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
        - 0.2 * _metric_int(metrics, "transition_compat_count")
        - 0.2 * _metric_int(metrics, "sunset_compat_count")
        - 0.5 * _metric_int(metrics, "expired_compat_count")
        - 0.2 * _metric_int(metrics, "public_entrypoint_growth_count")
        - 0.25 * _metric_int(metrics, "public_export_facade_growth_count")
        - 0.5 * _metric_int(metrics, "public_export_facade_conflict_count")
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


__all__ = [
    "_build_categories",
    "_interpretation",
    "_score_category",
]
