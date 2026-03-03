"""Relative regression budgets for performance hotspots.

Targets:
- Silver write pre-processing path (`_prepare_arrow_data`)
- Silver append write path
- Silver merge write path
- Adapter batch path (CrossRef DOI batch fetch)

These tests intentionally use synthetic deterministic datasets and relative
thresholds to reduce CI timing flakiness.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import pyarrow as pa
import pytest

from bioetl.infrastructure.adapters.crossref.batch import DoiBatchProcessor
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.silver_writer import SilverWriter

pytestmark = [pytest.mark.benchmark, pytest.mark.performance, pytest.mark.serial]

_BUDGETS_PATH = Path(__file__).with_name("hotspot_budgets.json")
_WARMUP_ROUNDS = 1
_REPEATS_FAST = 5
_REPEATS_IO = 3
_OBS_OUT_ENV = "BIOETL_PERF_OBS_OUT"


@dataclass(frozen=True)
class HotspotBudget:
    """Single hotspot budget definition."""

    baseline_latency_ms: float
    baseline_throughput_rps: float
    max_regression_pct: float


class _FakeResponse:
    """Lightweight fake HTTP response for adapter benchmarks."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.status_code = 200
        self._items = items

    def json(self) -> dict[str, Any]:
        return {"message": {"items": self._items}}


class _FakeHttp:
    """Lightweight async HTTP transport for adapter benchmarks."""

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    async def get(self, *args: Any, **kwargs: Any) -> _FakeResponse:
        del args, kwargs
        return self._response


class _FakeMetrics:
    """No-op metrics adapter with context manager API."""

    @contextmanager
    def measure_request(self, _route: str):  # type: ignore[no-untyped-def]
        yield


def _load_budgets() -> dict[str, HotspotBudget]:
    raw = json.loads(_BUDGETS_PATH.read_text(encoding="utf-8"))
    budgets = raw.get("benchmarks", {})
    return {
        key: HotspotBudget(
            baseline_latency_ms=float(value["baseline_latency_ms"]),
            baseline_throughput_rps=float(value["baseline_throughput_rps"]),
            max_regression_pct=float(value["max_regression_pct"]),
        )
        for key, value in budgets.items()
    }


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _run_sync_benchmark(op: Any, repeats: int) -> float:
    for _ in range(_WARMUP_ROUNDS):
        op()

    durations: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        op()
        durations.append(time.perf_counter() - started)
    return _median(durations)


def _build_silver_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("entity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("_content_hash", pa.string()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )


def _build_silver_records(
    count: int, run_id: str, batch_id: str
) -> list[dict[str, Any]]:
    ingestion_ts = "2026-03-03T00:00:00Z"
    return [
        {
            "entity_id": f"entity_{i:06d}",
            "value": float(i) * 0.1,
            "_content_hash": f"hash_{i:06d}",
            "_run_id": run_id,
            "_run_type": "benchmark",
            "_source_batch_id": batch_id,
            "_ingestion_ts": ingestion_ts,
        }
        for i in range(count)
    ]


def _merge_payloads(
    run_id: str, batch_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = _build_silver_records(600, run_id, batch_id)
    merge_records = _build_silver_records(600, run_id, batch_id)
    for i in range(300):
        merge_records[i]["value"] = merge_records[i]["value"] + 1000.0
    for i in range(300, 600):
        merge_records[i]["entity_id"] = f"entity_new_{i:06d}"
    return base, merge_records


def _assert_budget(
    benchmark_key: str,
    budget: HotspotBudget,
    median_latency_s: float,
    processed_records: int,
) -> None:
    latency_ms = median_latency_s * 1000.0
    throughput_rps = processed_records / median_latency_s

    max_latency_ms = budget.baseline_latency_ms * (1.0 + budget.max_regression_pct)
    min_throughput_rps = budget.baseline_throughput_rps * (
        1.0 - budget.max_regression_pct
    )

    assert latency_ms <= max_latency_ms, (
        f"{benchmark_key}: latency regression "
        f"(actual={latency_ms:.2f}ms, allowed<={max_latency_ms:.2f}ms; "
        f"baseline={budget.baseline_latency_ms:.2f}ms, budget={budget.max_regression_pct:.0%})"
    )
    assert throughput_rps >= min_throughput_rps, (
        f"{benchmark_key}: throughput regression "
        f"(actual={throughput_rps:.2f}r/s, required>={min_throughput_rps:.2f}r/s; "
        f"baseline={budget.baseline_throughput_rps:.2f}r/s, budget={budget.max_regression_pct:.0%})"
    )


def _record_observation(
    benchmark_key: str,
    median_latency_s: float,
    processed_records: int,
    obs_out_path: Path | None,
) -> None:
    """Append runtime observation to a JSONL file when enabled by env."""
    out_path_raw = (
        str(obs_out_path) if obs_out_path is not None else os.getenv(_OBS_OUT_ENV)
    )
    if not out_path_raw:
        return

    out_path = Path(out_path_raw)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    latency_ms = median_latency_s * 1000.0
    throughput_rps = processed_records / median_latency_s
    payload = {
        "benchmark_key": benchmark_key,
        "latency_ms": latency_ms,
        "throughput_rps": throughput_rps,
        "records": processed_records,
        "timestamp_unix": time.time(),
    }
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True, sort_keys=True))
        f.write("\n")


def _obs_out_from_config(pytestconfig: pytest.Config) -> Path | None:
    """Resolve observation file path from pytest option."""
    raw = pytestconfig.getoption("perf_obs_out")
    return Path(raw) if raw else None


def test_silver_prepare_arrow_data_budget(
    tmp_path: Path,
    pytestconfig: pytest.Config,
) -> None:
    """Budget gate for Arrow preparation hotspot in Silver writer."""
    budgets = _load_budgets()
    budget = budgets["silver_prepare_arrow_2000"]

    writer = SilverWriter(base_path=tmp_path / "silver_prepare", logger=NoOpLogger())
    schema = _build_silver_schema()
    records = _build_silver_records(2000, run_id=str(uuid4()), batch_id=str(uuid4()))

    def op() -> None:
        writer._prepare_arrow_data(
            records=records, schema=schema, primary_keys=["entity_id"]
        )

    median_latency = _run_sync_benchmark(op, repeats=_REPEATS_FAST)
    _assert_budget(
        benchmark_key="silver_prepare_arrow_2000",
        budget=budget,
        median_latency_s=median_latency,
        processed_records=len(records),
    )
    _record_observation(
        benchmark_key="silver_prepare_arrow_2000",
        median_latency_s=median_latency,
        processed_records=len(records),
        obs_out_path=_obs_out_from_config(pytestconfig),
    )


def test_silver_write_append_budget(
    tmp_path: Path,
    pytestconfig: pytest.Config,
) -> None:
    """Budget gate for Silver append write path."""
    budgets = _load_budgets()
    budget = budgets["silver_write_append_600"]

    writer = SilverWriter(base_path=tmp_path / "silver_append", logger=NoOpLogger())
    schema = _build_silver_schema()

    async def op() -> float:
        run_id = str(uuid4())
        batch_id = str(uuid4())
        table_name = f"perf.append_{uuid4().hex[:12]}"
        records = _build_silver_records(600, run_id=run_id, batch_id=batch_id)
        started = time.perf_counter()
        await writer.write_silver(
            table_name=table_name,
            records=records,
            primary_keys=["entity_id"],
            schema=schema,
            mode="append",
        )
        return time.perf_counter() - started

    async def run() -> float:
        for _ in range(_WARMUP_ROUNDS):
            await op()
        durations = [await op() for _ in range(_REPEATS_IO)]
        return _median(durations)

    median_latency = asyncio.run(run())
    _assert_budget(
        benchmark_key="silver_write_append_600",
        budget=budget,
        median_latency_s=median_latency,
        processed_records=600,
    )
    _record_observation(
        benchmark_key="silver_write_append_600",
        median_latency_s=median_latency,
        processed_records=600,
        obs_out_path=_obs_out_from_config(pytestconfig),
    )


def test_silver_write_merge_budget(
    tmp_path: Path,
    pytestconfig: pytest.Config,
) -> None:
    """Budget gate for Silver merge write path."""
    budgets = _load_budgets()
    budget = budgets["silver_write_merge_600"]

    writer = SilverWriter(base_path=tmp_path / "silver_merge", logger=NoOpLogger())
    schema = _build_silver_schema()

    async def op() -> float:
        run_id = str(uuid4())
        batch_id = str(uuid4())
        table_name = f"perf.merge_{uuid4().hex[:12]}"
        base_records, merge_records = _merge_payloads(run_id=run_id, batch_id=batch_id)
        await writer.write_silver(
            table_name=table_name,
            records=base_records,
            primary_keys=["entity_id"],
            schema=schema,
            mode="append",
        )
        started = time.perf_counter()
        await writer.write_silver(
            table_name=table_name,
            records=merge_records,
            primary_keys=["entity_id"],
            schema=schema,
            mode="merge",
        )
        return time.perf_counter() - started

    async def run() -> float:
        for _ in range(_WARMUP_ROUNDS):
            await op()
        durations = [await op() for _ in range(_REPEATS_IO)]
        return _median(durations)

    median_latency = asyncio.run(run())
    _assert_budget(
        benchmark_key="silver_write_merge_600",
        budget=budget,
        median_latency_s=median_latency,
        processed_records=600,
    )
    _record_observation(
        benchmark_key="silver_write_merge_600",
        median_latency_s=median_latency,
        processed_records=600,
        obs_out_path=_obs_out_from_config(pytestconfig),
    )


def test_crossref_batch_adapter_budget(pytestconfig: pytest.Config) -> None:
    """Budget gate for adapter batch-path (CrossRef DOI batch fetch)."""
    budgets = _load_budgets()
    budget = budgets["crossref_batch_fetch_200"]

    dois = [f"10.1000/test{i:04d}" for i in range(200)]
    items = [{"DOI": doi, "title": [f"title_{i}"]} for i, doi in enumerate(dois)]
    processor = DoiBatchProcessor(
        http=_FakeHttp(_FakeResponse(items)),
        logger=NoOpLogger(),
        metrics=_FakeMetrics(),
        mailto="perf@example.com",
        api_base="https://api.crossref.org",
        headers_fn=lambda: {"User-Agent": "bioetl-perf"},
    )

    async def op() -> float:
        started = time.perf_counter()
        records = [item async for item in processor.fetch_batch(dois)]
        elapsed = time.perf_counter() - started
        if len(records) != len(dois):
            raise AssertionError(
                f"crossref_batch_fetch_200: expected {len(dois)} records, got {len(records)}"
            )
        return elapsed

    async def run() -> float:
        for _ in range(_WARMUP_ROUNDS):
            await op()
        durations = [await op() for _ in range(_REPEATS_FAST)]
        return _median(durations)

    median_latency = asyncio.run(run())
    _assert_budget(
        benchmark_key="crossref_batch_fetch_200",
        budget=budget,
        median_latency_s=median_latency,
        processed_records=len(dois),
    )
    _record_observation(
        benchmark_key="crossref_batch_fetch_200",
        median_latency_s=median_latency,
        processed_records=len(dois),
        obs_out_path=_obs_out_from_config(pytestconfig),
    )
