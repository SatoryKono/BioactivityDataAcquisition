#!/usr/bin/env python3
"""Measure bounded, secret-free Codex launcher and MCP overhead.

The report intentionally stores command labels rather than argv/stdout/stderr so
prompts, tokens, headers, and machine-local paths cannot leak into evidence.
Optional Docker and monitoring services are never started by this tool.
Use --instruction-refs BEFORE_SHA AFTER_SHA for offline instruction-source
metadata instead; that mode never invokes launcher, MCP or model probes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "bioetl-codex-efficiency-baseline-v1"
DEFAULT_RUNS = 3
DEFAULT_TIMEOUT_SECONDS = 60.0
INSTRUCTION_PREFIXES = tuple(
    f".{runtime}/{surface}/"
    for runtime in ("codex", "junie", "devin")
    for surface in ("agents", "skills")
)
SHARED_INSTRUCTIONS = (
    "AGENTS.md",
    ".junie/guidelines.md",
    "docs/00-project/NORMATIVE_SOURCES.md",
    "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
    "docs/00-project/ai/memory/agent-memory.md",
    "src/memory/DAILY_WORKFLOW.md",
)
INSTRUCTION_SUFFIXES = (".md", ".toml", ".json", ".yaml", ".yml")


def _local_git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    """Read local objects only; inherited Git redirects and lazy fetch are off."""
    checked_args = []
    for argument in args:
        if not re.fullmatch(r"[A-Za-z0-9_./{}^-]+", argument):
            raise ValueError("Unsupported local Git metadata argument")
        checked_args.append(argument)
    environment = {
        k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")
    }
    environment.update(
        GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0"
    )
    return subprocess.run(
        ["git", "-c", "gc.auto=0", "-C", str(root), *checked_args],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
        timeout=30,
        env=environment,
    ).stdout


def _env_part(part: str) -> bool:
    normalized = part.split(":", 1)[0].rstrip(" .").casefold()
    return normalized == ".env" or normalized.startswith(".env.")


def _instruction_group(path: str) -> str | None:
    if any(_env_part(part) for part in path.replace("\\", "/").split("/")):
        return None
    if path in SHARED_INSTRUCTIONS:
        return "shared"
    if path.startswith(INSTRUCTION_PREFIXES) and path.endswith(INSTRUCTION_SUFFIXES):
        return path.split("/", 1)[0][1:]
    return None


def _instruction_entries(tree: bytes) -> list[tuple[str, str, str]]:
    entries = []
    for record in tree.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8")
        group = _instruction_group(path)
        if mode in ("100644", "100755") and kind == "blob" and group:
            entries.append((path, oid, group))
    return sorted(entries)


def _batch_blobs(root: Path, entries: list[tuple[str, str, str]]) -> list[bytes]:
    if not entries:
        raise ValueError("Instruction scope is empty at this commit")
    payload = _local_git(
        root,
        "cat-file",
        "--batch",
        data="".join(oid + "\n" for _, oid, _ in entries).encode("ascii"),
    )
    offset = 0
    blobs = []
    for _, expected_oid, _ in entries:
        end = payload.index(b"\n", offset)
        oid, kind, size = payload[offset:end].decode("ascii").split()
        start = end + 1
        stop = start + int(size)
        if oid != expected_oid or kind != "blob" or payload[stop : stop + 1] != b"\n":
            raise ValueError("Incomplete or unexpected local Git object")
        blobs.append(payload[start:stop].replace(b"\r\n", b"\n"))
        offset = stop + 1
    if offset != len(payload):
        raise ValueError("Unexpected trailing Git object data")
    return blobs


def instruction_snapshot(root: Path, commit: str) -> dict[str, Any]:
    """Return selected source metadata, never prompt text or context estimates."""
    if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", commit):
        raise ValueError("Instruction snapshots require a full local commit SHA")
    resolved = (
        _local_git(
            root, "rev-parse", "--verify", "--end-of-options", commit + "^{commit}"
        )
        .decode("ascii")
        .strip()
    )
    if resolved != commit:
        raise ValueError("Commit identity changed")
    entries = _instruction_entries(
        _local_git(
            root,
            "ls-tree",
            "-rz",
            commit,
            "--",
            *INSTRUCTION_PREFIXES,
            *SHARED_INSTRUCTIONS,
        )
    )
    groups = {
        g: {"files": 0, "bytes_lf": 0, "lines": 0}
        for g in ("codex", "junie", "devin", "shared")
    }
    files = {}
    for (path, _, group), blob in zip(
        entries, _batch_blobs(root, entries), strict=True
    ):
        item = {
            "sha256_lf": hashlib.sha256(blob).hexdigest(),
            "bytes_lf": len(blob),
            "lines": len(blob.splitlines()),
        }
        files[path] = item
        groups[group]["files"] += 1
        groups[group]["bytes_lf"] += item["bytes_lf"]
        groups[group]["lines"] += item["lines"]
    return {"commit": commit, "groups": groups, "files": files}


def compare_instructions(root: Path, before: str, after: str) -> dict[str, Any]:
    """Compare two immutable local source trees without executing any probe."""
    baseline = instruction_snapshot(root, before)
    candidate = instruction_snapshot(root, after)
    changes = []
    for path in sorted(baseline["files"].keys() | candidate["files"].keys()):
        old, new = baseline["files"].get(path), candidate["files"].get(path)
        if old != new:
            changes.append({"path": path, "before": old, "after": new})
    return {
        "schema_version": "bioetl-instruction-source-comparison-v1",
        "generator_sha256_lf": hashlib.sha256(
            Path(__file__).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
        "scope": {
            "prefixes": INSTRUCTION_PREFIXES,
            "shared_paths": SHARED_INSTRUCTIONS,
            "suffixes": INSTRUCTION_SUFFIXES,
            "regular_blobs_only": True,
        },
        "policy": {
            "mode": "offline_local_git",
            "normalization": "CRLF to LF",
            "raw_contents_retained": False,
            "agents_or_probes_started": False,
            "interpretation": "selected source metadata; not loaded context, tokens, usage frequency or savings",
        },
        "baseline": {k: v for k, v in baseline.items() if k != "files"},
        "after": {k: v for k, v in candidate.items() if k != "files"},
        "changes": changes,
        "runtime_metrics": dict.fromkeys(
            (
                "loaded_sources",
                "repeated_reads",
                "tool_calls",
                "elapsed_time",
                "tokens",
                "route_correctness",
                "skipped_checks",
                "task_quality",
            ),
            "NOT_MEASURED",
        ),
    }


def _check_output_target(path: Path) -> None:
    for candidate in (path.absolute(), path.resolve()):
        if any(_env_part(part) for part in candidate.parts):
            raise ValueError("Reports cannot target environment files or directories")


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
        (
            "mcp_ensure_check",
            [
                "bash",
                str(launcher),
                "mcp-check",
                "--profile",
                "stable",
                "--timeout",
                "1",
                "--overall-timeout",
                "10",
                "--no-write",
            ],
        ),
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
    parser.add_argument(
        "--instruction-refs",
        nargs=2,
        metavar=("BEFORE_SHA", "AFTER_SHA"),
        help="Offline source metadata only; no launcher, MCP or model probes",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.output:
        _check_output_target(args.output)
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be > 0")
    if args.instruction_refs:
        try:
            report = compare_instructions(_repo_root(), *args.instruction_refs)
        except (ValueError, OSError, subprocess.SubprocessError):
            raise SystemExit(
                "Local instruction snapshot unavailable; no fetch or probe attempted"
            ) from None
    else:
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
    if args.instruction_refs:
        return 0
    failed = any(
        summary["status_counts"]["failed"]
        or summary["status_counts"]["timed_out"]
        or summary["status_counts"]["unavailable"]
        for summary in report["probes"].values()
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
