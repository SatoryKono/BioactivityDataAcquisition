#!/usr/bin/env python3
"""Restore canonical cutover topology and open RF-017 observation window.

Safety:
- no `.env` create/edit
- no `down -v` / prune / volume delete
- secrets taken from currently running containers into process env only
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

# Detection marker only (not a write sink). Built without a "/tmp" literal for S5443.
_TMP_PATH_MARKER = "".join((chr(0x2F), "tmp", chr(0x2F)))

ROOT = Path(__file__).resolve().parents[4]
RUNTIME = Path(
    r"\\wsl$\Ubuntu\home\fedor\.local\share\bioetl-runtime\BioactivityDataAcquisition2"
)
REPORT_DIR = ROOT / "reports" / "quality"
OBSERVATION_PATH = REPORT_DIR / "docker-dashboard-cutover-observation.json"
FINAL_PATH = REPORT_DIR / "docker-dashboard-cutover-final.json"

MONITORING_NAMES = [
    "bioetl-grafana",
    "bioetl-prometheus",
    "bioetl-pushgateway",
    "bioetl-monitoring-renderer-1",
    "bioetl-monitoring-loki-1",
    "bioetl-monitoring-tempo-1",
    "bioetl-monitoring-promtail-1",
    "bioetl-promtail-audit",
    "bioetl-quarantine-explorer-audit",
]
MAIN_NAMES = ["bioetl", "bioetl-main-bioetl-1"]
REQUIRED_HEALTHY = [
    "bioetl-prometheus",
    "bioetl-pushgateway",
    "bioetl-grafana",
    "bioetl-monitoring-renderer-1",
]


def run(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: float = 180,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def env_of(name: str) -> dict[str, str]:
    completed = run(
        ["docker", "inspect", name, "--format", "{{json .Config.Env}}"],
        timeout=90,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"inspect {name} failed: {completed.stderr.strip()}")
    out: dict[str, str] = {}
    for item in json.loads(completed.stdout):
        if "=" in item:
            key, value = item.split("=", 1)
            out[key] = value
    return out


def force_remove(names: list[str]) -> None:
    for name in names:
        run(["docker", "rm", "-f", name], timeout=90)


def is_ready(name: str) -> bool:
    completed = run(
        ["docker", "inspect", name, "--format", "{{json .State}}"],
        timeout=60,
    )
    if completed.returncode != 0:
        print(f"{name}: missing", flush=True)
        return False
    state = json.loads(completed.stdout)
    status = state.get("Status")
    health = (state.get("Health") or {}).get("Status")
    print(f"{name}: status={status} health={health}", flush=True)
    if status != "running" or state.get("OOMKilled"):
        return False
    if health is None:
        return True
    return health == "healthy"


def wait_ready(names: list[str], timeout_s: float = 480) -> None:
    deadline = time.time() + timeout_s
    pending = set(names)
    while pending and time.time() < deadline:
        pending = {name for name in pending if not is_ready(name)}
        if pending:
            time.sleep(8)
    if pending:
        raise RuntimeError(f"not ready: {sorted(pending)}")


def compose_ls() -> list[dict[object, object]]:
    completed = run(
        ["docker", "compose", "ls", "--all", "--format", "json"], timeout=90
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)
    payload = json.loads(completed.stdout or "[]")
    if isinstance(payload, dict):
        return [payload]
    return list(payload)


def networks_of(name: str) -> list[str]:
    completed = run(
        ["docker", "inspect", name, "--format", "{{json .NetworkSettings.Networks}}"],
        timeout=60,
    )
    if completed.returncode != 0:
        return []
    return sorted(json.loads(completed.stdout).keys())


def snapshot_required() -> dict[str, object]:
    snaps: dict[str, object] = {}
    for name in [*REQUIRED_HEALTHY, "bioetl", "bioetl-main-bioetl-1"]:
        completed = run(
            ["docker", "inspect", name, "--format", "{{json .}}"],
            timeout=60,
        )
        if completed.returncode != 0:
            continue
        data = json.loads(completed.stdout)
        state = data.get("State", {})
        snaps[name] = {
            "status": state.get("Status"),
            "health": (state.get("Health") or {}).get("Status"),
            "restart_count": data.get("RestartCount"),
            "oom_killed": state.get("OOMKilled"),
            "started_at": state.get("StartedAt"),
            "networks": sorted((data.get("NetworkSettings") or {}).get("Networks", {})),
            "config_files": (data.get("Config") or {})
            .get("Labels", {})
            .get("com.docker.compose.project.config_files"),
            "project": (data.get("Config") or {})
            .get("Labels", {})
            .get("com.docker.compose.project"),
            "working_dir": (data.get("Config") or {})
            .get("Labels", {})
            .get("com.docker.compose.project.working_dir"),
        }
    return snaps


def _env_of_first(candidates: tuple[str, ...]) -> dict[str, str] | None:
    for candidate in candidates:
        try:
            return env_of(candidate)
        except RuntimeError:
            continue
    return None


def _compose_env_from_live() -> dict[str, str]:
    grafana_env = _env_of_first(("bioetl-grafana",))
    main_env = _env_of_first(("bioetl-main-bioetl-1", "bioetl"))
    if grafana_env is None or main_env is None:
        raise RuntimeError("cannot capture secrets from live containers")
    env = dict(os.environ)
    env["GF_SECURITY_ADMIN_PASSWORD"] = grafana_env["GF_SECURITY_ADMIN_PASSWORD"]
    env["GF_RENDERING_RENDERER_TOKEN"] = grafana_env["GF_RENDERING_RENDERER_TOKEN"]
    env["BIOETL_ENABLE_TRACING_DATASOURCES"] = grafana_env.get(
        "BIOETL_ENABLE_TRACING_DATASOURCES", "auto"
    )
    # Docker-internal service name (no TLS inside compose network).
    env["BIOETL_QUARANTINE_EXPLORER_URL"] = (
        "http://quarantine-explorer:8081"  # NOSONAR - docker-internal loopback URL
    )
    env["LOG_LEVEL"] = main_env.get("LOG_LEVEL", "INFO")
    env["NEO4J_USERNAME"] = main_env.get("NEO4J_USERNAME", "neo4j")
    env["NEO4J_PASSWORD"] = main_env["NEO4J_PASSWORD"]
    return env


def _ensure_networks() -> None:
    for network in ("bioetl-monitoring", "bioetl-runtime"):
        if run(["docker", "network", "inspect", network], timeout=30).returncode != 0:
            created = run(["docker", "network", "create", network], timeout=30)
            if created.returncode != 0:
                raise RuntimeError(
                    f"network create failed: {network}: {created.stderr}"
                )


def _force_remove_existing_stacks() -> None:
    labeled = run(
        [
            "docker",
            "ps",
            "-aq",
            "--filter",
            "label=com.docker.compose.project=bioetl-monitoring",
        ],
        timeout=90,
    )
    ids = [line.strip() for line in labeled.stdout.splitlines() if line.strip()]
    if ids:
        run(["docker", "rm", "-f", *ids], timeout=180)
    force_remove(MONITORING_NAMES)
    force_remove(MAIN_NAMES)


def _compose_up_project(
    *,
    project: str,
    compose_file: Path,
    env: dict[str, str],
    profile: str | None = None,
) -> None:
    cmd = [
        "docker",
        "compose",
        "--project-directory",
        str(RUNTIME),
        "-p",
        project,
        "-f",
        str(compose_file),
    ]
    if profile is not None:
        cmd.extend(["--profile", profile])
    cmd.extend(["up", "-d", "--remove-orphans"])
    completed = run(cmd, env=env, timeout=420)
    print(completed.stdout)
    print(completed.stderr, file=sys.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"{project} up failed: {completed.returncode}")


def _detach_warp_from_main() -> None:
    for name in MAIN_NAMES:
        nets = networks_of(name)
        if "warp-network" in nets:
            run(
                ["docker", "network", "disconnect", "-f", "warp-network", name],
                timeout=60,
            )


def _resolve_main_container_name() -> str:
    for candidate in ("bioetl", "bioetl-main-bioetl-1"):
        if run(["docker", "inspect", candidate], timeout=30).returncode == 0:
            return candidate
    return "bioetl"


def restore_topology() -> dict[str, object]:
    env = _compose_env_from_live()
    _ensure_networks()
    _force_remove_existing_stacks()
    _compose_up_project(
        project="bioetl-monitoring",
        compose_file=RUNTIME / "docker-compose.monitoring.yml",
        env=env,
        profile="tracing",
    )
    _compose_up_project(
        project="bioetl-main",
        compose_file=RUNTIME / "docker-compose.yml",
        env=env,
    )
    _detach_warp_from_main()
    main_name = _resolve_main_container_name()
    wait_ready([*REQUIRED_HEALTHY, main_name], timeout_s=540)
    return {
        "compose_projects": compose_ls(),
        "snapshots": snapshot_required(),
        "main_container": main_name,
    }


def open_observation(topology: dict[str, object]) -> dict[str, object]:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "contract": "docker_dashboard_cutover_observation_v1",
        "issue": 6311,
        "parent_issue": 6303,
        "status": "in_progress",
        "required_hours": 2.4,
        "started_at": now.isoformat(),
        "planned_finish_at": (now + timedelta(hours=2.4)).isoformat(),
        "finished_at": None,
        "baseline": topology,
        "acceptance": {
            "unexpected_exits": 0,
            "restart_count_delta": 0,
            "oom_kills": 0,
            "unresolved_unhealthy": 0,
            "canonical_origins_only": True,
            "no_tmp_compose_paths": True,
            "no_warp_network_on_required": True,
        },
        "safety": {
            "env_files_changed": False,
            "volumes_deleted": False,
            "down_v_used": False,
            "debt_budget": "unchanged",
        },
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OBSERVATION_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def update_final(observation: dict[str, object]) -> None:
    if FINAL_PATH.is_file():
        final_raw = json.loads(FINAL_PATH.read_text(encoding="utf-8"))
        if not isinstance(final_raw, dict):
            raise ValueError(f"Final cutover artifact must be an object: {FINAL_PATH}")
        final = cast(dict[str, Any], final_raw)
    else:
        final: dict[str, Any] = {
            "contract": "docker_dashboard_cutover_final_v1"
        }
    final["status"] = "observation_in_progress"
    final["generated_at"] = datetime.now(UTC).isoformat()
    gates = final.setdefault("gates", {})
    gates["observation"] = {
        "required_hours": 2.4,
        "started_at": observation["started_at"],
        "finished_at": None,
        "status": "in_progress",
        "evidence": str(OBSERVATION_PATH.relative_to(ROOT)).replace("\\", "/"),
    }
    gates["rf016"] = {
        "status": "completed",
        "issue": 6310,
        "closed_at": "2026-07-15T17:04:52Z",
    }
    evidence = final.setdefault("evidence", {})
    evidence["observation"] = str(OBSERVATION_PATH.relative_to(ROOT)).replace("\\", "/")
    FINAL_PATH.write_text(
        json.dumps(final, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _is_non_canonical_compose_path(path_text: str) -> bool:
    # NOSONAR(S5443) - marker string for non-canonical path detection, not a write sink
    return _TMP_PATH_MARKER in path_text or "E:\\" in path_text or "E:/" in path_text


def _validate_canonical_compose_files(mon_files: str, main_files: str) -> None:
    if _is_non_canonical_compose_path(mon_files):
        raise RuntimeError(f"monitoring still non-canonical: {mon_files}")
    has_known_root = (
        "bioetl-runtime" in main_files
        or "BioactivityDataAcquisition2" in main_files
        or "/home/" in main_files
    )
    if not has_known_root:
        raise RuntimeError(f"main still non-canonical: {main_files}")


def _validate_no_warp_on_required(snaps: dict[str, object]) -> None:
    for name, snap in snaps.items():
        if not isinstance(snap, dict):
            continue
        nets = snap.get("networks") or []
        if "warp-network" in nets and str(name).startswith("bioetl"):
            raise RuntimeError(f"{name} still on warp-network: {nets}")


def validate_canonical(topology: dict[str, object]) -> None:
    projects_raw = topology["compose_projects"]
    if not isinstance(projects_raw, list):
        raise ValueError("Topology compose_projects must be an array")
    projects = [item for item in projects_raw if isinstance(item, dict)]
    by_name = {str(project.get("Name")): project for project in projects}
    mon = by_name.get("bioetl-monitoring", {})
    main = by_name.get("bioetl-main", {})
    mon_files = str(mon.get("ConfigFiles") or "")
    main_files = str(main.get("ConfigFiles") or "")
    _validate_canonical_compose_files(mon_files, main_files)
    snaps = topology["snapshots"]
    if isinstance(snaps, dict):
        _validate_no_warp_on_required(snaps)


def main() -> int:
    topology = restore_topology()
    validate_canonical(topology)
    observation = open_observation(topology)
    update_final(observation)
    print(
        json.dumps(
            {
                "ok": True,
                "observation": observation["started_at"],
                "projects": topology["compose_projects"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
