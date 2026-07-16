#!/usr/bin/env python3
"""Run resumable, evidence-driven optional Docker stability campaigns."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml

ROOT = Path(__file__).resolve().parents[3]
MANAGER = ROOT / "scripts/ops/runtime/docker/runtime_manager.py"
PROBE = ROOT / "scripts/ops/runtime/docker/docker_runtime_probe.py"
CONFIRM_TOKEN = "I_UNDERSTAND_THIS_INTERRUPTS_DOCKER_DESKTOP"
CONTRACT_RELATIVE_PATH = Path("configs/quality/docker_runtime_contracts.yaml")
RELEASE_STACKS = ("main", "monitoring")
FAULT_CASE_NAMES = (
    "selected_service_termination",
    "failed_health_readiness",
    "occupied_required_port",
    "expected_image_identity_drift",
    "interrupted_startup",
    "bounded_memory_pid_pressure",
    "desktop_engine_restart",
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(password|passwd|secret|token|credential|authorization|auth)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_BARE_GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")
_WINDOWS_PATH = re.compile(r"(?i)^(?:[a-z]:[\\/]|\\\\)")


@dataclass(frozen=True)
class StackSpec:
    """One immutable member of the release bundle."""

    stack: str
    project: str
    compose_file: str
    required_services: tuple[str, ...]


@dataclass(frozen=True)
class FaultOperation:
    """A bounded operation in a reversible fault case."""

    kind: str
    stack: str | None = None
    service: str | None = None
    port: int | None = None
    max_seconds: float = 30.0
    expected: str = "success"


@dataclass(frozen=True)
class FaultCase:
    """A scheduled fault with an explicit, case-local restoration path."""

    name: str
    classification: str
    apply: tuple[FaultOperation, ...]
    observe: tuple[FaultOperation, ...]
    restore: tuple[FaultOperation, ...]
    max_seconds: float = 180.0


class FaultExecutor(Protocol):
    def __call__(
        self, operation: FaultOperation, remaining_seconds: float
    ) -> dict[str, Any]: ...


def _redact(value: Any) -> Any:
    """Recursively redact likely credentials from persisted subprocess evidence."""
    if isinstance(value, dict):
        return {
            key: (
                "<redacted>"
                if any(
                    marker in str(key).lower()
                    for marker in (
                        "password",
                        "secret",
                        "token",
                        "credential",
                        "authorization",
                        "auth",
                    )
                )
                else _redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if isinstance(value, str):
        assigned = _SECRET_ASSIGNMENT.sub(r"\1\2<redacted>", value)
        return _BARE_GITHUB_TOKEN.sub("<redacted-github-token>", assigned)
    return value


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Campaign state must be a JSON object")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _remember_evidence(
    state: dict[str, Any], path: Path, evidence_dir: Path
) -> None:
    relative = path.resolve().relative_to(evidence_dir.resolve()).as_posix()
    state.setdefault("evidence_sha256", {})[relative] = _file_sha256(path)


def _remember_evidence_tree(
    state: dict[str, Any], directory: Path, evidence_dir: Path
) -> None:
    if not directory.is_dir():
        return
    for path in sorted(directory.rglob("*.json")):
        _remember_evidence(state, path, evidence_dir)


def _validate_evidence_index(state: dict[str, Any], evidence_dir: Path) -> None:
    index = state.get("evidence_sha256", {})
    if not isinstance(index, dict):
        raise ValueError("Campaign evidence index must be a mapping")
    for relative, expected in index.items():
        path = evidence_dir / str(relative)
        if not path.is_file() or _file_sha256(path) != str(expected):
            raise ValueError(f"Campaign evidence is missing or changed: {relative}")


def _run(
    command: Sequence[str], timeout: float, *, cwd: Path = ROOT
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return _redact({
            "command": list(command),
            "returncode": 124 if isinstance(exc, subprocess.TimeoutExpired) else 127,
            "timed_out": isinstance(exc, subprocess.TimeoutExpired),
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": "",
            "stderr": str(exc)[:2000],
        })
    return _redact({
        "command": list(command),
        "returncode": completed.returncode,
        "timed_out": False,
        "duration_seconds": round(time.monotonic() - started, 3),
        "stdout": completed.stdout[:2000],
        "stderr": completed.stderr[:2000],
    })


def _origin_kind(value: str | Path) -> str:
    raw = str(value).strip()
    normalized = raw.replace("\\", "/")
    lowered = normalized.lower()
    if _WINDOWS_PATH.match(raw):
        return "windows"
    if lowered == "/tmp" or lowered.startswith("/tmp/"):
        return "tmp"
    if lowered == "/mnt" or lowered.startswith("/mnt/"):
        return "mnt"
    if not normalized.startswith("/"):
        return "relative"
    return "linux"


def _canonical_runtime_origin(path: Path) -> Path:
    """Resolve and validate a canonical Linux-filesystem runtime origin."""
    if _origin_kind(path) != "linux":
        raise ValueError("Runtime origin must be an absolute Linux path outside /mnt and /tmp")
    resolved = path.resolve(strict=True)
    if _origin_kind(resolved) != "linux":
        raise ValueError("Resolved runtime origin must remain outside /mnt and /tmp")
    return resolved


def _validate_runtime_layout(
    runtime_origin: Path,
    contract_path: Path,
    bundle: Sequence[StackSpec],
) -> None:
    required = [
        contract_path,
        Path("scripts/ops/runtime/docker/runtime_manager.py"),
        Path("scripts/ops/runtime/docker/docker_runtime_probe.py"),
        *(Path(spec.compose_file) for spec in bundle),
    ]
    missing = [
        str(path)
        for path in required
        if not (path if path.is_absolute() else runtime_origin / path).is_file()
    ]
    if missing:
        raise ValueError(f"Pinned runtime mirror is incomplete: {', '.join(missing)}")


def _load_contract(runtime_origin: Path, contract: Path) -> tuple[Path, dict[str, Any], str]:
    candidate = contract if contract.is_absolute() else runtime_origin / contract
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(runtime_origin)
    except ValueError as exc:
        raise ValueError("Contract must be inside the pinned runtime origin") from exc
    if _origin_kind(resolved) != "linux":
        raise ValueError("Contract origin must be an absolute Linux path outside /mnt and /tmp")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Docker runtime contract must be a mapping")
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return resolved, payload, digest


def _release_bundle(contract: dict[str, Any]) -> tuple[StackSpec, ...]:
    stacks = contract.get("stacks", {})
    if not isinstance(stacks, dict):
        raise ValueError("Docker runtime contract is missing stacks")
    bundle: list[StackSpec] = []
    for name in RELEASE_STACKS:
        raw = stacks.get(name)
        if not isinstance(raw, dict):
            raise ValueError(f"Docker runtime contract is missing release stack {name}")
        services = raw.get("required_services")
        if not isinstance(services, list) or not services:
            raise ValueError(f"Release stack {name} has no required services")
        bundle.append(
            StackSpec(
                stack=name,
                project=str(raw["project_name"]),
                compose_file=str(raw["compose_file"]),
                required_services=tuple(str(service) for service in services),
            )
        )
    projects = [spec.project for spec in bundle]
    if len(projects) != len(set(projects)):
        raise ValueError("Release bundle projects must be unique")
    return tuple(bundle)


def _bundle_identity(bundle: Sequence[StackSpec]) -> list[dict[str, Any]]:
    return [asdict(spec) for spec in bundle]


def _compose_origin_findings(
    rows: Sequence[dict[str, Any]],
    bundle: Sequence[StackSpec],
    runtime_origin: Path,
) -> list[str]:
    """Return fail-closed findings for mixed or noncanonical live Compose origins."""
    expected = {spec.project for spec in bundle}
    findings: list[str] = []
    seen: set[str] = set()
    for row in rows:
        project = str(row.get("Name", ""))
        if project not in expected:
            continue
        seen.add(project)
        raw_origins = str(row.get("ConfigFiles", ""))
        origins = [item.strip() for item in raw_origins.split(",") if item.strip()]
        if not origins:
            findings.append(f"{project}: missing runtime origin")
            continue
        kinds = {_origin_kind(origin) for origin in origins}
        if any(kind != "linux" for kind in kinds):
            findings.append(f"{row.get('Name')}: noncanonical origin")
            continue
        outside = []
        for origin in origins:
            try:
                Path(origin).resolve(strict=False).relative_to(runtime_origin)
            except ValueError:
                outside.append(origin)
        if outside or len(kinds) > 1:
            findings.append(f"{row.get('Name')}: mixed runtime origin")
    for project in sorted(expected - seen):
        findings.append(f"{project}: project not running")
    return findings


def _live_compose_rows(runtime_origin: Path) -> list[dict[str, Any]]:
    result = _run(
        ["docker", "compose", "ls", "--format", "json"], 30, cwd=runtime_origin
    )
    if result["returncode"] != 0:
        raise RuntimeError("Unable to verify live Compose project origins")
    stdout = str(result.get("stdout", "")).strip()
    if not stdout:
        return []
    payload = json.loads(stdout)
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise ValueError("docker compose ls returned an unexpected payload")
    return payload


def _volume_ids(project: str, runtime_origin: Path = ROOT) -> set[str]:
    result = _run(
        [
            "docker",
            "volume",
            "ls",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.Name}}",
        ],
        15,
        cwd=runtime_origin,
    )
    if result["returncode"] != 0:
        raise RuntimeError("Unable to capture named-volume identity")
    return {line for line in str(result["stdout"]).splitlines() if line}


def _bundle_volume_ids(
    bundle: Sequence[StackSpec], runtime_origin: Path = ROOT
) -> dict[str, list[str]]:
    return {
        spec.project: sorted(_volume_ids(spec.project, runtime_origin))
        for spec in bundle
    }


def new_state(
    *,
    cycles: int,
    soak_hours: float,
    bundle: Sequence[StackSpec] | None = None,
    runtime_origin: Path | None = None,
    contract_sha256: str = "",
    stack: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    # ``stack``/``project`` remain accepted for pure gate-unit compatibility;
    # executable campaigns always supply the explicit two-stack bundle.
    if bundle is None:
        if stack is None or project is None:
            raise ValueError("An explicit release bundle is required")
        bundle = (
            StackSpec(
                stack=stack,
                project=project,
                compose_file="",
                required_services=("unknown",),
            ),
        )
    return {
        "schema_version": "bioetl-docker-stability-campaign-state-v2",
        "release_bundle": _bundle_identity(bundle),
        "runtime_origin": str(runtime_origin) if runtime_origin is not None else "",
        "contract_sha256": contract_sha256,
        "required_cycles": cycles,
        "required_soak_hours": soak_hours,
        "required_engine_recovery_trials": 100,
        "soak_sample_seconds": None,
        "required_fault_cases": list(FAULT_CASE_NAMES),
        "fault_cases": {},
        "evidence_sha256": {},
        "incident_ids": [],
        "initial_volume_ids": {},
        "final_volume_ids": {},
        "completed_cycles": 0,
        "cycle_failures": 0,
        "soak_started_at": None,
        "soak_last_sample_at": None,
        "soak_observed_seconds": 0.0,
        "soak_interruptions": 0,
        "soak_window_interrupted": False,
        "engine_recovery_trials": 0,
        "engine_recovery_successes": 0,
        "volume_loss": False,
        "probe_samples": 0,
        "probe_failures": 0,
        "max_resource_ratio": 0.0,
        "restart_count_delta": 0,
        "oom_kills": 0,
        "unhealthy_samples": 0,
        "disk_reserve_breaches": 0,
        "image_or_project_drift": 0,
        "last_failure": None,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def release_gates(state: dict[str, Any], *, signature_exists: bool) -> dict[str, bool]:
    required_seconds = float(state["required_soak_hours"]) * 3600
    trials = int(state.get("engine_recovery_trials", 0))
    successes = int(state.get("engine_recovery_successes", 0))
    required_faults = set(state.get("required_fault_cases", FAULT_CASE_NAMES))
    fault_results = state.get("fault_cases", {})
    fault_matrix_complete = required_faults == set(fault_results)
    fault_matrix_clean = fault_matrix_complete and all(
        isinstance(fault_results[name], dict)
        and bool(fault_results[name].get("restored"))
        and bool(fault_results[name].get("passed"))
        for name in required_faults
    )
    return {
        "cycles_complete": int(state["completed_cycles"])
        >= int(state["required_cycles"]),
        "cycles_clean": int(state["cycle_failures"]) == 0,
        "soak_complete": float(state["soak_observed_seconds"]) >= required_seconds,
        "soak_continuous": not bool(state.get("soak_window_interrupted", False)),
        "engine_recovery_99_of_100": trials >= 100 and successes / trials >= 0.99,
        "volumes_preserved": not bool(state["volume_loss"]),
        "all_probe_samples_clean": int(state.get("probe_failures", 0)) == 0
        and int(state.get("probe_samples", 0)) > 0,
        "resource_peak_below_80_percent": float(state.get("max_resource_ratio", 0.0))
        < 0.8,
        "restart_delta_zero": int(state.get("restart_count_delta", 0)) == 0,
        "oom_kills_zero": int(state.get("oom_kills", 0)) == 0,
        "unhealthy_zero": int(state.get("unhealthy_samples", 0)) == 0,
        "disk_reserve_preserved": int(state.get("disk_reserve_breaches", 0)) == 0,
        "identity_drift_zero": int(state.get("image_or_project_drift", 0)) == 0,
        "fault_matrix_complete": fault_matrix_complete,
        "fault_matrix_clean": fault_matrix_clean,
        "detached_signature_present": signature_exists,
        "no_unresolved_failure": state.get("last_failure") is None,
    }


def _runtime_script(runtime_origin: Path, relative: str) -> Path:
    script = (runtime_origin / relative).resolve(strict=True)
    try:
        script.relative_to(runtime_origin)
    except ValueError as exc:
        raise ValueError("Runtime helper escaped the pinned runtime origin") from exc
    return script


def _manager(
    action: str,
    stack: str,
    timeout: float,
    runtime_origin: Path = ROOT,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    manager = _runtime_script(
        runtime_origin, "scripts/ops/runtime/docker/runtime_manager.py"
    )
    command = [
        sys.executable,
        str(manager),
        action,
        "--stack",
        stack,
        "--timeout",
        str(max(1.0, timeout - 2.0)),
    ]
    if report_dir is not None:
        command.extend(["--report-dir", str(report_dir)])
    result = _run(
        command,
        max(1.0, timeout),
        cwd=runtime_origin,
    )
    if report_dir is not None:
        incident = _load(report_dir / f"docker-incident-{stack}.json")
        preflight = _load(report_dir / f"docker-runtime-{stack}-preflight.json")
        if incident.get("primary_cause"):
            result["primary_cause"] = incident["primary_cause"]
        finding_codes = [
            str(row.get("code"))
            for row in preflight.get("findings", [])
            if isinstance(row, dict) and row.get("code")
        ]
        if finding_codes:
            result["finding_codes"] = finding_codes
    return result


def _sample_probe(
    stack: str,
    output: Path,
    runtime_origin: Path = ROOT,
    *,
    baseline: Path | None = None,
    incident: Path | None = None,
) -> dict[str, Any]:
    probe = _runtime_script(
        runtime_origin, "scripts/ops/runtime/docker/docker_runtime_probe.py"
    )
    command = [sys.executable, str(probe), "--stack", stack, "--output", str(output)]
    if baseline is not None:
        command.extend(["--baseline", str(baseline)])
    if incident is not None:
        command.extend(["--incident", str(incident)])
    result = _run(
        command,
        75,
        cwd=runtime_origin,
    )
    report = _load(output)
    if report.get("primary_cause"):
        result["primary_cause"] = report["primary_cause"]
    return result


def _restart_baseline_from_probe(probe_path: Path, baseline_path: Path) -> None:
    report = _load(probe_path)
    if not bool(report.get("summary", {}).get("ok")):
        raise RuntimeError("Cannot establish restart baseline from an unclean probe")
    restart_counts = {
        str(row["service"]): int(row.get("restart_count", 0))
        for row in report.get("services", [])
        if isinstance(row, dict) and row.get("service")
    }
    if not restart_counts:
        raise RuntimeError("Restart baseline has no required services")
    if any(count != 0 for count in restart_counts.values()):
        raise RuntimeError("A newly started cycle already has a restart increment")
    _atomic_json_once(baseline_path, {"restart_counts": restart_counts})


def _capture_restart_baseline(
    stack: str,
    probe_path: Path,
    baseline_path: Path,
    runtime_origin: Path,
) -> dict[str, Any]:
    result = _sample_probe(stack, probe_path, runtime_origin)
    if result["returncode"] == 0:
        _restart_baseline_from_probe(probe_path, baseline_path)
    return result


def _record_probe(state: dict[str, Any], path: Path) -> None:
    report = _load(path)
    slo = report.get("slo", {})
    state["probe_samples"] = int(state.get("probe_samples", 0)) + 1
    state["probe_failures"] = int(state.get("probe_failures", 0)) + int(
        not bool(report.get("summary", {}).get("ok"))
    )
    ratios = [
        float(value)
        for row in report.get("resources", [])
        for key, value in row.items()
        if key.endswith("_limit_ratio")
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


def run_cycle(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    bundle: Sequence[StackSpec] | None = None,
    runtime_origin: Path = ROOT,
) -> bool:
    if bundle is None:
        bundle = tuple(
            StackSpec(
                stack=str(row["stack"]),
                project=str(row["project"]),
                compose_file=str(row.get("compose_file", "")),
                required_services=tuple(row.get("required_services", ("unknown",))),
            )
            for row in state["release_bundle"]
        )
    number = int(state["completed_cycles"]) + 1
    before = _bundle_volume_ids(bundle, runtime_origin)
    steps: list[dict[str, Any]] = []
    probe_paths: list[Path] = []
    baseline_paths: dict[str, Path] = {}
    for spec in bundle:
        steps.append(
            _manager(
                "start",
                spec.stack,
                180,
                runtime_origin,
                evidence_dir / f"manager-cycle-{number:03d}-{spec.stack}-start-1",
            )
        )
        baseline_probe = evidence_dir / (
            f"probe-cycle-{number:03d}-{spec.stack}-baseline.json"
        )
        baseline_path = evidence_dir / (
            f"restart-cycle-{number:03d}-{spec.stack}-baseline.json"
        )
        baseline_paths[spec.stack] = baseline_path
        steps.append(
            _capture_restart_baseline(
                spec.stack, baseline_probe, baseline_path, runtime_origin
            )
        )
    for spec in bundle:
        steps.extend(
            (
                _manager(
                    "start",
                    spec.stack,
                    180,
                    runtime_origin,
                    evidence_dir / f"manager-cycle-{number:03d}-{spec.stack}-start-2",
                ),
                _manager(
                    "status",
                    spec.stack,
                    30,
                    runtime_origin,
                    evidence_dir / f"manager-cycle-{number:03d}-{spec.stack}-status",
                ),
            )
        )
        probe_path = evidence_dir / f"probe-cycle-{number:03d}-{spec.stack}.json"
        probe_paths.append(probe_path)
        steps.append(
            _sample_probe(
                spec.stack,
                probe_path,
                runtime_origin,
                baseline=baseline_paths[spec.stack],
            )
        )
    for spec in reversed(bundle):
        steps.extend(
            (
                _manager(
                    "stop",
                    spec.stack,
                    60,
                    runtime_origin,
                    evidence_dir / f"manager-cycle-{number:03d}-{spec.stack}-stop-1",
                ),
                _manager(
                    "stop",
                    spec.stack,
                    60,
                    runtime_origin,
                    evidence_dir / f"manager-cycle-{number:03d}-{spec.stack}-stop-2",
                ),
            )
        )
    after = _bundle_volume_ids(bundle, runtime_origin)
    for probe_path in probe_paths:
        if probe_path.is_file():
            _record_probe(state, probe_path)
    ok = all(step["returncode"] == 0 for step in steps) and before == after
    cycle_path = evidence_dir / f"cycle-{number:03d}.json"
    _atomic_json(
        cycle_path,
        {
            "cycle": number,
            "ok": ok,
            "volume_ids_before": before,
            "volume_ids_after": after,
            "steps": steps,
        },
    )
    for path in evidence_dir.glob(f"*cycle-{number:03d}*"):
        if path.is_file() and path.suffix == ".json":
            _remember_evidence(state, path, evidence_dir)
        elif path.is_dir():
            _remember_evidence_tree(state, path, evidence_dir)
    if ok:
        state["completed_cycles"] = number
    else:
        state["cycle_failures"] = int(state["cycle_failures"]) + 1
        state["volume_loss"] = before != after
        state["last_failure"] = f"cycle-{number:03d}"
    state["updated_at"] = datetime.now(UTC).isoformat()
    _atomic_json(state_path, state)
    return ok


def build_fault_cases(
    bundle: Sequence[StackSpec], contract: dict[str, Any]
) -> tuple[FaultCase, ...]:
    """Build the complete reversible RF-008 fault matrix."""
    by_stack = {spec.stack: spec for spec in bundle}
    main = by_stack["main"]
    selected_service = main.required_services[0]
    host_ports = contract.get("host_ports", {})
    selected_port = next(
        (
            int(port)
            for port, owner in host_ports.items()
            if isinstance(owner, dict)
            and owner.get("stack") == main.stack
            and owner.get("service") == selected_service
        ),
        None,
    )
    if selected_port is None:
        raise ValueError("Release contract has no required main-service host port")
    return (
        FaultCase(
            name="selected_service_termination",
            classification="service_exit_recovered",
            apply=(
                FaultOperation("compose_kill", main.stack, selected_service, max_seconds=30),
            ),
            observe=(FaultOperation("recover", main.stack, max_seconds=120),),
            restore=(FaultOperation("recover", main.stack, max_seconds=120),),
        ),
        FaultCase(
            name="failed_health_readiness",
            classification="readiness_failure_detected",
            apply=(
                FaultOperation("compose_pause", main.stack, selected_service, max_seconds=30),
            ),
            observe=(
                FaultOperation(
                    "probe",
                    main.stack,
                    max_seconds=75,
                    expected="cause:service_unready",
                ),
            ),
            restore=(
                FaultOperation("compose_unpause", main.stack, selected_service),
                FaultOperation("recover", main.stack, max_seconds=120),
            ),
        ),
        FaultCase(
            name="occupied_required_port",
            classification="port_ownership_failure_detected",
            apply=(
                FaultOperation("stop", main.stack, max_seconds=60),
                FaultOperation("reserve_port", port=selected_port),
            ),
            observe=(
                FaultOperation(
                    "start",
                    main.stack,
                    max_seconds=120,
                    expected="finding:HOST_PORT_COLLISION",
                ),
            ),
            restore=(
                FaultOperation("release_port", port=selected_port),
                FaultOperation("recover", main.stack, max_seconds=120),
            ),
        ),
        FaultCase(
            name="expected_image_identity_drift",
            classification="image_identity_drift",
            apply=(FaultOperation("inject_expected_image_drift", main.stack),),
            observe=(
                FaultOperation(
                    "classify_image_drift",
                    main.stack,
                    expected="classification:image_identity_drift",
                ),
            ),
            restore=(
                FaultOperation("clear_expected_image_drift", main.stack),
                FaultOperation("recover", main.stack, max_seconds=120),
            ),
        ),
        FaultCase(
            name="interrupted_startup",
            classification="startup_interruption_recovered",
            apply=(FaultOperation("stop", main.stack, max_seconds=60),),
            observe=(
                FaultOperation(
                    "interrupt_start",
                    main.stack,
                    max_seconds=5,
                    expected="timeout",
                ),
            ),
            restore=(FaultOperation("recover", main.stack, max_seconds=120),),
        ),
        FaultCase(
            name="bounded_memory_pid_pressure",
            classification="bounded_pressure_recovered",
            apply=(
                FaultOperation(
                    "bounded_pressure", main.stack, selected_service, max_seconds=30
                ),
            ),
            observe=(FaultOperation("probe", main.stack, max_seconds=75),),
            restore=(FaultOperation("recover", main.stack, max_seconds=120),),
        ),
        FaultCase(
            name="desktop_engine_restart",
            classification="desktop_restart_recovered",
            apply=(FaultOperation("desktop_restart", max_seconds=180),),
            observe=tuple(
                FaultOperation("recover", spec.stack, max_seconds=120)
                for spec in bundle
            ),
            restore=tuple(
                FaultOperation("recover", spec.stack, max_seconds=120)
                for spec in bundle
            ),
        ),
    )


def _operation_passed(operation: FaultOperation, result: dict[str, Any]) -> bool:
    expected = operation.expected
    if expected == "success":
        return int(result.get("returncode", 1)) == 0
    if expected == "failure":
        return int(result.get("returncode", 0)) != 0
    if expected == "timeout":
        return int(result.get("returncode", 0)) == 124 and bool(
            result.get("timed_out")
        )
    if expected.startswith("cause:"):
        return int(result.get("returncode", 0)) != 0 and str(
            result.get("primary_cause", "")
        ) == expected.partition(":")[2]
    if expected.startswith("finding:"):
        return int(result.get("returncode", 0)) != 0 and expected.partition(":")[
            2
        ] in set(map(str, result.get("finding_codes", [])))
    if expected.startswith("classification:"):
        return result.get("classification") == expected.partition(":")[2]
    raise ValueError(f"Unsupported fault expectation: {expected}")


def _atomic_json_once(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to replace existing campaign evidence: {path}")
    _atomic_json(path, payload)


def execute_fault_case(
    case: FaultCase,
    *,
    executor: FaultExecutor,
    volume_snapshot: Any,
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
) -> bool:
    """Execute one scheduled case, always restoring and emitting one incident at most."""
    existing = state.get("fault_cases", {}).get(case.name)
    if isinstance(existing, dict) and existing.get("passed") and existing.get("restored"):
        relative = str(existing.get("evidence", ""))
        expected_hash = state.get("evidence_sha256", {}).get(relative)
        evidence_path = evidence_dir / relative
        if not expected_hash or not evidence_path.is_file():
            raise ValueError(f"Completed fault evidence is missing: {case.name}")
        if _file_sha256(evidence_path) != expected_hash:
            raise ValueError(f"Completed fault evidence changed: {case.name}")
        return True
    evidence_path = evidence_dir / f"fault-{case.name}.json"
    if evidence_path.exists():
        raise FileExistsError(
            f"Cannot resume incomplete fault case over existing evidence: {case.name}"
        )
    started = time.monotonic()
    try:
        before = volume_snapshot()
    except Exception as exc:  # noqa: BLE001 - evidence must survive host failures
        before = {"capture_error": type(exc).__name__}
        operation_success = False
    else:
        operation_success = True
    results: list[dict[str, Any]] = []
    restored = True
    try:
        phases = () if not operation_success else (("apply", case.apply), ("observe", case.observe))
        for phase, operations in phases:
            for operation in operations:
                remaining = case.max_seconds - (time.monotonic() - started)
                if remaining <= 0:
                    result = {
                        "returncode": 124,
                        "timed_out": True,
                        "stderr": "fault deadline exhausted",
                    }
                else:
                    try:
                        result = executor(
                            operation, min(operation.max_seconds, remaining)
                        )
                    except Exception as exc:  # noqa: BLE001
                        result = {
                            "returncode": 125,
                            "timed_out": False,
                            "stderr": type(exc).__name__,
                        }
                passed = _operation_passed(operation, result)
                results.append(
                    {
                        "phase": phase,
                        "operation": asdict(operation),
                        "passed": passed,
                        "result": _redact(result),
                    }
                )
                operation_success = operation_success and passed
    finally:
        for operation in case.restore:
            remaining = case.max_seconds - (time.monotonic() - started)
            if remaining <= 0:
                result = {
                    "returncode": 124,
                    "timed_out": True,
                    "stderr": "restore deadline exhausted",
                }
            else:
                try:
                    result = executor(operation, min(operation.max_seconds, remaining))
                except Exception as exc:  # noqa: BLE001
                    result = {
                        "returncode": 125,
                        "timed_out": False,
                        "stderr": type(exc).__name__,
                    }
            passed = _operation_passed(operation, result)
            results.append(
                {
                    "phase": "restore",
                    "operation": asdict(operation),
                    "passed": passed,
                    "result": _redact(result),
                }
            )
            restored = restored and passed
    try:
        after = volume_snapshot()
    except Exception as exc:  # noqa: BLE001
        after = {"capture_error": type(exc).__name__}
        volumes_preserved = False
    else:
        volumes_preserved = before == after and "capture_error" not in before
    passed = operation_success and restored and volumes_preserved
    evidence = {
        "schema_version": "bioetl-docker-fault-evidence-v1",
        "case": case.name,
        "classification": case.classification,
        "passed": passed,
        "restored": restored,
        "volume_ids_before": before,
        "volume_ids_after": after,
        "duration_seconds": round(time.monotonic() - started, 3),
        "operations": results,
    }
    _atomic_json_once(evidence_path, evidence)
    state.setdefault("fault_cases", {})[case.name] = {
        "passed": passed,
        "restored": restored,
        "evidence": evidence_path.name,
    }
    state["volume_loss"] = bool(state.get("volume_loss")) or not volumes_preserved
    if not passed:
        incident_id = f"fault-{case.name}"
        incident_path = evidence_dir / f"incident-{case.name}.json"
        _atomic_json_once(
            incident_path,
            {
                "schema_version": "bioetl-docker-incident-v1",
                "incident_id": incident_id,
                "fault_evidence": evidence_path.name,
                "redacted": True,
            },
        )
        if incident_id not in state.setdefault("incident_ids", []):
            state["incident_ids"].append(incident_id)
        state["last_failure"] = incident_id
    for pattern in (
        f"fault-{case.name}.json",
        f"incident-{case.name}.json",
        "probe-fault-*.json",
    ):
        for path in evidence_dir.glob(pattern):
            _remember_evidence(state, path, evidence_dir)
    for path in evidence_dir.glob("manager-fault-*"):
        _remember_evidence_tree(state, path, evidence_dir)
    state["updated_at"] = datetime.now(UTC).isoformat()
    _atomic_json(state_path, state)
    return passed


class _HostFaultExecutor:
    """Bounded host adapter; construction alone never mutates Docker or WSL."""

    def __init__(
        self,
        runtime_origin: Path,
        bundle: Sequence[StackSpec],
        evidence_dir: Path,
    ) -> None:
        self.runtime_origin = runtime_origin
        self.bundle = {spec.stack: spec for spec in bundle}
        self.evidence_dir = evidence_dir
        self._reserved_ports: dict[int, socket.socket] = {}
        self._image_drift_injected: dict[str, dict[str, str]] = {}
        self._probe_counter = 0
        self._manager_counter = 0

    def _compose(
        self,
        operation: FaultOperation,
        *arguments: str,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        if operation.stack is None:
            raise ValueError("Compose fault operation requires a stack")
        spec = self.bundle[operation.stack]
        return _run(
            [
                "docker",
                "compose",
                "-p",
                spec.project,
                "-f",
                spec.compose_file,
                *arguments,
            ],
            operation.max_seconds if timeout is None else timeout,
            cwd=self.runtime_origin,
        )

    def __call__(
        self, operation: FaultOperation, remaining_seconds: float
    ) -> dict[str, Any]:
        timeout = max(0.1, min(operation.max_seconds, remaining_seconds))
        if operation.kind in {"start", "stop", "recover"}:
            if operation.stack is None:
                raise ValueError("Manager fault operation requires a stack")
            self._manager_counter += 1
            report_dir = self.evidence_dir / (
                f"manager-fault-{self._manager_counter:03d}-{operation.stack}-{operation.kind}"
            )
            return _manager(
                operation.kind,
                operation.stack,
                timeout,
                self.runtime_origin,
                report_dir,
            )
        if operation.kind == "compose_kill":
            return self._compose(
                operation,
                "kill",
                "-s",
                "TERM",
                str(operation.service),
                timeout=timeout,
            )
        if operation.kind == "compose_pause":
            return self._compose(
                operation, "pause", str(operation.service), timeout=timeout
            )
        if operation.kind == "compose_unpause":
            return self._compose(
                operation, "unpause", str(operation.service), timeout=timeout
            )
        if operation.kind == "probe":
            if operation.stack is None:
                raise ValueError("Probe fault operation requires a stack")
            self._probe_counter += 1
            path = self.evidence_dir / (
                f"probe-fault-{operation.stack}-{self._probe_counter:03d}.json"
            )
            return _sample_probe(operation.stack, path, self.runtime_origin)
        if operation.kind == "reserve_port":
            if operation.port is None or operation.port in self._reserved_ports:
                return {"returncode": 1, "stderr": "port reservation is not unique"}
            reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                reservation.bind(("127.0.0.1", operation.port))
                reservation.listen(1)
            except OSError as exc:
                reservation.close()
                return {"returncode": 1, "stderr": str(exc)}
            self._reserved_ports[operation.port] = reservation
            return {"returncode": 0, "port": operation.port}
        if operation.kind == "release_port":
            reservation = self._reserved_ports.pop(int(operation.port or 0), None)
            if reservation is None:
                return {"returncode": 1, "stderr": "port reservation not found"}
            reservation.close()
            return {"returncode": 0, "port": operation.port}
        if operation.kind == "inject_expected_image_drift":
            images = self._compose(
                operation, "images", "--format", "json", timeout=timeout
            )
            if images["returncode"] != 0:
                return images
            actual = hashlib.sha256(
                str(images.get("stdout", "")).encode("utf-8")
            ).hexdigest()
            expected = hashlib.sha256(
                f"{actual}:rf008-controlled-contract-drift".encode()
            ).hexdigest()
            self._image_drift_injected[str(operation.stack)] = {
                "actual_identity_sha256": actual,
                "expected_identity_sha256": expected,
            }
            return {"returncode": 0, **self._image_drift_injected[str(operation.stack)]}
        if operation.kind == "classify_image_drift":
            identities = self._image_drift_injected.get(str(operation.stack))
            classification = (
                "image_identity_drift"
                if identities is not None
                and identities["actual_identity_sha256"]
                != identities["expected_identity_sha256"]
                else "identity_match"
            )
            return {
                "returncode": 0,
                "classification": classification,
                **(identities or {}),
            }
        if operation.kind == "clear_expected_image_drift":
            self._image_drift_injected.pop(str(operation.stack), None)
            return {"returncode": 0}
        if operation.kind == "interrupt_start":
            if operation.stack is None:
                raise ValueError("Interrupted start requires a stack")
            manager = _runtime_script(
                self.runtime_origin,
                "scripts/ops/runtime/docker/runtime_manager.py",
            )
            return _run(
                [
                    sys.executable,
                    str(manager),
                    "start",
                    "--stack",
                    operation.stack,
                    "--timeout",
                    str(timeout),
                ],
                min(timeout, 0.1),
                cwd=self.runtime_origin,
            )
        if operation.kind == "bounded_pressure":
            # The workload is finite (16 MiB, six children, five seconds) and
            # cannot alter container resource limits or survive this command.
            script = (
                "import subprocess,time; "
                "buf=bytearray(16*1024*1024); "
                "ps=[subprocess.Popen(['sleep','5']) for _ in range(6)]; "
                "time.sleep(5); [p.wait() for p in ps]; assert len(buf)"
            )
            return self._compose(
                operation,
                "exec",
                "-T",
                str(operation.service),
                "python",
                "-c",
                script,
                timeout=timeout,
            )
        if operation.kind == "desktop_restart":
            return _run(
                ["docker", "desktop", "restart"], timeout, cwd=self.runtime_origin
            )
        raise ValueError(f"Unsupported fault operation: {operation.kind}")


def _signing_identity_matches(key: str, expected_fingerprint: str) -> bool:
    expected = re.sub(r"\s+", "", expected_fingerprint).upper()
    result = _run(
        [
            "gpg",
            "--batch",
            "--with-colons",
            "--fingerprint",
            "--list-secret-keys",
            key,
        ],
        30,
    )
    if result["returncode"] != 0:
        return False
    return any(
        len(parts) > 9 and parts[0] == "fpr" and parts[9].upper() == expected
        for line in str(result.get("stdout", "")).splitlines()
        if (parts := line.split(":"))
    )


def _sign(summary: Path, key: str) -> Path:
    result = _run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--armor",
            "--detach-sign",
            "--local-user",
            key,
            str(summary),
        ],
        60,
    )
    if result["returncode"] != 0:
        raise RuntimeError("Detached GPG signature failed")
    return summary.with_suffix(summary.suffix + ".asc")


def _signature_valid(
    summary: Path, signature: Path, expected_fingerprint: str
) -> bool:
    if not signature.is_file():
        return False
    result = _run(
        [
            "gpg",
            "--batch",
            "--status-fd",
            "1",
            "--verify",
            str(signature),
            str(summary),
        ],
        60,
    )
    if result["returncode"] != 0:
        return False
    expected = re.sub(r"\s+", "", expected_fingerprint).upper()
    return any(
        line.startswith("[GNUPG:] VALIDSIG ")
        and line.split()[2].upper() == expected
        for line in result.get("stdout", "").splitlines()
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-origin", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=CONTRACT_RELATIVE_PATH)
    parser.add_argument("--cycles", type=int, default=100)
    parser.add_argument("--soak-hours", type=float, default=72.0)
    parser.add_argument("--soak-sample-seconds", type=float, default=60.0)
    parser.add_argument("--engine-recovery-trials", type=int, default=100)
    parser.add_argument("--confirm-host-disruption", default="")
    parser.add_argument(
        "--state",
        type=Path,
        default=ROOT / "reports/quality/docker-stability-campaign-state.json",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=ROOT / "reports/quality/docker-stability-raw",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=ROOT / "reports/quality/docker-stability-summary.json",
    )
    parser.add_argument("--signing-key")
    parser.add_argument("--signing-fingerprint")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.execute:
        print("Refusing to count evidence without --execute", file=sys.stderr)
        return 2
    if args.cycles < 100 or args.soak_hours < 72 or args.engine_recovery_trials < 100:
        print("Release thresholds cannot be reduced", file=sys.stderr)
        return 2
    if args.soak_sample_seconds < 1:
        print("Soak sample interval must be at least one second", file=sys.stderr)
        return 2
    if args.confirm_host_disruption != CONFIRM_TOKEN:
        print(
            "Host recovery trials require explicit operator scheduling token",
            file=sys.stderr,
        )
        return 2
    if not args.signing_key:
        print("A detached GPG signing key is required for promotion evidence", file=sys.stderr)
        return 2
    if not args.signing_fingerprint:
        print(
            "An expected GPG signing fingerprint is required for promotion evidence",
            file=sys.stderr,
        )
        return 2
    runtime_origin = _canonical_runtime_origin(args.runtime_origin)
    _contract_path, contract, contract_sha256 = _load_contract(
        runtime_origin, args.contract
    )
    bundle = _release_bundle(contract)
    _validate_runtime_layout(runtime_origin, _contract_path, bundle)
    slo = contract.get("stability_slo", {})
    if (
        args.cycles < int(slo.get("startup_cycles", 100))
        or args.soak_hours < float(slo.get("soak_hours", 72))
        or args.engine_recovery_trials < int(slo.get("recovery_trials", 100))
    ):
        print("Contract release thresholds cannot be reduced", file=sys.stderr)
        return 2
    if not _signing_identity_matches(args.signing_key, args.signing_fingerprint):
        print(
            "The pre-existing secret signing identity does not match the exact fingerprint",
            file=sys.stderr,
        )
        return 2
    state = _load(args.state)
    expected_identity = {
        "schema_version": "bioetl-docker-stability-campaign-state-v2",
        "release_bundle": _bundle_identity(bundle),
        "runtime_origin": str(runtime_origin),
        "contract_sha256": contract_sha256,
        "required_cycles": args.cycles,
        "required_soak_hours": args.soak_hours,
        "required_engine_recovery_trials": args.engine_recovery_trials,
        "soak_sample_seconds": args.soak_sample_seconds,
        "required_fault_cases": list(FAULT_CASE_NAMES),
        "evidence_dir": str(args.evidence_dir.resolve()),
        "summary_path": str(args.summary.resolve()),
        "signing_fingerprint": re.sub(
            r"\s+", "", args.signing_fingerprint
        ).upper(),
    }
    if state:
        mismatches = [
            key for key, expected in expected_identity.items() if state.get(key) != expected
        ]
        if mismatches:
            raise ValueError(
                "Cannot resume campaign with different pinned identity: "
                + ", ".join(mismatches)
            )
        if state.get("last_failure") is not None:
            raise ValueError("Cannot resume a failed release gate as success")
        _validate_evidence_index(state, args.evidence_dir)
    else:
        state = new_state(
            bundle=bundle,
            runtime_origin=runtime_origin,
            contract_sha256=contract_sha256,
            cycles=args.cycles,
            soak_hours=args.soak_hours,
        )
        state.update(expected_identity)
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    if not state.get("initial_volume_ids"):
        state["initial_volume_ids"] = _bundle_volume_ids(bundle, runtime_origin)
        _atomic_json(args.state, state)
    for spec in bundle:
        bootstrap_dir = args.evidence_dir / f"manager-bootstrap-{spec.stack}"
        start = _manager(
            "start", spec.stack, 180, runtime_origin, bootstrap_dir
        )
        _remember_evidence_tree(state, bootstrap_dir, args.evidence_dir)
        if start["returncode"] != 0:
            state["last_failure"] = f"bootstrap-start-{spec.stack}"
            _atomic_json(args.state, state)
            return 1
    origin_findings = _compose_origin_findings(
        _live_compose_rows(runtime_origin), bundle, runtime_origin
    )
    if origin_findings:
        state["last_failure"] = "bootstrap-project-origin"
        _atomic_json(args.state, state)
        print("; ".join(origin_findings), file=sys.stderr)
        return 1
    _atomic_json(args.state, state)

    fault_executor = _HostFaultExecutor(runtime_origin, bundle, args.evidence_dir)
    for case in build_fault_cases(bundle, contract):
        if not execute_fault_case(
            case,
            executor=fault_executor,
            volume_snapshot=lambda: _bundle_volume_ids(bundle, runtime_origin),
            state=state,
            state_path=args.state,
            evidence_dir=args.evidence_dir,
        ):
            return 1

    while int(state["completed_cycles"]) < int(state["required_cycles"]):
        if not run_cycle(
            state, args.state, args.evidence_dir, bundle, runtime_origin
        ):
            return 1

    if state["soak_started_at"] is None:
        state["soak_started_at"] = time.time()
        state["soak_last_sample_at"] = None
        _atomic_json(args.state, state)
    for spec in bundle:
        start = _manager("start", spec.stack, 180, runtime_origin)
        if start["returncode"] != 0:
            state["last_failure"] = f"soak-start-{spec.stack}"
            _atomic_json(args.state, state)
            return 1
    previous_sample_at = state.get("soak_last_sample_at")
    if previous_sample_at is not None:
        gap = time.time() - float(previous_sample_at)
        if gap > max(120.0, args.soak_sample_seconds * 2):
            state["soak_interruptions"] = int(state.get("soak_interruptions", 0)) + 1
            state["soak_observed_seconds"] = 0.0
            state["soak_started_at"] = time.time()
    required_seconds = float(state["required_soak_hours"]) * 3600
    while float(state["soak_observed_seconds"]) < required_seconds:
        interval_started = time.monotonic()
        for spec in bundle:
            sample = args.evidence_dir / (
                f"probe-soak-{int(state['soak_observed_seconds']):09d}-{spec.stack}.json"
            )
            result = _sample_probe(spec.stack, sample, runtime_origin)
            if sample.is_file():
                _record_probe(state, sample)
            if result["returncode"] != 0:
                state["last_failure"] = sample.name
                _atomic_json(args.state, state)
                return 1
        state["soak_last_sample_at"] = time.time()
        _atomic_json(args.state, state)
        time.sleep(
            min(
                args.soak_sample_seconds,
                max(0.0, required_seconds - state["soak_observed_seconds"]),
            )
        )
        state["soak_observed_seconds"] = float(
            state["soak_observed_seconds"]
        ) + (time.monotonic() - interval_started)
        _atomic_json(args.state, state)

    # Engine interruption is deliberately delegated to the supported Desktop
    # helper. Every trial remains bounded and diagnostics-preserving.
    for trial in range(
        int(state["engine_recovery_trials"]), args.engine_recovery_trials
    ):
        trial_started = time.monotonic()
        before = _bundle_volume_ids(bundle, runtime_origin)
        interruption = _run(
            ["docker", "desktop", "restart"], 180, cwd=runtime_origin
        )
        remaining = max(1.0, 180.0 - (time.monotonic() - trial_started))
        stack_results: list[dict[str, Any]] = []
        if interruption["returncode"] == 0:
            for spec in bundle:
                recovery = _manager("recover", spec.stack, remaining, runtime_origin)
                status = (
                    _manager(
                        "status", spec.stack, min(30.0, remaining), runtime_origin
                    )
                    if recovery["returncode"] == 0
                    else {"returncode": 1, "stderr": "recovery failed"}
                )
                trial_probe = args.evidence_dir / (
                    f"probe-recovery-{trial + 1:03d}-{spec.stack}.json"
                )
                probe = (
                    _sample_probe(spec.stack, trial_probe, runtime_origin)
                    if status["returncode"] == 0
                    else {"returncode": 1, "stderr": "status failed"}
                )
                if trial_probe.is_file():
                    _record_probe(state, trial_probe)
                stack_results.append(
                    {
                        "stack": spec.stack,
                        "recovery": recovery,
                        "status": status,
                        "probe": probe,
                    }
                )
        after = _bundle_volume_ids(bundle, runtime_origin)
        duration = time.monotonic() - trial_started
        success = (
            interruption["returncode"] == 0
            and len(stack_results) == len(bundle)
            and all(
                row["recovery"]["returncode"] == 0
                and row["status"]["returncode"] == 0
                and row["probe"]["returncode"] == 0
                for row in stack_results
            )
            and duration <= 180
            and before == after
        )
        result = {
            "interruption": interruption,
            "stacks": stack_results,
            "returncode": 0 if success else 1,
            "duration_seconds": round(duration, 3),
            "volume_ids_before": before,
            "volume_ids_after": after,
        }
        state["engine_recovery_trials"] = trial + 1
        state["engine_recovery_successes"] = int(
            state["engine_recovery_successes"]
        ) + int(success)
        state["volume_loss"] = bool(state["volume_loss"]) or before != after
        _atomic_json(
            args.evidence_dir / f"engine-recovery-{trial + 1:03d}.json", result
        )
        _atomic_json(args.state, state)

    state["final_volume_ids"] = _bundle_volume_ids(bundle, runtime_origin)
    state["volume_loss"] = bool(state["volume_loss"]) or (
        state["initial_volume_ids"] != state["final_volume_ids"]
    )
    _atomic_json(args.state, state)
    raw_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(args.evidence_dir.glob("*.json"))
    }
    signature_path = args.summary.with_suffix(args.summary.suffix + ".asc")
    gates = release_gates(state, signature_exists=True)
    summary = {
        "schema_version": "bioetl-docker-stability-summary-v2",
        "state": state,
        "raw_evidence_sha256": raw_hashes,
        "signing_fingerprint": re.sub(
            r"\s+", "", args.signing_fingerprint
        ).upper(),
        "release_gates": gates,
        "promotion_passed": all(gates.values()),
    }
    _atomic_json_once(args.summary, summary)
    _sign(args.summary, args.signing_key)
    if not _signature_valid(args.summary, signature_path, args.signing_fingerprint):
        return 1
    return 0 if summary["promotion_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
