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
SUMMARY_FILENAME = "summary.txt"


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


def _merge_process_output(stdout: str, stderr: str) -> str:
    if not stderr:
        return stdout
    return f"{stdout}\n{stderr}" if stdout else stderr


def _decode_timeout_stream(stream: bytes | str | None) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace")
    return stream


def _timeout_output(
    *,
    exc: subprocess.TimeoutExpired,
    name: str,
    timeout_seconds: float | None,
) -> str:
    output = _merge_process_output(
        _decode_timeout_stream(exc.stdout),
        _decode_timeout_stream(exc.stderr),
    )
    timeout_note = (
        f"\n[run_pytest_resilient] pass '{name}' timed out "
        f"after {timeout_seconds:.0f}s."
    )
    return f"{output}{timeout_note}" if output else timeout_note.lstrip()


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
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    reports_dir = resolve_output_path(reports_dir, root=REPO_ROOT)
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
        from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

        completed = (
            subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv  # nosec B603
                ensure_safe_cli_argv([str(token) for token in command]),
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
        )
        return_code = completed.returncode
        output = _merge_process_output(completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = 124
        output = _timeout_output(
            exc=exc,
            name=name,
            timeout_seconds=timeout_seconds,
        )

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
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary_path(reports_dir: Path) -> Path:
    """Return the summary artifact path."""
    return reports_dir / SUMMARY_FILENAME


def _append_pass_summary(
    summary_lines: list[str],
    *,
    result: PassResult,
    effective_rc: int,
) -> None:
    """Append one pass summary and optional failed nodeids."""
    summary_lines.append(
        f"{result.name}: rc={result.return_code} effective_rc={effective_rc} "
        f"{_summary_state_fields(result)} "
        f"log={result.log_path} junit={result.junit_path}"
    )
    _append_failed_nodeids(summary_lines, result=result)


def _summary_state_fields(result: PassResult) -> str:
    """Render summary state fields for a pass result."""
    fields = [f"timed_out={result.timed_out}"]
    if result.name == "parallel":
        fields.insert(0, f"worker_crash={result.worker_crash_detected}")
    return " ".join(fields)


def _append_failed_nodeids(summary_lines: list[str], *, result: PassResult) -> None:
    """Append failed nodeids when present."""
    if not result.failed_nodeids:
        return
    summary_lines.append(f"{result.name}_failed_nodeids:")
    summary_lines.extend(f"  - {nodeid}" for nodeid in result.failed_nodeids)


def _run_named_pass(
    *,
    name: str,
    base_command: list[str],
    target: str,
    marker_expr: str,
    addopts: str,
    reports_dir: Path,
    timeout_seconds: float | None,
) -> PassResult:
    """Run a named pass using shell-split addopts."""
    return _run_pass(
        name=name,
        base_command=base_command,
        target=target,
        marker_expr=marker_expr,
        addopts=_split_args(addopts),
        reports_dir=reports_dir,
        timeout_seconds=timeout_seconds,
    )


def _run_serial_pass(
    *,
    base_command: list[str],
    args: argparse.Namespace,
    reports_dir: Path,
    serial_timeout: float | None,
    summary_lines: list[str],
) -> int:
    """Run dedicated serial marker pass and record the summary."""
    serial_result = _run_named_pass(
        name="serial",
        base_command=base_command,
        target=args.target,
        marker_expr=args.serial_marker,
        addopts=args.serial_addopts,
        reports_dir=reports_dir,
        timeout_seconds=serial_timeout,
    )
    serial_rc = _effective_exit_code(serial_result, allow_no_tests=True)
    _append_pass_summary(summary_lines, result=serial_result, effective_rc=serial_rc)
    return serial_rc


def _parallel_failure_is_stable(parallel_result: PassResult) -> bool:
    """Return True when the parallel failure should not trigger fallback."""
    return not parallel_result.worker_crash_detected and not parallel_result.timed_out


def _append_parallel_instability_markers(
    summary_lines: list[str], *, parallel_result: PassResult
) -> None:
    """Annotate summary when fallback was triggered by instability."""
    if parallel_result.worker_crash_detected:
        summary_lines.append("worker_crash_detected=true")
    if parallel_result.timed_out:
        summary_lines.append("parallel_timeout_detected=true")


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
            "--cov=src/bioetl --cov-report=term-missing "
            "--cov-report=xml:reports/coverage/coverage.xml "
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
            "--cov=src/bioetl --cov-report=term-missing "
            "--cov-report=xml:reports/coverage/coverage.xml "
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
    _append_pass_summary(
        summary_lines,
        result=parallel_result,
        effective_rc=parallel_rc,
    )

    run_serial_pass = not args.skip_serial_pass

    if parallel_rc == 0:
        if not run_serial_pass:
            _write_summary(_summary_path(reports_dir), summary_lines)
            return 0

        serial_rc = _run_serial_pass(
            base_command=base_command,
            args=args,
            reports_dir=reports_dir,
            serial_timeout=serial_timeout,
            summary_lines=summary_lines,
        )
        _write_summary(_summary_path(reports_dir), summary_lines)
        return serial_rc

    if _parallel_failure_is_stable(parallel_result):
        summary_lines.append("parallel_failed_without_worker_crash=true")
        _write_summary(_summary_path(reports_dir), summary_lines)
        return parallel_rc

    _append_parallel_instability_markers(
        summary_lines,
        parallel_result=parallel_result,
    )
    sys.stdout.write(
        "\nparallel pass unstable (worker crash/timeout), running serial fallback pass.\n"
    )

    fallback_result = _run_named_pass(
        name="fallback",
        base_command=base_command,
        target=args.target,
        marker_expr=args.parallel_marker,
        addopts=args.fallback_addopts,
        reports_dir=reports_dir,
        timeout_seconds=fallback_timeout,
    )
    fallback_rc = _effective_exit_code(fallback_result)
    _append_pass_summary(
        summary_lines,
        result=fallback_result,
        effective_rc=fallback_rc,
    )

    if fallback_rc != 0:
        _write_summary(_summary_path(reports_dir), summary_lines)
        return fallback_rc

    if run_serial_pass:
        serial_rc = _run_serial_pass(
            base_command=base_command,
            args=args,
            reports_dir=reports_dir,
            serial_timeout=serial_timeout,
            summary_lines=summary_lines,
        )
        _write_summary(_summary_path(reports_dir), summary_lines)
        return serial_rc

    _write_summary(_summary_path(reports_dir), summary_lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
