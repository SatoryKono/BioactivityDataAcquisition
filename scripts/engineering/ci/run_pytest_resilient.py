#!/usr/bin/env python3
"""Resilient pytest runner with xdist crash fallback for CI.

Runs non-serial tests in parallel first. If xdist workers crash,
re-runs the same non-serial subset in serial mode. Serial-only tests
are always executed as a dedicated serial pass.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.engineering.ci.pytest_receipts import (
    validate_receipt_ids,
    write_runner_terminal_receipt,
)

_WORKER_CRASH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\[gw\d+\]\s+node down:\s+\S", re.IGNORECASE),
    re.compile(r"^replacing crashed worker gw\d+\b", re.IGNORECASE),
    re.compile(r"^worker gw\d+ crashed\b", re.IGNORECASE),
    re.compile(r"^maximum crashed workers reached:", re.IGNORECASE),
    re.compile(r"^xdist\.[\w.]*(?:internal error|Interrupted)\b", re.IGNORECASE),
)
_MAXFAIL_INTERRUPT = re.compile(r"stopping after \d+ failures", re.IGNORECASE)
SUMMARY_FILENAME = "summary.txt"


@dataclass(frozen=True)
class ReceiptInvocation:
    """One resilient pytest invocation that must emit its own receipts."""

    directory: Path
    run_id: str
    attempt: str
    expected_sha: str | None

    def pytest_args(self, pass_name: str) -> list[str]:
        directory = self.directory.expanduser().resolve()
        args = [
            f"--receipt-dir={directory}",
            f"--receipt-run-id={self.run_id}",
            f"--receipt-attempt={self.attempt}",
            f"--receipt-pass={pass_name}",
            f"--receipt-repo-root={_REPO_ROOT}",
        ]
        if self.expected_sha:
            args.append(f"--receipt-expected-sha={self.expected_sha}")
        return args


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
    diagnostic_status: str = ""
    diagnostic_manifest: Path | None = None
    invocation_id: str = ""


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
    """Return True if output indicates an xdist worker or node crash.

    ``--maxfail`` stops with ``xdist.dsession.Interrupted: stopping after N
    failures``. That line is an ordinary early stop, not a worker crash.
    """
    for line in output.splitlines():
        if _MAXFAIL_INTERRUPT.search(line):
            continue
        if any(pattern.search(line) for pattern in _WORKER_CRASH_PATTERNS):
            return True
    return False


def _effective_exit_code(result: PassResult, *, allow_no_tests: bool = False) -> int:
    """Normalize pytest exit code for pass evaluation."""
    if allow_no_tests and result.return_code == 5:
        return 0
    return result.return_code


def _merge_process_output(stdout: str, stderr: str) -> str:
    if not stderr:
        return stdout
    return f"{stdout}\n{stderr}" if stdout else stderr


def _supervised_output(reports_dir: Path, stdout_file: str, stderr_file: str) -> str:
    """Read supervisor logs. The diagnostic manifest is not pytest output."""
    stdout = _read_supervised_log(reports_dir, stdout_file)
    stderr = _read_supervised_log(reports_dir, stderr_file)
    return _merge_process_output(stdout, stderr)


def _read_supervised_log(reports_dir: Path, relative: str) -> str:
    from scripts.engineering.common.repo_paths import read_text_confined

    if not relative:
        return ""
    try:
        return read_text_confined(
            reports_dir / relative,
            root=reports_dir,
            allow_external_absolute=False,
        )
    except (OSError, ValueError):
        return ""


def _journal_child_env(
    pass_name: str,
    invocation_id: str,
    *,
    allow_no_tests: bool = False,
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Environment for one journaled pytest child."""
    from scripts.engineering.ci.pytest_event_journal import ensure_redaction_key

    child_env = (os.environ if base_env is None else base_env).copy()
    child_env["BIOETL_JOURNAL_REDACTION_KEY"] = ensure_redaction_key()
    child_env["BIOETL_JOURNAL_INVOCATION_ID"] = invocation_id
    child_env["BIOETL_JOURNAL_PASS"] = pass_name
    if allow_no_tests:
        child_env["BIOETL_JOURNAL_ALLOW_NO_TESTS"] = "1"
    else:
        child_env.pop("BIOETL_JOURNAL_ALLOW_NO_TESTS", None)
    root = str(_REPO_ROOT)
    current = child_env.get("PYTHONPATH", "")
    if current:
        if current.split(os.pathsep)[0] != root:
            child_env["PYTHONPATH"] = root + os.pathsep + current
    else:
        child_env["PYTHONPATH"] = root
    return child_env


def _child_env() -> dict[str, str]:
    """Give the pytest child the repo root without dropping PYTHONPATH."""
    env = os.environ.copy()
    root = str(_REPO_ROOT)
    inherited = [part for part in env.get("PYTHONPATH", "").split(os.pathsep) if part]
    if root not in inherited:
        inherited.insert(0, root)
    env["PYTHONPATH"] = os.pathsep.join(inherited)
    return env


def _result_records_failure(item: object) -> bool:
    """True when a node outcome, or one duplicate occurrence, is not success."""
    if isinstance(item, list):
        return any(_result_records_failure(entry) for entry in item)
    if not isinstance(item, dict):
        return False
    return item.get("terminal") not in {"passed", "skipped", "xfailed", "xpassed"}


def _collection_failed(payload: Mapping[str, object]) -> bool:
    collection = payload.get("collection")
    return isinstance(collection, dict) and collection.get("status") == "error"


def _payload_explains_failure(payload: object) -> bool:
    """True when a worker receipt records a cause, not only a dirty tree.

    A tracked file that changes during the run makes completeness incomplete
    while every node still passes. That does not explain a later controller
    failure such as a coverage gate.
    """
    if not isinstance(payload, dict):
        return False
    if payload.get("exit_code") not in (0, None):
        return True
    if payload.get("early_stop") is True or _collection_failed(payload):
        return True
    results = payload.get("results")
    if not isinstance(results, dict):
        return False
    return any(_result_records_failure(item) for item in results.values())


def _worker_failure_is_explained(receipt: ReceiptInvocation, pass_name: str) -> bool:
    """True when a worker receipt already records the failing outcome."""
    root = receipt.directory / receipt.run_id / receipt.attempt / pass_name
    if not root.is_dir():
        return False
    for path in root.rglob("receipt.json"):
        if path.parent.name == "runner":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if _payload_explains_failure(payload):
            return True
    return False


def _record_runner_terminal(
    *,
    receipt: ReceiptInvocation | None,
    name: str,
    return_code: int,
    output: str,
    timed_out: bool,
    worker_crash: bool,
) -> None:
    """Persist a runner failure the worker receipts do not already explain."""
    if receipt is None:
        return
    if return_code == 0:
        worker_crash = False
    if timed_out:
        kind = "timeout"
    elif worker_crash:
        kind = "worker_crash"
    elif return_code != 0 and not _worker_failure_is_explained(receipt, name):
        kind = "aborted"
    else:
        return
    write_runner_terminal_receipt(
        receipt_dir=receipt.directory,
        run_id=receipt.run_id,
        attempt=receipt.attempt,
        pass_name=name,
        repo_root=_REPO_ROOT,
        exit_code=return_code,
        terminal_kind=kind,
        observed_error=output,
    )


def _run_pass(
    *,
    name: str,
    base_command: list[str],
    target: str,
    marker_expr: str,
    addopts: list[str],
    reports_dir: Path,
    journal_dir: Path | None = None,
    timeout_seconds: float | None = None,
    executed_passes: list[str] | None = None,
    expected_invocations: dict[str, str] | None = None,
    allow_no_tests: bool = False,
    receipt: ReceiptInvocation | None = None,
    child_env: dict[str, str] | None = None,
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
    invocation_id = ""
    if journal_dir is not None:
        if executed_passes is not None:
            executed_passes.append(name)
        invocation_id = uuid.uuid4().hex
        child_env = _journal_child_env(
            name, invocation_id, allow_no_tests=allow_no_tests, base_env=child_env
        )
        if expected_invocations is not None:
            expected_invocations[name] = invocation_id
        command.extend(
            [
                "-p",
                "scripts.engineering.ci.pytest_event_journal",
                f"--event-journal-dir={journal_dir}",
            ]
        )
    if receipt is not None:
        command.extend(receipt.pytest_args(name))

    sys.stdout.write(f"\n=== Running pytest pass: {name} ===\n")
    sys.stdout.write(f"Command: {' '.join(command)}\n")
    from scripts.engineering.ci.pytest_abort_diagnostic_adapter import (
        DIAGNOSTIC_DUMP_MARGIN_SECONDS,
        PytestAbortDiagnosticAdapter,
        child_watchdog_seconds,
    )
    from scripts.engineering.common.repo_paths import write_text_confined

    try:
        watchdog = (
            None if timeout_seconds is None else child_watchdog_seconds(timeout_seconds)
        )
    except ValueError as exc:
        output = f"[run_pytest_resilient] invalid timeout budget: {exc}\n"
        write_text_confined(
            log_path, output, root=reports_dir, allow_external_absolute=False
        )
        if receipt is not None:
            write_runner_terminal_receipt(
                receipt_dir=receipt.directory,
                run_id=receipt.run_id,
                attempt=receipt.attempt,
                pass_name=name,
                repo_root=_REPO_ROOT,
                exit_code=2,
                terminal_kind="invalid_invocation",
                observed_error=output,
            )
        return PassResult(
            name=name,
            command=command,
            return_code=2,
            output=output,
            junit_path=junit_path,
            log_path=log_path,
            failed_nodeids=[],
            worker_crash_detected=False,
            timed_out=False,
            diagnostic_status="INVALID_INVOCATION",
            invocation_id=invocation_id,
        )
    manifest = PytestAbortDiagnosticAdapter(
        timeout=watchdog,
        dump_margin=DIAGNOSTIC_DUMP_MARGIN_SECONDS,
        base=reports_dir,
        child_env=child_env,
    ).run(
        command,
        junit_path,
        reports_dir / "diagnostics" / name,
        base=reports_dir,
    )
    output = _supervised_output(reports_dir, manifest.stdout_file, manifest.stderr_file)
    if manifest.status == "WATCHDOG_TIMEOUT":
        elapsed = 0 if timeout_seconds is None else timeout_seconds
        output = (
            f"[run_pytest_resilient] pass '{name}' timed out "
            f"after {elapsed:.0f}s.\n{output}"
        ).lstrip("\n")
    write_text_confined(
        log_path, output, root=reports_dir, allow_external_absolute=False
    )
    if output:
        sys.stdout.write(output)
    worker_crash = _detect_worker_crash(output)
    _record_runner_terminal(
        receipt=receipt,
        name=name,
        return_code=manifest.wrapper_exit_code,
        output=output,
        timed_out=manifest.status == "WATCHDOG_TIMEOUT",
        worker_crash=worker_crash,
    )
    diagnostic_manifest = None
    if manifest.diagnostics_persisted and manifest.manifest_file:
        diagnostic_manifest = reports_dir / manifest.manifest_file

    return PassResult(
        name=name,
        command=command,
        return_code=manifest.wrapper_exit_code,
        output=output,
        junit_path=junit_path,
        log_path=log_path,
        failed_nodeids=_extract_failed_nodeids(output),
        worker_crash_detected=worker_crash,
        timed_out=manifest.status == "WATCHDOG_TIMEOUT",
        diagnostic_status=manifest.status,
        diagnostic_manifest=diagnostic_manifest,
        invocation_id=invocation_id,
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


def _persist_journal_verdict(
    verdict: dict[str, Any], destinations: tuple[Path, ...]
) -> bool:
    """Write each verdict copy. An OSError stays on stderr and does not raise."""
    from scripts.engineering.ci.pytest_event_journal import atomic_write_json

    persisted = True
    for destination in destinations:
        try:
            atomic_write_json(destination, verdict)
        except OSError as exc:
            persisted = False
            sys.stderr.write(
                f"EventJournal verdict write failed: {type(exc).__name__}:{exc.errno}\n"
            )
    return persisted


def _note_verdict_write_failure(verdict: dict[str, Any]) -> None:
    """Record a persistence failure without hiding a stronger journal status."""
    reasons = list(verdict["reasons"])
    if "verdict_write_failed" not in reasons:
        reasons.append("verdict_write_failed")
    verdict["reasons"] = reasons
    if verdict["status"] != "complete":
        return
    verdict["status"] = "incomplete"
    verdict["tests_passed"] = None


def _finish_run(
    *,
    reports_dir: Path,
    summary_lines: list[str],
    journal_dir: Path | None = None,
    executed_passes: list[str] | None = None,
    test_rc: int,
    expected_invocations: dict[str, str] | None = None,
) -> int:
    """Persist the summary and, when enabled, a separate journal verdict.

    A non-zero pytest result is preserved. Journal incompleteness replaces
    only a zero test result so a test failure cannot be reported as success.
    """
    if journal_dir is not None:
        from scripts.engineering.ci.pytest_event_journal import (
            JOURNAL_COMPLETENESS_EXIT,
            reconcile_directory,
        )

        verdict = reconcile_directory(
            journal_dir,
            executed_passes=executed_passes,
            expected_invocations=expected_invocations,
        )
        verdict["test_exit_code"] = test_rc
        destinations = (
            reports_dir / "journal-verdict.json",
            journal_dir / "journal-verdict.json",
        )
        if not _persist_journal_verdict(verdict, destinations):
            _note_verdict_write_failure(verdict)
            _persist_journal_verdict(verdict, destinations)
        summary_lines.append(
            f"journal_status={verdict['status']} "
            f"tests_passed={verdict['tests_passed']} test_exit_code={test_rc}"
        )
        if verdict["reasons"]:
            summary_lines.append("journal_reasons=" + ",".join(verdict["reasons"]))
        if verdict["status"] != "complete":
            sys.stderr.write(
                "EventJournal completeness "
                f"{verdict['status']}: {', '.join(verdict['reasons']) or 'unspecified'}\n"
            )
            if test_rc == 0:
                test_rc = JOURNAL_COMPLETENESS_EXIT
    _write_summary(_summary_path(reports_dir), summary_lines)
    return test_rc


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
    if result.diagnostic_manifest is not None:
        summary_lines.append(
            f"{result.name}_diagnostic: status={result.diagnostic_status} "
            f"manifest={result.diagnostic_manifest}"
        )


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
    journal_dir: Path | None = None,
    timeout_seconds: float | None,
    executed_passes: list[str] | None = None,
    expected_invocations: dict[str, str] | None = None,
    allow_no_tests: bool = False,
    receipt: ReceiptInvocation | None = None,
    child_env: dict[str, str] | None = None,
) -> PassResult:
    """Run a named pass using shell-split addopts."""
    return _run_pass(
        name=name,
        base_command=base_command,
        target=target,
        marker_expr=marker_expr,
        addopts=_split_args(addopts),
        reports_dir=reports_dir,
        journal_dir=journal_dir,
        timeout_seconds=timeout_seconds,
        executed_passes=executed_passes,
        expected_invocations=expected_invocations,
        allow_no_tests=allow_no_tests,
        receipt=receipt,
        child_env=child_env,
    )


def _run_serial_pass(
    *,
    base_command: list[str],
    args: argparse.Namespace,
    reports_dir: Path,
    journal_dir: Path | None = None,
    serial_timeout: float | None,
    summary_lines: list[str],
    executed_passes: list[str] | None = None,
    expected_invocations: dict[str, str] | None = None,
    receipt: ReceiptInvocation | None = None,
    child_env: dict[str, str] | None = None,
) -> int:
    """Run dedicated serial marker pass and record the summary."""
    serial_result = _run_named_pass(
        name="serial",
        base_command=base_command,
        target=args.target,
        marker_expr=args.serial_marker,
        addopts=args.serial_addopts,
        reports_dir=reports_dir,
        journal_dir=journal_dir,
        timeout_seconds=serial_timeout,
        executed_passes=executed_passes,
        expected_invocations=expected_invocations,
        allow_no_tests=True,
        receipt=receipt,
        child_env=child_env,
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
        "--journal-dir",
        default=None,
        help="Directory to store event journal receipts",
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
        "--no-fallback",
        action="store_true",
        help=(
            "Do not start a second pytest pass after a worker crash or watchdog "
            "timeout. The parallel pass status is returned as-is."
        ),
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
    # Receipt args
    parser.add_argument(
        "--receipt-dir",
        default=None,
        help="Directory to store per-worker receipts",
    )
    parser.add_argument(
        "--receipt-run-id",
        default="local",
        help="Receipt run identifier",
    )
    parser.add_argument(
        "--receipt-attempt",
        default="1",
        help="Receipt attempt identifier",
    )
    parser.add_argument(
        "--receipt-expected-sha",
        default=None,
        help="Expected git SHA to enforce. Requires --receipt-dir.",
    )
    return parser


def _reject_unsafe_receipt_ids(args: argparse.Namespace) -> int | None:
    """Reject ids that the receipt plugin cannot store as a path segment."""
    if not args.receipt_dir:
        return None
    try:
        validate_receipt_ids(str(args.receipt_run_id), str(args.receipt_attempt))
    except ValueError as exc:
        sys.stderr.write(f"[run_pytest_resilient] {exc}\n")
        return 2
    return None


def _reject_invalid_invocation(args: argparse.Namespace) -> int | None:
    rejected = _reject_sha_without_receipt_dir(args)
    if rejected is not None:
        return rejected
    return _reject_unsafe_receipt_ids(args)


def _reject_sha_without_receipt_dir(args: argparse.Namespace) -> int | None:
    """Reject an expected SHA that nothing will enforce."""
    if args.receipt_expected_sha and not args.receipt_dir:
        sys.stderr.write(
            "[run_pytest_resilient] --receipt-expected-sha requires --receipt-dir\n"
        )
        return 2
    return None


def _execute_passes(args: argparse.Namespace) -> int:
    """Run the parallel, fallback, and serial passes."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    reports_dir = resolve_output_path(Path(args.reports_dir), root=REPO_ROOT)
    journal_dir = (
        resolve_output_path(Path(args.journal_dir), root=REPO_ROOT)
        if args.journal_dir
        else None
    )
    summary_lines: list[str] = []
    executed_passes: list[str] = []
    expected_invocations: dict[str, str] = {}
    base_command = [sys.executable, "-X", "faulthandler", "-m", "pytest"]
    receipt: ReceiptInvocation | None = None
    if args.receipt_dir:
        base_command.extend(["-p", "scripts.engineering.ci.pytest_receipts"])
        receipt = ReceiptInvocation(
            directory=Path(args.receipt_dir),
            run_id=str(args.receipt_run_id),
            attempt=str(args.receipt_attempt),
            expected_sha=args.receipt_expected_sha,
        )
    child_env = _child_env()

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
        journal_dir=journal_dir,
        timeout_seconds=parallel_timeout,
        executed_passes=executed_passes,
        expected_invocations=expected_invocations,
        receipt=receipt,
        child_env=child_env,
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
            return _finish_run(
                reports_dir=reports_dir,
                summary_lines=summary_lines,
                journal_dir=journal_dir,
                executed_passes=executed_passes,
                test_rc=0,
                expected_invocations=expected_invocations,
            )

        serial_rc = _run_serial_pass(
            base_command=base_command,
            args=args,
            reports_dir=reports_dir,
            journal_dir=journal_dir,
            serial_timeout=serial_timeout,
            summary_lines=summary_lines,
            receipt=receipt,
            child_env=child_env,
            executed_passes=executed_passes,
            expected_invocations=expected_invocations,
        )
        return _finish_run(
            reports_dir=reports_dir,
            summary_lines=summary_lines,
            journal_dir=journal_dir,
            executed_passes=executed_passes,
            test_rc=serial_rc,
            expected_invocations=expected_invocations,
        )

    if _parallel_failure_is_stable(parallel_result) or args.no_fallback:
        if _parallel_failure_is_stable(parallel_result):
            summary_lines.append("parallel_failed_without_worker_crash=true")
        else:
            _append_parallel_instability_markers(
                summary_lines,
                parallel_result=parallel_result,
            )
            summary_lines.append("fallback_skipped=true")
        return _finish_run(
            reports_dir=reports_dir,
            summary_lines=summary_lines,
            journal_dir=journal_dir,
            executed_passes=executed_passes,
            test_rc=parallel_rc,
            expected_invocations=expected_invocations,
        )

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
        journal_dir=journal_dir,
        timeout_seconds=fallback_timeout,
        executed_passes=executed_passes,
        expected_invocations=expected_invocations,
        receipt=receipt,
        child_env=child_env,
    )
    fallback_rc = _effective_exit_code(fallback_result)
    _append_pass_summary(
        summary_lines,
        result=fallback_result,
        effective_rc=fallback_rc,
    )

    if fallback_rc != 0:
        return _finish_run(
            reports_dir=reports_dir,
            summary_lines=summary_lines,
            journal_dir=journal_dir,
            executed_passes=executed_passes,
            test_rc=fallback_rc,
            expected_invocations=expected_invocations,
        )

    if run_serial_pass:
        serial_rc = _run_serial_pass(
            base_command=base_command,
            args=args,
            reports_dir=reports_dir,
            journal_dir=journal_dir,
            serial_timeout=serial_timeout,
            summary_lines=summary_lines,
            receipt=receipt,
            child_env=child_env,
            executed_passes=executed_passes,
            expected_invocations=expected_invocations,
        )
        return _finish_run(
            reports_dir=reports_dir,
            summary_lines=summary_lines,
            journal_dir=journal_dir,
            executed_passes=executed_passes,
            test_rc=serial_rc,
            expected_invocations=expected_invocations,
        )

    return _finish_run(
        reports_dir=reports_dir,
        summary_lines=summary_lines,
        journal_dir=journal_dir,
        executed_passes=executed_passes,
        test_rc=0,
        expected_invocations=expected_invocations,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = _create_parser()
    args = parser.parse_args(argv)
    rejected = _reject_invalid_invocation(args)
    if rejected is not None:
        return rejected
    return _execute_passes(args)


if __name__ == "__main__":
    raise SystemExit(main())
