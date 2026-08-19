#!/usr/bin/env python3
"""Fail-closed smoke check: BioETL Prometheus scrape target must be UP.

Canonical topology (docker-compose.monitoring network):
  job_name: bioetl
  target: bioetl:8000
  scrape_interval: 30s

Host-side override (optional, not default): host.docker.internal:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

_LOCAL_HTTP = "http"
DEFAULT_PROMETHEUS_URL = f"{_LOCAL_HTTP}://localhost:9090"
EXIT_OK = 0
EXIT_TARGET_DOWN = 1
EXIT_NO_TARGET = 2
EXIT_PROMETHEUS = 3


def _fetch_targets(prometheus_url: str, timeout: float) -> list[dict[str, object]]:
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    prometheus_url = ensure_local_http_url(prometheus_url)
    url = f"{prometheus_url.rstrip('/')}/api/v1/targets"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise RuntimeError(f"unexpected targets payload: {payload!r}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("targets data is not an object")
    active = data.get("activeTargets") or []
    if not isinstance(active, list):
        raise RuntimeError("activeTargets is not a list")
    return [item for item in active if isinstance(item, dict)]


def _emit_error(detail: str, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"status": "error", "detail": detail}, indent=2))
    else:
        print(detail, file=sys.stderr)


def _emit_summary(summary: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2))
        return
    targets = summary.get("targets")
    if not isinstance(targets, list):
        return
    for item in targets:
        if isinstance(item, dict):
            print(f"{item.get('scrapeUrl')}: {item.get('health')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prometheus-url",
        default=DEFAULT_PROMETHEUS_URL,
        help=f"Prometheus base URL (default {DEFAULT_PROMETHEUS_URL})",
    )
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        targets = _fetch_targets(args.prometheus_url, args.timeout_seconds)
    except (
        urllib.error.URLError,
        TimeoutError,
        RuntimeError,
        json.JSONDecodeError,
    ) as exc:
        detail = f"prometheus unreachable or invalid: {exc}"
        _emit_error(detail, as_json=args.json)
        return EXIT_PROMETHEUS

    bioetl: list[dict[str, object]] = []
    for target in targets:
        labels = target.get("labels")
        if isinstance(labels, dict) and str(labels.get("job", "")).lower() == "bioetl":
            bioetl.append(target)
    if not bioetl:
        detail = (
            "no active Prometheus job named 'bioetl' "
            "(expected target bioetl:8000 in grafana/prometheus.yml)"
        )
        _emit_error(detail, as_json=args.json)
        return EXIT_NO_TARGET

    unhealthy = [
        target for target in bioetl if str(target.get("health", "")).lower() != "up"
    ]
    target_summaries = [
        {
            "scrapeUrl": target.get("scrapeUrl"),
            "health": target.get("health"),
            "lastError": target.get("lastError"),
        }
        for target in bioetl
    ]
    summary = {
        "status": "ok" if not unhealthy else "error",
        "job": "bioetl",
        "canonical_target": "bioetl:8000",
        "scrape_interval": "30s",
        "targets": target_summaries,
    }
    _emit_summary(summary, as_json=args.json)
    return EXIT_OK if not unhealthy else EXIT_TARGET_DOWN


if __name__ == "__main__":
    raise SystemExit(main())
