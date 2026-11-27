"""Regression coverage for observations from failed hotspot budget gates."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tests.performance import test_hotspot_budgets as hotspots


@pytest.mark.parametrize(
    ("benchmark", "key", "needs_tmp_path"),
    [
        (
            hotspots.test_silver_prepare_arrow_data_budget,
            "silver_prepare_arrow_2000",
            True,
        ),
        (hotspots.test_silver_write_append_budget, "silver_write_append_600", True),
        (hotspots.test_silver_write_merge_budget, "silver_write_merge_600", True),
        (
            hotspots.test_crossref_batch_adapter_budget,
            "crossref_batch_fetch_200",
            False,
        ),
        (hotspots.test_atomic_write_group_budget, "atomic_write_group_50", True),
    ],
)
def test_failed_budget_keeps_completed_observation(
    benchmark,
    key: str,
    needs_tmp_path: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed benchmark still publishes exactly one completed measurement."""
    output = tmp_path / "observations.jsonl"
    config = Mock(spec=pytest.Config)
    config.getoption.return_value = str(output)
    budget = hotspots.HotspotBudget(
        baseline_latency_ms=1e-12,
        baseline_throughput_rps=1e15,
        max_regression_pct=0.0,
        p95_latency_ms=1e-12,
        max_p95_regression_pct=0.0,
    )
    monkeypatch.setattr(hotspots, "_load_budgets", lambda: {key: budget})

    with pytest.raises(AssertionError, match="regression"):
        if needs_tmp_path:
            benchmark(tmp_path=tmp_path, pytestconfig=config)
        else:
            benchmark(pytestconfig=config)

    observations = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(observations) == 1
    assert observations[0]["benchmark_key"] == key
    assert observations[0]["latency_ms"] > 0
    assert observations[0]["p95_latency_ms"] > 0
    assert observations[0]["throughput_rps"] > 0
