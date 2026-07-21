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
    completed = run(["docker", "compose", "ls", "--all", "--format", "json"], timeout=90)
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
            "config_files": (data.get("Config") or {}).get("Labels", {}).get(
                "com.docker.compose.project.config_files"
            ),
            "project": (data.get("Config") or {}).get("Labels", {}).get(
                "com.docker.compose.project"
            ),
            "working_dir": (data.get("Config") or {}).get("Labels", {}).get(
                "com.docker.compose.project.working_dir"
            ),
        }
    return snaps


def restore_topology() -> dict[str, object]:
    # Prefer existing grafana/main for secrets; fall back across name variants.
    grafana_env: dict[str, str] | None = None
    main_env: dict[str, str] | None = None
    for candidate in ("bioetl-grafana",):
        try:
            grafana_env = env_of(candidate)
            break
        except RuntimeError:
            continue
    for candidate in ("bioetl-main-bioetl-1", "bioetl"):
        try:
            main_env = env_of(candidate)
            break
        except RuntimeError:
            continue
    if grafana_env is None or main_env is None:
        raise RuntimeError("cannot capture secrets from live containers")

    env = dict(os.environ)
    env["GF_SECURITY_ADMIN_PASSWORD"] = grafana_env["GF_SECURITY_ADMIN_PASSWORD"]
    env["GF_RENDERING_RENDERER_TOKEN"] = grafana_env["GF_RENDERING_RENDERER_TOKEN"]
    env["BIOETL_ENABLE_TRACING_DATASOURCES"] = grafana_env.get(
        "BIOETL_ENABLE_TRACING_DATASOURCES", "auto"
    )
    env["BIOETL_QUARANTINE_EXPLORER_URL"] = "http://quarantine-explorer:8081"
    env["LOG_LEVEL"] = main_env.get("LOG_LEVEL", "INFO")
    env["NEO4J_USERNAME"] = main_env.get("NEO4J_USERNAME", "neo4j")
    env["NEO4J_PASSWORD"] = main_env["NEO4J_PASSWORD"]

    for network in ("bioetl-monitoring", "bioetl-runtime"):
        if run(["docker", "network", "inspect", network], timeout=30).returncode != 0:
            created = run(["docker", "network", "create", network], timeout=30)
            if created.returncode != 0:
                raise RuntimeError(f"network create failed: {network}: {created.stderr}")

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

    mon = [
        "docker",
        "compose",
        "--project-directory",
        str(RUNTIME),
        "-p",
        "bioetl-monitoring",
        "-f",
        str(RUNTIME / "docker-compose.monitoring.yml"),
        "--profile",
        "tracing",
        "up",
        "-d",
        "--remove-orphans",
    ]
    up_mon = run(mon, env=env, timeout=420)
    print(up_mon.stdout)
    print(up_mon.stderr, file=sys.stderr)
    if up_mon.returncode != 0:
        raise RuntimeError(f"monitoring up failed: {up_mon.returncode}")

    main_cmd = [
        "docker",
        "compose",
        "--project-directory",
        str(RUNTIME),
        "-p",
        "bioetl-main",
        "-f",
        str(RUNTIME / "docker-compose.yml"),
        "up",
        "-d",
        "--remove-orphans",
    ]
    up_main = run(main_cmd, env=env, timeout=420)
    print(up_main.stdout)
    print(up_main.stderr, file=sys.stderr)
    if up_main.returncode != 0:
        raise RuntimeError(f"main up failed: {up_main.returncode}")

    for name in MAIN_NAMES:
        nets = networks_of(name)
        if "warp-network" in nets:
            run(
                ["docker", "network", "disconnect", "-f", "warp-network", name],
                timeout=60,
            )

    # Resolve actual main container name after recreate.
    main_name = "bioetl" if is_ready("bioetl") or True else "bioetl-main-bioetl-1"
    for candidate in ("bioetl", "bioetl-main-bioetl-1"):
        if run(["docker", "inspect", candidate], timeout=30).returncode == 0:
            main_name = candidate
            break
    wait_ready([*REQUIRED_HEALTHY, main_name], timeout_s=540)

    projects = compose_ls()
    return {
        "compose_projects": projects,
        "snapshots": snapshot_required(),
        "main_container": main_name,
    }


def open_observation(topology: dict[str, object]) -> dict[str, object]:
    now = datetime.now(UTC)
    payload = {
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
        final = json.loads(FINAL_PATH.read_text(encoding="utf-8"))
    else:
        final = {"contract": "docker_dashboard_cutover_final_v1"}
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


def validate_canonical(topology: dict[str, object]) -> None:
    projects = topology["compose_projects"]
    by_name = {str(p.get("Name")): p for p in projects}
    mon = by_name.get("bioetl-monitoring", {})
    main = by_name.get("bioetl-main", {})
    mon_files = str(mon.get("ConfigFiles") or "")
    main_files = str(main.get("ConfigFiles") or "")
    if "/tmp/" in mon_files or "E:\\" in mon_files or "E:/" in mon_files:
        raise RuntimeError(f"monitoring still non-canonical: {mon_files}")
    if "bioetl-runtime" not in main_files and "BioactivityDataAcquisition2" not in main_files:
        # main path should be Linux runtime
        if "/home/" not in main_files:
            raise RuntimeError(f"main still non-canonical: {main_files}")
    snaps = topology["snapshots"]
    for name, snap in snaps.items():
        nets = snap.get("networks") or []
        if "warp-network" in nets and name.startswith("bioetl"):
            raise RuntimeError(f"{name} still on warp-network: {nets}")


def main() -> int:
    topology = restore_topology()
    validate_canonical(topology)
    observation = open_observation(topology)
    update_final(observation)
    print(json.dumps({"ok": True, "observation": observation["started_at"], "projects": topology["compose_projects"]}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
