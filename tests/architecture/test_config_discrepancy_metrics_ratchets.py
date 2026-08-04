# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guardrails for config-surface discrepancy ratchets."""

from __future__ import annotations

from functools import cache
import json
from pathlib import Path

import pytest
import yaml
from scripts.schema import generate_config_matrix as generator

from scripts.schema.generate_config_matrix import (
    _collect_family_configs,
    build_config_discrepancy_evidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
BASELINE_PATH = PROJECT_ROOT / "reports/quality/config-discrepancy-baseline.json"


@cache
def _load_scorecard() -> dict[str, object]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@cache
def _load_baseline_payload() -> dict[str, object]:
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@cache
def _load_baseline_metrics() -> dict[str, int]:
    payload = _load_baseline_payload()
    metrics = payload.get("metrics")
    assert isinstance(metrics, dict)
    normalized: dict[str, int] = {}
    for key, value in metrics.items():
        assert isinstance(key, str)
        assert isinstance(value, int)
        normalized[key] = value
    return normalized


@cache
def _load_baseline_families() -> dict[str, dict[str, int]]:
    payload = _load_baseline_payload()
    families = payload.get("families")
    assert isinstance(families, dict)
    normalized: dict[str, dict[str, int]] = {}
    for family_name, metrics in families.items():
        assert isinstance(family_name, str)
        assert isinstance(metrics, dict)
        normalized[family_name] = {
            str(key): int(value)
            for key, value in metrics.items()
            if isinstance(key, str) and isinstance(value, int)
        }
    return normalized


@cache
def _load_baseline_taxonomy() -> dict[str, object]:
    payload = _load_baseline_payload()
    taxonomy = payload.get("parameter_taxonomy")
    assert isinstance(taxonomy, dict)
    return taxonomy


@cache
def _live_metrics() -> dict[str, int]:
    return build_config_discrepancy_evidence().baseline_metrics()


@cache
def _live_family_metrics() -> dict[str, dict[str, int]]:
    return build_config_discrepancy_evidence().family_metrics()


@cache
def _live_parameter_taxonomy() -> dict[str, object]:
    return build_config_discrepancy_evidence().parameter_taxonomy()


@pytest.mark.architecture
def test_config_discrepancy_evidence_is_immutable_and_byte_stable() -> None:
    first = build_config_discrepancy_evidence()
    second = build_config_discrepancy_evidence()

    assert first is second
    assert first.fingerprint == second.fingerprint
    assert first.baseline_metrics_json == second.baseline_metrics_json
    assert first.family_metrics_json == second.family_metrics_json
    assert first.parameter_taxonomy_json == second.parameter_taxonomy_json


@pytest.mark.architecture
def test_config_discrepancy_evidence_scans_config_snapshot_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    configs: dict[str, dict[str, object]] = {
        "entity/demo/item": {"pipeline.name": "demo"},
        "composite/demo": {"composite.seed.pipeline": "demo_item"},
    }

    def collect_once() -> dict[str, dict[str, object]]:
        nonlocal calls
        calls += 1
        return configs

    generator._build_config_discrepancy_evidence_cached.cache_clear()
    monkeypatch.setattr(generator, "_collect_configs", collect_once)

    first = generator._build_config_discrepancy_evidence_cached("test-fingerprint")
    second = generator._build_config_discrepancy_evidence_cached("test-fingerprint")

    assert first is second
    assert calls == 1
    generator._build_config_discrepancy_evidence_cached.cache_clear()


@pytest.mark.architecture
def test_config_discrepancy_baseline_matches_live_generator() -> None:
    """Committed config-surface baseline must match the deterministic generator."""
    assert BASELINE_PATH.exists(), (
        "Missing config-discrepancy baseline; regenerate with "
        "python -m scripts.schema generate-config-matrix --update"
    )
    assert _load_baseline_metrics() == _live_metrics()
    assert _load_baseline_families() == _live_family_metrics()
    assert _load_baseline_taxonomy() == _live_parameter_taxonomy()


@pytest.mark.architecture
def test_config_discrepancy_metrics_within_scorecard_budget() -> None:
    """Live config-surface metrics must not exceed reviewed scorecard budgets."""
    scorecard = _load_scorecard()
    ratchet = scorecard.get("config_surface_ratchet", {})
    assert isinstance(ratchet, dict)
    assert ratchet.get("mode") == "fail-fast"

    metrics_policy = ratchet.get("metrics", {})
    assert isinstance(metrics_policy, dict)

    live = _live_metrics()
    violations: list[str] = []
    for metric_name, live_count in live.items():
        metric = metrics_policy.get(metric_name)
        assert isinstance(metric, dict), (
            f"config_surface_ratchet.metrics.{metric_name} must be declared"
        )
        max_count = metric.get("max_count")
        assert isinstance(max_count, int), (
            f"config_surface_ratchet.metrics.{metric_name}.max_count must be int"
        )
        if live_count > max_count:
            violations.append(
                f"{metric_name}: live={live_count} exceeds max_count={max_count}"
            )

    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_config_discrepancy_family_metrics_within_scorecard_budget() -> None:
    """Family-scoped burn-down metrics must not exceed reviewed scorecard budgets."""
    scorecard = _load_scorecard()
    ratchet = scorecard.get("config_surface_ratchet", {})
    assert isinstance(ratchet, dict)
    families_policy = ratchet.get("families", {})
    assert isinstance(families_policy, dict)

    live_families = _live_family_metrics()
    violations: list[str] = []
    for family_name, live_metrics in live_families.items():
        family_policy = families_policy.get(family_name)
        assert isinstance(family_policy, dict), (
            f"config_surface_ratchet.families.{family_name} must be declared"
        )
        metrics_policy = family_policy.get("metrics", {})
        assert isinstance(metrics_policy, dict)
        for metric_name, live_count in live_metrics.items():
            metric = metrics_policy.get(metric_name)
            assert isinstance(metric, dict)
            max_count = metric.get("max_count")
            assert isinstance(max_count, int)
            if live_count > max_count:
                violations.append(
                    f"{family_name}.{metric_name}: live={live_count} "
                    f"exceeds max_count={max_count}"
                )

    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_config_parameter_taxonomy_has_owner_and_no_unclassified_parameters() -> None:
    """Config parameters must remain classified by a family-scoped taxonomy."""
    taxonomy = _live_parameter_taxonomy()

    assert taxonomy["owner"] == "BioETL Team"
    assert (
        taxonomy["classification_mode"]
        == "derived_from_flattened_config_parameter_paths"
    )
    evolution_policy = taxonomy["evolution_policy"]
    assert isinstance(evolution_policy, dict)
    assert (
        evolution_policy["compatibility_preserving_changes"]
        == "registered_alias_or_migration_entry_required"
    )
    assert (
        evolution_policy["alias_registry"]
        == "configs/quality/config_compatibility_registry.yaml"
    )
    assert evolution_policy["blocking_issue_budget"] == 0
    group_owner_map = taxonomy["group_owner_map"]
    assert isinstance(group_owner_map, dict)
    assert group_owner_map["compatibility_legacy"]["owner"] == "config-governance"
    assert group_owner_map["domain_entity_contract"]["owner"] == "contract-governance"
    families = taxonomy["families"]
    assert isinstance(families, dict)
    assert set(families) == {"composite_runtime", "entity_effective"}
    for family_name, family_taxonomy in families.items():
        assert isinstance(family_taxonomy, dict), family_name
        assert family_taxonomy["owner"] == "BioETL Team"
        assert family_taxonomy["parameter_count"] > 0
        assert family_taxonomy["unclassified_parameter_count"] == 0
        assert family_taxonomy["unclassified_parameters"] == []
        groups = family_taxonomy["groups"]
        assert isinstance(groups, dict) and groups
        family_group_owner_map = family_taxonomy["group_owner_map"]
        assert isinstance(family_group_owner_map, dict)
        assert set(family_group_owner_map) == set(groups)
        for group_name, owner_row in family_group_owner_map.items():
            assert owner_row == group_owner_map[group_name]
            assert owner_row["owner"].strip()
            assert owner_row["change_policy"].endswith("_required")
            assert owner_row["rationale"].strip()


@pytest.mark.architecture
def test_profile_derived_organism_class_filter_is_outside_ratchet_vocabulary() -> None:
    """Derived target organism_class filtering must not grow config-surface debt."""
    entity_keys = {
        key
        for config in _collect_family_configs()["entity_effective"].values()
        for key in config
    }

    assert "filters.gold_filters.columns.organism_class" not in entity_keys
    assert "filters.gold_filters.columns.organism_class.operator" not in entity_keys
    assert "filters.gold_filters.columns.organism_class.values" not in entity_keys
