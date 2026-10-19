"""Regression contracts for sequential Delta measurement reporting."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts.engineering.qa.generate_hotspot_degradation_report import (
    _load_observations,
)
from tests.performance import test_delta_sequential_merge as harness

pytestmark = [pytest.mark.unit, pytest.mark.fs_contract]


def _request(output: Path) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            getoption=lambda name, **k: (
                str(output.parent / "details")
                if name == "--delta-merge-report-dir"
                else str(output)
            )
        )
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
    retained = next((tmp_path / "details").glob("*/merge_scaling_N2_incomplete.json"))
    assert json.loads(retained.read_text()) == report
    assert not list((tmp_path / "details").glob("*/observations.jsonl"))
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
    assert not output.exists()
    isolated = next((tmp_path / "details").glob("*/observations.jsonl"))
    assert _load_observations(isolated)["delta_sequential_merge_N1"][
        0
    ].latency_ms == pytest.approx(100)


def test_slow_merge_keeps_existing_failure_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harness, "_WINDOWS_PLATFORM", False)
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


@pytest.mark.parametrize(
    ("actual_rows", "version", "message"),
    [(499, 0, "Expected 500 rows, got 499"), (500, -1, "Expected at least 0 versions")],
)
def test_final_validation_failure_preserves_completed_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    actual_rows: int,
    version: int,
    message: str,
) -> None:
    writer = SimpleNamespace(write_silver=AsyncMock())
    monkeypatch.setattr(harness, "_create_silver_writer", lambda path: writer)
    monkeypatch.setattr(
        "deltalake.DeltaTable",
        lambda *args: SimpleNamespace(
            version=lambda: version,
            to_pyarrow_dataset=lambda: SimpleNamespace(count_rows=lambda: actual_rows),
        ),
    )
    output = tmp_path / "observations.jsonl"
    with pytest.raises(AssertionError, match=message):
        harness.test_delta_sequential_merge_scaling(tmp_path, 1, _request(output))
    writer.write_silver.assert_awaited_once()
    report = json.loads((tmp_path / "merge_scaling_N1_incomplete.json").read_text())
    assert report["status"] == "incomplete"
    assert report["n_merges_completed"] == len(report["merges"]) == 1
    assert report["total_records_processed"] == 500
    assert report["merges"][0]["merge_time_raw_s"] > 0
    assert not (tmp_path / "merge_scaling_N1.json").exists()
    assert not output.exists()


def test_harness_has_both_performance_lane_markers() -> None:
    assert {"benchmark", "performance"} <= {mark.name for mark in harness.pytestmark}


def test_windows_slow_merge_is_recorded_without_linux_abort(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "_WINDOWS_PLATFORM", True)
    ticks = iter([0.0, 1.0, 2.0, 63.0])
    monkeypatch.setattr(
        harness, "time", SimpleNamespace(perf_counter=lambda: next(ticks))
    )
    hotspot = tmp_path / "hotspot.jsonl"
    hotspot.write_text("existing hotspot evidence\n")
    harness.test_delta_sequential_merge_scaling(tmp_path, 1, _request(hotspot))
    assert hotspot.read_text() == "existing hotspot evidence\n"
    report = next((tmp_path / "details").glob("*/merge_scaling_N1.json"))
    data = json.loads(report.read_text())
    assert data["status"] == "complete"
    assert data["merges"][0]["merge_time_raw_s"] == 61.0
    assert (report.parent / "observations.jsonl").is_file()


def test_schema_and_batches_use_canonical_content_hash():
    schema = harness._create_activity_schema()
    assert "content_hash" in schema.names
    assert "_content_hash" not in schema.names
    import pyarrow as pa
    from tests.benchmarks.test_delta_write import _prepare_records_for_delta
    from bioetl.infrastructure.storage.silver.delta_merge_helpers import (
        build_replay_safe_rerun_contract,
    )

    records = harness._generate_synthetic_batch(0, 2)
    for batch in [records, _prepare_records_for_delta(records)]:
        table = pa.Table.from_pylist(batch, schema=schema)
        assert table["content_hash"].null_count == 0
        contract = build_replay_safe_rerun_contract(table)
        assert contract.merge_update_policy == "content_hash_only"
        assert contract.strict_replay_safe
    assert all("content_hash" in row and "_content_hash" not in row for row in records)


def test_workflow_uploads_isolated_detail_artifacts():
    import yaml

    workflow = yaml.safe_load(
        Path(".github/workflows/performance-nightly.yml").read_text()
    )
    uploads = [
        step["with"]["path"]
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "upload-artifact@" in step.get("uses", "")
    ]
    assert any(
        "reports/performance/delta-sequential-merge/" in paths for paths in uploads
    )
