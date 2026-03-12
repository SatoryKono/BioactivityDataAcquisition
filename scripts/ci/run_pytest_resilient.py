#!/usr/bin/env python3
"""Resilient pytest runner with xdist crash fallback for CI.

Runs non-serial tests in parallel first. If xdist workers crash,
re-runs the same non-serial subset in serial mode. Serial-only tests
are always executed as a dedicated serial pass.
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_WORKER_CRASH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\[gw\d+\]\s+node down:\s+not properly terminated", re.IGNORECASE),
    re.compile(r"worker.+(crash|terminated unexpectedly)", re.IGNORECASE),
    re.compile(r"xdist.+(internal error|Interrupted)", re.IGNORECASE),
)


@dataclass(frozen=True)
class PassResult:
    """Outcome of a pytest pass."""

    name: str
    command: list[str]
    return_code: int
    output: str
    junit_path: Path
    log_path: Path
    failed_nodeids: list[str]
    worker_crash_detected: bool
    timed_out: bool


def _split_args(raw_args: str) -> list[str]:
    """Split shell-like arguments into list form."""
    if not raw_args.strip():
        return []
    return shlex.split(raw_args)


def _extract_failed_nodeids(output: str) -> list[str]:
    """Extract failed test nodeids from pytest text output."""
    nodeids: list[str] = []
    for line in output.splitlines():
        match = re.match(r"^FAILED\s+([^\s]+)", line.strip())
        if match is not None:
            nodeids.append(match.group(1))
    return sorted(set(nodeids))


def _detect_worker_crash(output: str) -> bool:
    """Return True if output indicates xdist worker crash/termination."""
    return any(pattern.search(output) for pattern in _WORKER_CRASH_PATTERNS)


def _effective_exit_code(result: PassResult, *, allow_no_tests: bool = False) -> int:
    """Normalize pytest exit code for pass evaluation."""
    if allow_no_tests and result.return_code == 5:
        return 0
    return result.return_code


def _run_pass(
    *,
    name: str,
    base_command: list[str],
    target: str,
    marker_expr: str,
    addopts: list[str],
    reports_dir: Path,
    timeout_seconds: float | None = None,
) -> PassResult:
    """Run pytest pass and persist logs/artifacts."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    junit_path = reports_dir / f"junit_{name}.xml"
    log_path = reports_dir / f"{name}.log"

    command = [
        *base_command,
        target,
        "-m",
        marker_expr,
        "--junitxml",
        str(junit_path),
        *addopts,
    ]

    sys.stdout.write(f"\n=== Running pytest pass: {name} ===\n")
    sys.stdout.write(f"Command: {' '.join(command)}\n")
    timed_out = False
    try:
        completed = subprocess.run(  # nosec B603
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        return_code = completed.returncode
        output = completed.stdout
        if completed.stderr:
            output = f"{output}\n{completed.stderr}" if output else completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = 124
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        output = stdout
        if stderr:
            output = f"{output}\n{stderr}" if output else stderr
        timeout_note = (
            f"\n[run_pytest_resilient] pass '{name}' timed out "
            f"after {timeout_seconds:.0f}s."
        )
        output = f"{output}{timeout_note}" if output else timeout_note.lstrip()

    log_path.write_text(output, encoding="utf-8")
    if output:
        sys.stdout.write(output)

    return PassResult(
        name=name,
        command=command,
        return_code=return_code,
        output=output,
        junit_path=junit_path,
        log_path=log_path,
        failed_nodeids=_extract_failed_nodeids(output),
        worker_crash_detected=_detect_worker_crash(output),
        timed_out=timed_out,
    )


def _write_summary(path: Path, lines: list[str]) -> None:
    """Write plain-text summary to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _create_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default="tests/",
        help="Pytest target path or nodeid (default: tests/).",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports/pytest",
        help="Directory for pass logs and junit xml files.",
    )
    parser.add_argument(
        "--parallel-marker",
        default="not e2e and not benchmark and not serial",
        help="Marker expression for parallel/fallback passes.",
    )
    parser.add_argument(
        "--serial-marker",
        default="serial",
        help="Marker expression for dedicated serial pass.",
    )
    parser.add_argument(
        "--parallel-addopts",
        default=(
            "-q --tb=short "
            "--ignore=tests/e2e --ignore=tests/contract "
            "-n auto --dist loadscope --max-worker-restart=0 "
            "--cov=src/bioetl --cov-report=term-missing --cov-report=xml:coverage.xml "
            "--cov-fail-under=85"
        ),
        help="Extra options for parallel pass.",
    )
    parser.add_argument(
        "--fallback-addopts",
        default=(
            "-q --tb=short "
            "--ignore=tests/e2e --ignore=tests/contract "
            "-p no:xdist "
            "--cov=src/bioetl --cov-report=term-missing --cov-report=xml:coverage.xml "
            "--cov-fail-under=85"
        ),
        help="Extra options for serial fallback pass.",
    )
    parser.add_argument(
        "--serial-addopts",
        default="-q --tb=short -p no:xdist",
        help="Extra options for dedicated serial-marker pass.",
    )
    parser.add_argument(
        "--skip-serial-pass",
        action="store_true",
        help="Skip dedicated serial-marker pass.",
    )
    parser.add_argument(
        "--parallel-timeout-seconds",
        type=float,
        default=900.0,
        help=(
            "Timeout for parallel pass in seconds (0 disables timeout). Default: 900."
        ),
    )
    parser.add_argument(
        "--fallback-timeout-seconds",
        type=float,
        default=1200.0,
        help=(
            "Timeout for fallback pass in seconds (0 disables timeout). Default: 1200."
        ),
    )
    parser.add_argument(
        "--serial-timeout-seconds",
        type=float,
        default=1200.0,
        help=(
            "Timeout for serial pass in seconds (0 disables timeout). Default: 1200."
        ),
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = _create_parser()
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    summary_lines: list[str] = []
    base_command = [sys.executable, "-m", "pytest"]
    parallel_timeout = args.parallel_timeout_seconds or None
    fallback_timeout = args.fallback_timeout_seconds or None
    serial_timeout = args.serial_timeout_seconds or None

    parallel_result = _run_pass(
        name="parallel",
        base_command=base_command,
        target=args.target,
        marker_expr=args.parallel_marker,
        addopts=_split_args(args.parallel_addopts),
        reports_dir=reports_dir,
        timeout_seconds=parallel_timeout,
    )

    parallel_rc = _effective_exit_code(parallel_result)

    summary_lines.append(
        f"parallel: rc={parallel_result.return_code} effective_rc={parallel_rc} "
        f"worker_crash={parallel_result.worker_crash_detected} "
        f"timed_out={parallel_result.timed_out} "
        f"log={parallel_result.log_path} junit={parallel_result.junit_path}"
    )

    if parallel_result.failed_nodeids:
        summary_lines.append("parallel_failed_nodeids:")
        summary_lines.extend(
            f"  - {nodeid}" for nodeid in parallel_result.failed_nodeids
        )

    run_serial_pass = not args.skip_serial_pass

    if parallel_rc == 0:
        if not run_serial_pass:
            _write_summary(reports_dir / "summary.txt", summary_lines)
            return 0

        serial_result = _run_pass(
            name="serial",
            base_command=base_command,
            target=args.target,
            marker_expr=args.serial_marker,
            addopts=_split_args(args.serial_addopts),
            reports_dir=reports_dir,
            timeout_seconds=serial_timeout,
        )
        serial_rc = _effective_exit_code(serial_result, allow_no_tests=True)
        summary_lines.append(
            f"serial: rc={serial_result.return_code} effective_rc={serial_rc} "
            f"timed_out={serial_result.timed_out} "
            f"log={serial_result.log_path} junit={serial_result.junit_path}"
        )
        if serial_result.failed_nodeids:
            summary_lines.append("serial_failed_nodeids:")
            summary_lines.extend(
                f"  - {nodeid}" for nodeid in serial_result.failed_nodeids
            )
        _write_summary(reports_dir / "summary.txt", summary_lines)
        return serial_rc

    if not parallel_result.worker_crash_detected and not parallel_result.timed_out:
        summary_lines.append("parallel_failed_without_worker_crash=true")
        _write_summary(reports_dir / "summary.txt", summary_lines)
        return parallel_rc

    if parallel_result.worker_crash_detected:
        summary_lines.append("worker_crash_detected=true")
    if parallel_result.timed_out:
        summary_lines.append("parallel_timeout_detected=true")
    sys.stdout.write(
        "\nparallel pass unstable (worker crash/timeout), running serial fallback pass.\n"
    )

    fallback_result = _run_pass(
        name="fallback",
        base_command=base_command,
        target=args.target,
        marker_expr=args.parallel_marker,
        addopts=_split_args(args.fallback_addopts),
        reports_dir=reports_dir,
        timeout_seconds=fallback_timeout,
    )
    fallback_rc = _effective_exit_code(fallback_result)
    summary_lines.append(
        f"fallback: rc={fallback_result.return_code} effective_rc={fallback_rc} "
        f"timed_out={fallback_result.timed_out} "
        f"log={fallback_result.log_path} junit={fallback_result.junit_path}"
    )
    if fallback_result.failed_nodeids:
        summary_lines.append("fallback_failed_nodeids:")
        summary_lines.extend(
            f"  - {nodeid}" for nodeid in fallback_result.failed_nodeids
        )

    if fallback_rc != 0:
        _write_summary(reports_dir / "summary.txt", summary_lines)
        return fallback_rc

    if run_serial_pass:
        serial_result = _run_pass(
            name="serial",
            base_command=base_command,
            target=args.target,
            marker_expr=args.serial_marker,
            addopts=_split_args(args.serial_addopts),
            reports_dir=reports_dir,
            timeout_seconds=serial_timeout,
        )
        serial_rc = _effective_exit_code(serial_result, allow_no_tests=True)
        summary_lines.append(
            f"serial: rc={serial_result.return_code} effective_rc={serial_rc} "
            f"timed_out={serial_result.timed_out} "
            f"log={serial_result.log_path} junit={serial_result.junit_path}"
        )
        if serial_result.failed_nodeids:
            summary_lines.append("serial_failed_nodeids:")
            summary_lines.extend(
                f"  - {nodeid}" for nodeid in serial_result.failed_nodeids
            )
        _write_summary(reports_dir / "summary.txt", summary_lines)
        return serial_rc

    _write_summary(reports_dir / "summary.txt", summary_lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
