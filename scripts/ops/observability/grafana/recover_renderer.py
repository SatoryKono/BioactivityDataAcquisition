#!/usr/bin/env python3
"""Recover optional Grafana image renderer without restarting Grafana UI.

Tertiary failure mode on 32 GiB Desktop hosts:
  Chromium OOM / flapping renderer → screenshot hangs → operators restart
  Grafana (wrong) or leave renderer dead after ``restart: on-failure:3``.

Contract:
  - Grafana UI MUST stay up (no force-recreate grafana).
  - Renderer is optional (ADR-010); recovery is explicit and bounded.
  - Pair with GF_RENDERING_RENDERING_TIMEOUT (default 60s) bounded wait.

Usage::

    python scripts/ops/observability/grafana/recover_renderer.py
    python scripts/ops/observability/grafana/recover_renderer.py --wait 90 --json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_COMPOSE = ROOT / "docker-compose.monitoring.yml"
DEFAULT_PROJECT = "bioetl-monitoring"
DEFAULT_WAIT = 90.0


@dataclass(frozen=True)
class RendererSnapshot:
    container_id: str
    name: str
    status: str
    health: str
    oom_killed: bool
    restart_count: int
    memory_limit_bytes: int | None


@dataclass(frozen=True)
class RecoverReport:
    ok: bool
    action: str
    project: str
    compose_file: str
    recreated: bool
    healthy: bool
    grafana_ui_ok: bool | None
    wait_seconds: float
    before: list[dict[str, Any]]
    after: list[dict[str, Any]]
    messages: list[str]
    remediation: list[str]


def _run(
    args: list[str], *, timeout: float = 120.0, cwd: Path = ROOT
) -> tuple[int, str, str]:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    safe_args = ensure_safe_cli_argv(args)
    try:
        proc = subprocess.run(
            safe_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            check=False,
        )
    except FileNotFoundError:
        return 127, "", f"executable not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s: {' '.join(args)}"
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _compose_base(project: str, compose_file: Path) -> list[str]:
    return [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        str(compose_file),
    ]


def list_renderer_snapshots(project: str, compose_file: Path) -> list[RendererSnapshot]:
    code, out, _err = _run(
        [*_compose_base(project, compose_file), "ps", "-q", "renderer"],
        timeout=30.0,
    )
    if code != 0 or not out:
        # Fallback: name filter (project-prefixed container names).
        code, out, _err = _run(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                "name=renderer",
            ],
            timeout=30.0,
        )
    ids = [line.strip() for line in out.splitlines() if line.strip()]
    return [snapshot for cid in ids if (snapshot := _inspect_renderer(cid)) is not None]


def _inspect_renderer(container_id: str) -> RendererSnapshot | None:
    code, raw, _ = _run(
        ["docker", "inspect", "--format", "{{json .}}", container_id],
        timeout=15.0,
    )
    if code != 0 or not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    state = payload.get("State") or {}
    health = (state.get("Health") or {}).get("Status") or "none"
    mem = (payload.get("HostConfig") or {}).get("Memory")
    return RendererSnapshot(
        container_id=container_id[:12],
        name=str(payload.get("Name") or "").lstrip("/"),
        status=str(state.get("Status") or "unknown"),
        health=str(health),
        oom_killed=bool(state.get("OOMKilled")),
        restart_count=int(state.get("RestartCount") or 0),
        memory_limit_bytes=int(mem) if mem else None,
    )


def probe_grafana_ui(*, timeout: float = 5.0) -> bool | None:
    try:
        from urllib.request import urlopen

        with urlopen("http://127.0.0.1:3000/api/health", timeout=timeout) as resp:
            return 200 <= int(resp.status) < 300
    except Exception:
        return False


def _recreate_renderer(
    project: str,
    compose_path: Path,
    *,
    wait_seconds: float,
) -> tuple[bool, str | None]:
    code, out, err = _run(
        [
            *_compose_base(project, compose_path),
            "up",
            "-d",
            "--force-recreate",
            "--no-deps",
            "renderer",
        ],
        timeout=max(120.0, wait_seconds + 30.0),
    )
    return code == 0, None if code == 0 else f"compose up renderer failed: {err or out}"


def _wait_for_renderer(
    project: str,
    compose_path: Path,
    *,
    wait_seconds: float,
    messages: list[str],
) -> tuple[bool, list[dict[str, Any]]]:
    deadline = time.monotonic() + max(5.0, wait_seconds)
    after: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        snaps = list_renderer_snapshots(project, compose_path)
        after = [asdict(s) for s in snaps]
        if any(s.oom_killed for s in snaps):
            messages.append("renderer OOMKilled — free host RAM before retry")
            return False, after
        if any(s.health == "healthy" for s in snaps):
            messages.append("renderer health=healthy")
            return True, after
        time.sleep(3.0)
    return False, after


def recover_renderer(
    *,
    project: str = DEFAULT_PROJECT,
    compose_file: Path = DEFAULT_COMPOSE,
    wait_seconds: float = DEFAULT_WAIT,
    skip_recreate: bool = False,
) -> RecoverReport:
    """Recreate renderer only; wait for healthy; never touch Grafana."""
    messages: list[str] = []
    remediation = [
        "Free host RAM (>= 4 GiB) if OOMKilled",
        "docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml logs renderer --tail 100",
        "Re-run: python scripts/ops/observability/grafana/recover_renderer.py",
        "Do NOT restart Grafana solely for renderer recovery",
    ]
    if shutil.which("docker") is None:
        return RecoverReport(
            ok=False,
            action="recover-renderer",
            project=project,
            compose_file=str(compose_file),
            recreated=False,
            healthy=False,
            grafana_ui_ok=None,
            wait_seconds=wait_seconds,
            before=[],
            after=[],
            messages=["docker executable not found"],
            remediation=remediation,
        )

    compose_path = compose_file if compose_file.is_absolute() else ROOT / compose_file
    before = [asdict(s) for s in list_renderer_snapshots(project, compose_path)]
    recreated = False
    if not skip_recreate:
        recreated, recreate_error = _recreate_renderer(
            project, compose_path, wait_seconds=wait_seconds
        )
        if recreate_error:
            messages.append(recreate_error)
            return RecoverReport(
                ok=False,
                action="recover-renderer",
                project=project,
                compose_file=str(compose_path),
                recreated=False,
                healthy=False,
                grafana_ui_ok=probe_grafana_ui(),
                wait_seconds=wait_seconds,
                before=before,
                after=before,
                messages=messages,
                remediation=remediation,
            )
        messages.append("recreated renderer via compose --no-deps")

    healthy, after = _wait_for_renderer(
        project,
        compose_path,
        wait_seconds=wait_seconds,
        messages=messages,
    )
    messages.extend(_renderer_wait_messages(healthy, after, wait_seconds=wait_seconds))
    grafana_ok = probe_grafana_ui()
    messages.extend(_grafana_probe_messages(grafana_ok))

    return RecoverReport(
        ok=healthy,
        action="recover-renderer",
        project=project,
        compose_file=str(compose_path),
        recreated=recreated,
        healthy=healthy,
        grafana_ui_ok=grafana_ok,
        wait_seconds=wait_seconds,
        before=before,
        after=after,
        messages=messages,
        remediation=remediation if not healthy else [],
    )


def check_renderer_health(
    *,
    project: str = DEFAULT_PROJECT,
    compose_file: Path = DEFAULT_COMPOSE,
) -> RecoverReport:
    """Read-only health snapshot (no recreate)."""
    return recover_renderer(
        project=project,
        compose_file=compose_file,
        wait_seconds=0.1,
        skip_recreate=True,
    )


def _as_check_only_report(report: RecoverReport) -> RecoverReport:
    snapshots = report.after or report.before
    healthy = any(snapshot.get("health") == "healthy" for snapshot in snapshots)
    if healthy:
        status_message = ["renderer healthy"]
        remediation: list[str] = []
    else:
        status_message = ["renderer not healthy (optional service)"]
        remediation = [
            "python scripts/ops/observability/grafana/recover_renderer.py",
            "or: python -m scripts.ops.runtime.docker.runtime_manager recover-renderer --stack monitoring",
        ]
    return RecoverReport(
        ok=healthy,
        action="check-renderer",
        project=report.project,
        compose_file=report.compose_file,
        recreated=False,
        healthy=healthy,
        grafana_ui_ok=report.grafana_ui_ok,
        wait_seconds=0.0,
        before=report.before,
        after=report.after,
        messages=report.messages + status_message,
        remediation=remediation,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE)
    parser.add_argument("--wait", type=float, default=DEFAULT_WAIT)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Do not recreate; only report renderer health",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.check_only:
        report = check_renderer_health(
            project=args.project, compose_file=args.compose_file
        )
        # check-only with wait 0.1 may not see healthy if just starting;
        # re-evaluate from after snapshots.
        report = _as_check_only_report(report)
    else:
        report = recover_renderer(
            project=args.project,
            compose_file=args.compose_file,
            wait_seconds=args.wait,
        )

    payload = asdict(report)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"=== {report.action} (project={report.project}) ===")
        for msg in report.messages:
            print(f"  {msg}")
        if report.before:
            print("  before:", report.before)
        if report.after:
            print("  after:", report.after)
        if report.remediation:
            print("  remediation:")
            for step in report.remediation:
                print(f"    - {step}")
        print("OK" if report.ok else "FAIL (Grafana UI should still work)")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
