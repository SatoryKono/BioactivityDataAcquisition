"""Immutable campaign model, state gates, redaction, and evidence integrity."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

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
SECRET_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "authorization",
    "auth",
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(password|passwd|secret|token|credential|authorization|auth)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_SECRET_FLAG = re.compile(
    r"(?i)^--?(?:password|passwd|secret|token|credential|authorization|auth)$"
)
_BARE_GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{12,}\b")
_URI_USERINFO = re.compile(r"(://)[^/@\s:]+:[^/@\s]+@")
_WINDOWS_PATH = re.compile(r"(?i)^(?:[a-z]:[\\/]|\\\\)")


@dataclass(frozen=True)
class StackSpec:
    """One immutable member of the tested release bundle."""

    stack: str
    project: str
    compose_file: str
    required_services: tuple[str, ...]
    protected_volumes: tuple[str, ...] = ()
    required_volumes: tuple[str, ...] = ()
    legacy_volumes: tuple[str, ...] = ()


@dataclass(frozen=True)
class FaultOperation:
    """One bounded operation with an exact expected outcome."""

    kind: str
    stack: str | None = None
    service: str | None = None
    port: int | None = None
    max_seconds: float = 30.0
    expected: str = "success"


@dataclass(frozen=True)
class FaultCase:
    """A scheduled fault with a case-local restoration path."""

    name: str
    classification: str
    apply: tuple[FaultOperation, ...]
    observe: tuple[FaultOperation, ...]
    restore: tuple[FaultOperation, ...]
    max_seconds: float = 180.0


def redact(value: Any) -> Any:
    """Recursively redact likely credentials, including split CLI flag values."""
    if isinstance(value, dict):
        return {
            str(key): (
                "<redacted>"
                if any(marker in str(key).lower() for marker in SECRET_MARKERS)
                else redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        protected: list[Any] = []
        redact_next = False
        for item in value:
            if redact_next:
                protected.append("<redacted>")
                redact_next = False
                continue
            protected.append(redact(item))
            redact_next = isinstance(item, str) and bool(_SECRET_FLAG.match(item))
        return protected if isinstance(value, list) else tuple(protected)
    if isinstance(value, str):
        assigned = _SECRET_ASSIGNMENT.sub(r"\1\2<redacted>", value)
        assigned = _BARE_GITHUB_TOKEN.sub("<redacted-github-token>", assigned)
        return _URI_USERINFO.sub(r"\1<redacted>:<redacted>@", assigned)
    return value


def atomic_json(path: Path, payload: dict[str, Any], *, replace: bool = True) -> None:
    """Write redacted JSON atomically; optionally refuse replacement."""
    if not replace and path.exists():
        raise FileExistsError(f"Refusing to replace campaign evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(redact(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def remember_evidence(state: dict[str, Any], path: Path, evidence_dir: Path) -> None:
    relative = path.resolve().relative_to(evidence_dir.resolve()).as_posix()
    state.setdefault("evidence_sha256", {})[relative] = file_sha256(path)


def remember_evidence_tree(
    state: dict[str, Any], directory: Path, evidence_dir: Path
) -> None:
    if directory.is_dir():
        for path in sorted(directory.rglob("*.json")):
            remember_evidence(state, path, evidence_dir)


def validate_evidence_index(state: dict[str, Any], evidence_dir: Path) -> None:
    """Fail closed when indexed evidence is missing/changed or unindexed JSON appears."""
    index = state.get("evidence_sha256", {})
    if not isinstance(index, dict):
        raise ValueError("Campaign evidence index must be a mapping")
    actual = {
        path.resolve().relative_to(evidence_dir.resolve()).as_posix(): path
        for path in evidence_dir.rglob("*.json")
    }
    if set(actual) != set(index):
        raise ValueError("Campaign evidence set differs from the pinned state index")
    for relative, expected in index.items():
        if file_sha256(actual[str(relative)]) != str(expected):
            raise ValueError(f"Campaign evidence changed: {relative}")


def origin_kind(value: str | Path) -> str:
    raw = str(value).strip()
    lowered = raw.replace("\\", "/").lower()
    if _WINDOWS_PATH.match(raw):
        return "windows"
    if lowered == "/tmp" or lowered.startswith("/tmp/"):
        return "tmp"
    if lowered == "/mnt" or lowered.startswith("/mnt/"):
        return "mnt"
    if not lowered.startswith("/"):
        return "relative"
    return "linux"


def canonical_runtime_origin(path: Path) -> Path:
    if origin_kind(path) != "linux":
        raise ValueError(
            "Runtime origin must be an absolute Linux path outside /mnt and /tmp"
        )
    resolved = path.resolve(strict=True)
    if origin_kind(resolved) != "linux":
        raise ValueError("Resolved runtime origin must remain outside /mnt and /tmp")
    return resolved


def load_contract(
    runtime_origin: Path, contract: Path
) -> tuple[Path, dict[str, Any], str]:
    candidate = contract if contract.is_absolute() else runtime_origin / contract
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(runtime_origin)
    except ValueError as exc:
        raise ValueError("Contract must be inside the pinned runtime origin") from exc
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Docker runtime contract must be a mapping")
    return resolved, payload, file_sha256(resolved)


def release_bundle(contract: dict[str, Any]) -> tuple[StackSpec, ...]:
    stacks = contract.get("stacks", {})
    bundle: list[StackSpec] = []
    for name in RELEASE_STACKS:
        raw = stacks.get(name) if isinstance(stacks, dict) else None
        if not isinstance(raw, dict):
            raise ValueError(f"Docker runtime contract is missing release stack {name}")
        services = raw.get("required_services")
        if not isinstance(services, list) or not services:
            raise ValueError(f"Release stack {name} has no required services")
        migration = raw.get("migration", {})
        volume_map = (
            migration.get("volume_map", {}) if isinstance(migration, dict) else {}
        )
        if not isinstance(volume_map, dict):
            raise ValueError(
                f"Release stack {name} has an invalid migration volume map"
            )
        legacy_volumes = tuple(sorted(str(item) for item in volume_map))
        required_volumes = tuple(sorted(str(item) for item in volume_map.values()))
        protected = tuple(sorted({*legacy_volumes, *required_volumes}))
        bundle.append(
            StackSpec(
                stack=name,
                project=str(raw["project_name"]),
                compose_file=str(raw["compose_file"]),
                required_services=tuple(map(str, services)),
                protected_volumes=protected,
                required_volumes=required_volumes,
                legacy_volumes=legacy_volumes,
            )
        )
    if len({spec.project for spec in bundle}) != len(bundle):
        raise ValueError("Release bundle project names must be unique")
    return tuple(bundle)


def bundle_identity(bundle: Sequence[StackSpec]) -> list[dict[str, Any]]:
    return [asdict(spec) for spec in bundle]


def compose_origin_findings(
    rows: Sequence[dict[str, Any]],
    bundle: Sequence[StackSpec],
    runtime_origin: Path,
) -> list[str]:
    expected = {spec.project for spec in bundle}
    seen: set[str] = set()
    findings: list[str] = []
    for row in rows:
        project = str(row.get("Name") or row.get("name") or "")
        if project not in expected:
            continue
        seen.add(project)
        raw = row.get("ConfigFiles") or row.get("configFiles") or ""
        origins = (
            [str(item) for item in raw]
            if isinstance(raw, list)
            else [item.strip() for item in str(raw).split(",") if item.strip()]
        )
        if not origins:
            findings.append(f"{project}: missing runtime origin")
            continue
        if any(origin_kind(origin) != "linux" for origin in origins):
            findings.append(f"{project}: noncanonical runtime origin")
            continue
        try:
            for origin in origins:
                Path(origin).resolve(strict=False).relative_to(runtime_origin)
        except ValueError:
            findings.append(f"{project}: runtime origin outside pinned mirror")
    findings.extend(
        f"{project}: project not running" for project in sorted(expected - seen)
    )
    return findings


def new_state(
    *,
    cycles: int,
    soak_hours: float,
    bundle: Sequence[StackSpec] | None = None,
    stack: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    if bundle is None:
        if stack is None or project is None:
            raise ValueError("An explicit release bundle is required")
        bundle = (StackSpec(stack, project, "", ("unknown",)),)
    return {
        "schema_version": "bioetl-docker-stability-campaign-state-v3",
        "release_bundle": bundle_identity(bundle),
        "required_cycles": cycles,
        "required_soak_hours": soak_hours,
        "required_engine_recovery_trials": 100,
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
        "docker_vm_reserve_breaches": 0,
        "docker_vm_min_free_bytes": None,
        "image_or_project_drift": 0,
        "last_failure": None,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def release_gates(state: dict[str, Any], *, signature_exists: bool) -> dict[str, bool]:
    trials = int(state.get("engine_recovery_trials", 0))
    successes = int(state.get("engine_recovery_successes", 0))
    required_trials = int(state.get("required_engine_recovery_trials", 100))
    required_faults = set(state.get("required_fault_cases", FAULT_CASE_NAMES))
    faults = state.get("fault_cases", {})
    complete = required_faults == set(faults)
    return {
        "cycles_complete": int(state["completed_cycles"])
        >= int(state["required_cycles"]),
        "cycles_clean": int(state["cycle_failures"]) == 0,
        "soak_complete": float(state["soak_observed_seconds"])
        >= float(state["required_soak_hours"]) * 3600,
        "soak_continuous": not bool(state.get("soak_window_interrupted", False)),
        "engine_recovery_99_of_100": trials >= required_trials
        and successes / trials >= 0.99,
        "volumes_preserved": not bool(state["volume_loss"]),
        "all_probe_samples_clean": int(state.get("probe_failures", 0)) == 0
        and int(state.get("probe_samples", 0)) > 0,
        "resource_peak_below_80_percent": float(state.get("max_resource_ratio", 0.0))
        < 0.8,
        "restart_delta_zero": int(state.get("restart_count_delta", 0)) == 0,
        "oom_kills_zero": int(state.get("oom_kills", 0)) == 0,
        "unhealthy_zero": int(state.get("unhealthy_samples", 0)) == 0,
        "disk_reserve_preserved": int(state.get("disk_reserve_breaches", 0)) == 0,
        "docker_vm_reserve_at_least_4_gib": int(
            state.get("docker_vm_reserve_breaches", 0)
        )
        == 0
        and int(state.get("docker_vm_min_free_bytes") or 0) >= 4 * 1024**3,
        "identity_drift_zero": int(state.get("image_or_project_drift", 0)) == 0,
        "fault_matrix_complete": complete,
        "fault_matrix_clean": complete
        and all(bool(faults[name].get("passed")) for name in required_faults),
        "detached_signature_present": signature_exists,
        "no_unresolved_failure": state.get("last_failure") is None,
    }


def updated_now(state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now(UTC).isoformat()
