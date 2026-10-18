"""Bounded Linux Phase-0 probe of the production eager Silver input path.

Fixture creation and each observation run in fresh, resource-limited interpreters.
RSS is the measurement process lifetime high-water mark (imports included), never
an incremental allocation estimate. This is not an end-to-end merge benchmark.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MIB = 1024**2
THREAD_ENV = {
    "MALLOC_ARENA_MAX": "2",
    "POLARS_MAX_THREADS": "2",
    "RAYON_NUM_THREADS": "2",
    "TOKIO_WORKER_THREADS": "2",
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "ARROW_NUM_THREADS": "2",
}


def apply_guard(memory_mib: int, timeout_s: int) -> None:
    """Fail closed before native imports; RLIMIT_AS bounds virtual memory, not RSS."""
    if sys.platform != "linux":
        raise RuntimeError("This harness requires Linux RLIMIT_AS and /proc")
    os.environ.update(THREAD_ENV)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (memory_mib * MIB, memory_mib * MIB))
    resource.setrlimit(resource.RLIMIT_CPU, (timeout_s, timeout_s))


def prepare_fixture(rows: int, directory: Path) -> None:
    """Write deterministic narrow Activity/Target-like data, in a separate process."""
    import polars as pl
    from deltalake import write_deltalake

    frame = pl.DataFrame(
        {
            "entity_id": [f"activity_{i}" for i in range(rows)],
            "content_hash": [f"hash_{i % 1000}" for i in range(rows)],
            "target_id": [f"target_{i % 50}" for i in range(rows)],
            "activity_value": [float(i) * 1.5 for i in range(rows)],
            "_run_id": ["run_uuid_constant"] * rows,
            "_ingestion_ts": ["2026-01-01T12:00:00Z"] * rows,
            "_source_batch_id": ["batch_uuid_constant"] * rows,
        }
    )
    write_deltalake(str(directory / "chembl" / "activity"), frame.to_arrow())


def build_service(directory: Path):
    """Use production composition, MergeService and DeltaReader; no copied read logic.

    Output storage is unused: only _read_silver_table is exercised, not merge().
    """
    from bioetl.composition.bootstrap.runtime.composite_merge_service_builder import (
        build_composite_merge_service,
    )
    from bioetl.domain.composite import (
        CompositeConfig,
        DependencyConfig,
        MergeConfig,
        SeedConfig,
    )
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger
    from bioetl.infrastructure.storage.delta_reader import DeltaReader
    from bioetl.infrastructure.time.system_clock import SystemClock

    logger = NoOpLogger()
    config = CompositeConfig(
        name="measurement",
        version="1.0.0",
        seed=SeedConfig(
            "chembl_activity", ("entity_id", "target_id"), "chembl/activity"
        ),
        enrichers=(),
        dependencies=(DependencyConfig("chembl_target", ("target_id",)),),
        merge=MergeConfig(
            "left_outer", "seed_priority", "unused/silver", "unused/gold"
        ),
    )
    return build_composite_merge_service(
        config=config,
        storage=None,
        resolve_gold_schema=lambda _: None,
        delta_reader=DeltaReader(directory, logger),
        field_group_registry=None,
        cross_validator=None,
        logger=logger,
        system_columns_to_drop=frozenset(),
        normalization_policies={},
        clock=SystemClock(),
    )


async def measure(rows: int, directory: Path) -> dict:
    """Measure the live read; fixture preparation never occurs in this interpreter."""
    import pyarrow as pa

    pa.set_cpu_count(2)
    pa.set_io_thread_count(2)
    service = build_service(directory)
    start = time.perf_counter()
    frame = await service._read_silver_table("chembl/activity")
    elapsed = time.perf_counter() - start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    if frame.height != rows or frame["activity_value"].sum() != 0.75 * rows * (
        rows - 1
    ):
        raise ValueError("Production read failed row count/value validation")
    return {
        "rows": rows,
        "wall_time_s": elapsed,
        "process_peak_rss_bytes": peak,
        "pid": os.getpid(),
        "service": f"{type(service).__module__}.{type(service).__name__}",
        "read_method": service._read_silver_table.__func__.__module__,
        "rlimit_as_bytes": resource.getrlimit(resource.RLIMIT_AS)[0],
    }


def run_bounded(command: list[str], timeout_s: int) -> dict:
    """Capture actual exits, including termination after a timeout; never infer OOM."""
    start = time.perf_counter()
    env = {**os.environ, **THREAD_ENV}
    with subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            stdout, stderr = proc.communicate()
    return {
        "command": command,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "elapsed_s": time.perf_counter() - start,
        "stdout": stdout,
        "stderr": stderr,
    }


def source_identity() -> dict:
    """Bind observations to commit AND actual source bytes, including an uncommitted harness."""

    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

    files = [Path(__file__), ROOT / "uv.lock"]
    files.extend(sorted((ROOT / "src" / "bioetl").rglob("*.py")))
    digest = hashlib.sha256()
    for path in files:
        digest.update(
            path.relative_to(ROOT).as_posix().encode() + b"\0" + path.read_bytes()
        )
    return {
        "head_sha": git("rev-parse", "HEAD"),
        "head_tree": git("rev-parse", "HEAD^{tree}"),
        "working_tree_status": git("status", "--porcelain"),
        "source_bytes_sha256": digest.hexdigest(),
        "hash_scope": "harness, uv.lock, sorted src/bioetl/**/*.py; path NUL bytes",
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def fixture_identity(directory: Path) -> dict:
    """Record the actual Delta bytes; log IDs/timestamps need not be deterministic."""
    return {
        p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def orchestrate(args: argparse.Namespace) -> int:
    """Run bounded preparation followed by fresh repeated measurement processes."""
    source = source_identity()
    observations = []
    for rows in args.scales:
        with tempfile.TemporaryDirectory(prefix="merger-measurement-") as tmp:
            directory = Path(tmp)
            common = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--rows",
                str(rows),
                "--fixture",
                tmp,
                "--memory-mib",
                str(args.memory_mib),
                "--timeout-s",
                str(args.timeout_s),
            ]
            preparation = run_bounded([*common, "--phase", "prepare"], args.timeout_s)
            fixture = fixture_identity(directory)
            for repeat in range(1, args.repeats + 1):
                result = {
                    "rows": rows,
                    "repeat": repeat,
                    "preparation": preparation,
                    "fixture_sha256": fixture,
                    "measurement": None,
                    "status": "BLOCKED",
                }
                if preparation["exit_code"] == 0 and not preparation["timed_out"]:
                    run = run_bounded([*common, "--phase", "measure"], args.timeout_s)
                    result["measurement"] = run
                    if run["exit_code"] == 0 and not run["timed_out"]:
                        try:
                            result["raw"] = json.loads(run["stdout"])
                            result["status"] = "COMPLETED"
                        except json.JSONDecodeError:
                            result["status"] = "BLOCKED_INVALID_OUTPUT"
                observations.append(result)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "command": [sys.executable, *sys.argv],
        "source": source,
        "source_unchanged": source == source_identity(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "executable": sys.executable,
            "cgroup_memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip(),
            "threads": THREAD_ENV,
            "packages": {
                dist.metadata["Name"]: dist.version
                for dist in sorted(
                    importlib.metadata.distributions(), key=lambda d: d.metadata["Name"]
                )
            },
            "cpu_affinity_count": len(os.sched_getaffinity(0)),
        },
        "limits": {
            "address_space_mib": args.memory_mib,
            "timeout_s": args.timeout_s,
            "cpu_seconds": args.timeout_s,
        },
        "observations": observations,
        "conclusion": "NOT_ESTABLISHED: bounded synthetic input-read measurements only",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite historical evidence, even on a failed run.
    with args.out.open("x") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")
    return (
        0
        if payload["source_unchanged"]
        and all(row["status"] == "COMPLETED" for row in observations)
        else 1
    )


def main() -> int:
    """Parse explicit bounded execution controls before any data allocation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "measure"))
    parser.add_argument("--rows", type=int)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--scales", type=int, nargs="+", default=[100, 1000])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--memory-mib", type=int, default=4096)
    parser.add_argument("--timeout-s", type=int, default=30)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not 128 <= args.memory_mib <= 4096 or not 1 <= args.timeout_s <= 120:
        parser.error("memory must be 128..4096 MiB; timeout must be 1..120 seconds")
    if not 1 <= args.repeats <= 10 or any(not 1 <= n <= 100_000 for n in args.scales):
        parser.error("repeats must be 1..10; scales must be 1..100000 rows")
    if args.phase:
        if args.rows is None or not 1 <= args.rows <= 100_000 or args.fixture is None:
            parser.error("worker requires --rows 1..100000 and --fixture")
        apply_guard(args.memory_mib, args.timeout_s)
        if args.phase == "prepare":
            prepare_fixture(args.rows, args.fixture)
        else:
            print(json.dumps(asyncio.run(measure(args.rows, args.fixture))))
        return 0
    if args.out is None or args.out.exists():
        parser.error("provide --out pointing to a new raw-observation JSON file")
    return orchestrate(args)


if __name__ == "__main__":
    raise SystemExit(main())
