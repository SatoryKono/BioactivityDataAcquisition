#!/usr/bin/env python3
"""One-shot RF-017 stack recreate for #6311 (no .env writes, no down -v)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

_RUNTIME_ORIGIN = os.environ.get("BIOETL_RUNTIME_ORIGIN", "").strip()
if not _RUNTIME_ORIGIN:
    raise RuntimeError(
        "BIOETL_RUNTIME_ORIGIN is required; use runtime_manager.py for normal lifecycle"
    )
RUNTIME = Path(_RUNTIME_ORIGIN)

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


def run(
    cmd: list[str], *, env: dict[str, str] | None = None, timeout: float = 120
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
        raise RuntimeError(f"inspect {name} failed: {completed.stderr}")
    out: dict[str, str] = {}
    for item in json.loads(completed.stdout):
        if "=" in item:
            key, value = item.split("=", 1)
            out[key] = value
    return out


def force_remove(names: list[str]) -> None:
    for name in names:
        run(["docker", "rm", "-f", name], timeout=90)


def _container_ready_state(name: str) -> bool:
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
    ok = status == "running" and not state.get("OOMKilled")
    if health is not None:
        ok = ok and health == "healthy"
    return bool(ok)


def wait_ready(names: list[str], timeout_s: float = 420) -> None:
    deadline = time.time() + timeout_s
    pending = set(names)
    while pending and time.time() < deadline:
        pending = {name for name in sorted(pending) if not _container_ready_state(name)}
        if pending:
            time.sleep(8)
    if pending:
        raise RuntimeError(f"not ready: {sorted(pending)}")


def _capture_live_compose_env() -> dict[str, str]:
    grafana = env_of("bioetl-grafana")
    main = env_of("bioetl-main-bioetl-1")
    env = dict(os.environ)
    env["GF_SECURITY_ADMIN_PASSWORD"] = grafana["GF_SECURITY_ADMIN_PASSWORD"]
    env["GF_RENDERING_RENDERER_TOKEN"] = grafana["GF_RENDERING_RENDERER_TOKEN"]
    env["BIOETL_ENABLE_TRACING_DATASOURCES"] = grafana.get(
        "BIOETL_ENABLE_TRACING_DATASOURCES", "auto"
    )
    # Docker-internal service name (no TLS inside compose network).
    env["BIOETL_QUARANTINE_EXPLORER_URL"] = (
        "http://quarantine-explorer:8081"  # NOSONAR - docker-internal loopback URL
    )
    env["LOG_LEVEL"] = main.get("LOG_LEVEL", "INFO")
    env["NEO4J_USERNAME"] = main.get("NEO4J_USERNAME", "neo4j")
    env["NEO4J_PASSWORD"] = main["NEO4J_PASSWORD"]
    return env


def _force_remove_cutover_containers() -> None:
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


def _compose_up(
    *,
    project: str,
    compose_file: Path,
    env: dict[str, str],
    profile: str | None = None,
) -> int:
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
    return completed.returncode


def _detach_warp_from_main() -> None:
    for name in MAIN_NAMES:
        inspect = run(["docker", "inspect", name], timeout=60)
        if inspect.returncode != 0:
            continue
        networks = json.loads(inspect.stdout)[0]["NetworkSettings"]["Networks"]
        if "warp-network" in networks:
            run(
                ["docker", "network", "disconnect", "-f", "warp-network", name],
                timeout=60,
            )


def main() -> int:
    env = _capture_live_compose_env()
    print("env captured (secrets redacted)", flush=True)
    _force_remove_cutover_containers()

    mon_rc = _compose_up(
        project="bioetl-monitoring",
        compose_file=RUNTIME / "docker-compose.monitoring.yml",
        env=env,
        profile="tracing",
    )
    if mon_rc != 0:
        return mon_rc

    main_rc = _compose_up(
        project="bioetl-main",
        compose_file=RUNTIME / "docker-compose.yml",
        env=env,
    )
    if main_rc != 0:
        return main_rc

    _detach_warp_from_main()
    wait_ready(
        [
            "bioetl-prometheus",
            "bioetl-pushgateway",
            "bioetl-grafana",
            "bioetl-monitoring-renderer-1",
            "bioetl",
        ],
        timeout_s=480,
    )
    ls = run(["docker", "compose", "ls", "--all"], timeout=90)
    print(ls.stdout)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
