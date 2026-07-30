#!/usr/bin/env python3
"""Measure bounded, secret-free Codex launcher and MCP overhead.

The report intentionally stores command labels rather than argv/stdout/stderr so
prompts, tokens, headers, and machine-local paths cannot leak into evidence.
Optional Docker and monitoring services are never started by this tool.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "bioetl-codex-efficiency-baseline-v1"
DEFAULT_RUNS = 3
DEFAULT_TIMEOUT_SECONDS = 60.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _codex_bin() -> Path | str:
    override = os.environ.get("CODEX_BIN")
    if override:
        return override
    managed = Path.home() / ".cache" / "bioetl-codex" / "npm-global" / "bin" / "codex"
    return managed if managed.is_file() else "codex"


def _probe_commands(root: Path) -> list[tuple[str, list[str]]]:
    launcher = root / "scripts" / "ai" / "codex" / "run-codex.sh"
    headless = root / "scripts" / "ai" / "codex" / "headless.sh"
    return [
        ("codex_version", [str(_codex_bin()), "--version"]),
        ("launcher_help", ["bash", str(launcher), "--help"]),
        ("headless_help", ["bash", str(headless), "--help"]),
        ("environment_check", ["bash", str(launcher), "check"]),
        ("mcp_ensure_check", ["bash", str(launcher), "mcp-check"]),
    ]


def _run_probe(
    label: str,
    argv: list[str],
    *,
    root: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            cwd=root,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            env=os.environ.copy(),
        )
        status = "passed" if result.returncode == 0 else "failed"
        returncode: int | None = result.returncode
    except subprocess.TimeoutExpired:
        status = "timed_out"
        returncode = None
    except OSError:
        status = "unavailable"
        returncode = None
    return {
        "label": label,
        "status": status,
        "returncode": returncode,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


def _summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    durations = [int(sample["duration_ms"]) for sample in samples]
    return {
        "runs": len(samples),
        "status_counts": {
            status: sum(sample["status"] == status for sample in samples)
            for status in ("passed", "failed", "timed_out", "unavailable")
        },
        "duration_ms": {
            "min": min(durations),
            "median": round(statistics.median(durations)),
            "max": max(durations),
        },
        "samples": samples,
    }


def collect_baseline(
    *,
    root: Path,
    runs: int = DEFAULT_RUNS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Collect a bounded baseline without retaining subprocess output."""
    probes: dict[str, list[dict[str, Any]]] = {}
    for label, argv in _probe_commands(root):
        probes[label] = [
            _run_probe(
                label,
                argv,
                root=root,
                timeout_seconds=timeout_seconds,
            )
            for _ in range(runs)
        ]
    return {
        "schema_version": SCHEMA_VERSION,
        "host": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "wsl": bool(os.environ.get("WSL_DISTRO_NAME")),
        },
        "policy": {
            "runs": runs,
            "timeout_seconds": timeout_seconds,
            "captures_subprocess_output": False,
            "starts_optional_services": False,
        },
        "probes": {label: _summarize(samples) for label, samples in probes.items()},
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument(
        "--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be > 0")
    report = collect_baseline(
        root=_repo_root(),
        runs=args.runs,
        timeout_seconds=args.timeout_seconds,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    failed = any(
        summary["status_counts"]["failed"]
        or summary["status_counts"]["timed_out"]
        or summary["status_counts"]["unavailable"]
        for summary in report["probes"].values()
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
