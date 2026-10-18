"""Regression contracts for sequential Delta measurement reporting."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.qa.generate_hotspot_degradation_report import (
    _load_observations,
)
from tests.performance import test_delta_sequential_merge as harness

pytestmark = [pytest.mark.unit, pytest.mark.fs_contract]


def _request(output: Path) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(getoption=lambda *a, **k: str(output))
    )


def test_observations_use_measured_samples_and_load(tmp_path: Path) -> None:
    observation = harness._build_observation(3, [0.1, 0.2, 0.3], 1500)
    output = tmp_path / "observations.jsonl"
    output.write_text(json.dumps(observation) + "\n", encoding="utf-8")
    loaded = _load_observations(output)["delta_sequential_merge_N3"][0]
    assert loaded.latency_ms == pytest.approx(200)
    assert loaded.p95_latency_ms == pytest.approx(300)
    assert loaded.throughput_rps == pytest.approx(2500)
    assert loaded.timestamp_unix == observation["timestamp_unix"]
    assert observation["context"]["processed_rows"] == 1500


@pytest.mark.parametrize(
    "durations", [[], [0.0], [-1.0], [float("nan")], [float("inf")]]
)
def test_invalid_measurements_are_not_published(durations: list[float]) -> None:
    with pytest.raises(ValueError):
        harness._build_observation(1, durations, 500)


@pytest.mark.parametrize("successful_merges", [0, 1])
def test_writer_failure_preserves_completed_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, successful_merges: int
) -> None:
    original_factory = harness._create_silver_writer
    calls = 0
    error = RuntimeError("injected writer failure")

    def factory(path: Path) -> SimpleNamespace:
        writer = original_factory(path)

        async def write(**kwargs: object) -> None:
            nonlocal calls
            if calls == successful_merges:
                raise error
            await writer.write_silver(**kwargs)
            calls += 1

        return SimpleNamespace(write_silver=write)

    monkeypatch.setattr(harness, "_create_silver_writer", factory)
    output = tmp_path / "observations.jsonl"
    with pytest.raises(RuntimeError) as raised:
        harness.test_delta_sequential_merge_scaling(tmp_path, 2, _request(output))
    assert raised.value is error
    report = json.loads((tmp_path / "merge_scaling_N2_incomplete.json").read_text())
    assert report["status"] == "incomplete"
    assert report["n_merges_completed"] == successful_merges
    assert len(report["merges"]) == successful_merges
    assert report["total_records_processed"] == successful_merges * 500
    assert not output.exists()
    assert not (tmp_path / "merge_scaling_N2.json").exists()


def test_setup_includes_writer_schema_and_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events = []
    ticks = iter([10.0, 20.0, 21.0, 21.1])

    def tick() -> float:
        events.append("clock")
        return next(ticks)

    for name in ["_create_silver_writer", "_create_activity_schema"]:
        original = getattr(harness, name)

        def wrapped(*args: object, original=original, name=name):
            events.append(name)
            return original(*args)

        monkeypatch.setattr(harness, name, wrapped)
    original_loop = harness.asyncio.new_event_loop

    def create_loop():
        events.append("event_loop")
        return original_loop()

    monkeypatch.setattr(harness.asyncio, "new_event_loop", create_loop)
    monkeypatch.setattr(harness, "time", SimpleNamespace(perf_counter=tick))
    output = tmp_path / "observations.jsonl"
    harness.test_delta_sequential_merge_scaling(tmp_path, 1, _request(output))
    report = json.loads((tmp_path / "merge_scaling_N1.json").read_text())
    assert events[:5] == [
        "clock",
        "_create_silver_writer",
        "_create_activity_schema",
        "event_loop",
        "clock",
    ]
    assert report["setup_time_s"] == 10.0
    assert report["actual_final_rows"] == 500
    assert _load_observations(output)["delta_sequential_merge_N1"][
        0
    ].latency_ms == pytest.approx(100)


def test_slow_merge_keeps_existing_failure_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ticks = iter([0.0, 1.0, 2.0, 63.0])
    monkeypatch.setattr(
        harness, "time", SimpleNamespace(perf_counter=lambda: next(ticks))
    )
    output = tmp_path / "observations.jsonl"
    with pytest.raises(pytest.fail.Exception, match="Merge degraded severely"):
        harness.test_delta_sequential_merge_scaling(tmp_path, 1, _request(output))
    report = json.loads((tmp_path / "merge_scaling_N1_incomplete.json").read_text())
    assert report["n_merges_completed"] == 1
    assert report["merges"][0]["merge_time_s"] == 61.0
    assert not output.exists()


def test_harness_has_both_performance_lane_markers() -> None:
    assert {"benchmark", "performance"} <= {mark.name for mark in harness.pytestmark}
