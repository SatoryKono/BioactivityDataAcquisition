#!/usr/bin/env python3
"""Recreate bioetl-main + bioetl-monitoring from the Linux runtime origin.

Preserves named volumes. Never uses `down -v`. Does not create or edit `.env`
files; required secrets are taken from currently running containers into the
process environment for a single Compose invocation.

Used to restore canonical project origins for RF-017 (#6311) closeout when live
topology drifts to /tmp or mixed Windows/WSL config paths.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

SECRET_KEY = re.compile(r"(?:password|secret|token|credential|auth|key)", re.I)

DEFAULT_RUNTIME = Path(
    r"\\wsl$\Ubuntu\home\fedor\.local\share\bioetl-runtime\BioactivityDataAcquisition2"
)

MAIN_ENV_KEYS = ("LOG_LEVEL", "NEO4J_USERNAME", "NEO4J_PASSWORD")
MONITORING_ENV_KEYS = (
    "GF_SECURITY_ADMIN_PASSWORD",
    "GF_RENDERING_RENDERER_TOKEN",
    "BIOETL_ENABLE_TRACING_DATASOURCES",
    "BIOETL_QUARANTINE_EXPLORER_URL",
    "GRAFANA_IMAGE_RENDERER_READINESS_TIMEOUT",
    "GRAFANA_IMAGE_RENDERER_GOMEMLIMIT",
)


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = 600.0,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        env=dict(env) if env is not None else None,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def _container_env(container: str) -> dict[str, str]:
    completed = _run(
        ["docker", "inspect", container, "--format", "{{json .Config.Env}}"],
        timeout=60.0,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"inspect failed for {container}: {completed.stderr.strip()}"
        )
    items = json.loads(completed.stdout)
    result: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key] = value
    return result


def _pick_env(source: Mapping[str, str], keys: tuple[str, ...]) -> dict[str, str]:
    selected: dict[str, str] = {}
    for key in keys:
        if key in source and source[key] != "":
            selected[key] = source[key]
    return selected


def _print_env_summary(label: str, env_map: Mapping[str, str]) -> None:
    redacted = {
        key: ("***" if SECRET_KEY.search(key) else value[:48])
        for key, value in sorted(env_map.items())
    }
    print(f"{label}: {json.dumps(redacted, ensure_ascii=False)}", flush=True)


def _compose_env(
    base: Mapping[str, str], overrides: Mapping[str, str]
) -> dict[str, str]:
    merged = dict(base)
    merged.update(overrides)
    # Avoid Windows path rewriting of Linux-style compose paths by keeping PATH.
    return merged


def recreate_stack(
    *,
    runtime: Path,
    project: str,
    compose_file: Path,
    env_overrides: Mapping[str, str],
    profile: str | None = None,
) -> None:
    if not compose_file.is_file():
        raise FileNotFoundError(compose_file)

    env = _compose_env(os.environ, env_overrides)
    base_cmd = [
        "docker",
        "compose",
        "--project-directory",
        str(runtime),
        "-p",
        project,
        "-f",
        str(compose_file),
    ]
    if profile:
        base_cmd.extend(["--profile", profile])

    down = _run([*base_cmd, "down", "--remove-orphans"], env=env, timeout=300.0)
    print(down.stdout)
    if down.stderr:
        print(down.stderr, file=sys.stderr)
    if down.returncode != 0:
        raise RuntimeError(f"compose down failed for {project}: {down.returncode}")

    up = _run([*base_cmd, "up", "-d", "--remove-orphans"], env=env, timeout=600.0)
    print(up.stdout)
    if up.stderr:
        print(up.stderr, file=sys.stderr)
    if up.returncode != 0:
        raise RuntimeError(f"compose up failed for {project}: {up.returncode}")


def _is_ready(container: str) -> bool:
    completed = _run(
        [
            "docker",
            "inspect",
            container,
            "--format",
            "{{json .State}}",
        ],
        timeout=30.0,
    )
    if completed.returncode != 0:
        print(f"health {container}=missing", flush=True)
        return False
    state = json.loads(completed.stdout)
    status = state.get("Status")
    health = (state.get("Health") or {}).get("Status")
    print(f"health {container}=status:{status}/health:{health}", flush=True)
    if status != "running" or state.get("OOMKilled"):
        return False
    if health is None:
        return True
    return health == "healthy"


def wait_healthy(containers: list[str], *, timeout_seconds: float = 300.0) -> None:
    deadline = time.time() + timeout_seconds
    pending = set(containers)
    while pending and time.time() < deadline:
        pending = {name for name in pending if not _is_ready(name)}
        if pending:
            time.sleep(5)
    if pending:
        raise RuntimeError(f"containers not healthy before timeout: {sorted(pending)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime",
        type=Path,
        default=DEFAULT_RUNTIME,
        help="Linux-filesystem BioETL runtime origin",
    )
    parser.add_argument(
        "--include-tracing-profile",
        action="store_true",
        help="Also start monitoring services under the tracing profile",
    )
    parser.add_argument(
        "--skip-main",
        action="store_true",
        help="Only recreate monitoring",
    )
    args = parser.parse_args()
    runtime: Path = args.runtime

    grafana_env = _container_env("bioetl-grafana")
    main_env = _container_env("bioetl-main-bioetl-1")

    monitoring_overrides = _pick_env(grafana_env, MONITORING_ENV_KEYS)
    main_overrides = _pick_env(main_env, MAIN_ENV_KEYS)
    # Defaults for non-secret main keys if missing.
    main_overrides.setdefault("LOG_LEVEL", "INFO")
    main_overrides.setdefault("NEO4J_USERNAME", "neo4j")

    required_monitoring = (
        "GF_SECURITY_ADMIN_PASSWORD",
        "GF_RENDERING_RENDERER_TOKEN",
    )
    missing_mon = [k for k in required_monitoring if k not in monitoring_overrides]
    if missing_mon:
        raise RuntimeError(
            f"missing monitoring secrets from live containers: {missing_mon}"
        )
    if "NEO4J_PASSWORD" not in main_overrides:
        raise RuntimeError("missing NEO4J_PASSWORD from live main container")

    _print_env_summary("monitoring_env", monitoring_overrides)
    _print_env_summary("main_env", main_overrides)

    # Ensure shared networks exist (external in compose).
    for network in ("bioetl-monitoring", "bioetl-runtime"):
        exists = _run(["docker", "network", "inspect", network], timeout=30.0)
        if exists.returncode != 0:
            created = _run(["docker", "network", "create", network], timeout=30.0)
            if created.returncode != 0:
                raise RuntimeError(
                    f"failed to create network {network}: {created.stderr}"
                )

    recreate_stack(
        runtime=runtime,
        project="bioetl-monitoring",
        compose_file=runtime / "docker-compose.monitoring.yml",
        env_overrides=monitoring_overrides,
        profile="tracing" if args.include_tracing_profile else None,
    )

    if not args.skip_main:
        recreate_stack(
            runtime=runtime,
            project="bioetl-main",
            compose_file=runtime / "docker-compose.yml",
            env_overrides=main_overrides,
        )

    # Detach residual warp-network if still attached after recreate.
    for container in ("bioetl", "bioetl-main-bioetl-1"):
        inspect = _run(["docker", "inspect", container], timeout=30.0)
        if inspect.returncode != 0:
            continue
        payload = json.loads(inspect.stdout)[0]
        networks = payload.get("NetworkSettings", {}).get("Networks", {})
        if "warp-network" in networks:
            detach = _run(
                ["docker", "network", "disconnect", "-f", "warp-network", container],
                timeout=60.0,
            )
            print(detach.stdout)
            if detach.stderr:
                print(detach.stderr, file=sys.stderr)

    healthy_targets = [
        "bioetl-prometheus",
        "bioetl-pushgateway",
        "bioetl-grafana",
        "bioetl-monitoring-renderer-1",
    ]
    # Main container_name is `bioetl` in current compose.
    for candidate in ("bioetl", "bioetl-main-bioetl-1"):
        probe = _run(["docker", "inspect", candidate], timeout=30.0)
        if probe.returncode == 0:
            healthy_targets.append(candidate)
            break

    wait_healthy(healthy_targets, timeout_seconds=420.0)

    ls = _run(["docker", "compose", "ls", "--all"], timeout=60.0)
    print(ls.stdout)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - operator script surface
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
