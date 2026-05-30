"""Architecture guardrails for config-surface discrepancy ratchets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.schema.generate_config_matrix import (
    _build_artifact_contents,
    _collect_family_configs,
    _family_metrics,
    _live_baseline_metrics,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
BASELINE_PATH = PROJECT_ROOT / "reports/quality/config-discrepancy-baseline.json"


def _load_scorecard() -> dict[str, object]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_baseline_metrics() -> dict[str, int]:
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    metrics = payload.get("metrics")
    assert isinstance(metrics, dict)
    normalized: dict[str, int] = {}
    for key, value in metrics.items():
        assert isinstance(key, str)
        assert isinstance(value, int)
        normalized[key] = value
    return normalized


def _load_baseline_families() -> dict[str, dict[str, int]]:
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
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


def _live_metrics() -> dict[str, int]:
    _, _, unique_parameter_count, config_count, inconsistent_parameter_count = (
        _build_artifact_contents()
    )
    return _live_baseline_metrics(
        config_count=config_count,
        unique_parameter_count=unique_parameter_count,
        _cross_family_raw_inconsistent=inconsistent_parameter_count,
    )


def _live_family_metrics() -> dict[str, dict[str, int]]:
    return {
        family_name: _family_metrics(family_configs)
        for family_name, family_configs in _collect_family_configs().items()
    }


@pytest.mark.architecture
def test_config_discrepancy_baseline_matches_live_generator() -> None:
    """Committed config-surface baseline must match the deterministic generator."""
    assert BASELINE_PATH.exists(), (
        "Missing config-discrepancy baseline; regenerate with "
        "python -m scripts.schema generate-config-matrix --update"
    )
    assert _load_baseline_metrics() == _live_metrics()
    assert _load_baseline_families() == _live_family_metrics()


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
