"""Architecture guardrails for canonical test-health reporting taxonomy."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml


pytestmark = pytest.mark.architecture

def _load_taxonomy() -> dict[str, object]:
    path = Path("configs/quality/test_health_reporting.yaml")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def test_test_health_reporting_taxonomy_keeps_informational_mode() -> None:
    """Descriptive test-health classes must remain non-blocking taxonomy."""
    taxonomy = _load_taxonomy()
    assert taxonomy.get("classification_mode") == "informational"
    assert taxonomy.get("merge_blocking_source") == "ci_pass_fail_and_quality_gate"


def test_test_health_reporting_taxonomy_defines_all_current_statuses() -> None:
    """Canonical taxonomy must define each status emitted by quality gate."""
    taxonomy = _load_taxonomy()
    statuses = taxonomy.get("statuses", {})
    assert isinstance(statuses, dict)

    expected = {
        "fully_exercised_green",
        "staged_green",
        "environment_limited_green",
        "non_green",
    }
    assert expected <= set(statuses)

    for status in expected:
        entry = statuses[status]
        assert isinstance(entry, dict)
        assert isinstance(entry.get("short_label"), str) and entry["short_label"]
        assert isinstance(entry.get("definition"), str) and entry["definition"]
        assert (
            isinstance(entry.get("merge_semantics"), str) and entry["merge_semantics"]
        )


def test_test_health_reporting_taxonomy_defines_current_skip_classes() -> None:
    """Canonical taxonomy must define skip/conditional buckets emitted by gate."""
    taxonomy = _load_taxonomy()
    skip_classes = taxonomy.get("skip_classes", {})
    assert isinstance(skip_classes, dict)

    expected = {
        "architecture_suite_skips",
        "live_network_opt_in_gate",
        "live_api_gate_mode_non_always",
        "pilot_provider_count",
        "vcr_only_provider_count",
    }
    assert expected <= set(skip_classes)

    for skip_class in expected:
        entry = skip_classes[skip_class]
        assert isinstance(entry, dict)
        assert isinstance(entry.get("short_label"), str) and entry["short_label"]
        assert isinstance(entry.get("definition"), str) and entry["definition"]
