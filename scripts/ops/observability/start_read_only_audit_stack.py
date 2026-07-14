#!/usr/bin/env python3
"""Start and verify the fail-closed read-only observability audit stack."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_COMPOSE = REPO_ROOT / "docker-compose.monitoring.yml"
AUDIT_COMPOSE = REPO_ROOT / "docker-compose.monitoring.audit.yml"
READY_URL = "http://127.0.0.1:18081/ops/control-plane/ready"


def require_absolute_directory(value: str, *, option_name: str) -> Path:
    """Return one resolved existing directory or fail before Docker is invoked."""
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{option_name} must be an absolute path: {value}")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"{option_name} must identify a directory: {value}")
    return resolved


def build_compose_command() -> tuple[str, ...]:
    """Build the only supported compose invocation for the audit profile."""
    return (
        "docker",
        "compose",
        "-f",
        str(BASE_COMPOSE),
        "-f",
        str(AUDIT_COMPOSE),
        "--profile",
        "audit",
        "up",
        "-d",
        "prometheus",
        "pushgateway",
        "quarantine-explorer-audit",
        "loki",
        "promtail-audit",
        "grafana",
        "renderer",
    )


def _read_ready_data_root(
    *,
    opener: Callable[..., Any],
) -> str | None:
    with opener(READY_URL, timeout=3.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return None
    value = payload.get("data_root")
    return str(value) if value is not None else None


def start_and_verify_audit_stack(
    *,
    data_root: Path,
    log_root: Path,
    timeout_seconds: float,
    run: Callable[..., subprocess.CompletedProcess[object]] = subprocess.run,
    opener: Callable[..., Any] = urlopen,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Start the audit stack and prove that HTTP serves the requested root."""
    environment = os.environ.copy()
    environment["BIOETL_AUDIT_DATA_ROOT"] = str(data_root)
    environment["BIOETL_AUDIT_LOG_ROOT"] = str(log_root)
    run(
        build_compose_command(),
        cwd=REPO_ROOT,
        env=environment,
        check=True,
    )

    deadline = monotonic() + timeout_seconds
    last_error = "backend not probed"
    while monotonic() < deadline:
        try:
            served_root = _read_ready_data_root(opener=opener)
        except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            if served_root == str(data_root):
                return
            last_error = (
                f"backend served data_root={served_root!r}; "
                f"expected {str(data_root)!r}"
            )
        sleep(1.0)
    raise RuntimeError(f"read-only audit backend verification failed: {last_error}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--log-root", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse explicit roots, launch the isolated stack, and verify routing."""
    args = _build_parser().parse_args(argv)
    try:
        data_root = require_absolute_directory(
            args.data_root,
            option_name="--data-root",
        )
        log_root = require_absolute_directory(
            args.log_root,
            option_name="--log-root",
        )
        start_and_verify_audit_stack(
            data_root=data_root,
            log_root=log_root,
            timeout_seconds=args.timeout_seconds,
        )
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        _build_parser().error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
