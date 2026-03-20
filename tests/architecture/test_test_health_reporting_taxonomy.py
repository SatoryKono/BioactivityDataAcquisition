"""Architecture guardrails for canonical test-health reporting taxonomy."""

from __future__ import annotations

from pathlib import Path

import yaml


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
