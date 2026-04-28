#!/usr/bin/env python3
"""Live Grafana datasource smoke for tracing-off and tracing-on monitoring modes."""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
BASE_COMPOSE_FILE = REPO_ROOT / "docker-compose.monitoring.yml"
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = "bioetl-smoke-admin"


def _find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _build_temp_compose(*, suffix: str, grafana_port: int) -> str:
    payload = yaml.safe_load(BASE_COMPOSE_FILE.read_text(encoding="utf-8"))
    services = payload["services"]

    for service in services.values():
        volumes = service.get("volumes")
        if isinstance(volumes, list):
            service["volumes"] = [_rewrite_volume(volume) for volume in volumes]

    for service_name in ("prometheus", "pushgateway", "loki", "promtail", "tempo"):
        service = services[service_name]
        base_name = str(service["container_name"])
        service["container_name"] = f"{base_name}-{suffix}"
        service.pop("ports", None)

    grafana = services["grafana"]
    grafana["container_name"] = f"{grafana['container_name']}-{suffix}"
    grafana["ports"] = [f"{grafana_port}:3000"]

    return yaml.safe_dump(payload, sort_keys=False)


def _rewrite_volume(volume: object) -> object:
    if isinstance(volume, str):
        parts = volume.split(":")
        source = parts[0]
        if source.startswith("./"):
            resolved = str((REPO_ROOT / source[2:]).resolve())
            return ":".join([resolved, *parts[1:]])
        return volume
    if isinstance(volume, dict):
        source = volume.get("source")
        if isinstance(source, str) and source.startswith("./"):
            volume = dict(volume)
            volume["source"] = str((REPO_ROOT / source[2:]).resolve())
        return volume
    return volume


def _run(
    command: list[str], *, env: dict[str, str], check: bool = True
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            "Command failed\n"
            f"cmd: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def _run_cleanup(command: list[str], *, env: dict[str, str]) -> None:
    _run(command, env=env, check=False)


def _wait_for_grafana(port: int, *, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    health_url = f"http://127.0.0.1:{port}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("database") == "ok":
                    return
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            time.sleep(1.0)
            continue
    raise TimeoutError(
        f"Grafana did not become healthy on port {port} within {timeout_s:.0f}s"
    )


def _grafana_auth_header() -> str:
    raw = f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _fetch_datasource_names(port: int) -> list[str]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/datasources",
        headers={"Authorization": _grafana_auth_header()},
    )
    with urllib.request.urlopen(request, timeout=5.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return sorted(
        item["name"] for item in payload if isinstance(item, dict) and "name" in item
    )


def _assert_datasource_expectations(names: list[str], *, tracing_enabled: bool) -> None:
    required = {"Prometheus", "Quarantine Explorer"}
    missing = sorted(required - set(names))
    if missing:
        raise AssertionError(f"Missing required datasources: {missing}; got {names}")

    tracing_sources = {"Loki", "Tempo"}
    present_tracing = sorted(tracing_sources & set(names))
    if tracing_enabled and present_tracing != ["Loki", "Tempo"]:
        raise AssertionError(
            "Tracing mode expected Loki and Tempo datasources; "
            f"got {present_tracing} in {names}"
        )
    if not tracing_enabled and present_tracing:
        raise AssertionError(
            "Tracing-off mode must not provision Loki/Tempo datasources; "
            f"got {present_tracing} in {names}"
        )


def _smoke_mode(mode: str, *, timeout_s: float) -> None:
    tracing_enabled = mode == "on"
    grafana_port = _find_free_port()
    suffix = f"smoke-{mode}-{os.getpid()}"
    project_name = f"bioetl-grafana-smoke-{mode}-{os.getpid()}"
    override_text = _build_temp_compose(
        suffix=suffix,
        grafana_port=grafana_port,
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f".{mode}.compose.yml",
        prefix="bioetl-grafana-smoke-",
        delete=False,
        encoding="utf-8",
    ) as handle:
        handle.write(override_text)
        override_path = Path(handle.name)

    compose_env = os.environ.copy()
    compose_env["GF_SECURITY_ADMIN_PASSWORD"] = GRAFANA_PASSWORD
    compose_env["BIOETL_ENABLE_TRACING_DATASOURCES"] = (
        "true" if tracing_enabled else "false"
    )
    compose_command = [
        "docker",
        "compose",
        "-p",
        project_name,
        "-f",
        str(override_path),
    ]

    try:
        up_command = compose_command.copy()
        if tracing_enabled:
            up_command.extend(["--profile", "tracing"])
        up_command.extend(["up", "-d"])
        _run(up_command, env=compose_env)
        _wait_for_grafana(grafana_port, timeout_s=timeout_s)
        datasource_names = _fetch_datasource_names(grafana_port)
        _assert_datasource_expectations(
            datasource_names,
            tracing_enabled=tracing_enabled,
        )
        print(
            json.dumps(
                {
                    "mode": mode,
                    "grafana_port": grafana_port,
                    "datasources": datasource_names,
                }
            )
        )
    finally:
        down_command = compose_command.copy()
        if tracing_enabled:
            down_command.extend(["--profile", "tracing"])
        down_command.extend(["down", "-v", "--remove-orphans"])
        try:
            _run_cleanup(down_command, env=compose_env)
            for service_name in (
                "prometheus",
                "pushgateway",
                "loki",
                "promtail",
                "tempo",
                "grafana",
            ):
                _run_cleanup(
                    ["docker", "rm", "-f", f"bioetl-{service_name}-{suffix}"],
                    env=compose_env,
                )
            _run_cleanup(
                ["docker", "network", "rm", f"{project_name}_monitoring"],
                env=compose_env,
            )
            for volume_name in (
                "prometheus-data",
                "grafana-data",
                "loki-data",
                "tempo-data",
            ):
                _run_cleanup(
                    ["docker", "volume", "rm", f"{project_name}_{volume_name}"],
                    env=compose_env,
                )
        finally:
            override_path.unlink(missing_ok=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a live Grafana datasource smoke against temporary compose stacks "
            "for tracing-off and tracing-on monitoring modes."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("off", "on", "both"),
        default="both",
        help="Which topology mode to verify.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="Per-mode Grafana health timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    modes = ("off", "on") if args.mode == "both" else (args.mode,)
    try:
        for mode in modes:
            _smoke_mode(mode, timeout_s=args.timeout)
    except Exception as exc:  # pragma: no cover - operational failure path
        print(f"live tracing smoke failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
