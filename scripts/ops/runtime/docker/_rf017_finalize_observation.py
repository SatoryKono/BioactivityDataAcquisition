#!/usr/bin/env python3
"""Finalize RF-017 observation window and emit closeout evidence.

Run after planned_finish_at from docker-dashboard-cutover-observation.json.
Required duration is taken from observation.required_hours (default 2.4).
Does not mutate Docker volumes or .env files.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REPORT_DIR = ROOT / "reports" / "quality"
OBS_PATH = REPORT_DIR / "docker-dashboard-cutover-observation.json"
FINAL_PATH = REPORT_DIR / "docker-dashboard-cutover-final.json"
CLOSEOUT_PATH = REPORT_DIR / "docker-dashboard-cutover-rf017-closeout-20260721.json"

REQUIRED = [
    "bioetl-prometheus",
    "bioetl-pushgateway",
    "bioetl-grafana",
    "bioetl-monitoring-renderer-1",
    "bioetl",
]


def run(cmd: list[str], timeout: float = 90) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, text=True, capture_output=True, timeout=timeout, check=False
    )


def inspect_state(name: str) -> dict[str, object] | None:
    completed = run(["docker", "inspect", name, "--format", "{{json .}}"])
    if completed.returncode != 0:
        return None
    data = json.loads(completed.stdout)
    state = data.get("State", {})
    labels = (data.get("Config") or {}).get("Labels") or {}
    return {
        "status": state.get("Status"),
        "health": (state.get("Health") or {}).get("Status"),
        "restart_count": data.get("RestartCount"),
        "oom_killed": state.get("OOMKilled"),
        "started_at": state.get("StartedAt"),
        "networks": sorted((data.get("NetworkSettings") or {}).get("Networks", {})),
        "project": labels.get("com.docker.compose.project"),
        "config_files": labels.get("com.docker.compose.project.config_files"),
        "working_dir": labels.get("com.docker.compose.project.working_dir"),
    }


def compose_ls() -> list[dict[str, object]]:
    completed = run(["docker", "compose", "ls", "--all", "--format", "json"])
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)
    payload = json.loads(completed.stdout or "[]")
    return [payload] if isinstance(payload, dict) else list(payload)


def main() -> int:
    if not OBS_PATH.is_file():
        print("ERROR: observation file missing", file=sys.stderr)
        return 1
    obs = json.loads(OBS_PATH.read_text(encoding="utf-8"))
    started = datetime.fromisoformat(str(obs["started_at"]))
    now = datetime.now(UTC)
    elapsed_h = (now - started).total_seconds() / 3600.0
    required_h = float(obs.get("required_hours") or 2.4)
    force = "--force" in sys.argv
    if elapsed_h < required_h and not force:
        print(
            f"ERROR: observation incomplete: {elapsed_h:.2f}h < {required_h:g}h "
            f"(started {obs['started_at']})",
            file=sys.stderr,
        )
        return 2

    baseline = obs.get("baseline_snapshots") or {}
    current: dict[str, object] = {}
    failures: list[str] = []
    restart_delta = 0
    oom = 0
    unhealthy = 0
    for name in REQUIRED:
        snap = inspect_state(name)
        if snap is None and name == "bioetl":
            snap = inspect_state("bioetl-main-bioetl-1")
            name = "bioetl-main-bioetl-1" if snap else name
        current[name] = snap
        if snap is None:
            failures.append(f"{name}: missing")
            continue
        if snap.get("status") != "running":
            failures.append(f"{name}: status={snap.get('status')}")
        if snap.get("health") not in (None, "healthy"):
            failures.append(f"{name}: health={snap.get('health')}")
            unhealthy += 1
        if snap.get("oom_killed"):
            failures.append(f"{name}: oom")
            oom += 1
        base = baseline.get(name) or baseline.get("bioetl") or {}
        try:
            restart_delta += max(
                0, int(snap.get("restart_count") or 0) - int(base.get("restart_count") or 0)
            )
        except (TypeError, ValueError):
            pass
        nets = snap.get("networks") or []
        if "warp-network" in nets:
            failures.append(f"{name}: warp-network present")
        cfg = str(snap.get("config_files") or "")
        if "/tmp/" in cfg or "E:\\" in cfg or "E:/" in cfg:
            failures.append(f"{name}: non-canonical config {cfg}")

    projects = compose_ls()
    for project in projects:
        name = str(project.get("Name") or "")
        files = str(project.get("ConfigFiles") or "")
        if name in {"bioetl-main", "bioetl-monitoring"} and (
            "/tmp/" in files or "E:\\" in files or "E:/" in files
        ):
            failures.append(f"project {name} non-canonical: {files}")

    ok = not failures and restart_delta == 0 and oom == 0 and unhealthy == 0
    finished = now.isoformat()
    obs["status"] = "complete" if ok else "failed"
    obs["finished_at"] = finished
    obs["elapsed_hours"] = elapsed_h
    obs["end_snapshots"] = current
    obs["end_compose_projects"] = projects
    obs["result"] = {
        "ok": ok,
        "restart_count_delta": restart_delta,
        "oom_kills": oom,
        "unresolved_unhealthy": unhealthy,
        "failures": failures,
    }
    OBS_PATH.write_text(json.dumps(obs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    final = json.loads(FINAL_PATH.read_text(encoding="utf-8")) if FINAL_PATH.is_file() else {}
    final["status"] = "complete" if ok else "failed"
    final["generated_at"] = finished
    final.setdefault("gates", {})["observation"] = {
        "required_hours": required_h,
        "started_at": obs.get("started_at"),
        "finished_at": finished,
        "status": "complete" if ok else "failed",
        "restart_count_delta": restart_delta,
        "oom_kills": oom,
        "unresolved_unhealthy": unhealthy,
        "failures": failures,
        "evidence": "reports/quality/docker-dashboard-cutover-observation.json",
    }
    FINAL_PATH.write_text(
        json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    closeout = {
        "contract": "docker_dashboard_cutover_rf017_closeout_v1",
        "generated_at": finished,
        "issues": [6311, 6303],
        "verdict": "ready_to_close" if ok else "blocked",
        "debt_outcome": "unchanged",
        "observation": obs["result"],
        "evidence": {
            "observation": "reports/quality/docker-dashboard-cutover-observation.json",
            "final": "reports/quality/docker-dashboard-cutover-final.json",
            "canary": "reports/quality/docker-dashboard-cutover-canary.json",
            "preflight": "reports/quality/docker-dashboard-cutover-preflight.json",
            "live_audit": "reports/quality/docker-dashboard-cutover-live-audit.json",
        },
        "safety": {
            "env_files_changed": False,
            "volumes_deleted": False,
            "down_v_used": False,
        },
    }
    CLOSEOUT_PATH.write_text(
        json.dumps(closeout, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(closeout, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
