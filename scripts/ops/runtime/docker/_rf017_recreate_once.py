#!/usr/bin/env python3
"""One-shot RF-017 stack recreate for #6311 (no .env writes, no down -v)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

RUNTIME = Path(
    r"\\wsl$\Ubuntu\home\fedor\.local\share\bioetl-runtime\BioactivityDataAcquisition2"
)

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


def wait_ready(names: list[str], timeout_s: float = 420) -> None:
    deadline = time.time() + timeout_s
    pending = set(names)
    while pending and time.time() < deadline:
        still: set[str] = set()
        for name in sorted(pending):
            completed = run(
                ["docker", "inspect", name, "--format", "{{json .State}}"],
                timeout=60,
            )
            if completed.returncode != 0:
                print(f"{name}: missing", flush=True)
                still.add(name)
                continue
            state = json.loads(completed.stdout)
            status = state.get("Status")
            health = (state.get("Health") or {}).get("Status")
            print(f"{name}: status={status} health={health}", flush=True)
            ok = status == "running" and not state.get("OOMKilled")
            if health is not None:
                ok = ok and health == "healthy"
            if not ok:
                still.add(name)
        pending = still
        if pending:
            time.sleep(8)
    if pending:
        raise RuntimeError(f"not ready: {sorted(pending)}")


def main() -> int:
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
    print("env captured (secrets redacted)", flush=True)

    # Force-remove current monitoring/main containers (volumes retained).
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
        return up_mon.returncode

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
        return up_main.returncode

    # Drop residual warp attachment if any.
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
