"""Performance harness for measuring sequential Delta merge behavior.

This test focuses on N sequential merges into a growing Delta table
to identify O(N^2) or linear degradation characteristics, isolating
Delta Engine overhead from generic pytest-benchmark runs.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
from filelock import FileLock

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.delta.resilience import (
    build_default_silver_merge_policy,
)
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.time import SystemClock
from tests.helpers.deterministic_ids import (
    deterministic_uuid_from_callsite,
    deterministic_uuid_string_from_callsite,
)

pytestmark = [
    pytest.mark.performance,
    pytest.mark.serial,
    pytest.mark.timeout(900),  # Sequential merges can be slow
]

_WINDOWS_PLATFORM = sys.platform == "win32" or os.name == "nt"


class FakeLogger:
    """Minimal fake logger for performance tests."""

    def info(self, _msg: str, **_kwargs: Any) -> None:
        pass

    def debug(self, _msg: str, **_kwargs: Any) -> None:
        pass

    def warning(self, _msg: str, **_kwargs: Any) -> None:
        pass

    def error(self, _msg: str, **_kwargs: Any) -> None:
        pass

    def bind(self, **_kwargs: Any) -> FakeLogger:
        return self


def _create_activity_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("molecule_id", pa.string()),
            pa.field("assay_id", pa.string()),
            pa.field("target_id", pa.string()),
            pa.field("standard_value", pa.float64()),
            pa.field("standard_units", pa.string()),
            pa.field("pchembl_value", pa.float64()),
            pa.field("canonical_smiles", pa.string()),
            pa.field("_content_hash", pa.string()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.timestamp("us")),
        ]
    )


def _generate_synthetic_batch(
    start_idx: int, batch_size: int, overlap_ratio: float = 0.2
) -> list[dict[str, Any]]:
    """Generate a deterministic synthetic batch of records with specified overlap."""
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    run_id = deterministic_uuid_string_from_callsite("perf_delta_merge")
    records = []

    overlap_count = int(batch_size * overlap_ratio)

    for i in range(batch_size):
        idx = (
            max(0, start_idx - overlap_count + i)
            if i < overlap_count and start_idx > 0
            else start_idx + i
        )

        record_id = f"ACT_{idx:08d}"

        records.append(
            {
                "id": record_id,
                "molecule_id": f"CHEMBL_{idx % 1000}",
                "assay_id": f"ASSAY_{idx % 100}",
                "target_id": f"TGT_{idx % 50}",
                "standard_value": float(idx % 1000) * 1.5,
                "standard_units": "nM",
                "pchembl_value": 9.0 - (idx % 100) * 0.01,
                "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
                "_content_hash": f"hash_{idx}_{start_idx}",
                "_run_id": run_id,
                "_run_type": "perf_test",
                "_source_batch_id": f"batch_{start_idx}",
                "_ingestion_ts": now,
            }
        )

    return records


def _create_silver_writer(base_path: Path) -> SilverWriter:
    clock = SystemClock()
    from dataclasses import replace

    return SilverWriter(
        base_path=base_path,
        logger=FakeLogger(),
        runtime_request=SilverWriterRuntimeServicesRequest(
            clock=clock,
            merge_resilience_policy=replace(
                build_default_silver_merge_policy(),
                execution_timeout_seconds=600.0,
                plain_write_process_isolation=False,
            ),
        ),
    )


def _get_process_rss_mb() -> float:
    """Get current process RSS in MB."""
    import psutil

    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def _get_file_stats(directory: Path, pattern: str) -> dict[str, int]:
    """Count matching files and their on-disk bytes."""
    total_bytes = 0
    file_count = 0
    for path in directory.glob(pattern):
        if path.is_file():
            total_bytes += path.stat().st_size
            file_count += 1
    return {"bytes": total_bytes, "files": file_count}


@pytest.mark.parametrize("n_merges", [10, 50, 100])
def test_delta_sequential_merge_scaling(
    tmp_path: Path, n_merges: int, request: pytest.FixtureRequest
):
    """Measure N sequential merges into the same Delta table."""
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    is_ci = os.environ.get("CI", "").lower() in ("true", "1")
    if is_ci and n_merges > 50:
        pytest.skip(
            "Skipping N=100 on CI to prevent timeouts due to known issue #12042"
        )

    table_name = f"perf_sequential_{n_merges}"
    round_root = (
        tmp_path / f"seq_merge_{deterministic_uuid_from_callsite('perf_merge').hex[:8]}"
    )
    round_root.mkdir(parents=True, exist_ok=True)
    table_path = round_root / table_name

    writer = _create_silver_writer(round_root)
    schema = _create_activity_schema()

    batch_size = 500
    overlap_ratio = 0.2

    results = []
    total_records_processed = 0

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 1. Setup cost phase
    t_setup_start = time.perf_counter()
    start_rss = _get_process_rss_mb()

    t_setup_end = time.perf_counter()
    setup_time = t_setup_end - t_setup_start

    try:
        for i in range(n_merges):
            start_idx = i * int(batch_size * (1 - overlap_ratio))
            batch = _generate_synthetic_batch(start_idx, batch_size, overlap_ratio)
            total_records_processed += len(batch)

            t_start = time.perf_counter()

            loop.run_until_complete(
                writer.write_silver(
                    table_name=table_name,
                    records=batch,
                    schema=schema,
                    primary_keys=["id"],
                    mode=SilverWriteMode.MERGE,
                )
            )
            t_end = time.perf_counter()

            merge_time = t_end - t_start

            log_stats = _get_file_stats(table_path / "_delta_log", "*")
            parquet_stats = _get_file_stats(table_path, "**/*.parquet")
            current_rss = _get_process_rss_mb()

            from deltalake import DeltaTable

            dt = DeltaTable(str(table_path))

            results.append(
                {
                    "round": i + 1,
                    "merge_time_s": round(merge_time, 4),
                    "rss_mb": round(current_rss, 2),
                    "rss_delta_mb": round(current_rss - start_rss, 2),
                    "delta_log_files": log_stats["files"],
                    "delta_log_bytes": log_stats["bytes"],
                    "parquet_files": parquet_stats["files"],
                    "parquet_bytes": parquet_stats["bytes"],
                    "table_version": dt.version(),
                }
            )

            if merge_time > 60.0:
                # Save incomplete results before failing
                summary_data = {
                    "n_merges_target": n_merges,
                    "n_merges_completed": i + 1,
                    "status": "incomplete",
                    "batch_size": batch_size,
                    "overlap_ratio": overlap_ratio,
                    "total_records_processed": total_records_processed,
                    "setup_time_s": round(setup_time, 4),
                    "platform": sys.platform,
                    "merges": results,
                }
                summary_path = tmp_path / f"merge_scaling_N{n_merges}_incomplete.json"
                with summary_path.open("w", encoding="utf-8") as f:
                    json.dump(summary_data, f, indent=2)
                pytest.fail(
                    f"Merge degraded severely: round {i + 1} took {merge_time:.2f}s"
                )

    finally:
        loop.close()

    # Smoke regression check for row outcomes
    from deltalake import DeltaTable

    dt = DeltaTable(str(table_path))
    # actual total rows = N * batch_size - overlaps
    # total overlaps = (N - 1) * overlap_ratio * batch_size
    expected_rows = n_merges * batch_size - (n_merges - 1) * int(
        batch_size * overlap_ratio
    )
    actual_rows = dt.to_pyarrow_dataset().count_rows()

    assert actual_rows == expected_rows, (
        f"Expected {expected_rows} rows, got {actual_rows}"
    )
    assert dt.version() >= n_merges - 1, (
        f"Expected at least {n_merges - 1} versions, got {dt.version()}"
    )

    summary_path = tmp_path / f"merge_scaling_N{n_merges}.json"
    summary_data = {
        "n_merges_target": n_merges,
        "n_merges_completed": n_merges,
        "status": "complete",
        "batch_size": batch_size,
        "overlap_ratio": overlap_ratio,
        "total_records_processed": total_records_processed,
        "expected_final_rows": expected_rows,
        "actual_final_rows": actual_rows,
        "setup_time_s": round(setup_time, 4),
        "platform": sys.platform,
        "merges": results,
    }

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    perf_out = request.config.getoption("--perf-obs-out", default=None)
    if perf_out:
        with (
            FileLock(f"{perf_out}.lock"),
            Path(perf_out).open("a", encoding="utf-8") as f,
        ):
            f.write(
                json.dumps(
                    {
                        "test": f"test_delta_sequential_merge_scaling_N{n_merges}",
                        "metric_type": "delta_merge_latency_total",
                        "value": sum(r["merge_time_s"] for r in results),
                        "timestamp": datetime.now(UTC).isoformat(),
                        "unit": "s",
                        "context": {"n_merges": n_merges},
                    }
                )
                + "\n"
            )
