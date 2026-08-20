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
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_ROOT = _REPO_ROOT / "src"
for _path in (_REPO_ROOT, _SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from bioetl.application.services.run_reports.paths import (
    REPORT_ROOT_MARKER_NAME,
    REPORT_ROOT_MARKER_VALUE,
    inspect_report_root_marker,
    inspect_report_root_source_identity,
)
from bioetl.application.services.run_reports.query import (
    list_pipeline_reports,
)
from bioetl.application.services.run_reports.source_identity import (
    IDENTITY_STATE_ALIGNED,
    RuntimeSourceIdentityResolutionResult,
    compare_runtime_source_identity,
    resolve_runtime_source_identity,
)
from scripts.ops.runtime.docker import docker_runtime_preflight as runtime_preflight
from scripts.engineering.common.repo_paths import (
    ensure_local_http_url,
    ensure_safe_cli_argv,
)

DEFAULT_OPS_URL = "http://127.0.0.1:8000"
DEFAULT_CONTAINER = "bioetl"
DEFAULT_MOUNT_TARGET = "/app/reports"


def _validated_container_name(value: str) -> str:
    """Return one bounded Docker object name safe for argv execution."""
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value) is None:
        raise ValueError(f"invalid Docker container name: {value!r}")
    return value


def _repo_root() -> Path:
    configured = os.environ.get("BIOETL_REPO_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _REPO_ROOT


def _looks_like_container_path(value: str) -> bool:
    """True when *value* is a Linux container path, not a host bind source.

    Compose injects ``BIOETL_REPORT_ROOT=/app/reports/run-reports`` for the
    bioetl service. Operators who re-export that shell env on Windows must not
    make host-side verify resolve to a bogus host path. Git Bash MSYS path
    conversion rewrites ``/app/...`` to ``C:/Program Files/Git/app/...``.
    """
    normalized = value.strip().replace("\\", "/")
    if normalized == "/app" or normalized.startswith("/app/"):
        return True
    lowered = normalized.casefold()
    # Git Bash (MSYS) rewrite of absolute container paths under the Git install.
    return "/git/app/" in lowered or lowered.endswith("/git/app")


def _host_report_root(repo: Path) -> Path:
    from scripts.engineering.common.repo_paths import resolve_output_path

    env = os.environ.get("BIOETL_REPORT_ROOT", "").strip()
    if env and not _looks_like_container_path(env):
        return resolve_output_path(Path(env).expanduser(), root=repo)
    # When BIOETL_REPORT_ROOT is unset or a container path, follow the
    # dashboard reports bind (BIOETL_DASHBOARD_REPORT_ROOT) rather than
    # always using the current repo's reports/ tree.
    return resolve_output_path(
        _host_reports_mount(repo) / "run-reports",
        root=repo,
    )


def _host_reports_mount(repo: Path) -> Path:
    from scripts.engineering.common.repo_paths import resolve_output_path

    env = os.environ.get("BIOETL_DASHBOARD_REPORT_ROOT", "").strip()
    if env and not _looks_like_container_path(env):
        return resolve_output_path(Path(env).expanduser(), root=repo)
    return resolve_output_path(repo / "reports", root=repo)


def _json_get(url: str, *, timeout: float = 5.0) -> dict[str, Any] | None:
    safe_url = ensure_local_http_url(url)
    try:
        with urllib.request.urlopen(  # NOSONAR -- loopback URL validated above
            safe_url, timeout=timeout
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"WARN: ops HTTP unreachable at {url}: {exc}")
        return None
    return payload if isinstance(payload, dict) else None


def _docker_inspect_mounts(container: str) -> list[dict[str, Any]] | None:
    container = _validated_container_name(container)
    try:
        completed = subprocess.run(
            ensure_safe_cli_argv(
                ["docker", "inspect", container, "--format", "{{json .Mounts}}"]
            ),
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


def _docker_inspect_source_identity(
    container: str,
) -> RuntimeSourceIdentityResolutionResult | None:
    """Resolve the producer identity from container env, then its label."""
    container = _validated_container_name(container)
    try:
        completed = subprocess.run(
            ensure_safe_cli_argv(
                [
                    "docker",
                    "inspect",
                    container,
                    "--format",
                    (
                        '{"environment":{{json .Config.Env}},'
                        '"label":{{json (index .Config.Labels '
                        '"io.bioetl.dashboard-source-id")}}}'
                    ),
                ]
            ),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"WARN: docker source identity inspect failed: {exc}")
        return None
    if completed.returncode != 0:
        print(
            f"WARN: docker source identity inspect rc={completed.returncode}: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        print("WARN: docker source identity inspect returned non-JSON output")
        return None
    if not isinstance(payload, Mapping):
        return None
    container_environment: dict[str, str] = {}
    raw_environment = payload.get("environment")
    if isinstance(raw_environment, list):
        for item in raw_environment:
            if isinstance(item, str) and "=" in item:
                name, value = item.split("=", 1)
                container_environment[name] = value
    return resolve_runtime_source_identity(
        container_environment=container_environment,
        container_labels={"io.bioetl.dashboard-source-id": payload.get("label")},
    )


def _coerce_container_source_resolution(
    value: RuntimeSourceIdentityResolutionResult | str | None,
) -> RuntimeSourceIdentityResolutionResult | None:
    """Keep tests/callers using the historical digest-only seam compatible."""
    if value is None or isinstance(value, RuntimeSourceIdentityResolutionResult):
        return value
    return resolve_runtime_source_identity(
        container_environment={"BIOETL_RUNTIME_SOURCE_ID": value}
    )


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
    return runtime_preflight.normalise_host_path(
        left,
        root=_repo_root(),
    ) == runtime_preflight.normalise_host_path(right, root=_repo_root())


def _expected_runtime_environment(repo: Path) -> dict[str, str]:
    contract_path = repo / runtime_preflight.DEFAULT_CONTRACT
    if not contract_path.is_file():
        contract_path = _REPO_ROOT / runtime_preflight.DEFAULT_CONTRACT
    payload = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"invalid Docker runtime contract: {contract_path}")
    return runtime_preflight.dashboard_source_environment(repo, payload)


@dataclass(slots=True)
class _VerificationState:
    ok: bool = True
    findings: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.ok = False
        self.findings.append(message)

    def warn(self, message: str) -> None:
        self.findings.append(message)


def _verify_host_source(
    state: _VerificationState,
    *,
    host_mount: Path,
    host_root: Path,
    expected_source_id: str | None,
) -> None:
    marker_path = host_mount / REPORT_ROOT_MARKER_NAME
    if not marker_path.is_file():
        state.fail(
            f"FAIL: host marker missing at {marker_path} "
            f"(expected token {REPORT_ROOT_MARKER_VALUE!r})"
        )
    elif marker_path.read_text(encoding="utf-8").strip() != REPORT_ROOT_MARKER_VALUE:
        token = marker_path.read_text(encoding="utf-8").strip()
        state.fail(f"FAIL: host marker token mismatch at {marker_path}: {token!r}")
    else:
        print(f"OK: host marker {marker_path}")

    host_check = inspect_report_root_marker(report_root=host_root)
    print(f"host_marker_check={json.dumps(host_check, sort_keys=True)}")
    if host_check.get("status") != "healthy":
        state.fail(f"FAIL: {host_check.get('message')}")
    source_check = inspect_report_root_source_identity(
        report_root=host_root, expected_source_id=expected_source_id
    )
    print(f"host_source_check={json.dumps(source_check, sort_keys=True)}")
    if source_check.get("source_identity_status") != "healthy":
        state.fail(
            "FAIL: "
            + str(source_check.get("source_identity_message") or "source mismatch")
        )


def _host_pipeline_summary(
    state: _VerificationState,
    *,
    pipeline: str | None,
    host_root: Path,
) -> tuple[int | None, str | None]:
    if not pipeline:
        return None, None
    entries = list_pipeline_reports(pipeline_name=pipeline, limit=100, root=host_root)
    count = len(entries)
    latest_run_id = entries[0].run_id if entries else None
    print(f"host_pipeline_count pipeline={pipeline!r} count={count}")
    print(f"host_latest_run_id={latest_run_id!r}")
    if count == 0:
        state.warn(f"WARN: no host pipeline reports for {pipeline!r} under {host_root}")
    return count, latest_run_id


def _verify_container_mount(
    state: _VerificationState,
    *,
    container: str,
    mounts: list[dict[str, Any]] | None,
    host_mount: Path,
) -> None:
    if mounts is None:
        state.warn(
            f"WARN: could not inspect container {container!r}; "
            "skip bind-source comparison"
        )
        return
    source = _mount_source_for_target(mounts, DEFAULT_MOUNT_TARGET)
    print(f"container_mount target={DEFAULT_MOUNT_TARGET} source={source!r}")
    if source is None:
        state.fail(
            f"FAIL: container {container!r} has no bind at {DEFAULT_MOUNT_TARGET}"
        )
        return
    if not _paths_equivalent(source, host_mount):
        state.fail(
            f"FAIL: bind mismatch — container source={source!r} "
            f"expected host_reports_mount={host_mount}"
        )
        state.warn(
            "Remediation: from the canonical checkout run "
            "`python scripts/ops/runtime/docker/runtime_manager.py start "
            "--stack main` (or recreate bioetl with "
            "BIOETL_DASHBOARD_REPORT_ROOT pointing at this reports/)."
        )
        return
    print("OK: container bind source matches host reports mount")


def _verify_container_identity(
    state: _VerificationState,
    *,
    container: str,
    resolution: RuntimeSourceIdentityResolutionResult | None,
    expected_source_id: str | None,
    require_ops: bool,
) -> None:
    actual = resolution.value if resolution is not None else None
    print(
        "container_source_identity="
        + json.dumps(resolution.as_dict() if resolution else None, sort_keys=True)
    )
    comparison = compare_runtime_source_identity(
        expected=expected_source_id, actual=actual
    )
    if resolution is None or not resolution.is_resolved:
        message = f"could not inspect managed source identity for {container!r}"
        if require_ops:
            state.fail(f"FAIL: {message}")
        else:
            state.warn(f"WARN: {message}")
        return
    if comparison.state != IDENTITY_STATE_ALIGNED or not resolution.is_consistent:
        state.fail(
            "FAIL: container source identity mismatch — "
            f"state={comparison.state!r} actual={actual!r} "
            f"expected={expected_source_id!r} conflicts={resolution.conflicts!r}"
        )


def _verify_ready_endpoint(
    state: _VerificationState,
    *,
    ops_url: str,
    expected_source_id: str | None,
    require_ops: bool,
    bind_aligned: bool,
) -> None:
    ready = _json_get(f"{ops_url.rstrip('/')}/health/ready", timeout=20.0)
    if ready is None:
        live = _json_get(f"{ops_url.rstrip('/')}/health/live", timeout=5.0)
        message = f"ops HTTP not reachable at {ops_url}"
        if live is not None and bind_aligned:
            state.warn(
                "WARN: /health/ready timed out while /health/live is up and "
                "host/container bind identity is aligned; not a REPORT_BIND fail"
            )
            return
        if require_ops:
            state.fail(f"FAIL: {message}")
        else:
            state.warn(f"WARN: {message}")
        return
    report_check = ready.get("checks", {}).get("report_root")
    print(f"ops_ready_status={ready.get('status')!r}")
    print(f"ops_report_root_check={json.dumps(report_check, sort_keys=True)}")
    if isinstance(report_check, Mapping) and report_check.get("status") != "healthy":
        state.fail(
            "FAIL: /health/ready report_root check is not healthy "
            f"({report_check.get('message') or report_check.get('marker')})"
        )
    if ready.get("status") == "unhealthy":
        state.fail("FAIL: /health/ready status=unhealthy")
    if (
        not isinstance(report_check, Mapping)
        or report_check.get("source_identity_status") != "healthy"
    ):
        state.fail("FAIL: /health/ready source identity is not healthy")
    elif report_check.get("source_identity_state") not in {
        None,
        IDENTITY_STATE_ALIGNED,
    }:
        state.fail("FAIL: /health/ready source identity is not aligned")
    elif report_check.get("source_identity_actual") != expected_source_id:
        state.fail("FAIL: /health/ready source identity differs from host")


def _latest_ops_run_id(items: object) -> str | None:
    if not isinstance(items, list) or not items or not isinstance(items[0], Mapping):
        return None
    run_id = items[0].get("run_id")
    return str(run_id) if run_id else None


def _verify_ops_list_source_identity(
    state: _VerificationState,
    listed: Mapping[str, Any],
    expected_source_id: str | None,
) -> None:
    if listed.get("source_identity_status") != "healthy":
        state.fail(
            "FAIL: ops list source_identity_status="
            f"{listed.get('source_identity_status')!r}"
        )
    elif listed.get("source_identity_state") not in {None, IDENTITY_STATE_ALIGNED}:
        state.fail("FAIL: ops list source identity is not aligned")
    elif listed.get("source_identity_actual") != expected_source_id:
        state.fail("FAIL: ops list source identity differs from host")


def _verify_pipeline_endpoint(
    state: _VerificationState,
    *,
    ops_url: str,
    pipeline: str | None,
    expected_source_id: str | None,
    host_count: int | None,
    host_latest_run_id: str | None,
    require_ops: bool,
    bind_aligned: bool,
) -> None:
    if not pipeline:
        return
    list_url = (
        f"{ops_url.rstrip('/')}/ops/observability/pipeline-run-reports"
        f"?pipeline={pipeline}&limit=20"
    )
    listed = _json_get(list_url, timeout=20.0)
    if listed is None:
        if bind_aligned:
            state.warn(
                "WARN: list endpoint timed out while host/container bind "
                f"identity is aligned: {list_url}"
            )
            return
        if require_ops:
            state.fail(f"FAIL: list endpoint unreachable: {list_url}")
        return
    ops_count = int(listed.get("count") or 0)
    print(
        f"ops_pipeline_count pipeline={pipeline!r} count={ops_count} "
        f"report_root={listed.get('report_root')!r} "
        f"marker_status={listed.get('marker_status')!r}"
    )
    if listed.get("marker_status") and listed.get("marker_status") != "healthy":
        state.fail(f"FAIL: ops list marker_status={listed.get('marker_status')!r}")
    _verify_ops_list_source_identity(state, listed, expected_source_id)
    if host_count is not None and host_count > 0 and ops_count == 0:
        state.fail(
            f"FAIL: host has {host_count} report(s) for {pipeline!r} "
            "but ops HTTP returns count=0 — classic bind mismatch"
        )
    elif host_count is not None and ops_count > 0:
        print("OK: ops HTTP sees pipeline reports")
    ops_latest_run_id = _latest_ops_run_id(listed.get("items"))
    print(f"ops_latest_run_id={ops_latest_run_id!r}")
    if host_latest_run_id != ops_latest_run_id:
        state.fail(
            "FAIL: newest run mismatch — "
            f"host={host_latest_run_id!r} ops={ops_latest_run_id!r}"
        )


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
    expected_environment = _expected_runtime_environment(repo)
    expected_source_id = expected_environment.get("BIOETL_RUNTIME_SOURCE_ID")
    state = _VerificationState()

    print(f"repo_root={repo}")
    print(f"host_reports_mount={host_mount}")
    print(f"host_report_root={host_root}")

    _verify_host_source(
        state,
        host_mount=host_mount,
        host_root=host_root,
        expected_source_id=expected_source_id,
    )
    host_count, host_latest_run_id = _host_pipeline_summary(
        state, pipeline=pipeline, host_root=host_root
    )

    mounts = _docker_inspect_mounts(container)
    container_resolution = _coerce_container_source_resolution(
        _docker_inspect_source_identity(container)
    )
    _verify_container_mount(
        state, container=container, mounts=mounts, host_mount=host_mount
    )
    _verify_container_identity(
        state,
        container=container,
        resolution=container_resolution,
        expected_source_id=expected_source_id,
        require_ops=require_ops,
    )

    bind_aligned = state.ok
    _verify_ready_endpoint(
        state,
        ops_url=ops_url,
        expected_source_id=expected_source_id,
        require_ops=require_ops,
        bind_aligned=bind_aligned,
    )

    _verify_pipeline_endpoint(
        state,
        ops_url=ops_url,
        pipeline=pipeline,
        expected_source_id=expected_source_id,
        host_count=host_count,
        host_latest_run_id=host_latest_run_id,
        require_ops=require_ops,
        bind_aligned=bind_aligned,
    )

    for line in state.findings:
        print(line)

    if state.ok:
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
