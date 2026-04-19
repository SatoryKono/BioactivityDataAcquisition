#!/usr/bin/env python3
"""Probe narrow pytest/mypy quality gates with timeout and first-output logging."""

from __future__ import annotations

import argparse
import json
import os
import queue
import shlex
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIMEOUT_SECONDS = 15.0
NARROW_PYTEST_PLUGINS = (
    "anyio.pytest_plugin",
    "pytest_asyncio.plugin",
    "_hypothesis_pytestplugin",
    "pytest_timeout",
    "syrupy",
    "pytest_archon.plugin",
)


@dataclass(slots=True)
class Probe:
    name: str
    description: str
    command: list[str]


@dataclass(slots=True)
class ProbeResult:
    name: str
    description: str
    command: list[str]
    timeout_seconds: float
    exit_code: int | None
    duration_seconds: float
    first_output_latency_seconds: float | None
    timed_out: bool
    stdout: str
    stderr: str

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "command": self.command,
            "timeout_seconds": self.timeout_seconds,
            "exit_code": self.exit_code,
            "duration_seconds": round(self.duration_seconds, 3),
            "first_output_latency_seconds": (
                None
                if self.first_output_latency_seconds is None
                else round(self.first_output_latency_seconds, 3)
            ),
            "timed_out": self.timed_out,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def _preferred_python() -> tuple[str, str]:
    wsl_venv_dir = Path(
        os.environ.get("BIOETL_WSL_VENV_DIR", str(Path.home() / ".venvs" / "bioetl"))
    )
    wsl_python = wsl_venv_dir / "bin" / "python"
    if wsl_python.exists():
        return str(wsl_python), "wsl-venv"

    repo_python = REPO_ROOT / ".venv" / "bin" / "python"
    if repo_python.exists():
        return str(repo_python), "repo-posix-venv"

    return sys.executable, "current-interpreter"


def _stream_reader(
    stream: object,
    stream_name: str,
    output_queue: queue.Queue[tuple[str, str, float]],
) -> None:
    readline = getattr(stream, "readline", None)
    close = getattr(stream, "close", None)
    if readline is None:
        return

    try:
        while True:
            line = readline()
            if line == "":
                break
            output_queue.put((stream_name, line, time.monotonic()))
    finally:
        if close is not None:
            close()


def _run_probe(
    probe: Probe,
    *,
    timeout_seconds: float,
    cwd: Path,
    env: dict[str, str],
) -> ProbeResult:
    start = time.monotonic()
    process = subprocess.Popen(
        probe.command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    output_queue: queue.Queue[tuple[str, str, float]] = queue.Queue()
    threads = [
        threading.Thread(
            target=_stream_reader,
            args=(process.stdout, "stdout", output_queue),
            daemon=True,
        ),
        threading.Thread(
            target=_stream_reader,
            args=(process.stderr, "stderr", output_queue),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    first_output_latency: float | None = None
    timed_out = False

    while True:
        if time.monotonic() - start > timeout_seconds:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
            break

        try:
            stream_name, text, seen_at = output_queue.get(timeout=0.1)
        except queue.Empty:
            if process.poll() is not None and output_queue.empty():
                break
            continue

        if first_output_latency is None:
            first_output_latency = seen_at - start

        if stream_name == "stdout":
            stdout_chunks.append(text)
        else:
            stderr_chunks.append(text)

    for thread in threads:
        thread.join(timeout=0.2)

    while not output_queue.empty():
        stream_name, text, seen_at = output_queue.get_nowait()
        if first_output_latency is None:
            first_output_latency = seen_at - start
        if stream_name == "stdout":
            stdout_chunks.append(text)
        else:
            stderr_chunks.append(text)

    return ProbeResult(
        name=probe.name,
        description=probe.description,
        command=probe.command,
        timeout_seconds=timeout_seconds,
        exit_code=None if timed_out else process.poll(),
        duration_seconds=time.monotonic() - start,
        first_output_latency_seconds=first_output_latency,
        timed_out=timed_out,
        stdout="".join(stdout_chunks).strip(),
        stderr="".join(stderr_chunks).strip(),
    )


def _narrow_pytest_command(python_bin: str, *extra_args: str) -> list[str]:
    command = [python_bin, "-m", "pytest"]
    for plugin in NARROW_PYTEST_PLUGINS:
        command.extend(["-p", plugin])
    command.extend(extra_args)
    return command


def _build_probes(python_bin: str) -> list[Probe]:
    return [
        Probe(
            name="python-startup",
            description="Interpreter baseline without heavy imports.",
            command=[python_bin, "-c", "print('python-ok')"],
        ),
        Probe(
            name="pytest-version-default",
            description="Default pytest startup to detect plugin-autoload stalls.",
            command=[python_bin, "-m", "pytest", "--version"],
        ),
        Probe(
            name="pytest-version-narrow",
            description="Narrow pytest startup with explicit plugin allowlist.",
            command=_narrow_pytest_command(python_bin, "--version"),
        ),
        Probe(
            name="pytest-collect-narrow",
            description="Collect-only architecture slice in narrow mode.",
            command=_narrow_pytest_command(
                python_bin,
                "--collect-only",
                "tests/architecture/test_boundary_assertions.py",
            ),
        ),
        Probe(
            name="pytest-file-narrow",
            description="Single-file architecture pytest slice in narrow mode.",
            command=_narrow_pytest_command(
                python_bin,
                "tests/architecture/test_boundary_assertions.py",
                "-q",
            ),
        ),
        Probe(
            name="mypy-version",
            description="Mypy process startup baseline.",
            command=[python_bin, "-m", "mypy", "--version"],
        ),
        Probe(
            name="mypy-file-default",
            description="Single-file strict mypy with normal import traversal.",
            command=[
                python_bin,
                "-m",
                "mypy",
                "--config-file",
                "pyproject.toml",
                "--strict",
                "src/bioetl/domain/__init__.py",
            ],
        ),
        Probe(
            name="mypy-file-narrow",
            description="Single-file strict mypy with follow-imports disabled.",
            command=[
                python_bin,
                "-m",
                "mypy",
                "--config-file",
                "pyproject.toml",
                "--strict",
                "--follow-imports=skip",
                "src/bioetl/domain/__init__.py",
            ],
        ),
    ]


def _probe_env(base_env: dict[str, str], probe_name: str) -> dict[str, str]:
    probe_env = base_env.copy()
    if "pytest" in probe_name and "narrow" in probe_name:
        probe_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return probe_env


def _json_payload(
    python_bin: str,
    interpreter_kind: str,
    results: list[ProbeResult],
) -> dict[str, object]:
    return {
        "interpreter": python_bin,
        "interpreter_kind": interpreter_kind,
        "results": [result.as_dict() for result in results],
    }


def _print_markdown(
    *,
    interpreter: str,
    interpreter_kind: str,
    results: list[ProbeResult],
) -> None:
    print("# Quality Gate Probe")
    print("")
    print(f"- generated_at_utc: `{datetime.now(tz=UTC).isoformat()}`")
    print(f"- interpreter_kind: `{interpreter_kind}`")
    print(f"- interpreter: `{interpreter}`")
    print("")
    print("| Probe | Exit | Duration (s) | First output (s) | Timed out |")
    print("| --- | ---: | ---: | ---: | --- |")
    for result in results:
        exit_value = "timeout" if result.timed_out else str(result.exit_code)
        first_output = (
            "-"
            if result.first_output_latency_seconds is None
            else f"{result.first_output_latency_seconds:.3f}"
        )
        print(
            f"| `{result.name}` | {exit_value} | {result.duration_seconds:.3f} | "
            f"{first_output} | `{result.timed_out}` |"
        )
    print("")
    for result in results:
        print(f"## {result.name}")
        print("")
        print(f"- description: {result.description}")
        print(f"- command: `{shlex.join(result.command)}`")
        if result.stdout:
            print("- stdout:")
            print("```text")
            print(result.stdout)
            print("```")
        if result.stderr:
            print("- stderr:")
            print("```text")
            print(result.stderr)
            print("```")
        if not result.stdout and not result.stderr:
            print("- output: _(no output captured)_")
        print("")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-probe timeout in seconds.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of Markdown.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    python_bin, interpreter_kind = _preferred_python()
    probes = _build_probes(python_bin)
    results: list[ProbeResult] = []
    base_env = os.environ.copy()

    for probe in probes:
        results.append(
            _run_probe(
                probe,
                timeout_seconds=args.timeout,
                cwd=REPO_ROOT,
                env=_probe_env(base_env, probe.name),
            )
        )

    if args.json:
        json.dump(
            _json_payload(python_bin, interpreter_kind, results),
            sys.stdout,
            indent=2,
        )
        print()
        return

    _print_markdown(
        interpreter=python_bin,
        interpreter_kind=interpreter_kind,
        results=results,
    )


if __name__ == "__main__":
    main()
