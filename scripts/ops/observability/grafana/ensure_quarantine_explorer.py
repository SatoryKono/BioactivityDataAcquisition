#!/usr/bin/env python3
"""Ensure the long-lived Quarantine Explorer backend for Grafana HTTP panels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[4]
    src_root = repo_root / "src"
    for path in (str(repo_root), str(src_root)):
        if path not in sys.path:
            sys.path.insert(0, path)

from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    DEFAULT_HEALTH_SERVER_PORT,
    DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST,
    DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST,
    DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
    build_observability_backend_health_url,
    ensure_observability_backend_started,
    probe_observability_backend,
)

DEFAULT_IDENTITY_PROBE = (
    "/ops/control-plane/identity-table?pipeline=unknown&run_type=__all&run_id=-"
)
DEFAULT_PROCESSED_RECORDS_PROBE = (
    "/ops/observability/processed-records?pipeline=chembl_target&run_type=backfill"
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Start or reuse bioetl quarantine serve on port 8081 so Grafana ID and "
            "Processed Records HTTP panels can load data."
        )
    )
    parser.add_argument("--port", type=int, default=DEFAULT_HEALTH_SERVER_PORT)
    parser.add_argument(
        "--bind-host",
        default=DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST,
        help="Listen address for the detached backend (default 0.0.0.0 for Docker/Grafana).",
    )
    parser.add_argument(
        "--probe-host",
        default=DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST,
        help="Host used for local readiness probes (default 127.0.0.1).",
    )
    parser.add_argument(
        "--refresh",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Restart a stale listener missing required HTTP routes.",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    required_probe_paths = (
        DEFAULT_IDENTITY_PROBE,
        DEFAULT_PROCESSED_RECORDS_PROBE,
    )
    if args.refresh:
        from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
            drop_listening_backend_on_port,
            probe_observability_backend_required_paths,
        )

        health_url = build_observability_backend_health_url(
            host=args.probe_host,
            port=args.port,
        )
        if probe_observability_backend(health_url) and not probe_observability_backend_required_paths(
            health_url,
            required_probe_paths=required_probe_paths,
        ):
            drop_listening_backend_on_port(args.port)

    result = ensure_observability_backend_started(
        enabled=True,
        port=args.port,
        probe_host=args.probe_host,
        bind_host=args.bind_host,
        ready_timeout_seconds=max(DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS, 60.0),
        required_probe_paths=required_probe_paths,
    )
    payload = {
        "status": result.status,
        "health_url": result.health_url,
        "backend_available": result.backend_available,
        "pid": result.pid,
        "message": result.message,
        "command": list(result.command),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"quarantine-explorer: {result.status} -> {result.health_url}")
        if result.message:
            print(result.message)
        if result.command:
            print("command:", " ".join(result.command))
    return 0 if result.backend_available else 1


if __name__ == "__main__":
    raise SystemExit(main())
