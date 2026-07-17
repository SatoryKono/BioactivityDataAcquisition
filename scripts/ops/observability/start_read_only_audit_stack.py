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
from tempfile import NamedTemporaryFile, mkdtemp


MAX_PROBE_TIMEOUT_SECONDS = 3.0
from typing import Any, NamedTuple
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4

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
PROMTAIL_READY_URL = "http://127.0.0.1:19080/ready"
LOKI_QUERY_RANGE_URL = "http://127.0.0.1:3100/loki/api/v1/query_range"
PROMTAIL_SENTINEL_PREFIX = "bioetl-promtail-audit-sentinel:"
PROMTAIL_SENTINEL_LOOKBACK_NS = 300 * 1_000_000_000


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


class PromtailAuditState(StrEnum):
    """Observable state of Promtail readiness and sentinel delivery."""

    DOWN = "down"
    PENDING = "pending"
    DELIVERED = "delivered"


class PromtailAuditProbeResult(NamedTuple):
    """One fail-closed Promtail readiness and delivery result."""

    state: PromtailAuditState
    detail: str


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
    timeout: float = MAX_PROBE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    with opener(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"backend returned a non-object payload for {url}")
    return payload


def _read_text_payload(
    url: str,
    *,
    opener: Callable[..., Any],
    timeout: float = MAX_PROBE_TIMEOUT_SECONDS,
) -> str:
    with opener(url, timeout=timeout) as response:
        return response.read().decode("utf-8").strip()


def write_promtail_audit_sentinel(probe_log_root: Path, *, sentinel_id: str) -> str:
    """Write one unique probe line outside the operator's read-only log root."""
    probe_log_root.mkdir(parents=True, exist_ok=True)
    marker = f"{PROMTAIL_SENTINEL_PREFIX}{sentinel_id}"
    path = probe_log_root / f"bioetl-promtail-audit-sentinel-{sentinel_id}.log"
    payload = json.dumps(
        {
            "event": "bioetl_promtail_audit_sentinel",
            "level": "info",
            "message": marker,
        },
        sort_keys=True,
    ) + "\n"
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=probe_log_root,
        prefix=f".{path.name}.",
        delete=False,
    ) as temporary:
        temporary.write(payload)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return marker


def probe_promtail_audit_delivery(
    *,
    marker: str,
    opener: Callable[..., Any] = urlopen,
    wall_time_ns: Callable[[], int] = time.time_ns,
    sentinel_written_ns: int | None = None,
    timeout: float = MAX_PROBE_TIMEOUT_SECONDS,
) -> PromtailAuditProbeResult:
    """Require both Promtail readiness and observable Loki sentinel delivery."""
    try:
        readiness = _read_text_payload(PROMTAIL_READY_URL, opener=opener, timeout=timeout)
    except (OSError, UnicodeError) as exc:
        return PromtailAuditProbeResult(
            PromtailAuditState.DOWN,
            f"Promtail readiness request failed: {type(exc).__name__}: {exc}",
        )
    if readiness.lower() != "ready":
        return PromtailAuditProbeResult(
            PromtailAuditState.DOWN,
            f"Promtail readiness returned {readiness[:80]!r}",
        )

    end_ns = wall_time_ns()
    start_ns = (sentinel_written_ns or end_ns) - PROMTAIL_SENTINEL_LOOKBACK_NS
    query_url = f"{LOKI_QUERY_RANGE_URL}?" + urlencode(
        {
            "query": f'{{job="bioetl-audit"}} |= "{marker}"',
            "start": start_ns,
            "end": end_ns,
            "limit": 100,
        }
    )
    try:
        payload = _read_json_payload(query_url, opener=opener, timeout=timeout)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        return PromtailAuditProbeResult(
            PromtailAuditState.DOWN,
            f"Loki sentinel query failed: {type(exc).__name__}: {exc}",
        )
    data = payload.get("data")
    results = data.get("result") if isinstance(data, dict) else None
    if payload.get("status") != "success" or not isinstance(results, list):
        return PromtailAuditProbeResult(
            PromtailAuditState.DOWN,
            "Loki sentinel query returned an invalid response shape",
        )
    for result in results:
        values = result.get("values") if isinstance(result, dict) else None
        if not isinstance(values, list):
            continue
        if any(
            isinstance(value, list) and len(value) >= 2 and marker in str(value[1])
            for value in values
        ):
            return PromtailAuditProbeResult(
                PromtailAuditState.DELIVERED,
                "Promtail audit sentinel is visible in Loki",
            )
    return PromtailAuditProbeResult(
        PromtailAuditState.PENDING,
        "Promtail is ready but the audit sentinel is not yet visible in Loki",
    )


def probe_audit_backend(
    *,
    expected_data_root: Path,
    opener: Callable[..., Any] = urlopen,
    timeout: float = MAX_PROBE_TIMEOUT_SECONDS,
) -> AuditBackendProbeResult:
    """Classify readiness, routing, and whether the audit catalog has data."""
    try:
        ready_payload = _read_json_payload(READY_URL, opener=opener, timeout=timeout)
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
        catalog_payload = _read_json_payload(CATALOG_URL, opener=opener, timeout=timeout)
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
    wall_time_ns: Callable[[], int] = time.time_ns,
    sentinel_id: str | None = None,
    probe_log_root: Path | None = None,
) -> AuditBackendProbeResult:
    """Start the audit stack and prove routing, catalog, and log delivery."""
    managed_probe_root = probe_log_root is None
    resolved_probe_log_root = (
        probe_log_root or Path(mkdtemp(prefix="bioetl-promtail-audit-probe-"))
    ).resolve()
    if managed_probe_root:
        resolved_probe_log_root.chmod(0o755)
    sentinel_written_ns = wall_time_ns()
    deadline = monotonic() + timeout_seconds
    marker = write_promtail_audit_sentinel(
        resolved_probe_log_root,
        sentinel_id=sentinel_id or uuid4().hex,
    )
    environment = os.environ.copy()
    environment["BIOETL_AUDIT_DATA_ROOT"] = str(data_root)
    environment["BIOETL_AUDIT_LOG_ROOT"] = str(log_root)
    environment["BIOETL_AUDIT_PROBE_LOG_ROOT"] = str(resolved_probe_log_root)
    run(
        build_compose_command(),
        cwd=REPO_ROOT,
        env=environment,
        check=True,
    )

    last_result = AuditBackendProbeResult(
        AuditBackendState.DOWN,
        "backend not probed",
    )
    last_promtail = PromtailAuditProbeResult(
        PromtailAuditState.DOWN,
        "Promtail not probed",
    )
    while monotonic() < deadline:
        remaining = max(0.0, deadline - monotonic())
        probe_timeout = min(MAX_PROBE_TIMEOUT_SECONDS, max(0.1, remaining))
        last_result = probe_audit_backend(
            expected_data_root=data_root,
            opener=opener,
            timeout=probe_timeout,
        )
        if last_result.state in {
            AuditBackendState.VALID_EMPTY,
            AuditBackendState.POPULATED,
        }:
            last_promtail = probe_promtail_audit_delivery(
                marker=marker,
                opener=opener,
                wall_time_ns=wall_time_ns,
                sentinel_written_ns=sentinel_written_ns,
                timeout=min(MAX_PROBE_TIMEOUT_SECONDS, max(0.1, deadline - monotonic())),
            )
            if last_promtail.state is PromtailAuditState.DELIVERED:
                return last_result
        if last_result.state is AuditBackendState.WRONG_ROOT:
            raise RuntimeError(
                "read-only audit backend verification failed: "
                f"state={last_result.state.value}; {last_result.detail}"
            )
        sleep(min(1.0, max(0.0, deadline - monotonic())))
    raise RuntimeError(
        "read-only audit stack verification failed: "
        f"backend_state={last_result.state.value}; {last_result.detail}; "
        f"promtail_state={last_promtail.state.value}; {last_promtail.detail}"
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
