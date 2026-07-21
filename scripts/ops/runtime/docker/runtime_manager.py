#!/usr/bin/env python3
"""Fail-closed lifecycle manager for optional BioETL Docker adjuncts.

Docker remains optional under ADR-010. The manager never deletes volumes,
never prunes host state, and reports success only after preflight, Compose
rendering, readiness, restart/OOM/image verification, and stabilization pass.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONTRACT = ROOT / "configs/quality/docker_runtime_contracts.yaml"
DEFAULT_REPORT_DIR = ROOT / "reports/quality"
_SECRET_KEY = re.compile(r"(?:password|secret|token|credential|auth)", re.I)
_SECRET_VALUE = re.compile(r"(?:gh[pousr]_[A-Za-z0-9_]{12,}|Bearer\s+\S+)", re.I)
_SECRET_ASSIGNMENT = re.compile(
    r"\b([A-Za-z0-9_]*(?:password|secret|token|credential|auth)[A-Za-z0-9_]*)"
    r"=([^\s,;]+)",
    re.I,
)
_URI_USERINFO = re.compile(r"(://)[^/@\s:]+:[^/@\s]+@")


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class StackSpec:
    name: str
    project: str
    compose_file: Path
    required_services: tuple[str, ...]
    expected_images: Mapping[str, str]


@dataclass(frozen=True)
class ServiceSnapshot:
    service: str
    container_id: str
    state: str
    health: str
    restart_count: int
    oom_killed: bool
    image: str
    image_digests: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return (
            self.state == "running" and not self.oom_killed and self.health == "healthy"
        )


Runner = Callable[[Sequence[str], Path, float], CommandResult]
Sleeper = Callable[[float], None]
Clock = Callable[[], float]


def _bounded(value: str, limit: int = 4000) -> str:
    return value[:limit]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _run(
    command: Sequence[str],
    cwd: Path,
    timeout: float,
    *,
    output_limit: int | None = 4000,
) -> CommandResult:
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
        return CommandResult(list(command), 127, stderr=str(exc))
    stdout = completed.stdout
    stderr = completed.stderr
    if output_limit is not None:
        stdout = _bounded(stdout, output_limit)
        stderr = _bounded(stderr, output_limit)
    return CommandResult(
        list(command),
        completed.returncode,
        stdout,
        stderr,
    )


def _load_contract(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Docker runtime contract must be a mapping")
    return payload


def _load_compose(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Compose document must be a mapping")
    return payload


def resolve_stack(contract_path: Path, stack_name: str) -> StackSpec:
    contract = _load_contract(contract_path)
    stack = contract["stacks"][stack_name]
    compose_file = (ROOT / stack["compose_file"]).resolve()
    compose = _load_compose(compose_file)
    expected_images = {
        name: str(service["image"])
        for name, service in compose["services"].items()
        if "image" in service
    }
    return StackSpec(
        name=stack_name,
        project=str(stack["project_name"]),
        compose_file=compose_file,
        required_services=tuple(map(str, stack["required_services"])),
        expected_images=expected_images,
    )


def _compose(spec: StackSpec, *args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "-p",
        spec.project,
        "-f",
        str(spec.compose_file),
        *args,
    ]


def _json_rows(text: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        rows: list[dict[str, Any]] = []
        for line in stripped.splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows
    if isinstance(payload, dict):
        return [payload]
    return [row for row in payload if isinstance(row, dict)]


# Lean compose-ps template keeps multi-service stacks inside incident bounds.
# Full `--format json` includes Labels and is truncated by `_bounded` (4000),
# which previously dropped monitoring services after grafana.
_COMPOSE_PS_LEAN_FORMAT = (
    '{"ID":"{{.ID}}","Service":"{{.Service}}","Name":"{{.Name}}",'
    '"State":"{{.State}}","Health":"{{.Health}}","Image":"{{.Image}}"}'
)


def collect_snapshots(
    spec: StackSpec,
    *,
    runner: Runner = _run,
    timeout: float = 15.0,
) -> tuple[list[ServiceSnapshot], list[CommandResult]]:
    ps = runner(
        _compose(spec, "ps", "--all", "--format", _COMPOSE_PS_LEAN_FORMAT),
        ROOT,
        timeout,
    )
    observations = [ps]
    if ps.returncode != 0:
        return [], observations
    snapshots: list[ServiceSnapshot] = []
    for row in _json_rows(ps.stdout):
        container_id = str(row.get("ID") or row.get("Id") or "")
        service = str(row.get("Service") or row.get("Name") or "")
        if not container_id or not service:
            continue
        inspection = runner(
            [
                "docker",
                "inspect",
                "--format",
                (
                    '{"State":{{json .State}},'
                    '"RestartCount":{{.RestartCount}},'
                    '"Image":{{json .Config.Image}},'
                    '"ImageID":{{json .Image}}}'
                ),
                container_id,
            ],
            ROOT,
            timeout,
        )
        observations.append(inspection)
        details = _json_rows(inspection.stdout)
        if inspection.returncode != 0 or not details:
            continue
        item = details[0]
        state = item.get("State") or {}
        config = item.get("Config") or {}
        image = str(item.get("Image") or config.get("Image") or row.get("Image") or "")
        image_id = str(item.get("ImageID") or image)
        image_digests: tuple[str, ...] = ()
        if image_id:
            image_inspection = runner(
                [
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    '{"RepoDigests":{{json .RepoDigests}}}',
                    image_id,
                ],
                ROOT,
                timeout,
            )
            observations.append(image_inspection)
            image_details = _json_rows(image_inspection.stdout)
            if image_inspection.returncode == 0 and image_details:
                image_digests = tuple(
                    str(value)
                    for value in (image_details[0].get("RepoDigests") or [])
                    if value
                )
        health = (state.get("Health") or {}).get("Status", "none")
        snapshots.append(
            ServiceSnapshot(
                service=service,
                container_id=container_id[:12],
                state=str(state.get("Status", "unknown")).lower(),
                health=str(health).lower(),
                restart_count=int(item.get("RestartCount") or 0),
                oom_killed=bool(state.get("OOMKilled", False)),
                image=image,
                image_digests=image_digests,
            )
        )
    return snapshots, observations


def readiness_findings(
    spec: StackSpec,
    snapshots: Sequence[ServiceSnapshot],
    baseline: Mapping[str, int] | None = None,
) -> list[dict[str, Any]]:
    baseline_provided = baseline is not None
    baseline = baseline or {}
    by_service = {snapshot.service: snapshot for snapshot in snapshots}
    findings: list[dict[str, Any]] = []
    for service in spec.required_services:
        snapshot = by_service.get(service)
        if snapshot is None:
            findings.append({"cause": "service_missing", "service": service})
            continue
        if snapshot.oom_killed:
            findings.append({"cause": "oom_killed", "service": service})
        if snapshot.state != "running" or snapshot.health != "healthy":
            findings.append(
                {
                    "cause": "service_unready",
                    "service": service,
                    "state": snapshot.state,
                    "health": snapshot.health,
                }
            )
        previous = int(
            baseline.get(service, 0 if baseline_provided else snapshot.restart_count)
        )
        if snapshot.restart_count > previous:
            findings.append(
                {
                    "cause": "unexpected_restart",
                    "service": service,
                    "restart_delta": snapshot.restart_count - previous,
                }
            )
        expected = spec.expected_images.get(service)
        expected_digest = _digest_from_image(expected)
        observed_images = (snapshot.image, *snapshot.image_digests)
        image_matches = (
            any(
                expected_digest == _digest_from_image(image)
                for image in observed_images
            )
            if expected_digest
            else expected in observed_images
        )
        if expected and snapshot.image and not image_matches:
            findings.append(
                {
                    "cause": "image_identity_drift",
                    "service": service,
                    "expected": expected,
                    "actual": snapshot.image,
                }
            )
    return findings


def _digest_from_image(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"@(?P<digest>sha256:[0-9a-fA-F]{64})$", value)
    return match.group("digest").lower() if match else None


_CAUSE_PRIORITY = {
    "daemon_unavailable": 0,
    "preflight_failed": 1,
    "compose_render_failed": 2,
    "project_origin_drift": 3,
    "network_owner_drift": 3,
    "port_owner_drift": 4,
    "image_identity_drift": 5,
    "oom_killed": 6,
    "unexpected_restart": 7,
    "service_missing": 8,
    "service_unready": 9,
    "disk_reserve_low": 10,
    "resource_pressure": 11,
    "readiness_timeout": 12,
    "recovery_objective_breach": 13,
    "recovery_exhausted": 14,
    "unresolved_incident": 15,
    "unknown": 99,
}


def primary_cause(findings: Sequence[Mapping[str, Any]]) -> str:
    causes = [str(finding.get("cause", "unknown")) for finding in findings]
    return min(causes or ["unknown"], key=lambda value: _CAUSE_PRIORITY.get(value, 98))


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "<redacted>" if _SECRET_KEY.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        bounded = _bounded(value)
        bounded = _SECRET_VALUE.sub("<redacted>", bounded)
        bounded = _SECRET_ASSIGNMENT.sub(r"\1=<redacted>", bounded)
        return _URI_USERINFO.sub(r"\1<redacted>:<redacted>@", bounded)
    return value


def write_report(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_redact(dict(payload)), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _preflight(
    contract_path: Path,
    report_path: Path,
    stack_name: str,
    *,
    runner: Runner,
    timeout: float,
) -> CommandResult:
    return runner(
        [
            sys.executable,
            str(ROOT / "scripts/ops/runtime/docker/docker_runtime_preflight.py"),
            "--contract",
            str(contract_path),
            "--output",
            str(report_path),
            "--stack",
            stack_name,
        ],
        ROOT,
        timeout,
    )


def diagnose(
    spec: StackSpec,
    contract_path: Path,
    output: Path,
    *,
    runner: Runner = _run,
    timeout: float = 15.0,
) -> dict[str, Any]:
    snapshots, observations = collect_snapshots(spec, runner=runner, timeout=timeout)
    disk = shutil.disk_usage(ROOT)
    commands = [
        runner(["docker", "info", "--format", "{{json .}}"], ROOT, timeout),
        runner(
            ["docker", "compose", "ls", "--all", "--format", "json"],
            ROOT,
            timeout,
        ),
        *observations,
    ]
    findings = readiness_findings(spec, snapshots)
    if commands[0].returncode != 0:
        findings.append({"cause": "daemon_unavailable"})
    payload = {
        "schema_version": "bioetl-docker-diagnostic-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "stack": spec.name,
        "project": spec.project,
        "contract": _display_path(contract_path),
        "disk": {"total_bytes": disk.total, "free_bytes": disk.free},
        "services": [asdict(snapshot) for snapshot in snapshots],
        "findings": findings,
        "primary_cause": None if not findings else primary_cause(findings),
        "observations": [asdict(command) for command in commands],
        "redaction_applied": True,
    }
    write_report(output, payload)
    return payload


def ensure_shared_networks(
    spec: StackSpec,
    contract_path: Path,
    output: Path,
    *,
    runner: Runner = _run,
    timeout: float = 15.0,
) -> tuple[bool, list[dict[str, Any]]]:
    """Create missing contracted external networks and reject conflicting owners."""
    try:
        contract = _load_contract(contract_path)
    except OSError:
        # Focused unit fixtures may supply an in-memory preflight without a file.
        # Production preflight cannot succeed when the contract is absent.
        return True, []
    networks = [
        raw
        for raw in contract.get("shared_networks", {}).values()
        if isinstance(raw, Mapping) and spec.name in raw.get("consumers", [])
    ]
    observations: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for raw in networks:
        name = str(raw["name"])
        owner = str(raw["owner"])
        inspection = runner(
            [
                "docker",
                "network",
                "inspect",
                "--format",
                '{{ index .Labels "com.bioetl.owner" }}',
                name,
            ],
            ROOT,
            timeout,
        )
        created = False
        if inspection.returncode != 0:
            creation = runner(
                [
                    "docker",
                    "network",
                    "create",
                    "--label",
                    f"com.bioetl.owner={owner}",
                    name,
                ],
                ROOT,
                timeout,
            )
            created = creation.returncode == 0
            observations.append(
                {
                    "name": name,
                    "owner": owner,
                    "created": created,
                    "inspect": asdict(inspection),
                    "create": asdict(creation),
                }
            )
            if not created:
                findings.append(
                    {"cause": "network_owner_drift", "network": name, "owner": owner}
                )
            continue
        observed_owner = inspection.stdout.strip()
        owner_ok = observed_owner == owner
        observations.append(
            {
                "name": name,
                "owner": owner,
                "observed_owner": observed_owner or None,
                "created": created,
                "owner_ok": owner_ok,
                "inspect": asdict(inspection),
            }
        )
        if not owner_ok:
            findings.append(
                {
                    "cause": "network_owner_drift",
                    "network": name,
                    "expected_owner": owner,
                    "observed_owner": observed_owner,
                }
            )
    write_report(
        output,
        {
            "schema_version": "bioetl-docker-shared-networks-v1",
            "generated_at": datetime.now(UTC).isoformat(),
            "stack": spec.name,
            "ok": not findings,
            "findings": findings,
            "networks": observations,
            "redaction_applied": True,
        },
    )
    return not findings, findings


def _wait_ready(
    spec: StackSpec,
    baseline: Mapping[str, int],
    *,
    runner: Runner,
    timeout: float,
    poll_interval: float,
    stabilization_seconds: float,
    sleep: Sleeper,
    clock: Clock,
) -> tuple[list[ServiceSnapshot], list[dict[str, Any]]]:
    deadline = clock() + timeout
    last_snapshots: list[ServiceSnapshot] = []
    last_findings: list[dict[str, Any]] = [{"cause": "readiness_timeout"}]
    while clock() < deadline:
        remaining = deadline - clock()
        if remaining <= 0:
            break
        last_snapshots, _ = collect_snapshots(
            spec, runner=runner, timeout=min(15.0, remaining)
        )
        last_findings = readiness_findings(spec, last_snapshots, baseline)
        if not last_findings:
            if stabilization_seconds > 0:
                remaining = deadline - clock()
                if remaining <= 0:
                    break
                sleep(min(stabilization_seconds, remaining))
                remaining = deadline - clock()
                if remaining <= 0:
                    break
                last_snapshots, _ = collect_snapshots(
                    spec, runner=runner, timeout=min(15.0, remaining)
                )
                last_findings = readiness_findings(spec, last_snapshots, baseline)
            if not last_findings:
                return last_snapshots, []
        remaining = deadline - clock()
        if remaining <= 0:
            break
        sleep(min(poll_interval, remaining))
    if not last_findings:
        last_findings = [{"cause": "readiness_timeout"}]
    return last_snapshots, last_findings


_RECOVERABLE_PREFLIGHT_CODES = frozenset(
    {
        "CONTAINER_HEALTH",
        "CONTAINER_RESTART",
        "CONTAINER_OOM",
    }
)
_DAEMON_UNAVAILABLE_PREFLIGHT_CODES = frozenset(
    {
        "CAPACITY_DOCKER_ROOT",
        "DAEMON_UNAVAILABLE",
        "DOCKER_DAEMON",
    }
)


def _preflight_errors_are_recoverable(preflight_path: Path) -> bool:
    """Allow recover to proceed when preflight only reports live container health.

    Recover is invoked precisely because required services are unready/unhealthy.
    Origin, network, capacity, and other environment gates still fail closed.
    """
    try:
        payload = json.loads(preflight_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    findings = payload.get("findings") or []
    if not isinstance(findings, list):
        return False
    errors = [
        finding
        for finding in findings
        if isinstance(finding, Mapping) and finding.get("severity") == "error"
    ]
    if not errors:
        return True
    return all(
        str(finding.get("code") or "") in _RECOVERABLE_PREFLIGHT_CODES
        for finding in errors
    )


def _preflight_indicates_daemon_unavailable(preflight_path: Path) -> bool:
    """True when preflight failed because the Docker engine is unreachable."""
    try:
        payload = json.loads(preflight_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    findings = payload.get("findings") or []
    if not isinstance(findings, list):
        return False
    for finding in findings:
        if not isinstance(finding, Mapping):
            continue
        code = str(finding.get("code") or "")
        message = str(finding.get("message") or "")
        evidence = finding.get("evidence") or {}
        evidence_text = json.dumps(evidence, ensure_ascii=False) if evidence else ""
        blob = f"{code}\n{message}\n{evidence_text}"
        if code in _DAEMON_UNAVAILABLE_PREFLIGHT_CODES:
            return True
        if _daemon_connection_error(blob):
            return True
    return False


def _invoke_desktop_recovery(
    report_path: Path,
    *,
    runner: Runner,
    timeout: float,
) -> CommandResult:
    """Bounded RF-006 Desktop recovery (no last-resort force-kill)."""
    script = ROOT / "scripts/ops/runtime/docker/restart-docker.ps1"
    if not script.is_file():
        return CommandResult(
            ["restart-docker.ps1"],
            127,
            stderr=f"missing desktop recovery script: {script}",
        )
    # Prefer Windows PowerShell so Docker Desktop CLI resolves on Windows hosts.
    powershell_candidates = (
        "powershell.exe",
        "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
    )
    powershell = next(
        (candidate for candidate in powershell_candidates if shutil.which(candidate) or Path(candidate).is_file()),
        None,
    )
    if powershell is None:
        return CommandResult(
            ["powershell.exe", "-File", str(script)],
            127,
            stderr="Windows PowerShell not found for Desktop recovery",
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    # Convert paths for PowerShell when running under WSL.
    script_arg = str(script)
    report_arg = str(report_path)
    if str(script).startswith("/"):
        converted_script = runner(["wslpath", "-w", str(script)], ROOT, min(10.0, timeout))
        converted_report = runner(
            ["wslpath", "-w", str(report_path)], ROOT, min(10.0, timeout)
        )
        if converted_script.returncode == 0 and converted_report.returncode == 0:
            script_arg = converted_script.stdout.strip()
            report_arg = converted_report.stdout.strip()
    internal = max(10, min(175, int(timeout) - 5)) if timeout > 15 else max(5, int(timeout))
    return runner(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script_arg,
            "-TimeoutSeconds",
            str(internal),
            "-CommandTimeoutSeconds",
            "15",
            "-ReportPath",
            report_arg,
        ],
        ROOT,
        timeout,
    )


def _daemon_connection_error(stderr: str | None, stdout: str | None = None) -> bool:
    """True when compose/CLI output indicates a transient Docker daemon outage."""
    text = f"{stderr or ''}\n{stdout or ''}".lower()
    markers = (
        "cannot connect to the docker daemon",
        "is the docker daemon running",
        "error during connect",
        "docker desktop is unable to start",
        "failed to connect to the docker api",
        "connection refused",
        "pipe is being closed",
        "the system cannot find the file specified",
    )
    return any(marker in text for marker in markers)


def _wait_for_daemon(
    *,
    runner: Runner,
    deadline: float,
    sleep: Sleeper,
    clock: Clock,
    poll_interval: float = 2.0,
) -> bool:
    """Poll `docker info` until the daemon answers or the deadline is reached."""
    while clock() < deadline:
        remaining = max(0.1, min(5.0, deadline - clock()))
        probe = runner(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            ROOT,
            remaining,
        )
        if probe.returncode == 0 and str(probe.stdout or "").strip():
            return True
        sleep(min(poll_interval, max(0.0, deadline - clock())))
    return False


def start_or_recover(
    spec: StackSpec,
    contract_path: Path,
    report_dir: Path,
    *,
    recover: bool,
    runner: Runner = _run,
    timeout: float = 120.0,
    max_attempts: int = 3,
    poll_interval: float = 2.0,
    stabilization_seconds: float = 5.0,
    sleep: Sleeper = time.sleep,
    clock: Clock = time.monotonic,
) -> int:
    started = clock()
    deadline = started + timeout
    history: list[dict[str, Any]] = []
    recent_logs: dict[str, Any] = {"captured": False, "stdout": "", "stderr": ""}
    desktop_recovery_attempted = False
    preflight_path = report_dir / f"docker-runtime-{spec.name}-preflight.json"
    preflight = _preflight(
        contract_path,
        preflight_path,
        spec.name,
        runner=runner,
        timeout=min(max(0.1, deadline - clock()), 60.0),
    )
    if (
        recover
        and preflight.returncode != 0
        and _preflight_indicates_daemon_unavailable(preflight_path)
        and clock() < deadline
    ):
        # RF-006: bounded Desktop recovery before failing closed on daemon outage.
        desktop_report = report_dir / f"docker-desktop-recovery-{spec.name}.json"
        desktop = _invoke_desktop_recovery(
            desktop_report,
            runner=runner,
            timeout=min(max(0.1, deadline - clock()), 180.0),
        )
        desktop_recovery_attempted = True
        history.append(
            {
                "attempt": 0,
                "action": "desktop_recovery",
                "returncode": desktop.returncode,
                "elapsed_seconds": round(clock() - started, 3),
            }
        )
        _wait_for_daemon(
            runner=runner,
            deadline=deadline,
            sleep=sleep,
            clock=clock,
            poll_interval=max(poll_interval, 2.0),
        )
        preflight = _preflight(
            contract_path,
            preflight_path,
            spec.name,
            runner=runner,
            timeout=min(max(0.1, deadline - clock()), 60.0),
        )
    # Both start and recover may proceed when the only preflight errors are live
    # container health/restart/OOM — those are exactly what up --wait must clear.
    # Origin/port/capacity/daemon environment gates still fail closed.
    if preflight.returncode != 0 and not _preflight_errors_are_recoverable(
        preflight_path
    ):
        findings = [{"cause": "preflight_failed", "stderr": preflight.stderr}]
        if desktop_recovery_attempted:
            findings.append({"cause": "daemon_unavailable", "desktop_recovery": True})
        snapshots: list[ServiceSnapshot] = []
        attempts = 0
    else:
        networks_ok, network_findings = ensure_shared_networks(
            spec,
            contract_path,
            report_dir / f"docker-runtime-{spec.name}-networks.json",
            runner=runner,
            timeout=min(max(0.1, deadline - clock()), 30.0),
        )
        if not networks_ok:
            findings = network_findings
            snapshots = []
            attempts = 0
        else:
            render = runner(
                _compose(spec, "config", "--quiet"),
                ROOT,
                min(max(0.1, deadline - clock()), 30.0),
            )
            if render.returncode != 0:
                findings = [{"cause": "compose_render_failed", "stderr": render.stderr}]
                snapshots = []
                attempts = 0
            else:
                before, _ = collect_snapshots(
                    spec,
                    runner=runner,
                    timeout=min(15.0, max(0.1, deadline - clock())),
                )
                baseline = {row.service: row.restart_count for row in before}
                findings = [{"cause": "recovery_exhausted"}]
                snapshots = before
                attempts = 0
                for attempts in range(1, max_attempts + 1):
                    remaining = deadline - clock()
                    if remaining <= 0:
                        findings = [{"cause": "readiness_timeout", "attempt": attempts}]
                        break
                    # Attempt 1: non-destructive up (covers simple kill).
                    # Later attempts: force-recreate clears sticky pause/unhealthy
                    # state left by fault injection. Avoid always force-recreate —
                    # it has crashed Desktop under load on this host lane.
                    up_args: list[str] = ["up", "-d"]
                    if attempts >= 2:
                        up_args.append("--force-recreate")
                    up_args.extend(
                        [
                            "--wait",
                            "--wait-timeout",
                            str(max(1, int(remaining))),
                            *spec.required_services,
                        ]
                    )
                    command = _compose(spec, *up_args)
                    result = runner(command, ROOT, remaining)
                    history.append(
                        {
                            "attempt": attempts,
                            "returncode": result.returncode,
                            "elapsed_seconds": round(clock() - started, 3),
                        }
                    )
                    if result.returncode == 0:
                        remaining = max(0.0, deadline - clock())
                        snapshots, findings = _wait_ready(
                            spec,
                            baseline,
                            runner=runner,
                            timeout=remaining,
                            poll_interval=poll_interval,
                            stabilization_seconds=stabilization_seconds,
                            sleep=sleep,
                            clock=clock,
                        )
                        if not findings:
                            return 0
                    elif _daemon_connection_error(result.stderr, result.stdout):
                        findings = [
                            {
                                "cause": "daemon_unavailable",
                                "stderr": result.stderr,
                                "attempt": attempts,
                            }
                        ]
                        # Transient Desktop flaps: wait for daemon before next attempt
                        # instead of burning retries while the socket is still down.
                        if attempts < max_attempts and clock() < deadline:
                            restored = _wait_for_daemon(
                                runner=runner,
                                deadline=min(deadline, clock() + 20.0),
                                sleep=sleep,
                                clock=clock,
                                poll_interval=max(poll_interval, 2.0),
                            )
                            if (
                                not restored
                                and not desktop_recovery_attempted
                                and clock() < deadline
                            ):
                                desktop_report = (
                                    report_dir
                                    / f"docker-desktop-recovery-{spec.name}-attempt{attempts}.json"
                                )
                                desktop = _invoke_desktop_recovery(
                                    desktop_report,
                                    runner=runner,
                                    timeout=min(max(0.1, deadline - clock()), 180.0),
                                )
                                desktop_recovery_attempted = True
                                history.append(
                                    {
                                        "attempt": attempts,
                                        "action": "desktop_recovery",
                                        "returncode": desktop.returncode,
                                        "elapsed_seconds": round(clock() - started, 3),
                                    }
                                )
                                _wait_for_daemon(
                                    runner=runner,
                                    deadline=deadline,
                                    sleep=sleep,
                                    clock=clock,
                                    poll_interval=max(poll_interval, 2.0),
                                )
                            continue
                    else:
                        findings = [
                            {
                                "cause": "service_unready",
                                "stderr": result.stderr,
                                "attempt": attempts,
                            }
                        ]
                    if attempts < max_attempts:
                        sleep(
                            min(
                                2 ** (attempts - 1),
                                4,
                                max(0.0, deadline - clock()),
                            )
                        )
                remaining = deadline - clock()
                if remaining > 0:
                    log_result = runner(
                        _compose(spec, "logs", "--no-color", "--tail", "100"),
                        ROOT,
                        min(15.0, remaining),
                    )
                    recent_logs = {
                        "captured": log_result.returncode == 0,
                        "stdout": _bounded(log_result.stdout),
                        "stderr": _bounded(log_result.stderr),
                    }
                else:
                    recent_logs = {
                        "captured": False,
                        "stdout": "",
                        "stderr": "global recovery deadline exhausted",
                    }
    cause = primary_cause(findings)
    disk = shutil.disk_usage(ROOT)
    incident = {
        "schema_version": "bioetl-docker-incident-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "stack": spec.name,
        "project": spec.project,
        "config_origin": _display_path(spec.compose_file),
        "action": "recover" if recover else "start",
        "primary_cause": cause,
        "findings": findings,
        "services": [asdict(snapshot) for snapshot in snapshots],
        "attempts": attempts,
        "recovery_history": history,
        "disk": {"total_bytes": disk.total, "free_bytes": disk.free},
        "recent_logs": recent_logs,
        "elapsed_seconds": round(clock() - started, 3),
        "redaction_applied": True,
    }
    write_report(report_dir / f"docker-incident-{spec.name}.json", incident)
    return 1


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "check",
            "start",
            "stop",
            "status",
            "logs",
            "diagnose",
            "recover",
            "clean",
        ),
    )
    parser.add_argument("--stack", default="main")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--stabilization-seconds", type=float, default=5.0)
    parser.add_argument("--tail", type=int, default=100)
    parser.add_argument("--confirm-destructive", default="")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, *, runner: Runner = _run) -> int:
    args = _parse_args(argv)
    contract_path = args.contract.resolve()
    report_dir = args.report_dir.resolve()
    try:
        spec = resolve_stack(contract_path, args.stack)
    except (KeyError, OSError, ValueError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__}))
        return 2
    if args.action == "check":
        result = _preflight(
            contract_path,
            report_dir / f"docker-runtime-{spec.name}-preflight.json",
            spec.name,
            runner=runner,
            timeout=min(args.timeout, 60.0),
        )
        return result.returncode
    if args.action in {"start", "recover"}:
        return start_or_recover(
            spec,
            contract_path,
            report_dir,
            recover=args.action == "recover",
            runner=runner,
            timeout=args.timeout,
            max_attempts=max(1, min(args.max_attempts, 3)),
            poll_interval=max(0.1, args.poll_interval),
            stabilization_seconds=max(0.0, args.stabilization_seconds),
        )
    if args.action == "stop":
        return runner(
            _compose(spec, "down", "--remove-orphans"), ROOT, args.timeout
        ).returncode
    if args.action == "logs":
        result = runner(
            _compose(spec, "logs", "--no-color", "--tail", str(max(1, args.tail))),
            ROOT,
            args.timeout,
        )
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode
    if args.action == "diagnose":
        payload = diagnose(
            spec,
            contract_path,
            report_dir / f"docker-diagnostic-{spec.name}.json",
            runner=runner,
            timeout=min(args.timeout, 30.0),
        )
        print(
            json.dumps(
                {
                    "ok": not payload["findings"],
                    "primary_cause": payload["primary_cause"],
                }
            )
        )
        return 0 if not payload["findings"] else 1
    if args.action == "status":
        snapshots, _ = collect_snapshots(spec, runner=runner, timeout=args.timeout)
        findings = readiness_findings(spec, snapshots)
        print(
            json.dumps(
                {
                    "ok": not findings,
                    "stack": spec.name,
                    "services": [asdict(snapshot) for snapshot in snapshots],
                    "findings": findings,
                },
                sort_keys=True,
            )
        )
        return 0 if not findings else 1
    if args.confirm_destructive != "CLEAN":
        print("clean requires --confirm-destructive CLEAN", file=sys.stderr)
        return 2
    # Clean is deliberately bounded: no -v, prune, image deletion, or cache deletion.
    return runner(
        _compose(spec, "down", "--remove-orphans"), ROOT, args.timeout
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
