#!/usr/bin/env python3
"""Emit bounded Docker stability reports and Prometheus exposition.

The probe runs on the host and uses the Docker CLI.  It never changes Docker
state and never requires the Docker socket to be mounted into a container.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .runtime_manager import (
        DEFAULT_CONTRACT,
        ROOT,
        CommandResult,
        ServiceSnapshot,
        StackSpec,
        _load_compose,
        _load_contract,
        _redact,
        _run,
        collect_snapshots,
        primary_cause,
        readiness_findings,
        resolve_stack,
        write_report,
    )
except ImportError:  # pragma: no cover - direct script execution
    from scripts.ops.runtime.docker.runtime_manager import (
        DEFAULT_CONTRACT,
        ROOT,
        CommandResult,
        ServiceSnapshot,
        StackSpec,
        _load_compose,
        _load_contract,
        _redact,
        _run,
        collect_snapshots,
        primary_cause,
        readiness_findings,
        resolve_stack,
        write_report,
    )

DEFAULT_REPORT_DIR = ROOT / "reports/quality"
_PERCENT = re.compile(r"^\s*(\d+(?:\.\d+)?)%\s*$")
_ALLOWED_CAUSES = {
    "daemon_unavailable",
    "disk_reserve_low",
    "image_identity_drift",
    "oom_killed",
    "project_origin_drift",
    "recovery_objective_breach",
    "resource_pressure",
    "service_missing",
    "service_unready",
    "unexpected_restart",
    "unresolved_incident",
}
_CAUSE_ENUM = {
    cause: index
    for index, cause in enumerate(
        (
            "daemon_unavailable",
            "disk_reserve_low",
            "image_identity_drift",
            "oom_killed",
            "project_origin_drift",
            "recovery_objective_breach",
            "resource_pressure",
            "service_missing",
            "service_unready",
            "unexpected_restart",
            "unresolved_incident",
        ),
        start=1,
    )
}

Runner = Callable[[Sequence[str], Path, float], CommandResult]
DiskUsage = Callable[[Path], Any]


def _json_rows(text: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        value = json.loads(stripped)
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
    if isinstance(value, dict):
        return [value]
    return [row for row in value if isinstance(row, dict)]


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _percent(value: Any) -> float:
    match = _PERCENT.match(str(value))
    return float(match.group(1)) / 100.0 if match else 0.0


def _project_origin_findings(
    spec: StackSpec, compose_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    expected = str(spec.compose_file.resolve())
    matches = [
        row
        for row in compose_rows
        if str(row.get("Name") or row.get("name") or "") == spec.project
    ]
    if not matches:
        return []
    origins: set[str] = set()
    for row in matches:
        raw = row.get("ConfigFiles") or row.get("configFiles") or ""
        if isinstance(raw, list):
            origins.update(str(item) for item in raw)
        else:
            origins.update(item.strip() for item in str(raw).split(",") if item.strip())
    if (
        expected in {str(Path(origin).resolve()) for origin in origins}
        and len(matches) == 1
    ):
        return []
    return [
        {
            "cause": "project_origin_drift",
            "project": spec.project,
            "expected": expected,
            "observed": sorted(origins),
        }
    ]


def _service_resource_ratios(
    *,
    service: str,
    row: Mapping[str, Any],
    service_limits: Mapping[str, float],
) -> dict[str, Any]:
    """Compute limit ratios for one container stats row."""
    memory_ratio = _percent(row.get("MemPerc", "0%"))
    cpu_usage = _percent(row.get("CPUPerc", "0%"))
    pids = int(row.get("PIDs") or 0)
    cpu_limit = float(service_limits.get("cpus") or 0.0)
    pids_limit = float(service_limits.get("pids_limit") or 0.0)
    cpu_ratio = cpu_usage / cpu_limit if cpu_limit else 0.0
    pids_ratio = pids / pids_limit if pids_limit else 0.0
    return {
        "service": service,
        "memory_limit_ratio": memory_ratio,
        "cpu_limit_ratio": cpu_ratio,
        "pids_limit_ratio": pids_ratio,
        "pids": pids,
    }


def _pressure_findings_for_resource(
    resource: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Emit resource_pressure findings for ratios at or above the 0.8 threshold."""
    findings: list[dict[str, Any]] = []
    service = resource["service"]
    for resource_name, key in (
        ("memory", "memory_limit_ratio"),
        ("cpu", "cpu_limit_ratio"),
        ("pids", "pids_limit_ratio"),
    ):
        ratio = float(resource[key])
        if ratio < 0.8:
            continue
        findings.append(
            {
                "cause": "resource_pressure",
                "service": service,
                "resource": resource_name,
                "ratio": ratio,
            }
        )
    return findings


def _resource_findings(
    stats_rows: Sequence[Mapping[str, Any]],
    snapshots: Sequence[ServiceSnapshot],
    limits: Mapping[str, Mapping[str, float]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    known = {item.container_id: item.service for item in snapshots}
    resources: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for row in stats_rows:
        container_id = str(row.get("ID") or row.get("Container") or "")[:12]
        service = known.get(container_id)
        if not service:
            continue
        resource = _service_resource_ratios(
            service=service,
            row=row,
            service_limits=limits.get(service, {}),
        )
        resources.append(resource)
        findings.extend(_pressure_findings_for_resource(resource))
    return resources, findings


def _compose_service_limits(compose: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    return {
        str(service): {
            "cpus": float(config.get("cpus") or 0.0),
            "pids_limit": float(config.get("pids_limit") or 0.0),
        }
        for service, config in compose.get("services", {}).items()
        if isinstance(config, Mapping)
    }


def _collect_live_probe_observations(
    *,
    spec: StackSpec,
    runner: Runner,
    timeout: float,
    limits: Mapping[str, Mapping[str, float]],
    baseline: Mapping[str, int] | None,
    observations: list[CommandResult],
) -> tuple[
    list[ServiceSnapshot],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Collect snapshots, compose rows, resources, and findings while daemon is up."""
    snapshots, snapshot_commands = collect_snapshots(
        spec, runner=runner, timeout=timeout
    )
    observations.extend(snapshot_commands)
    findings = list(readiness_findings(spec, snapshots, baseline))

    compose_ls = runner(
        ["docker", "compose", "ls", "--all", "--format", "json"],
        ROOT,
        timeout,
    )
    observations.append(compose_ls)
    compose_rows = _json_rows(compose_ls.stdout)
    if compose_ls.returncode == 0:
        findings.extend(_project_origin_findings(spec, compose_rows))

    stats = runner(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
        ROOT,
        timeout,
    )
    observations.append(stats)
    resources: list[dict[str, Any]] = []
    if stats.returncode == 0:
        resources, pressure = _resource_findings(
            _json_rows(stats.stdout), snapshots, limits
        )
        findings.extend(pressure)
    return snapshots, findings, compose_rows, resources


def _disk_and_incident_findings(
    *,
    contract: Mapping[str, Any],
    disk: Any,
    incident: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Capacity and incident-recovery findings for one probe report."""
    findings: list[dict[str, Any]] = []
    reserve_bytes, recovery_attempts, recovery_seconds, recovery_limit = (
        _capacity_recovery_values(contract, incident)
    )
    if disk.free < reserve_bytes:
        findings.append(
            {
                "cause": "disk_reserve_low",
                "free_bytes": disk.free,
                "required_free_bytes": reserve_bytes,
            }
        )
    if recovery_attempts > 3 or recovery_seconds > recovery_limit:
        findings.append(
            {
                "cause": "recovery_objective_breach",
                "attempts": recovery_attempts,
                "elapsed_seconds": recovery_seconds,
            }
        )
    if incident.get("primary_cause"):
        findings.append(
            {
                "cause": "unresolved_incident",
                "incident_cause": str(incident["primary_cause"]),
            }
        )
    return findings


def _capacity_recovery_values(
    contract: Mapping[str, Any],
    incident: Mapping[str, Any],
) -> tuple[int, int, float, float]:
    """Resolve capacity and recovery values shared by findings and SLO output."""
    reserve_gib = int(contract.get("capacity", {}).get("minimum_free_disk_gib", 4))
    return (
        reserve_gib * 1024**3,
        int(incident.get("attempts") or 0),
        float(incident.get("elapsed_seconds") or 0.0),
        float(contract.get("stability_slo", {}).get("recovery_seconds_p99", 180)),
    )


def build_report(
    spec: StackSpec,
    contract_path: Path,
    *,
    baseline: Mapping[str, int] | None = None,
    incident: Mapping[str, Any] | None = None,
    runner: Runner = _run,
    disk_usage: DiskUsage = shutil.disk_usage,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Collect one read-only stability sample for a contracted stack."""

    started = time.monotonic()
    contract = _load_contract(contract_path)
    compose = _load_compose(spec.compose_file)
    limits = _compose_service_limits(compose)
    observations: list[CommandResult] = []
    info = runner(["docker", "info", "--format", "{{json .}}"], ROOT, timeout)
    observations.append(info)

    snapshots: list[ServiceSnapshot] = []
    findings: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    if info.returncode != 0:
        findings.append({"cause": "daemon_unavailable"})
    else:
        snapshots, live_findings, _compose_rows, resources = (
            _collect_live_probe_observations(
                spec=spec,
                runner=runner,
                timeout=timeout,
                limits=limits,
                baseline=baseline,
                observations=observations,
            )
        )
        findings.extend(live_findings)

    disk = disk_usage(ROOT)
    incident = dict(incident or {})
    reserve_bytes, recovery_attempts, recovery_seconds, recovery_limit = (
        _capacity_recovery_values(contract, incident)
    )
    findings.extend(
        _disk_and_incident_findings(
            contract=contract,
            disk=disk,
            incident=incident,
        )
    )

    cause = primary_cause(findings) if findings else None
    if findings and cause not in _ALLOWED_CAUSES:
        cause = "unresolved_incident"
    restart_delta = sum(
        int(item.get("restart_delta") or 0)
        for item in findings
        if item.get("cause") == "unexpected_restart"
    )
    payload = {
        "schema_version": "docker-runtime-signals-v2",
        "generated_at": datetime.now(UTC).isoformat(),
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
        "stack": spec.name,
        "project": spec.project,
        "config_origin": str(spec.compose_file),
        "signals": findings,
        "primary_cause": cause,
        "services": [{**asdict(item), "ready": item.ready} for item in snapshots],
        "resources": resources,
        "slo": {
            "daemon_available": info.returncode == 0,
            "required_services_ready": not any(
                item.get("cause") in {"service_missing", "service_unready"}
                for item in findings
            ),
            "restart_count_delta": restart_delta,
            "oom_kills": sum(item.oom_killed for item in snapshots),
            "resource_peak_below_80_percent": not any(
                item.get("cause") == "resource_pressure" for item in findings
            ),
            "disk_reserve_bytes": disk.free,
            "disk_reserve_ok": disk.free >= reserve_bytes,
            "project_origin_drift": any(
                item.get("cause") == "project_origin_drift" for item in findings
            ),
            "image_identity_drift": any(
                item.get("cause") == "image_identity_drift" for item in findings
            ),
            "recovery_attempt_count": recovery_attempts,
            "recovery_duration_seconds": recovery_seconds,
            "recovery_objective_met": recovery_attempts <= 3
            and recovery_seconds <= recovery_limit,
            "unresolved_incident": cause is not None,
        },
        "summary": {"ok": cause is None, "signal_count": len(findings)},
        "observations": [asdict(item) for item in observations],
        "redaction_applied": True,
    }
    return _redact(payload)


def _metric(name: str, value: float | int, labels: Mapping[str, str]) -> str:
    rendered = ",".join(
        f'{key}="{str(item).replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
        for key, item in sorted(labels.items())
    )
    return f"{name}{{{rendered}}} {value}"


def _safe_metric_text(value: Any) -> str:
    """Redact dynamic text before it reaches metrics or Pushgateway URLs."""
    return str(_redact(value))


def _cause_enum(report: Mapping[str, Any]) -> int:
    """Map a cause to a bounded numeric enum without exporting its text."""
    return _CAUSE_ENUM.get(str(report.get("primary_cause")), 0)


def prometheus_exposition(report: Mapping[str, Any]) -> str:
    """Render bounded-cardinality host metrics from a probe report."""

    labels = {
        "project": _safe_metric_text(report["project"]),
        "stack": _safe_metric_text(report["stack"]),
    }
    slo = report["slo"]
    lines = [
        "# TYPE bioetl_docker_runtime_probe_success gauge",
        _metric("bioetl_docker_runtime_probe_success", 1, labels),
        "# TYPE bioetl_docker_runtime_daemon_available gauge",
        _metric(
            "bioetl_docker_runtime_daemon_available",
            int(bool(slo["daemon_available"])),
            labels,
        ),
        "# TYPE bioetl_docker_runtime_restart_delta gauge",
        _metric(
            "bioetl_docker_runtime_restart_delta", slo["restart_count_delta"], labels
        ),
        "# TYPE bioetl_docker_runtime_oom_kills gauge",
        _metric("bioetl_docker_runtime_oom_kills", slo["oom_kills"], labels),
        "# TYPE bioetl_docker_runtime_disk_free_bytes gauge",
        _metric(
            "bioetl_docker_runtime_disk_free_bytes", slo["disk_reserve_bytes"], labels
        ),
        "# TYPE bioetl_docker_runtime_recovery_attempts gauge",
        _metric(
            "bioetl_docker_runtime_recovery_attempts",
            slo["recovery_attempt_count"],
            labels,
        ),
        "# TYPE bioetl_docker_runtime_recovery_duration_seconds gauge",
        _metric(
            "bioetl_docker_runtime_recovery_duration_seconds",
            slo["recovery_duration_seconds"],
            labels,
        ),
        "# TYPE bioetl_docker_runtime_primary_cause gauge",
        _metric(
            "bioetl_docker_runtime_primary_cause",
            _cause_enum(report),
            labels,
        ),
    ]
    for service in report["services"]:
        service_labels = {
            **labels,
            "service": _safe_metric_text(service["service"]),
        }
        lines.extend(
            [
                _metric(
                    "bioetl_docker_runtime_service_ready",
                    int(bool(service["ready"])),
                    service_labels,
                ),
                _metric(
                    "bioetl_docker_runtime_service_restart_count",
                    int(service["restart_count"]),
                    service_labels,
                ),
                _metric(
                    "bioetl_docker_runtime_service_oom_killed",
                    int(bool(service["oom_killed"])),
                    service_labels,
                ),
            ]
        )
    for resource in report["resources"]:
        service_labels = {
            **labels,
            "service": _safe_metric_text(resource["service"]),
        }
        for resource_name, key in (
            ("memory", "memory_limit_ratio"),
            ("cpu", "cpu_limit_ratio"),
            ("pids", "pids_limit_ratio"),
        ):
            lines.append(
                _metric(
                    "bioetl_docker_runtime_resource_peak_ratio",
                    float(resource[key]),
                    {**service_labels, "resource": resource_name},
                )
            )
    return "\n".join(lines) + "\n"


def push_exposition(
    gateway_url: str,
    report: Mapping[str, Any],
    exposition: str,
    *,
    timeout: float,
) -> None:
    """Replace one bounded Pushgateway group without changing Docker state."""
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    safe_gateway_url = ensure_local_http_url(gateway_url)
    stack = urllib.parse.quote(_safe_metric_text(report["stack"]), safe="")
    project = urllib.parse.quote(_safe_metric_text(report["project"]), safe="")
    target = (
        safe_gateway_url
        + "/metrics/job/bioetl_docker_runtime/project/"
        + project
        + "/stack/"
        + stack
    )
    request = urllib.request.Request(
        target,
        data=exposition.encode("utf-8"),
        headers={"Content-Type": "text/plain; version=0.0.4"},
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status >= 300:
            raise OSError(f"Pushgateway returned HTTP {response.status}")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", default="main")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--metrics-output", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--incident", type=Path)
    parser.add_argument(
        "--expected-image-override",
        metavar="SERVICE=IMAGE",
        help="Test-only expected identity override used by the scheduled drift fault.",
    )
    parser.add_argument("--pushgateway-url")
    parser.add_argument("--timeout", type=float, default=15.0)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    contract = args.contract.resolve()
    try:
        spec = resolve_stack(contract, args.stack)
        if args.expected_image_override:
            service, separator, image = args.expected_image_override.partition("=")
            # Build-only services have no compose `image` field, so they are absent
            # from expected_images until this scheduled drift fault injects one.
            if (
                separator != "="
                or not service
                or not image
                or service not in spec.required_services
            ):
                raise ValueError("Invalid required-service expected image override")
            spec = replace(
                spec,
                expected_images={**dict(spec.expected_images), service: image},
            )
        report = build_report(
            spec,
            contract,
            baseline=_read_json(args.baseline).get("restart_counts"),
            incident=_read_json(args.incident),
            timeout=max(1.0, min(args.timeout, 60.0)),
        )
    except (KeyError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__}))
        return 2
    output = args.output or DEFAULT_REPORT_DIR / f"docker-stability-{spec.name}.json"
    write_report(output, report)
    exposition = prometheus_exposition(report)
    if args.metrics_output:
        args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_output.write_text(exposition, encoding="utf-8")
    if args.pushgateway_url:
        try:
            push_exposition(
                args.pushgateway_url,
                report,
                exposition,
                timeout=max(1.0, min(args.timeout, 60.0)),
            )
        except (OSError, ValueError):
            print(json.dumps({"ok": False, "error": "pushgateway_publication_failed"}))
            return 2
    print(json.dumps({"ok": report["summary"]["ok"], "output": str(output)}))
    return 0 if report["summary"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
