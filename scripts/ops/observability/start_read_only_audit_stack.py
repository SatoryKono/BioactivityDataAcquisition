#!/usr/bin/env python3
"""Start and verify the fail-closed read-only observability audit stack."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections.abc import Callable, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, NamedTuple
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_COMPOSE = REPO_ROOT / "docker-compose.monitoring.yml"
AUDIT_COMPOSE = (
    REPO_ROOT
    / "scripts"
    / "ops"
    / "observability"
    / "docker-compose.monitoring.audit.yml"
)
READY_URL = "http://127.0.0.1:18081/ops/control-plane/ready"
CATALOG_URL = (
    "http://127.0.0.1:18081/ops/control-plane/filter-options"
    "?dimension=pipeline&response_shape=list"
)


class AuditBackendState(StrEnum):
    """Operator-visible classification of the isolated audit backend."""

    DOWN = "down"
    TIMEOUT = "timeout"
    WRONG_ROOT = "wrong-root"
    VALID_EMPTY = "valid-empty"
    POPULATED = "populated"


class AuditBackendProbeResult(NamedTuple):
    """One classified probe result with enough detail for diagnostics."""

    state: AuditBackendState
    detail: str
    data_root: str | None = None
    item_count: int | None = None


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


def _read_json_payload(
    url: str,
    *,
    opener: Callable[..., Any],
) -> dict[str, Any]:
    with opener(url, timeout=3.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"backend returned a non-object payload for {url}")
    return payload


def probe_audit_backend(
    *,
    expected_data_root: Path,
    opener: Callable[..., Any] = urlopen,
) -> AuditBackendProbeResult:
    """Classify readiness, routing, and whether the audit catalog has data."""
    try:
        ready_payload = _read_json_payload(READY_URL, opener=opener)
    except TimeoutError as exc:
        return AuditBackendProbeResult(
            AuditBackendState.TIMEOUT,
            f"readiness request timed out: {exc}",
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return AuditBackendProbeResult(
            AuditBackendState.DOWN,
            f"readiness request failed: {type(exc).__name__}: {exc}",
        )

    raw_root = ready_payload.get("data_root")
    served_root = str(raw_root) if raw_root is not None else None
    if served_root != str(expected_data_root):
        return AuditBackendProbeResult(
            AuditBackendState.WRONG_ROOT,
            (
                f"backend served data_root={served_root!r}; "
                f"expected {str(expected_data_root)!r}"
            ),
            data_root=served_root,
        )

    try:
        catalog_payload = _read_json_payload(CATALOG_URL, opener=opener)
    except TimeoutError as exc:
        return AuditBackendProbeResult(
            AuditBackendState.TIMEOUT,
            f"catalog request timed out: {exc}",
            data_root=served_root,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return AuditBackendProbeResult(
            AuditBackendState.DOWN,
            f"catalog request failed: {type(exc).__name__}: {exc}",
            data_root=served_root,
        )

    items = catalog_payload.get("items")
    if not isinstance(items, list):
        return AuditBackendProbeResult(
            AuditBackendState.DOWN,
            "catalog response is missing a list-valued items field",
            data_root=served_root,
        )
    state = AuditBackendState.POPULATED if items else AuditBackendState.VALID_EMPTY
    return AuditBackendProbeResult(
        state,
        f"audit catalog contains {len(items)} pipeline item(s)",
        data_root=served_root,
        item_count=len(items),
    )


def start_and_verify_audit_stack(
    *,
    data_root: Path,
    log_root: Path,
    timeout_seconds: float,
    run: Callable[..., subprocess.CompletedProcess[object]] = subprocess.run,
    opener: Callable[..., Any] = urlopen,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> AuditBackendProbeResult:
    """Start the audit stack and prove routing plus a valid catalog response."""
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
    last_result = AuditBackendProbeResult(
        AuditBackendState.DOWN,
        "backend not probed",
    )
    while monotonic() < deadline:
        last_result = probe_audit_backend(
            expected_data_root=data_root,
            opener=opener,
        )
        if last_result.state in {
            AuditBackendState.VALID_EMPTY,
            AuditBackendState.POPULATED,
        }:
            return last_result
        if last_result.state is AuditBackendState.WRONG_ROOT:
            raise RuntimeError(
                "read-only audit backend verification failed: "
                f"state={last_result.state.value}; {last_result.detail}"
            )
        sleep(1.0)
    raise RuntimeError(
        "read-only audit backend verification failed: "
        f"state={last_result.state.value}; {last_result.detail}"
    )


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
