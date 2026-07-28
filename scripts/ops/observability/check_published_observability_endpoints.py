#!/usr/bin/env python3
"""Check published observability endpoints against container-internal health."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from collections.abc import Callable, Iterable
from urllib import error, request


@dataclass(frozen=True)
class EndpointSpec:
    """Describe one observability endpoint to probe."""

    name: str
    published_url: str
    container_name: str
    container_internal_url: str
    description: str


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of a single HTTP or container probe."""

    ok: bool
    status_code: int | None = None
    detail: str | None = None


@dataclass(frozen=True)
class EndpointCheck:
    """Combined health view for one published endpoint."""

    name: str
    published_url: str
    container_name: str
    container_internal_url: str
    description: str
    published_probe: ProbeResult
    container_probe: ProbeResult | None
    diagnosis: str


CORE_ENDPOINTS: tuple[EndpointSpec, ...] = (
    EndpointSpec(
        name="grafana",
        published_url="http://127.0.0.1:3000/api/health",
        container_name="bioetl-grafana",
        container_internal_url="http://127.0.0.1:3000/api/health",
        description="Grafana published API health",
    ),
    EndpointSpec(
        name="prometheus",
        published_url="http://127.0.0.1:9090/-/healthy",
        container_name="bioetl-prometheus",
        container_internal_url="http://127.0.0.1:9090/-/healthy",
        description="Prometheus published API health",
    ),
    EndpointSpec(
        name="pushgateway",
        published_url="http://127.0.0.1:9091/-/healthy",
        container_name="bioetl-pushgateway",
        container_internal_url="http://127.0.0.1:9091/-/healthy",
        description="Pushgateway published API health",
    ),
)


def _fetch_http(url: str, timeout_seconds: float) -> ProbeResult:
    try:
        with request.urlopen(url, timeout=timeout_seconds) as response:
            status_code = getattr(response, "status", None)
            detail = response.read(200).decode("utf-8", errors="replace").strip()
            return ProbeResult(
                ok=bool(status_code and 200 <= status_code < 300),
                status_code=status_code,
                detail=detail or None,
            )
    except error.HTTPError as exc:
        detail = exc.read(200).decode("utf-8", errors="replace").strip()
        return ProbeResult(ok=False, status_code=exc.code, detail=detail or str(exc))
    except Exception as exc:  # pragma: no cover - exercised via callers
        return ProbeResult(ok=False, detail=str(exc))


def _probe_container_internal(
    container_name: str,
    url: str,
    timeout_seconds: float,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProbeResult:
    command = [
        "docker",
        "exec",
        container_name,
        "wget",
        "-qO-",
        url,
    ]
    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - exercised via callers
        return ProbeResult(ok=False, detail=str(exc))

    detail = (completed.stdout or completed.stderr or "").strip() or None
    return ProbeResult(
        ok=completed.returncode == 0,
        status_code=completed.returncode,
        detail=detail,
    )


def _classify_diagnosis(
    published_probe: ProbeResult,
    container_probe: ProbeResult | None,
) -> str:
    if published_probe.ok and (container_probe is None or container_probe.ok):
        return "healthy"
    if not published_probe.ok and container_probe and container_probe.ok:
        return "published_port_unreachable_but_container_healthy"
    if published_probe.ok and container_probe and not container_probe.ok:
        return "published_port_healthy_but_container_probe_failed"
    if not published_probe.ok and container_probe and not container_probe.ok:
        return "published_and_container_unhealthy"
    if published_probe.ok:
        return "published_healthy"
    return "published_unhealthy"


def run_checks(
    *,
    endpoints: Iterable[EndpointSpec] = CORE_ENDPOINTS,
    timeout_seconds: float = 3.0,
    include_container_checks: bool = True,
    http_probe: Callable[[str, float], ProbeResult] = _fetch_http,
    container_probe: Callable[
        [str, str, float], ProbeResult
    ] = _probe_container_internal,
) -> list[EndpointCheck]:
    checks: list[EndpointCheck] = []
    for endpoint in endpoints:
        published_result = http_probe(endpoint.published_url, timeout_seconds)
        container_result = (
            container_probe(
                endpoint.container_name,
                endpoint.container_internal_url,
                timeout_seconds,
            )
            if include_container_checks
            else None
        )
        checks.append(
            EndpointCheck(
                name=endpoint.name,
                published_url=endpoint.published_url,
                container_name=endpoint.container_name,
                container_internal_url=endpoint.container_internal_url,
                description=endpoint.description,
                published_probe=published_result,
                container_probe=container_result,
                diagnosis=_classify_diagnosis(published_result, container_result),
            )
        )
    return checks


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check host-published Grafana/Prometheus-style endpoints and compare "
            "them with container-internal health probes."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Render the full check result as JSON.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=3.0,
        help="Per-endpoint timeout for both published and container probes.",
    )
    parser.add_argument(
        "--skip-container-check",
        action="store_true",
        help="Only probe host-published URLs; skip docker exec container checks.",
    )
    parser.add_argument(
        "--require-container-health",
        action="store_true",
        help="Return non-zero when an internal container probe fails.",
    )
    return parser


def _format_text(checks: Iterable[EndpointCheck]) -> str:
    lines = []
    for check in checks:
        published = "ok" if check.published_probe.ok else "failed"
        container_probe = check.container_probe
        if container_probe is None:
            container = "skipped"
        elif container_probe.ok:
            container = "ok"
        else:
            container = "failed"
        lines.append(
            f"{check.name}: diagnosis={check.diagnosis} "
            f"published={published} container={container}"
        )
        if not check.published_probe.ok and check.published_probe.detail:
            lines.append(f"  published_detail: {check.published_probe.detail}")
        if container_probe and not container_probe.ok and container_probe.detail:
            lines.append(f"  container_detail: {container_probe.detail}")
    return "\n".join(lines)


def _exit_code(
    checks: Iterable[EndpointCheck],
    *,
    require_container_health: bool,
) -> int:
    for check in checks:
        if not check.published_probe.ok:
            return 1
        if require_container_health and check.container_probe is not None:
            if not check.container_probe.ok:
                return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    checks = run_checks(
        timeout_seconds=args.timeout_seconds,
        include_container_checks=not args.skip_container_check,
    )

    if args.json:
        payload = {
            "checks": [
                {
                    **asdict(check),
                }
                for check in checks
            ]
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(_format_text(checks))

    return _exit_code(
        checks,
        require_container_health=args.require_container_health,
    )


if __name__ == "__main__":
    raise SystemExit(main())
