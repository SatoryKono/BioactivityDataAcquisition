"""Bounded command adapters and read-only campaign observations."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .model import StackSpec, atomic_json, load_json, redact

COMMAND_OUTPUT_LIMIT = 4000
DOCKER_VM_MIN_FREE_BYTES = 4 * 1024**3
_WINDOWS_POWERSHELL_CANDIDATES = (
    "powershell.exe",
    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
    "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
)


def run_command(
    command: Sequence[str],
    timeout: float,
    *,
    cwd: Path,
) -> dict[str, Any]:
    """Run one subprocess within a hard deadline and return bounded evidence."""
    started = time.monotonic()
    bounded_timeout = max(0.1, float(timeout))
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=bounded_timeout,
        )
        returncode = completed.returncode
        stdout = completed.stdout[:COMMAND_OUTPUT_LIMIT]
        stderr = completed.stderr[:COMMAND_OUTPUT_LIMIT]
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = str(exc.stdout or "")[:COMMAND_OUTPUT_LIMIT]
        stderr = f"command timed out after {bounded_timeout:.3f}s"
        timed_out = True
    except FileNotFoundError as exc:
        returncode = 127
        stdout = ""
        stderr = str(exc)[:COMMAND_OUTPUT_LIMIT]
        timed_out = False
    return redact(
        {
            "command": list(command),
            "returncode": returncode,
            "timed_out": timed_out,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": stdout,
            "stderr": stderr,
        }
    )


def remaining_seconds(deadline: float, *, reserve: float = 0.0) -> float:
    """Return remaining wall-clock budget, failing before a deadline is exceeded."""
    remaining = deadline - time.monotonic() - reserve
    if remaining <= 0:
        raise TimeoutError("campaign operation exceeded its global deadline")
    return remaining


def resolve_windows_powershell() -> str | None:
    """Locate Windows PowerShell for Docker Desktop host operations.

    The WSL `docker desktop` plugin looks for `/opt/docker-desktop/bin/com.docker.backend`
    and fails on standard Docker Desktop for Windows installs. Host control must go
    through the Windows docker.exe Desktop CLI via powershell.exe.
    """
    for candidate in _WINDOWS_POWERSHELL_CANDIDATES:
        if os.path.sep in candidate or (len(candidate) > 1 and candidate[1] == ":"):
            if Path(candidate).is_file():
                return candidate
            continue
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def desktop_engine_restart_command(
    runtime_origin: Path,
    timeout: float,
) -> dict[str, Any]:
    """Interrupt Docker Desktop via the Windows host CLI (not the WSL plugin path).

    Returns bounded subprocess evidence. Callers still run stack recover/probe after
    this injection; this helper only owns the engine restart primitive.
    """
    powershell = resolve_windows_powershell()
    if powershell is None:
        return {
            "command": ["powershell.exe", "-NoProfile", "-Command", "docker desktop restart"],
            "returncode": 127,
            "timed_out": False,
            "duration_seconds": 0.0,
            "stdout": "",
            "stderr": (
                "Windows PowerShell not found; cannot run docker desktop restart "
                "from the Windows host CLI"
            ),
            "primary_cause": "windows_powershell_missing",
        }
    # Prefer docker.exe on the Windows PATH so the Desktop CLI plugin resolves
    # against the Desktop backend, not the incomplete WSL plugin install.
    script = (
        "$ErrorActionPreference = 'Continue'; "
        "docker desktop restart; "
        "if ($null -ne $LASTEXITCODE) { exit $LASTEXITCODE }; "
        "if (-not $?) { exit 1 }; "
        "exit 0"
    )
    return run_command(
        [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        timeout,
        cwd=runtime_origin,
    )


def desktop_recovery_diagnostic_bundle(
    runtime_origin: Path,
    report: Path,
    timeout: float = 180.0,
) -> dict[str, Any]:
    """Run bounded evidence-first Desktop recovery without destructive fallback."""
    if report.exists():
        raise FileExistsError(
            f"refusing to replace Desktop recovery evidence: {report}"
        )
    report.parent.mkdir(parents=True, exist_ok=True)
    script = runtime_origin / "scripts/ops/runtime/docker/restart-docker.ps1"
    converted_script = run_command(
        ["wslpath", "-w", str(script)],
        10.0,
        cwd=runtime_origin,
    )
    converted_report = run_command(
        ["wslpath", "-w", str(report)],
        10.0,
        cwd=runtime_origin,
    )
    if converted_script["returncode"] != 0 or converted_report["returncode"] != 0:
        return {
            "returncode": 1,
            "primary_cause": "diagnostic_path_conversion_failed",
            "script_path": converted_script,
            "report_path": converted_report,
            "diagnostic_bundle_present": False,
        }
    internal_timeout = max(10, min(175, int(timeout) - 5))
    powershell = resolve_windows_powershell() or "powershell.exe"
    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(converted_script["stdout"]).strip(),
            "-TimeoutSeconds",
            str(internal_timeout),
            "-CommandTimeoutSeconds",
            "15",
            "-ReportPath",
            str(converted_report["stdout"]).strip(),
        ],
        timeout,
        cwd=runtime_origin,
    )
    payload = load_json(report)
    result["diagnostic_bundle_present"] = bool(payload)
    result["diagnostic_bundle"] = str(report)
    result["diagnostic_schema_version"] = payload.get("schema_version")
    if not payload:
        result["returncode"] = 1
        result["primary_cause"] = "diagnostic_bundle_missing"
    return result


def manager_command(
    runtime_origin: Path,
    action: str,
    spec: StackSpec,
    timeout: float,
    report_dir: Path,
    *,
    contract: Path,
) -> dict[str, Any]:
    """Invoke the canonical lifecycle manager without exceeding the caller budget."""
    internal = max(0.1, timeout - 1.0)
    result = run_command(
        [
            sys.executable,
            str(runtime_origin / "scripts/ops/runtime/docker/runtime_manager.py"),
            action,
            "--stack",
            spec.stack,
            "--contract",
            str(contract),
            "--report-dir",
            str(report_dir),
            "--timeout",
            f"{internal:.3f}",
        ],
        timeout,
        cwd=runtime_origin,
    )
    incident = load_json(report_dir / f"docker-incident-{spec.stack}.json")
    if incident:
        result["primary_cause"] = incident.get("primary_cause")
    preflight = load_json(report_dir / f"docker-runtime-{spec.stack}-preflight.json")
    if preflight:
        result["preflight_findings"] = [
            str(row.get("code"))
            for row in preflight.get("findings", [])
            if isinstance(row, Mapping) and row.get("code")
        ]
    return result


def probe_command(
    runtime_origin: Path,
    spec: StackSpec,
    output: Path,
    timeout: float,
    *,
    contract: Path,
    baseline: Path | None = None,
    incident: Path | None = None,
    expected_image_override: tuple[str, str] | None = None,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(runtime_origin / "scripts/ops/runtime/docker/docker_runtime_probe.py"),
        "--stack",
        spec.stack,
        "--contract",
        str(contract),
        "--output",
        str(output),
        "--timeout",
        f"{max(1.0, timeout - 1.0):.3f}",
    ]
    if baseline is not None:
        command.extend(("--baseline", str(baseline)))
    if incident is not None:
        command.extend(("--incident", str(incident)))
    if expected_image_override is not None:
        service, image = expected_image_override
        command.extend(("--expected-image-override", f"{service}={image}"))
    result = run_command(command, timeout, cwd=runtime_origin)
    report = load_json(output)
    if report:
        result["primary_cause"] = report.get("primary_cause")
        result["summary_ok"] = bool(report.get("summary", {}).get("ok"))
    return result


def compose_command(
    runtime_origin: Path,
    spec: StackSpec,
    args: Sequence[str],
    timeout: float,
) -> dict[str, Any]:
    return run_command(
        [
            "docker",
            "compose",
            "-p",
            spec.project,
            "-f",
            str(runtime_origin / spec.compose_file),
            *args,
        ],
        timeout,
        cwd=runtime_origin,
    )


def live_compose_rows(
    runtime_origin: Path, timeout: float = 20.0
) -> list[dict[str, Any]]:
    result = run_command(
        ["docker", "compose", "ls", "--all", "--format", "json"],
        timeout,
        cwd=runtime_origin,
    )
    if result["returncode"] != 0:
        raise RuntimeError("unable to read Compose project origins")
    text = str(result["stdout"]).strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(payload, dict):
        return [payload]
    return [row for row in payload if isinstance(row, dict)]


def volume_ids(
    runtime_origin: Path,
    spec: StackSpec,
    timeout: float = 20.0,
) -> set[str]:
    project = run_command(
        [
            "docker",
            "volume",
            "ls",
            "--filter",
            f"label=com.docker.compose.project={spec.project}",
            "--format",
            "{{.Name}}",
        ],
        timeout,
        cwd=runtime_origin,
    )
    all_volumes = run_command(
        ["docker", "volume", "ls", "--format", "{{.Name}}"],
        timeout,
        cwd=runtime_origin,
    )
    if project["returncode"] != 0 or all_volumes["returncode"] != 0:
        raise RuntimeError(f"unable to capture volume identity for {spec.stack}")
    names = {line for line in str(project["stdout"]).splitlines() if line}
    existing = {line for line in str(all_volumes["stdout"]).splitlines() if line}
    names.update(set(spec.protected_volumes) & existing)
    return names


def required_volume_precondition(
    runtime_origin: Path,
    bundle: Sequence[StackSpec],
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Require target volumes before any campaign lifecycle mutation."""
    result = run_command(
        ["docker", "volume", "ls", "--format", "{{.Name}}"],
        timeout,
        cwd=runtime_origin,
    )
    if result["returncode"] != 0:
        raise RuntimeError("unable to verify required campaign volumes")
    existing = {line for line in str(result["stdout"]).splitlines() if line}
    stacks: dict[str, Any] = {}
    missing: list[str] = []
    for spec in bundle:
        absent = sorted(set(spec.required_volumes) - existing)
        missing.extend(absent)
        stacks[spec.stack] = {
            "required_target_volumes": {
                name: ("present" if name in existing else "missing")
                for name in spec.required_volumes
            },
            "legacy_volumes": {
                name: ("present" if name in existing else "not_applicable")
                for name in spec.legacy_volumes
            },
        }
    return {
        "passed": not missing,
        "missing_required_target_volumes": sorted(set(missing)),
        "stacks": stacks,
        "observation": result,
    }


def bundle_volume_ids(
    runtime_origin: Path,
    bundle: Sequence[StackSpec],
    timeout: float = 20.0,
) -> dict[str, list[str]]:
    return {
        spec.project: sorted(volume_ids(runtime_origin, spec, timeout))
        for spec in bundle
    }


def restart_baseline(
    report: Mapping[str, Any],
) -> tuple[dict[str, int], dict[str, str]]:
    """Require a clean sample, then pin restart counters and container identities."""
    if not bool(report.get("summary", {}).get("ok")):
        raise ValueError("restart baseline requires a clean runtime probe")
    services = report.get("services", [])
    restart_counts: dict[str, int] = {}
    container_ids: dict[str, str] = {}
    for row in services:
        if not isinstance(row, Mapping):
            continue
        service = str(row.get("service") or "")
        container_id = str(row.get("container_id") or "")
        if not service or not container_id:
            continue
        restart_counts[service] = int(row.get("restart_count") or 0)
        container_ids[service] = container_id
    if not restart_counts or any(value != 0 for value in restart_counts.values()):
        raise ValueError("campaign baseline requires zero restart counters")
    return restart_counts, container_ids


def write_baseline(path: Path, report_path: Path) -> dict[str, str]:
    report = load_json(report_path)
    restart_counts, container_ids = restart_baseline(report)
    atomic_json(
        path,
        {"restart_counts": restart_counts, "container_ids": container_ids},
        replace=False,
    )
    return container_ids


def record_probe(
    state: dict[str, Any], path: Path, *, release_sample: bool = True
) -> None:
    report = load_json(path)
    if not report:
        raise ValueError(f"runtime probe did not write evidence: {path}")
    if not release_sample:
        return
    slo = report.get("slo", {})
    state["probe_samples"] = int(state.get("probe_samples", 0)) + 1
    state["probe_failures"] = int(state.get("probe_failures", 0)) + int(
        not bool(report.get("summary", {}).get("ok"))
    )
    ratios = [
        float(value)
        for row in report.get("resources", [])
        if isinstance(row, Mapping)
        for key, value in row.items()
        if str(key).endswith("_limit_ratio")
    ]
    state["max_resource_ratio"] = max(
        [float(state.get("max_resource_ratio", 0.0)), *ratios]
    )
    state["restart_count_delta"] = max(
        int(state.get("restart_count_delta", 0)),
        int(slo.get("restart_count_delta", 0)),
    )
    state["oom_kills"] = max(
        int(state.get("oom_kills", 0)), int(slo.get("oom_kills", 0))
    )
    state["unhealthy_samples"] = int(state.get("unhealthy_samples", 0)) + int(
        not bool(slo.get("required_services_ready", False))
    )
    state["disk_reserve_breaches"] = int(state.get("disk_reserve_breaches", 0)) + int(
        not bool(slo.get("disk_reserve_ok", False))
    )
    state["image_or_project_drift"] = int(state.get("image_or_project_drift", 0)) + int(
        bool(slo.get("image_identity_drift")) or bool(slo.get("project_origin_drift"))
    )


def _parse_df_pk_available_kib(stdout: str) -> int | None:
    """Parse BusyBox/GNU `df -Pk` Available column (1 KiB blocks)."""
    for line in str(stdout).splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        # Header row: Filesystem 1024-blocks Used Available ...
        if parts[0].lower().startswith("filesystem"):
            continue
        if not parts[3].isdigit():
            continue
        return int(parts[3])
    return None


def observe_docker_vm_reserve(
    state: dict[str, Any], runtime_origin: Path, timeout: float = 15.0
) -> dict[str, Any]:
    """Measure free Docker-VM disk with BusyBox-compatible df.

    Docker Desktop's ``docker-desktop`` distro ships BusyBox (no
    ``--output=avail``) and stores the engine disk at
    ``/mnt/docker-desktop-disk`` rather than a mount at ``/var/lib/docker``.
    """
    # Prefer the Desktop virtual disk; fall back for older layouts / Linux hosts.
    probe_paths = (
        "/mnt/docker-desktop-disk",
        "/var/lib/docker",
        "/",
    )
    attempts: list[dict[str, Any]] = []
    free_bytes = 0
    result: dict[str, Any] = {
        "returncode": 1,
        "stdout": "",
        "stderr": "docker vm free space unavailable",
        "timed_out": False,
        "command": [],
        "duration_seconds": 0.0,
    }
    for path in probe_paths:
        # BusyBox-safe: POSIX output, 1 KiB blocks. Avoid GNU-only --output=.
        candidate = run_command(
            [
                "wsl.exe",
                "-d",
                "docker-desktop",
                "--exec",
                "df",
                "-Pk",
                path,
            ],
            timeout,
            cwd=runtime_origin,
        )
        attempts.append({"path": path, **candidate})
        kib = (
            _parse_df_pk_available_kib(str(candidate.get("stdout", "")))
            if candidate.get("returncode") == 0
            else None
        )
        if kib is None:
            continue
        free_bytes = kib * 1024
        result = {**candidate, "path": path}
        break
    else:
        # Preserve the last attempt's command evidence for the incident bundle.
        if attempts:
            result = dict(attempts[-1])

    previous = state.get("docker_vm_min_free_bytes")
    state["docker_vm_min_free_bytes"] = (
        free_bytes if previous is None else min(int(previous), free_bytes)
    )
    if free_bytes < DOCKER_VM_MIN_FREE_BYTES:
        state["docker_vm_reserve_breaches"] = (
            int(state.get("docker_vm_reserve_breaches", 0)) + 1
        )
    return {**result, "free_bytes": free_bytes, "attempts": attempts}
