"""Prove composite replay from saved inputs with external connections denied."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from scripts.ops.observability.green_acceptance import (
    Case,
    command,
    inspect_pipeline,
    launch_timeout,
    logged_errors,
    run_launch,
)

NETWORK_GUARD = """import socket
_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex
def connect(self, address):
    if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1", "localhost"):
        return _connect(self, address)
    raise RuntimeError("OFFLINE_REPLAY_NETWORK_ACCESS_DENIED")
def connect_ex(self, address):
    if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1", "localhost"):
        return _connect_ex(self, address)
    raise RuntimeError("OFFLINE_REPLAY_NETWORK_ACCESS_DENIED")
socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
"""


def compare_gold(source: Path, replay: Path, entity: str) -> dict[str, object]:
    """Compare complete current tables, including all persisted provenance fields."""
    import polars as pl
    from deltalake import DeltaTable

    tables = []
    for directory in (source, replay):
        path = directory / "data/output/gold/composite" / entity
        tables.append(
            pl.from_arrow(DeltaTable(str(path)).to_pyarrow_table()).sort("entity_id")
        )
    original, reproduced = tables
    differences = [
        name
        for name in original.columns
        if name not in reproduced.columns or not original[name].equals(reproduced[name])
    ]
    return {
        "original_rows": original.height,
        "replayed_rows": reproduced.height,
        "schema_equal": original.schema == reproduced.schema,
        "different_columns": differences,
        "equal": original.equals(reproduced),
    }


def execute_replay(
    case: Case, root: Path, source: Path, output: Path, env_file: Path
) -> list[str]:
    """Replay a green same-revision parent into empty Silver/Gold tables."""
    from dotenv import dotenv_values

    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=root, text=True
    ).strip()
    assert branch.startswith("codex/") and (root / ".git").is_file(), branch
    assert not subprocess.check_output(
        ["git", "status", "--porcelain", "-uno"], cwd=root, text=True
    ).strip()
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    saved = json.loads((source / "result.json").read_text(encoding="utf-8"))
    assert saved["passed"] is True, "Replay proof requires a green parent launch"
    assert saved["source_commit"] == sha, (
        "Replay proof requires the same source revision"
    )
    assert saved["case"] == case.id
    limit = saved["limit"]
    assert type(limit) is int and limit > 0
    parents = []
    for path in (source / "data/output/control/run_manifest").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("provider") == "composite"
            and payload.get("pipeline_name") == case.name
        ):
            parents.append(payload)
    assert len(parents) == 1, "Expected one source composite parent"
    parent = parents[0]
    assert parent["launch_context"].get("child_replay_manifests")
    destination = output / case.id
    assert destination.resolve().is_relative_to(root.resolve())
    destination.mkdir(parents=True, exist_ok=False)
    for relative in (
        "data/input",
        "data/output/bronze",
        "data/output/control",
        "configs",
    ):
        shutil.copytree(source / relative, destination / relative)
    shutil.copy2(source / "uv.lock", destination / "uv.lock")
    guard = destination / "network_guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(NETWORK_GUARD, encoding="utf-8")
    data, reports = destination / "data", destination / "reports"
    environment = {
        **os.environ,
        **{
            key: value
            for key, value in dotenv_values(env_file).items()
            if value is not None
        },
    }
    environment.update(
        BIOETL_DATA_DIR=str(data),
        BIOETL_REPORT_ROOT=str(reports),
        BIOETL_CONFIGS_ROOT=str(root / "configs"),
        PYTHONPATH=os.pathsep.join((str(guard), str(root / "src"), str(root))),
        PYTHONDONTWRITEBYTECODE="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        POLARS_MAX_THREADS="2",
        TOKIO_WORKER_THREADS="2",
        BIOETL_METRICS_ENABLED="false",
        BIOETL_OBSERVABILITY__METRICS_ENABLED="false",
        BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED="false",
        BIOETL_PUSHGATEWAY_URL="",
    )
    if os.name == "nt":
        environment[
            "BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__PLAIN_WRITE_PROCESS_ISOLATION"
        ] = "true"
    args = command(case, limit=limit) + [
        "--no-ensure-observability-backend",
        "--replay-of-manifest-id",
        parent["manifest_id"],
    ]
    with (destination / "launch.log").open("w", encoding="utf-8") as log:
        failures = run_launch(
            args,
            destination,
            environment,
            log,
            timeout_seconds=launch_timeout(case, root),
        )
    failures.extend(
        logged_errors((destination / "launch.log").read_text(encoding="utf-8"))
    )
    paths = sorted(reports.glob("pipeline/*/*/pipeline-run-report.json"))
    if not paths:
        failures.append("pipeline_reports_missing")
    for path in paths:
        failures.extend(inspect_pipeline(path, reports, data))
    comparison: dict[str, object] = {}
    try:
        comparison = compare_gold(
            source, destination, case.name.removeprefix("composite_")
        )
        if comparison["equal"] is not True:
            failures.append("replayed_gold_differs_from_original")
    except (OSError, RuntimeError, ValueError) as exc:
        failures.append(f"gold_comparison_failed: {exc}")
    (destination / "result.json").write_text(
        json.dumps(
            {
                "case": case.id,
                "command": args,
                "source_commit": sha,
                "parent_manifest_id": parent["manifest_id"],
                "limit": limit,
                "external_connections_denied": True,
                "empty_output_tables_at_start": True,
                "gold_comparison": comparison,
                "passed": not failures,
                "failures": failures,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return failures
