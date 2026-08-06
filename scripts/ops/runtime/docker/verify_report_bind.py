#!/usr/bin/env python3
"""Verify host vs container report-root bind alignment for Browse Recent Runs.

Fail-closed operator check for the stale Docker Desktop bind class of bugs:
CLI/pipeline writers land under the checkout ``reports/run-reports/`` tree while
the ``bioetl`` health container may still mount an empty cached tree at
``/app/reports``.

Usage (from repository root)::

    python scripts/ops/runtime/docker/verify_report_bind.py
    python scripts/ops/runtime/docker/verify_report_bind.py --pipeline chembl_assay
    python scripts/ops/runtime/docker/verify_report_bind.py --ops-url http://127.0.0.1:8000

Exit codes:
    0 — host marker, host reports, and (when reachable) ops HTTP agree
    1 — mismatch or missing marker / empty bind
    2 — usage / infrastructure error (docker inspect failed, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_ROOT = _REPO_ROOT / "src"
for _path in (_REPO_ROOT, _SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from bioetl.application.services.run_reports.paths import (  # noqa: E402
    REPORT_ROOT_MARKER_NAME,
    REPORT_ROOT_MARKER_TOKEN,
    inspect_report_root_marker,
)
from bioetl.application.services.run_reports.query import (  # noqa: E402
    list_pipeline_reports,
)

DEFAULT_OPS_URL = "http://127.0.0.1:8000"
DEFAULT_CONTAINER = "bioetl"
DEFAULT_MOUNT_TARGET = "/app/reports"


def _repo_root() -> Path:
    configured = os.environ.get("BIOETL_REPO_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _REPO_ROOT


def _host_report_root(repo: Path) -> Path:
    env = os.environ.get("BIOETL_REPORT_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (repo / "reports" / "run-reports").resolve()


def _host_reports_mount(repo: Path) -> Path:
    env = os.environ.get("BIOETL_DASHBOARD_REPORT_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (repo / "reports").resolve()


def _json_get(url: str, *, timeout: float = 5.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"WARN: ops HTTP unreachable at {url}: {exc}")
        return None
    return payload if isinstance(payload, dict) else None


def _docker_inspect_mounts(container: str) -> list[dict[str, Any]] | None:
    try:
        completed = subprocess.run(
            ["docker", "inspect", container, "--format", "{{json .Mounts}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"WARN: docker inspect failed: {exc}")
        return None
    if completed.returncode != 0:
        print(
            f"WARN: docker inspect {container!r} rc={completed.returncode}: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
        return None
    try:
        mounts = json.loads(completed.stdout)
    except json.JSONDecodeError:
        print("WARN: docker inspect returned non-JSON mounts payload")
        return None
    return mounts if isinstance(mounts, list) else None


def _mount_source_for_target(
    mounts: Sequence[Mapping[str, Any]],
    target: str,
) -> str | None:
    for mount in mounts:
        if str(mount.get("Destination") or mount.get("Target") or "") == target:
            source = mount.get("Source")
            return str(source) if source else None
    return None


def _paths_equivalent(left: str, right: Path) -> bool:
    try:
        left_resolved = Path(left).resolve()
    except OSError:
        left_resolved = Path(left)
    try:
        right_resolved = right.resolve()
    except OSError:
        right_resolved = right
    return left_resolved.as_posix().lower() == right_resolved.as_posix().lower()


def verify(
    *,
    repo: Path,
    ops_url: str,
    container: str,
    pipeline: str | None,
    require_ops: bool,
) -> int:
    host_mount = _host_reports_mount(repo)
    host_root = _host_report_root(repo)
    findings: list[str] = []
    ok = True

    print(f"repo_root={repo}")
    print(f"host_reports_mount={host_mount}")
    print(f"host_report_root={host_root}")

    marker_path = host_mount / REPORT_ROOT_MARKER_NAME
    if not marker_path.is_file():
        ok = False
        findings.append(
            f"FAIL: host marker missing at {marker_path} "
            f"(expected token {REPORT_ROOT_MARKER_TOKEN!r})"
        )
    else:
        token = marker_path.read_text(encoding="utf-8").strip()
        if token != REPORT_ROOT_MARKER_TOKEN:
            ok = False
            findings.append(
                f"FAIL: host marker token mismatch at {marker_path}: {token!r}"
            )
        else:
            print(f"OK: host marker {marker_path}")

    host_check = inspect_report_root_marker(report_root=host_root)
    print(f"host_marker_check={json.dumps(host_check, sort_keys=True)}")
    if host_check.get("status") != "healthy":
        ok = False
        findings.append(f"FAIL: {host_check.get('message')}")

    host_count: int | None = None
    if pipeline:
        entries = list_pipeline_reports(
            pipeline_name=pipeline,
            limit=100,
            root=host_root,
        )
        host_count = len(entries)
        print(f"host_pipeline_count pipeline={pipeline!r} count={host_count}")
        if host_count == 0:
            findings.append(
                f"WARN: no host pipeline reports for {pipeline!r} under {host_root}"
            )

    mounts = _docker_inspect_mounts(container)
    if mounts is None:
        findings.append(
            f"WARN: could not inspect container {container!r}; "
            "skip bind-source comparison"
        )
    else:
        source = _mount_source_for_target(mounts, DEFAULT_MOUNT_TARGET)
        print(f"container_mount target={DEFAULT_MOUNT_TARGET} source={source!r}")
        if source is None:
            ok = False
            findings.append(
                f"FAIL: container {container!r} has no bind at {DEFAULT_MOUNT_TARGET}"
            )
        elif not _paths_equivalent(source, host_mount):
            ok = False
            findings.append(
                f"FAIL: bind mismatch — container source={source!r} "
                f"expected host_reports_mount={host_mount}"
            )
            findings.append(
                "Remediation: from the canonical checkout run "
                "`python scripts/ops/runtime/docker/runtime_manager.py start "
                "--stack main` (or recreate bioetl with "
                "BIOETL_DASHBOARD_REPORT_ROOT pointing at this reports/)."
            )
        else:
            print("OK: container bind source matches host reports mount")

    ready = _json_get(f"{ops_url.rstrip('/')}/health/ready")
    if ready is None:
        if require_ops:
            ok = False
            findings.append(f"FAIL: ops HTTP not reachable at {ops_url}")
        else:
            findings.append(f"WARN: ops HTTP not reachable at {ops_url}")
    else:
        report_check = ready.get("checks", {}).get("report_root")
        print(f"ops_ready_status={ready.get('status')!r}")
        print(f"ops_report_root_check={json.dumps(report_check, sort_keys=True)}")
        if isinstance(report_check, Mapping) and report_check.get("status") != "healthy":
            ok = False
            findings.append(
                "FAIL: /health/ready report_root check is not healthy "
                f"({report_check.get('message') or report_check.get('marker')})"
            )
        if ready.get("status") == "unhealthy":
            ok = False
            findings.append("FAIL: /health/ready status=unhealthy")

    if pipeline:
        list_url = (
            f"{ops_url.rstrip('/')}/ops/observability/pipeline-run-reports"
            f"?pipeline={pipeline}&limit=20"
        )
        listed = _json_get(list_url)
        if listed is None:
            if require_ops:
                ok = False
                findings.append(f"FAIL: list endpoint unreachable: {list_url}")
        else:
            ops_count = int(listed.get("count") or 0)
            print(
                f"ops_pipeline_count pipeline={pipeline!r} count={ops_count} "
                f"report_root={listed.get('report_root')!r} "
                f"marker_status={listed.get('marker_status')!r}"
            )
            if listed.get("marker_status") and listed.get("marker_status") != "healthy":
                ok = False
                findings.append(
                    f"FAIL: ops list marker_status={listed.get('marker_status')!r}"
                )
            if host_count is not None and host_count > 0 and ops_count == 0:
                ok = False
                findings.append(
                    f"FAIL: host has {host_count} report(s) for {pipeline!r} "
                    f"but ops HTTP returns count=0 — classic bind mismatch"
                )
            elif host_count is not None and ops_count > 0:
                print("OK: ops HTTP sees pipeline reports")

    for line in findings:
        print(line)

    if ok:
        print("RESULT: report bind verification passed")
        return 0
    print("RESULT: report bind verification FAILED")
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify BioETL host/container report-root bind alignment",
    )
    parser.add_argument(
        "--pipeline",
        default=os.environ.get("BIOETL_VERIFY_PIPELINE", "chembl_assay"),
        help="Pipeline name for host vs ops count comparison (default: chembl_assay)",
    )
    parser.add_argument(
        "--ops-url",
        default=os.environ.get("BIOETL_OPS_HTTP_URL", DEFAULT_OPS_URL),
        help=f"Ops HTTP base URL (default: {DEFAULT_OPS_URL})",
    )
    parser.add_argument(
        "--container",
        default=os.environ.get("BIOETL_CONTAINER_NAME", DEFAULT_CONTAINER),
        help=f"Docker container name (default: {DEFAULT_CONTAINER})",
    )
    parser.add_argument(
        "--require-ops",
        action="store_true",
        help="Fail when ops HTTP is unreachable (default: warn only)",
    )
    parser.add_argument(
        "--no-pipeline",
        action="store_true",
        help="Skip host/ops pipeline count comparison",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    pipeline = None if args.no_pipeline else str(args.pipeline or "").strip() or None
    return verify(
        repo=_repo_root(),
        ops_url=str(args.ops_url),
        container=str(args.container),
        pipeline=pipeline,
        require_ops=bool(args.require_ops),
    )


if __name__ == "__main__":
    raise SystemExit(main())
