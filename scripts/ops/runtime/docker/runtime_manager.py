#!/usr/bin/env python3
"""Fail-closed lifecycle manager for optional BioETL Docker adjuncts.

Docker remains optional under ADR-010. The manager never deletes volumes,
never prunes host state, and reports success only after preflight, Compose
rendering, readiness, restart/OOM/image verification, and stabilization pass.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from scripts.ops.runtime.docker import docker_runtime_preflight as runtime_preflight

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONTRACT = ROOT / "configs/quality/docker_runtime_contracts.yaml"
DEFAULT_REPORT_DIR = ROOT / "reports/quality"
_SECRET_KEY = re.compile(r"(?:password|secret|token|credential|auth)", re.I)
_SECRET_VALUE = re.compile(r"(?:gh[pousr]_\w{12,}|Bearer\s+\S+)", re.I)
_SECRET_ASSIGNMENT = re.compile(
    r"\b(\w*(?:password|secret|token|credential|auth)\w*)"
    r"=([^\s,;]+)",
    re.I,
)
_URI_USERINFO = re.compile(r"(://)[^/@\s:]+:[^/@\s]+@")


@contextmanager
def _dashboard_runtime_environment(
    contract_path: Path,
) -> Iterator[dict[str, str]]:
    """Expose one scoped source identity to Compose without touching `.env`."""
    contract = _load_contract(contract_path)
    overrides = runtime_preflight.dashboard_source_environment(ROOT, contract)
    previous = {name: os.environ.get(name) for name in overrides}
    os.environ.update(overrides)
    try:
        yield overrides
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


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


def _image_digests_for(
    image_id: str,
    *,
    runner: Runner,
    timeout: float,
    observations: list[CommandResult],
) -> tuple[str, ...]:
    """Resolve repo digests for one image id, appending inspect observations."""
    if not image_id:
        return ()
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
    if image_inspection.returncode != 0 or not image_details:
        return ()
    return tuple(
        str(value) for value in (image_details[0].get("RepoDigests") or []) if value
    )


def _inspect_container_details(
    container_id: str,
    *,
    runner: Runner,
    timeout: float,
    observations: list[CommandResult],
) -> dict[str, Any] | None:
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
        return None
    return details[0]


def _snapshot_from_ps_row(
    row: Mapping[str, Any],
    *,
    runner: Runner,
    timeout: float,
    observations: list[CommandResult],
) -> ServiceSnapshot | None:
    """Inspect one compose ps row into a ServiceSnapshot when identity is complete."""
    container_id = str(row.get("ID") or row.get("Id") or "")
    service = str(row.get("Service") or row.get("Name") or "")
    if not container_id or not service:
        return None
    item = _inspect_container_details(
        container_id, runner=runner, timeout=timeout, observations=observations
    )
    if item is None:
        return None
    state = item.get("State") or {}
    config = item.get("Config") or {}
    image = str(item.get("Image") or config.get("Image") or row.get("Image") or "")
    image_id = str(item.get("ImageID") or image)
    image_digests = _image_digests_for(
        image_id, runner=runner, timeout=timeout, observations=observations
    )
    health = (state.get("Health") or {}).get("Status", "none")
    return ServiceSnapshot(
        service=service,
        container_id=container_id[:12],
        state=str(state.get("Status", "unknown")).lower(),
        health=str(health).lower(),
        restart_count=int(item.get("RestartCount") or 0),
        oom_killed=bool(state.get("OOMKilled", False)),
        image=image,
        image_digests=image_digests,
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
        snapshot = _snapshot_from_ps_row(
            row, runner=runner, timeout=timeout, observations=observations
        )
        if snapshot is not None:
            snapshots.append(snapshot)
    return snapshots, observations


def _image_matches_expected(snapshot: ServiceSnapshot, expected: str | None) -> bool:
    """Return whether the snapshot image identity matches the expected reference."""
    if not expected or not snapshot.image:
        return True
    expected_digest = _digest_from_image(expected)
    observed_images = (snapshot.image, *snapshot.image_digests)
    if expected_digest:
        return any(
            expected_digest == _digest_from_image(image) for image in observed_images
        )
    return expected in observed_images


def _service_readiness_findings(
    *,
    service: str,
    snapshot: ServiceSnapshot | None,
    baseline: Mapping[str, int],
    baseline_provided: bool,
    expected_image: str | None,
) -> list[dict[str, Any]]:
    """Compute readiness findings for one required service."""
    if snapshot is None:
        return [{"cause": "service_missing", "service": service}]
    findings: list[dict[str, Any]] = []
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
    if not _image_matches_expected(snapshot, expected_image):
        findings.append(
            {
                "cause": "image_identity_drift",
                "service": service,
                "expected": expected_image,
                "actual": snapshot.image,
            }
        )
    return findings


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
        findings.extend(
            _service_readiness_findings(
                service=service,
                snapshot=by_service.get(service),
                baseline=baseline,
                baseline_provided=baseline_provided,
                expected_image=spec.expected_images.get(service),
            )
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
    "dashboard_source_drift": 3,
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


def _create_shared_network(
    name: str,
    owner: str,
    inspection: CommandResult,
    *,
    runner: Runner,
    timeout: float,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
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
    observation = {
        "name": name,
        "owner": owner,
        "created": created,
        "inspect": asdict(inspection),
        "create": asdict(creation),
    }
    finding = None
    if not created:
        finding = {
            "cause": "network_owner_drift",
            "network": name,
            "owner": owner,
        }
    return observation, finding


def _verify_shared_network_owner(
    name: str,
    owner: str,
    inspection: CommandResult,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    observed_owner = inspection.stdout.strip()
    owner_ok = observed_owner == owner
    observation = {
        "name": name,
        "owner": owner,
        "observed_owner": observed_owner or None,
        "created": False,
        "owner_ok": owner_ok,
        "inspect": asdict(inspection),
    }
    finding = None
    if not owner_ok:
        finding = {
            "cause": "network_owner_drift",
            "network": name,
            "expected_owner": owner,
            "observed_owner": observed_owner,
        }
    return observation, finding


def _ensure_one_shared_network(
    raw: Mapping[str, Any],
    *,
    runner: Runner,
    timeout: float,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Ensure one contracted shared network exists with the expected owner label."""
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
    if inspection.returncode != 0:
        return _create_shared_network(
            name, owner, inspection, runner=runner, timeout=timeout
        )
    return _verify_shared_network_owner(name, owner, inspection)


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
    shared_networks = contract.get("shared_networks", {})
    network_values = (
        shared_networks.values() if isinstance(shared_networks, Mapping) else ()
    )
    networks = []
    for raw in network_values:
        if not isinstance(raw, Mapping):
            continue
        consumers = raw.get("consumers", [])
        if isinstance(consumers, list) and spec.name in consumers:
            networks.append(raw)
    observations: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for raw in networks:
        observation, finding = _ensure_one_shared_network(
            raw, runner=runner, timeout=timeout
        )
        observations.append(observation)
        if finding is not None:
            findings.append(finding)
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


def _stabilize_ready_snapshots(
    spec: StackSpec,
    baseline: Mapping[str, int],
    *,
    runner: Runner,
    deadline: float,
    stabilization_seconds: float,
    sleep: Sleeper,
    clock: Clock,
    last_snapshots: list[ServiceSnapshot],
) -> tuple[list[ServiceSnapshot], list[dict[str, Any]]]:
    remaining = deadline - clock()
    if remaining <= 0:
        return last_snapshots, [{"cause": "readiness_timeout"}]
    sleep(min(stabilization_seconds, remaining))
    remaining = deadline - clock()
    if remaining <= 0:
        return last_snapshots, [{"cause": "readiness_timeout"}]
    last_snapshots, _ = collect_snapshots(
        spec, runner=runner, timeout=min(15.0, remaining)
    )
    return last_snapshots, readiness_findings(spec, last_snapshots, baseline)


def _poll_ready_once(
    spec: StackSpec,
    baseline: Mapping[str, int],
    *,
    runner: Runner,
    deadline: float,
    stabilization_seconds: float,
    sleep: Sleeper,
    clock: Clock,
) -> tuple[list[ServiceSnapshot], list[dict[str, Any]], bool]:
    """Return (snapshots, findings, ready). ready True means caller should return."""
    remaining = deadline - clock()
    if remaining <= 0:
        return [], [{"cause": "readiness_timeout"}], False
    last_snapshots, _ = collect_snapshots(
        spec, runner=runner, timeout=min(15.0, remaining)
    )
    last_findings = readiness_findings(spec, last_snapshots, baseline)
    if last_findings:
        return last_snapshots, last_findings, False
    if stabilization_seconds > 0:
        last_snapshots, last_findings = _stabilize_ready_snapshots(
            spec,
            baseline,
            runner=runner,
            deadline=deadline,
            stabilization_seconds=stabilization_seconds,
            sleep=sleep,
            clock=clock,
            last_snapshots=last_snapshots,
        )
    if not last_findings:
        return last_snapshots, [], True
    return last_snapshots, last_findings, False


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
        last_snapshots, last_findings, ready = _poll_ready_once(
            spec,
            baseline,
            runner=runner,
            deadline=deadline,
            stabilization_seconds=stabilization_seconds,
            sleep=sleep,
            clock=clock,
        )
        if ready:
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
        "DASHBOARD_SOURCE_MOUNT",
        "DASHBOARD_SOURCE_IDENTITY",
        # Windows Docker Desktop requires host drive-letter binds; preflight still
        # flags them as discouraged, but absolute bind env + force-recreate clears
        # the empty Desktop virtual-bind class of Browse Recent Runs failures.
        "MOUNT_ORIGIN",
    }
)
_CROSS_STACK_IGNORABLE_PREFLIGHT_CODES = frozenset(
    {
        "PROJECT_ORIGIN",
        "MOUNT_ORIGIN",
        "F003",
        "HOST_PORT_COLLISION",
        "CAPACITY_DOCKER_ROOT",
    }
)
_DAEMON_UNAVAILABLE_PREFLIGHT_CODES = frozenset(
    {
        "CAPACITY_DOCKER_ROOT",
        "DAEMON_UNAVAILABLE",
        "DOCKER_DAEMON",
    }
)


def _preflight_errors_are_recoverable(
    preflight_path: Path, *, stack: str | None = None
) -> bool:
    """Allow start/recover when remaining errors can be cleared by compose up.

    Recoverable classes include live container health/restart/OOM and dashboard
    producer bind/identity drift (fixed by absolute bind env + recreate).
    Cross-stack PROJECT_ORIGIN / MOUNT_ORIGIN / port inventory noise does not
    block starting the selected stack.

    NOSONAR - S3776: complexity 29 exceeds 15; extraction would obscure error classification logic
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
    for finding in errors:
        code = str(finding.get("code") or "")
        evidence = finding.get("evidence") if isinstance(finding, Mapping) else None
        finding_stack: str | None = None
        if isinstance(evidence, Mapping):
            raw_stack = evidence.get("stack")
            if isinstance(raw_stack, str) and raw_stack.strip():
                finding_stack = raw_stack.strip()
            else:
                owner = evidence.get("actual_owner")
                if isinstance(owner, str) and "/" in owner:
                    finding_stack = owner.split("/", 1)[0]
        if (
            stack
            and finding_stack
            and finding_stack != stack
            and code in _CROSS_STACK_IGNORABLE_PREFLIGHT_CODES
        ):
            continue
        if code in _RECOVERABLE_PREFLIGHT_CODES:
            continue
        if code in _CROSS_STACK_IGNORABLE_PREFLIGHT_CODES and finding_stack is None:
            continue
        return False
    return True


def _preflight_has_dashboard_source_drift(preflight_path: Path) -> bool:
    """True when preflight reports dashboard producer bind/identity drift."""
    try:
        payload = json.loads(preflight_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    findings = payload.get("findings") or []
    if not isinstance(findings, list):
        return False
    return any(
        isinstance(finding, Mapping)
        and finding.get("severity") == "error"
        and str(finding.get("code") or "")
        in {"DASHBOARD_SOURCE_MOUNT", "DASHBOARD_SOURCE_IDENTITY"}
        for finding in findings
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
        (
            candidate
            for candidate in powershell_candidates
            if shutil.which(candidate) or Path(candidate).is_file()
        ),
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
        converted_script = runner(
            ["wslpath", "-w", str(script)], ROOT, min(10.0, timeout)
        )
        converted_report = runner(
            ["wslpath", "-w", str(report_path)], ROOT, min(10.0, timeout)
        )
        if converted_script.returncode == 0 and converted_report.returncode == 0:
            script_arg = converted_script.stdout.strip()
            report_arg = converted_report.stdout.strip()
    internal = (
        max(10, min(175, int(timeout) - 5)) if timeout > 15 else max(5, int(timeout))
    )
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


def _maybe_desktop_recovery_before_preflight(
    *,
    recover: bool,
    preflight: CommandResult,
    preflight_path: Path,
    spec: StackSpec,
    contract_path: Path,
    report_dir: Path,
    history: list[dict[str, Any]],
    runner: Runner,
    deadline: float,
    started: float,
    poll_interval: float,
    sleep: Sleeper,
    clock: Clock,
) -> tuple[CommandResult, bool]:
    """RF-006: optional Desktop recovery when daemon is unavailable at preflight."""
    if not (
        recover
        and preflight.returncode != 0
        and _preflight_indicates_daemon_unavailable(preflight_path)
        and clock() < deadline
    ):
        return preflight, False
    desktop_report = report_dir / f"docker-desktop-recovery-{spec.name}.json"
    desktop = _invoke_desktop_recovery(
        desktop_report,
        runner=runner,
        timeout=min(max(0.1, deadline - clock()), 180.0),
    )
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
    refreshed = _preflight(
        contract_path,
        preflight_path,
        spec.name,
        runner=runner,
        timeout=min(max(0.1, deadline - clock()), 60.0),
    )
    return refreshed, True


def _capture_recent_logs(
    *,
    spec: StackSpec,
    runner: Runner,
    deadline: float,
    clock: Clock,
) -> dict[str, Any]:
    """Capture a bounded compose logs snippet when recovery time remains."""
    remaining = deadline - clock()
    if remaining <= 0:
        return {
            "captured": False,
            "stdout": "",
            "stderr": "global recovery deadline exhausted",
        }
    log_result = runner(
        _compose(spec, "logs", "--no-color", "--tail", "100"),
        ROOT,
        min(15.0, remaining),
    )
    return {
        "captured": log_result.returncode == 0,
        "stdout": _bounded(log_result.stdout),
        "stderr": _bounded(log_result.stderr),
    }


def _handle_daemon_error_during_attempt(
    *,
    result: CommandResult,
    attempts: int,
    max_attempts: int,
    desktop_recovery_attempted: bool,
    spec: StackSpec,
    report_dir: Path,
    history: list[dict[str, Any]],
    runner: Runner,
    deadline: float,
    started: float,
    poll_interval: float,
    sleep: Sleeper,
    clock: Clock,
) -> tuple[list[dict[str, Any]], bool]:
    """Wait/recover after a daemon socket flap during an up attempt."""
    findings = [
        {
            "cause": "daemon_unavailable",
            "stderr": result.stderr,
            "attempt": attempts,
        }
    ]
    recovered = desktop_recovery_attempted
    if attempts >= max_attempts or clock() >= deadline:
        return findings, recovered
    restored = _wait_for_daemon(
        runner=runner,
        deadline=min(deadline, clock() + 20.0),
        sleep=sleep,
        clock=clock,
        poll_interval=max(poll_interval, 2.0),
    )
    if restored or recovered or clock() >= deadline:
        return findings, recovered
    desktop_report = (
        report_dir / f"docker-desktop-recovery-{spec.name}-attempt{attempts}.json"
    )
    desktop = _invoke_desktop_recovery(
        desktop_report,
        runner=runner,
        timeout=min(max(0.1, deadline - clock()), 180.0),
    )
    recovered = True
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
    return findings, recovered


def _compose_up_wait_args(
    spec: StackSpec,
    *,
    attempts: int,
    remaining: float,
    force_recreate: bool = False,
) -> list[str]:
    # Attempt 1: non-destructive up (covers simple kill).
    # Later attempts or dashboard bind drift: force-recreate clears sticky empty binds.
    up_args: list[str] = ["up", "-d"]
    if force_recreate or attempts >= 2:
        up_args.append("--force-recreate")
    up_args.extend(
        [
            "--wait",
            "--wait-timeout",
            str(max(1, int(remaining))),
            *spec.required_services,
        ]
    )
    return up_args


@dataclass(frozen=True, slots=True)
class _RecoveryTimingContext:
    """Packed recovery timing/runtime handles (python:S107)."""

    deadline: float
    started: float
    poll_interval: float
    stabilization_seconds: float
    sleep: Sleeper
    clock: Clock
    runner: Runner
    force_recreate: bool = False


def _evaluate_up_attempt(
    *,
    result: CommandResult,
    attempts: int,
    max_attempts: int,
    recovered: bool,
    spec: StackSpec,
    baseline: Mapping[str, int],
    report_dir: Path,
    history: list[dict[str, Any]],
    timing: _RecoveryTimingContext,
) -> tuple[list[ServiceSnapshot] | None, list[dict[str, Any]], bool, bool]:
    """Returns (snapshots|None, findings, recovered, succeeded)."""
    if result.returncode == 0:
        snapshots, findings = _wait_ready(
            spec,
            baseline,
            runner=timing.runner,
            timeout=max(0.0, timing.deadline - timing.clock()),
            poll_interval=timing.poll_interval,
            stabilization_seconds=timing.stabilization_seconds,
            sleep=timing.sleep,
            clock=timing.clock,
        )
        return snapshots, findings, recovered, not findings
    if _daemon_connection_error(result.stderr, result.stdout):
        findings, recovered = _handle_daemon_error_during_attempt(
            result=result,
            attempts=attempts,
            max_attempts=max_attempts,
            desktop_recovery_attempted=recovered,
            spec=spec,
            report_dir=report_dir,
            history=history,
            runner=timing.runner,
            deadline=timing.deadline,
            started=timing.started,
            poll_interval=timing.poll_interval,
            sleep=timing.sleep,
            clock=timing.clock,
        )
        return None, findings, recovered, False
    findings = [
        {
            "cause": "service_unready",
            "stderr": result.stderr,
            "attempt": attempts,
        }
    ]
    return None, findings, recovered, False


def _run_recovery_attempts(
    *,
    spec: StackSpec,
    baseline: Mapping[str, int],
    initial_snapshots: list[ServiceSnapshot],
    report_dir: Path,
    history: list[dict[str, Any]],
    max_attempts: int,
    timing: _RecoveryTimingContext,
    desktop_recovery_attempted: bool,
) -> tuple[list[ServiceSnapshot], list[dict[str, Any]], int, bool, bool]:
    """Execute bounded compose up/wait recovery attempts.

    Returns snapshots, findings, attempt count, desktop-recovery flag, and
    whether readiness succeeded (caller should return 0 immediately).
    """
    findings: list[dict[str, Any]] = [{"cause": "recovery_exhausted"}]
    snapshots: list[ServiceSnapshot] = list(initial_snapshots)
    attempts = 0
    recovered = desktop_recovery_attempted
    for attempts in range(1, max_attempts + 1):
        remaining = timing.deadline - timing.clock()
        if remaining <= 0:
            findings = [{"cause": "readiness_timeout", "attempt": attempts}]
            break
        up_args = _compose_up_wait_args(
            spec,
            attempts=attempts,
            remaining=remaining,
            force_recreate=timing.force_recreate,
        )
        result = timing.runner(_compose(spec, *up_args), ROOT, remaining)
        history.append(
            {
                "attempt": attempts,
                "returncode": result.returncode,
                "elapsed_seconds": round(timing.clock() - timing.started, 3),
            }
        )
        maybe_snapshots, findings, recovered, succeeded = _evaluate_up_attempt(
            result=result,
            attempts=attempts,
            max_attempts=max_attempts,
            recovered=recovered,
            spec=spec,
            baseline=baseline,
            report_dir=report_dir,
            history=history,
            timing=timing,
        )
        if maybe_snapshots is not None:
            snapshots = maybe_snapshots
        if succeeded:
            return snapshots, findings, attempts, recovered, True
        if attempts < max_attempts:
            timing.sleep(
                min(
                    2 ** (attempts - 1),
                    4,
                    max(0.0, timing.deadline - timing.clock()),
                )
            )
    return snapshots, findings, attempts, recovered, False


def _bootstrap_recovery_surface(
    *,
    spec: StackSpec,
    contract_path: Path,
    report_dir: Path,
    preflight: CommandResult,
    preflight_path: Path,
    desktop_recovery_attempted: bool,
    runner: Runner,
    deadline: float,
    clock: Clock,
) -> tuple[list[ServiceSnapshot], list[dict[str, Any]], int, Mapping[str, int] | None]:
    """Validate preflight/networks/render and collect a restart baseline.

    Returns snapshots, findings, attempts, and baseline when recovery may proceed.
    baseline is None when the surface failed closed before attempts.
    """
    # Both start and recover may proceed when the only preflight errors are live
    # container health/restart/OOM — those are exactly what up --wait must clear.
    if preflight.returncode != 0 and not _preflight_errors_are_recoverable(
        preflight_path, stack=spec.name
    ):
        findings: list[dict[str, Any]] = [
            {"cause": "preflight_failed", "stderr": preflight.stderr}
        ]
        if desktop_recovery_attempted:
            findings.append({"cause": "daemon_unavailable", "desktop_recovery": True})
        return [], findings, 0, None
    networks_ok, network_findings = ensure_shared_networks(
        spec,
        contract_path,
        report_dir / f"docker-runtime-{spec.name}-networks.json",
        runner=runner,
        timeout=min(max(0.1, deadline - clock()), 30.0),
    )
    if not networks_ok:
        return [], network_findings, 0, None
    render = runner(
        _compose(spec, "config", "--quiet"),
        ROOT,
        min(max(0.1, deadline - clock()), 30.0),
    )
    if render.returncode != 0:
        return (
            [],
            [{"cause": "compose_render_failed", "stderr": render.stderr}],
            0,
            None,
        )
    before, _ = collect_snapshots(
        spec,
        runner=runner,
        timeout=min(15.0, max(0.1, deadline - clock())),
    )
    baseline = {row.service: row.restart_count for row in before}
    return before, [{"cause": "recovery_exhausted"}], 0, baseline


def _post_start_report_bind_gate(*, spec: StackSpec, report_dir: Path) -> int:
    """Fail closed when main stack Ops HTTP cannot see host run-reports.

    Prevents healthy bioetl containers with empty Desktop bind caches from being
    treated as a successful start (Browse Recent Runs would stay empty).
    """
    if spec.name != "main":
        return 0
    # Unit tests inject mock runners and do not stand up Ops HTTP; skip the
    # live bind gate so recovery logic remains the subject under test (#8264).
    if os.environ.get("BIOETL_TEST_MODE", "").strip().lower() in {"1", "true", "yes"}:
        return 0
    # pytest sets PYTEST_CURRENT_TEST; keep live gate for real stacks only.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return 0
    try:
        from scripts.ops.runtime.docker import verify_report_bind as bind_verify
    except ImportError:
        return 0
    pipeline = os.environ.get("BIOETL_VERIFY_PIPELINE", "chembl_assay").strip() or None
    rc = bind_verify.verify(
        repo=ROOT,
        ops_url=os.environ.get("BIOETL_OPS_HTTP_URL", bind_verify.DEFAULT_OPS_URL),
        container=os.environ.get(
            "BIOETL_CONTAINER_NAME", bind_verify.DEFAULT_CONTAINER
        ),
        pipeline=pipeline,
        require_ops=True,
    )
    if rc == 0:
        return 0
    incident = {
        "schema_version": "bioetl-docker-incident-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "stack": spec.name,
        "project": spec.project,
        "action": "post_start_report_bind_gate",
        "primary_cause": "report_bind_mismatch",
        "findings": [
            {
                "cause": "report_bind_mismatch",
                "message": (
                    "bioetl is up but host/ops report-root bind verification failed; "
                    "Browse Recent Runs would stay empty. Re-run start from the "
                    "canonical checkout or set BIOETL_DASHBOARD_REPORT_ROOT to the "
                    "absolute reports/ path."
                ),
            }
        ],
    }
    write_report(report_dir / f"docker-incident-{spec.name}.json", incident)
    return 1


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
    preflight_path = report_dir / f"docker-runtime-{spec.name}-preflight.json"
    preflight = _preflight(
        contract_path,
        preflight_path,
        spec.name,
        runner=runner,
        timeout=min(max(0.1, deadline - clock()), 60.0),
    )
    preflight, desktop_recovery_attempted = _maybe_desktop_recovery_before_preflight(
        recover=recover,
        preflight=preflight,
        preflight_path=preflight_path,
        spec=spec,
        contract_path=contract_path,
        report_dir=report_dir,
        history=history,
        runner=runner,
        deadline=deadline,
        started=started,
        poll_interval=poll_interval,
        sleep=sleep,
        clock=clock,
    )
    snapshots, findings, attempts, baseline = _bootstrap_recovery_surface(
        spec=spec,
        contract_path=contract_path,
        report_dir=report_dir,
        preflight=preflight,
        preflight_path=preflight_path,
        desktop_recovery_attempted=desktop_recovery_attempted,
        runner=runner,
        deadline=deadline,
        clock=clock,
    )
    if baseline is not None:
        (
            snapshots,
            findings,
            attempts,
            _desktop_recovery_attempted,
            succeeded,
        ) = _run_recovery_attempts(
            spec=spec,
            baseline=baseline,
            initial_snapshots=snapshots,
            report_dir=report_dir,
            history=history,
            max_attempts=max_attempts,
            timing=_RecoveryTimingContext(
                deadline=deadline,
                started=started,
                poll_interval=poll_interval,
                stabilization_seconds=stabilization_seconds,
                sleep=sleep,
                clock=clock,
                runner=runner,
                force_recreate=(
                    _preflight_has_dashboard_source_drift(preflight_path)
                    or spec.name == "main"
                ),
            ),
            desktop_recovery_attempted=desktop_recovery_attempted,
        )
        if succeeded:
            verify_rc = _post_start_report_bind_gate(spec=spec, report_dir=report_dir)
            if verify_rc != 0:
                return verify_rc
            return 0
        recent_logs = _capture_recent_logs(
            spec=spec, runner=runner, deadline=deadline, clock=clock
        )
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


_STATUS_ORIGIN_CODES = frozenset(
    {
        "DASHBOARD_SOURCE_IDENTITY",
        "DASHBOARD_SOURCE_MOUNT",
        "MOUNT_ORIGIN",
        "PROJECT_ORIGIN",
    }
)


def _status_origin_findings(
    preflight_path: Path,
    preflight: CommandResult,
) -> list[dict[str, Any]]:
    """Extract only origin/data-plane failures for the lightweight status view."""
    try:
        payload = json.loads(preflight_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        if preflight.returncode == 0:
            return []
        return [{"cause": "preflight_failed", "stderr": preflight.stderr}]
    raw_findings = payload.get("findings") or []
    return [
        {
            "cause": "dashboard_source_drift",
            "code": finding.get("code"),
            "message": finding.get("message"),
            "evidence": finding.get("evidence"),
        }
        for finding in raw_findings
        if isinstance(finding, Mapping)
        and finding.get("severity") == "error"
        and str(finding.get("code") or "") in _STATUS_ORIGIN_CODES
    ]


def _dispatch_action(
    args: argparse.Namespace,
    *,
    spec: StackSpec,
    contract_path: Path,
    report_dir: Path,
    runner: Runner,
) -> int:
    """Dispatch one lifecycle action after source environment activation."""
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
        preflight_path = report_dir / f"docker-runtime-{spec.name}-preflight.json"
        preflight = _preflight(
            contract_path,
            preflight_path,
            spec.name,
            runner=runner,
            timeout=min(args.timeout, 60.0),
        )
        snapshots, _ = collect_snapshots(spec, runner=runner, timeout=args.timeout)
        findings = readiness_findings(spec, snapshots)
        findings.extend(_status_origin_findings(preflight_path, preflight))
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


def main(argv: Sequence[str] | None = None, *, runner: Runner = _run) -> int:
    args = _parse_args(argv)
    contract_path = args.contract.resolve()
    report_dir = args.report_dir.resolve()
    try:
        spec = resolve_stack(contract_path, args.stack)
        with _dashboard_runtime_environment(contract_path):
            return _dispatch_action(
                args,
                spec=spec,
                contract_path=contract_path,
                report_dir=report_dir,
                runner=runner,
            )
    except (KeyError, OSError, ValueError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
