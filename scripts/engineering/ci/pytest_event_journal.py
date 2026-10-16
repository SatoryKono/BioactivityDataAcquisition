"""Pytest receipt journal and completeness reconciliation.

Write contract (not an atomic snapshot of the whole file):

- Each event is one UTF-8 JSON object, one line, terminated by ``\\n``.
- The line is flushed and ``os.fsync``'d before the hook returns.
- A crash can leave a partial trailing line. That receipt is not intact.
- The last intact line must be ``journal_finalized`` and its
  ``prior_line_count`` must match the lines before it.
- The verdict file is a separate document and is replaced via
  ``temp`` + ``os.replace``.

Journal I/O errors are written to stderr and recorded when the file is
still writable. They do not propagate out of pytest hooks, and they do
not change the pytest process exit code. Completeness stays not-complete.

Completeness is not the number of JSONL rows and not pytest's exit code.
``complete`` requires an intact controller collection, intact receipts,
and an explained terminal state for every selected test. A complete run
may still contain failures. ``GITHUB_RUN_ATTEMPT`` is the workflow
attempt, not a retry inside this runner.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
JOURNAL_COMPLETENESS_EXIT = 4
GIT_SHA_TIMEOUT_SECONDS = 10.0
_SECRET_KEY = re.compile(
    r"(?i)(secret|token|password|passwd|api_key|apikey|credential|authorization)"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(token|secret|password|passwd|api[_-]?key|authorization|credential)"
)
_SECRET_PREFIX = re.compile(r"(?i)^(ghp_|github_pat_|sk-|xox[baprs]-|AKIA)")
_SAFE_ENV_KEYS = frozenset(
    {
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
        "GITHUB_JOB",
        "PYTEST_XDIST_WORKER",
        "EXPECTED_CHECKOUT_SHA",
        "BIOETL_JOURNAL_INVOCATION_ID",
        "BIOETL_JOURNAL_PASS",
        "BIOETL_JOURNAL_JOB",
        "BIOETL_JOURNAL_MATRIX",
    }
)
_CALL_CLASSIFICATIONS = frozenset({"passed", "failed", "skipped", "xfail", "xpass"})
_SETUP_TERMINAL = frozenset({"setup_error", "skipped", "xfail"})
_FAILURE_CLASSIFICATIONS = frozenset(
    {"failed", "setup_error", "teardown_error", "xpass"}
)


def pytest_addoption(parser: Any) -> None:
    parser.addoption(
        "--event-journal-dir",
        action="store",
        default=None,
        help="Directory for pytest event-journal receipts",
    )


def _secret_values() -> tuple[str, ...]:
    values: list[str] = []
    for key, value in os.environ.items():
        if len(value) < 8 or _SECRET_KEY.search(key) is None:
            continue
        values.append(value)
    return tuple(values)


def _redact_text(text: str, secrets: tuple[str, ...]) -> str:
    redacted = text
    for secret in secrets:
        if secret in redacted:
            redacted = redacted.replace(secret, "[redacted]")
    if _SECRET_ASSIGNMENT.search(redacted) or _SECRET_PREFIX.search(redacted):
        return "[redacted]"
    return redacted


def _redact_args(args: list[str], secrets: tuple[str, ...]) -> list[str]:
    return [_redact_text(token, secrets) for token in args]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def measure_checkout_sha(
    *, timeout_seconds: float = GIT_SHA_TIMEOUT_SECONDS
) -> tuple[str | None, str | None]:
    """Return ``(sha, error)``. ``error`` is set when git does not answer."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return None, "git_rev_parse_timeout"
    except OSError as exc:
        return None, f"git_rev_parse_oserror:{exc.errno}"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return None, f"git_rev_parse_failed:{detail[:120]}"
    sha = completed.stdout.strip()
    if len(sha) != 40:
        return None, "git_rev_parse_unexpected"
    return sha, None


def _parse_matrix(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(value, dict):
        return value
    return None


def _identity_from_env(
    *,
    actual_sha: str | None,
    secrets: tuple[str, ...],
) -> dict[str, Any]:
    matrix_raw = os.environ.get("BIOETL_JOURNAL_MATRIX", "")
    job = os.environ.get("BIOETL_JOURNAL_JOB") or os.environ.get("GITHUB_JOB") or ""
    worker = os.environ.get("PYTEST_XDIST_WORKER") or "controller"
    role = "worker" if os.environ.get("PYTEST_XDIST_WORKER") else "controller"
    invocation = os.environ.get("BIOETL_JOURNAL_INVOCATION_ID") or uuid.uuid4().hex
    return {
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID") or "local",
        "workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT") or "local",
        "job": _redact_text(job, secrets),
        "matrix": _parse_matrix(matrix_raw),
        "actual_checkout_sha": actual_sha,
        "expected_checkout_sha": os.environ.get("EXPECTED_CHECKOUT_SHA") or None,
        "invocation_id": invocation,
        "pass_name": os.environ.get("BIOETL_JOURNAL_PASS") or "unspecified",
        "worker_id": worker,
        "role": role,
    }


def _selection_from_config(config: Any, secrets: tuple[str, ...]) -> dict[str, Any]:
    option = config.option
    maxfail = getattr(option, "maxfail", None)
    return {
        "args": _redact_args([str(arg) for arg in config.args], secrets),
        "marker": _redact_text(str(getattr(option, "markexpr", "") or ""), secrets),
        "collect_only": bool(getattr(option, "collectonly", False)),
        "exitfirst": bool(getattr(option, "exitfirst", False)),
        "maxfail": int(maxfail) if isinstance(maxfail, int) else None,
    }


class EventJournalPlugin:
    """Append-only receipt writer. Hook exceptions from I/O are contained."""

    def __init__(self, config: Any, path: Path, identity: dict[str, Any]) -> None:
        self.config = config
        self.path = path
        self.identity = identity
        self.secrets = _secret_values()
        self._file: Any = None
        self._closed = False
        self._io_error: str | None = None
        self._line_count = 0
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._file = path.open("w", encoding="utf-8", newline="\n")
        except OSError as exc:
            self._mark_io_error(f"open_failed:{exc.errno}")

    def _mark_io_error(self, message: str) -> None:
        redacted = _redact_text(message, self.secrets)
        self._io_error = redacted
        sys.stderr.write(f"EventJournal: {redacted}\n")
        if self._file is not None and not self._closed:
            try:
                self._file.close()
            except OSError:
                sys.stderr.write("EventJournal: close_failed\n")
            self._closed = True

    def record(self, event_type: str, data: dict[str, Any]) -> None:
        if self._closed or self._file is None:
            return
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "timestamp": _utc_now(),
            "event": event_type,
            "identity": self.identity,
        }
        for key, value in data.items():
            if isinstance(value, str):
                payload[key] = _redact_text(value, self.secrets)
            else:
                payload[key] = value
        line = json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n"
        try:
            self._file.write(line)
            self._file.flush()
            os.fsync(self._file.fileno())
        except OSError as exc:
            self._mark_io_error(f"write_failed:{exc.errno}")
            return
        self._line_count += 1

    def finalize(self) -> None:
        if self._closed:
            return
        self.record(
            "journal_finalized",
            {"prior_line_count": self._line_count, "io_error": self._io_error},
        )
        if self._file is not None and not self._closed:
            try:
                self._file.close()
            except OSError as exc:
                self._mark_io_error(f"close_failed:{exc.errno}")
                return
        self._closed = True

    def pytest_collection_modifyitems(
        self, session: Any, config: Any, items: list[Any]
    ) -> None:
        _ = session
        _ = config
        nodeids = sorted(_redact_text(str(item.nodeid), self.secrets) for item in items)
        self.record("collection_finished", {"nodeids": nodeids})

    def pytest_deselected(self, items: list[Any]) -> None:
        nodeids = sorted(_redact_text(str(item.nodeid), self.secrets) for item in items)
        self.record("deselected", {"nodeids": nodeids})

    def pytest_collectreport(self, report: Any) -> None:
        if not getattr(report, "failed", False):
            return
        self.record(
            "collection_error",
            {"nodeid": str(getattr(report, "nodeid", ""))},
        )

    def pytest_runtest_logreport(self, report: Any) -> None:
        wasxfail = getattr(report, "wasxfail", None)
        classification = _classify_report(report, wasxfail)
        retry_index = getattr(report, "rerun", None)
        if retry_index is None:
            retry_index = 0
        self.record(
            "outcome",
            {
                "nodeid": str(report.nodeid),
                "when": str(report.when),
                "classification": classification,
                "retry_index": int(retry_index),
                "wasxfail": wasxfail is not None,
            },
        )

    def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
        _ = session
        self.record("session_finish", {"exitstatus": int(exitstatus)})
        self.finalize()


def _classify_report(report: Any, wasxfail: Any) -> str:
    if report.when == "setup" and report.failed:
        return "setup_error"
    if report.when == "teardown" and report.failed:
        return "teardown_error"
    if wasxfail is not None and report.skipped:
        return "xfail"
    if wasxfail is not None and report.passed:
        return "xpass"
    if report.skipped:
        return "skipped"
    if report.failed:
        return "failed"
    if report.passed:
        return "passed"
    return str(getattr(report, "outcome", "unknown"))


def pytest_configure(config: Any) -> None:
    journal_dir = config.getoption("--event-journal-dir")
    if not journal_dir:
        return
    secrets = _secret_values()
    actual_sha, sha_error = measure_checkout_sha()
    identity = _identity_from_env(actual_sha=actual_sha, secrets=secrets)
    directory = Path(str(journal_dir))
    filename = (
        f"receipt_{identity['pass_name']}_{identity['invocation_id']}_"
        f"{identity['role']}_{identity['worker_id']}_{uuid.uuid4().hex}.jsonl"
    )
    plugin = EventJournalPlugin(config, directory / filename, identity)
    if plugin._file is None:
        return
    config.pluginmanager.register(plugin, "event_journal_plugin")
    plugin.record(
        "session_start",
        {
            "selection": _selection_from_config(config, secrets),
            "sha_error": sha_error,
            "safe_env": {
                key: _redact_text(os.environ[key], secrets)
                for key in sorted(_SAFE_ENV_KEYS)
                if key in os.environ
            },
        },
    )
    expected = identity["expected_checkout_sha"]
    if sha_error and expected:
        plugin.record("checkout_mismatch", {"reason": sha_error})
        plugin.finalize()
        import pytest

        pytest.exit(f"EventJournal failed to check git SHA: {sha_error}", returncode=3)
    if expected and actual_sha and actual_sha != expected:
        plugin.record(
            "checkout_mismatch",
            {"reason": "sha_mismatch", "actual": actual_sha, "expected": expected},
        )
        plugin.finalize()
        import pytest

        pytest.exit(
            f"EventJournal SHA mismatch: actual {actual_sha} != expected {expected}",
            returncode=3,
        )


def _load_receipt(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    truncated = bool(raw) and not raw.endswith(b"\n")
    text = raw.decode("utf-8", errors="replace")
    events: list[dict[str, Any]] = []
    parse_error = False
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            parse_error = True
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
        else:
            parse_error = True
    finalized = bool(events) and events[-1].get("event") == "journal_finalized"
    prior_ok = False
    if finalized:
        prior = events[-1].get("prior_line_count")
        prior_ok = prior == len(events) - 1
    return {
        "path": str(path),
        "events": events,
        "truncated": truncated or parse_error,
        "finalized": finalized and prior_ok and not truncated and not parse_error,
        "io_error": next(
            (
                event.get("io_error")
                for event in events
                if event.get("event") == "journal_finalized"
            ),
            None,
        ),
    }


def _group_receipts(journal_dir: Path) -> list[dict[str, Any]]:
    if not journal_dir.is_dir():
        return []
    receipts: list[dict[str, Any]] = []
    for path in sorted(journal_dir.glob("receipt_*.jsonl")):
        receipts.append(_load_receipt(path))
    return receipts


def _pass_of(receipt: dict[str, Any]) -> str:
    for event in receipt["events"]:
        identity = event.get("identity") or {}
        name = identity.get("pass_name")
        if isinstance(name, str) and name:
            return name
    return "unspecified"


def _controller_collection(
    events: list[dict[str, Any]],
) -> tuple[list[str] | None, list[str], list[str], bool]:
    """Return controller nodeids, deselected nodeids, errors, and conflict.

    Worker collection lists are ignored so per-worker collection cannot be
    summed into extra tests.
    """
    collections: list[list[str]] = []
    deselected: list[str] = []
    errors: list[str] = []
    for event in events:
        identity = event.get("identity") or {}
        if identity.get("role") != "controller":
            continue
        if event.get("event") == "collection_finished":
            nodeids = event.get("nodeids")
            if isinstance(nodeids, list):
                collections.append(sorted(str(nodeid) for nodeid in nodeids))
        elif event.get("event") == "deselected":
            nodeids = event.get("nodeids")
            if isinstance(nodeids, list):
                deselected.extend(str(nodeid) for nodeid in nodeids)
        elif event.get("event") == "collection_error":
            errors.append(str(event.get("nodeid") or ""))
    if not collections:
        return None, sorted(set(deselected)), sorted(set(errors)), False
    unique = {tuple(nodeids) for nodeids in collections}
    if len(unique) != 1:
        return None, sorted(set(deselected)), sorted(set(errors)), True
    return list(unique.pop()), sorted(set(deselected)), sorted(set(errors)), False


def _repeated_worker_collection(events: list[dict[str, Any]]) -> list[str] | None:
    """Use one worker collection only when every worker reported that same set.

    Differing per-worker subsets are not unioned or summed: without a
    controller collection that would invent a selection.
    """
    collections: list[tuple[str, ...]] = []
    for event in events:
        identity = event.get("identity") or {}
        if (
            identity.get("role") != "worker"
            or event.get("event") != "collection_finished"
        ):
            continue
        nodeids = event.get("nodeids")
        if isinstance(nodeids, list):
            collections.append(tuple(sorted(str(nodeid) for nodeid in nodeids)))
    if not collections:
        return None
    unique = set(collections)
    if len(unique) != 1 or not unique:
        return None
    return list(unique.pop())


def _dedup_outcomes(
    events: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str, int], dict[str, Any]], list[str]]:
    """Collapse controller redelivery when the originating worker also reported.

    Key is ``(nodeid, when, retry_index)``. A later pytest retry keeps its own
    index and is not merged into the earlier attempt. Two workers reporting
    the same key is a conflict, not an extra test.
    """
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event.get("event") != "outcome":
            continue
        identity = event.get("identity") or {}
        key = (
            str(event.get("nodeid") or ""),
            str(event.get("when") or ""),
            int(event.get("retry_index") or 0),
        )
        grouped[key].append(
            {
                "role": identity.get("role"),
                "worker_id": identity.get("worker_id"),
                "classification": event.get("classification"),
            }
        )
    reasons: list[str] = []
    chosen: dict[tuple[str, str, int], dict[str, Any]] = {}
    for key, rows in grouped.items():
        workers = [row for row in rows if row["role"] == "worker"]
        controllers = [row for row in rows if row["role"] == "controller"]
        pool = workers or controllers
        signatures = {(row["worker_id"], row["classification"]) for row in pool}
        if len(signatures) > 1:
            reasons.append("conflicting_outcome")
            continue
        chosen[key] = pool[0]
    return chosen, sorted(set(reasons))


def _terminal_states(
    selected: list[str],
    outcomes: dict[tuple[str, str, int], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    by_node: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)
    workers: dict[tuple[str, int], str] = {}
    for (nodeid, when, retry_index), row in outcomes.items():
        phase = by_node[nodeid].setdefault(retry_index, {})
        phase[when] = str(row["classification"])
        if row["role"] == "worker":
            workers[(nodeid, retry_index)] = str(row["worker_id"])
        else:
            workers.setdefault((nodeid, retry_index), str(row["worker_id"]))
    terminals: list[dict[str, Any]] = []
    missing: list[str] = []
    for nodeid in selected:
        attempts = by_node.get(nodeid) or {}
        if not attempts:
            missing.append(nodeid)
            continue
        retry_index = max(attempts)
        phases = attempts[retry_index]
        explained, classification = _explain_phases(phases)
        if not explained:
            missing.append(nodeid)
            continue
        terminals.append(
            {
                "nodeid": nodeid,
                "classification": classification,
                "call_classification": phases.get("call"),
                "retry_index": retry_index,
                "worker_id": workers.get((nodeid, retry_index), "controller"),
                "attempt_count": len(attempts),
            }
        )
    terminals.sort(key=lambda item: str(item["nodeid"]))
    return terminals, missing


def _explain_phases(phases: dict[str, str]) -> tuple[bool, str]:
    call = phases.get("call")
    setup = phases.get("setup")
    teardown = phases.get("teardown")
    if call in _CALL_CLASSIFICATIONS:
        if teardown == "teardown_error":
            return True, "teardown_error"
        return True, call
    if setup in _SETUP_TERMINAL and call is None:
        return True, setup
    return False, "unexplained"


def _session_flags(events: list[dict[str, Any]]) -> dict[str, Any]:
    selection: dict[str, Any] = {}
    exitstatus: int | None = None
    sha_error: str | None = None
    mismatch = False
    actual: str | None = None
    expected: str | None = None
    for event in events:
        identity = event.get("identity") or {}
        if event.get("event") == "checkout_mismatch":
            mismatch = True
            actual = event.get("actual") or actual
            expected = event.get("expected") or expected
        if identity.get("role") != "controller":
            continue
        if event.get("event") == "session_start":
            raw_selection = event.get("selection")
            if isinstance(raw_selection, dict):
                selection = raw_selection
            sha_error = event.get("sha_error")
            actual = identity.get("actual_checkout_sha")
            expected = identity.get("expected_checkout_sha")
        elif event.get("event") == "session_finish":
            status = event.get("exitstatus")
            if isinstance(status, int):
                exitstatus = status
    return {
        "selection": selection,
        "exitstatus": exitstatus,
        "sha_error": sha_error,
        "mismatch": mismatch,
        "actual_checkout_sha": actual,
        "expected_checkout_sha": expected,
    }


def reconcile_pass(receipts: list[dict[str, Any]], *, pass_name: str) -> dict[str, Any]:
    """Reconcile one runner pass. See module docstring for the status rules."""
    reasons: list[str] = []
    if not receipts:
        return _pass_verdict(
            pass_name=pass_name,
            status="unknown",
            reasons=["missing_receipt"],
            tests_passed=None,
        )
    if any(item["truncated"] for item in receipts):
        reasons.append("truncated_jsonl")
    if any(not item["finalized"] for item in receipts):
        reasons.append("missing_terminal_event")
    if any(item.get("io_error") for item in receipts):
        reasons.append("journal_io_error")
    events = [event for item in receipts for event in item["events"]]
    flags = _session_flags(events)
    if flags["mismatch"] or (
        flags["expected_checkout_sha"]
        and flags["actual_checkout_sha"]
        and flags["expected_checkout_sha"] != flags["actual_checkout_sha"]
    ):
        reasons.append("checkout_sha_mismatch")
    if flags["expected_checkout_sha"] and not flags["actual_checkout_sha"]:
        reasons.append("checkout_sha_unmeasured")
    damaged = [
        reason
        for reason in reasons
        if reason
        in {
            "truncated_jsonl",
            "missing_terminal_event",
            "journal_io_error",
            "checkout_sha_unmeasured",
        }
    ]
    selected, deselected, collection_errors, collection_conflict = (
        _controller_collection(events)
    )
    if selected is None:
        selected = _repeated_worker_collection(events)
    outcomes, outcome_reasons = _dedup_outcomes(events)
    reasons.extend(outcome_reasons)
    terminals: list[dict[str, Any]] = []
    missing: list[str] = []
    if selected is not None:
        terminals, missing = _terminal_states(selected, outcomes)
    selection = flags["selection"]
    collect_only = bool(selection.get("collect_only"))
    early_stop = bool(selection.get("exitfirst")) or (
        isinstance(selection.get("maxfail"), int) and int(selection["maxfail"]) > 0
    )
    if collect_only:
        reasons.append("collect_only")
    if collection_errors:
        reasons.append("collection_error")
    if collection_conflict:
        reasons.append("conflicting_collection")
    if missing and not collect_only:
        reasons.append("unexplained_selected_tests")
        if early_stop:
            reasons.append("early_stop")
    if (
        selected is None
        and "checkout_sha_mismatch" not in reasons
        and not damaged
        and not collection_errors
    ):
        reasons.append("missing_controller_collection")
    status = "complete"
    if (
        damaged
        or "conflicting_outcome" in reasons
        or "conflicting_collection" in reasons
    ):
        status = "unknown"
    elif "missing_controller_collection" in reasons:
        status = "unknown"
    elif (
        "checkout_sha_mismatch" in reasons
        or "collect_only" in reasons
        or "collection_error" in reasons
        or "unexplained_selected_tests" in reasons
    ):
        status = "incomplete"
    tests_passed: bool | None
    if status != "complete":
        tests_passed = None
    else:
        tests_passed = all(
            item["classification"] not in _FAILURE_CLASSIFICATIONS for item in terminals
        )
    return _pass_verdict(
        pass_name=pass_name,
        status=status,
        reasons=sorted(set(reasons)),
        tests_passed=tests_passed,
        selected_count=0 if selected is None else len(selected),
        deselected_count=len(deselected),
        terminals=terminals,
        unexplained=missing,
        actual_checkout_sha=flags["actual_checkout_sha"],
        expected_checkout_sha=flags["expected_checkout_sha"],
        workflow_run_attempt=_first_identity_field(events, "workflow_run_attempt"),
        invocation_id=_first_identity_field(events, "invocation_id"),
        job=_first_identity_field(events, "job"),
        matrix=_first_identity_value(events, "matrix"),
    )


def _first_identity_field(events: list[dict[str, Any]], field: str) -> str | None:
    for event in events:
        identity = event.get("identity") or {}
        value = identity.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def _first_identity_value(events: list[dict[str, Any]], field: str) -> Any:
    for event in events:
        identity = event.get("identity") or {}
        if field in identity:
            return identity[field]
    return None


def _pass_verdict(**payload: Any) -> dict[str, Any]:
    payload.setdefault("selected_count", 0)
    payload.setdefault("deselected_count", 0)
    payload.setdefault("terminals", [])
    payload.setdefault("unexplained", [])
    payload.setdefault("actual_checkout_sha", None)
    payload.setdefault("expected_checkout_sha", None)
    payload.setdefault("workflow_run_attempt", None)
    payload.setdefault("invocation_id", None)
    payload.setdefault("job", None)
    payload.setdefault("matrix", None)
    return payload


def authoritative_pass_names(executed_passes: list[str]) -> tuple[list[str], list[str]]:
    """Fallback supersedes parallel. Serial stays authoritative when it ran."""
    present = set(executed_passes)
    authoritative: list[str] = []
    superseded: list[str] = []
    if "fallback" in present:
        authoritative.append("fallback")
        if "parallel" in present:
            superseded.append("parallel")
    elif "parallel" in present:
        authoritative.append("parallel")
    if "serial" in present:
        authoritative.append("serial")
    return authoritative, superseded


def reconcile_directory(
    journal_dir: Path, *, executed_passes: list[str]
) -> dict[str, Any]:
    receipts = _group_receipts(journal_dir)
    by_pass: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        by_pass[_pass_of(receipt)].append(receipt)
    names = list(dict.fromkeys([*executed_passes, *sorted(by_pass)]))
    passes = {
        name: reconcile_pass(by_pass.get(name, []), pass_name=name) for name in names
    }
    authoritative, superseded = authoritative_pass_names(
        [name for name in executed_passes if name in {"parallel", "fallback", "serial"}]
        or [name for name in names if name in {"parallel", "fallback", "serial"}]
    )
    if not authoritative:
        status = "unknown"
        reasons = ["missing_receipt"]
        tests_passed = None
    else:
        states = [passes[name]["status"] for name in authoritative]
        if any(state == "unknown" for state in states):
            status = "unknown"
        elif any(state == "incomplete" for state in states):
            status = "incomplete"
        else:
            status = "complete"
        reasons = sorted(
            {
                f"{name}:{reason}"
                for name in authoritative
                for reason in passes[name]["reasons"]
            }
        )
        if status == "complete":
            tests_passed = all(
                bool(passes[name]["tests_passed"]) for name in authoritative
            )
        else:
            tests_passed = None
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reasons": reasons,
        "tests_passed": tests_passed,
        "authoritative_passes": authoritative,
        "superseded_passes": superseded,
        "executed_passes": executed_passes,
        "producer_scope": (
            "resilient-runner passes started by this process; "
            "other workflow jobs are outside this receipt"
        ),
        "passes": passes,
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Replace a JSON document atomically. Journal lines do not use this."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def verify_directory(
    journal_dir: Path, *, executed_passes: list[str] | None = None
) -> int:
    verdict_path = journal_dir / "journal-verdict.json"
    executed = executed_passes
    if executed is None and verdict_path.is_file():
        stored = json.loads(verdict_path.read_text(encoding="utf-8"))
        raw = stored.get("executed_passes")
        executed = [str(item) for item in raw] if isinstance(raw, list) else []
    verdict = reconcile_directory(journal_dir, executed_passes=executed or [])
    if verdict["status"] != "complete":
        sys.stderr.write(
            "EventJournal completeness "
            f"{verdict['status']}: {', '.join(verdict['reasons']) or 'unspecified'}\n"
        )
        return JOURNAL_COMPLETENESS_EXIT
    return 0


def _parse_verify_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, required=True)
    parser.add_argument("--executed-pass", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_verify_args(sys.argv[1:] if argv is None else argv)
    return verify_directory(
        args.verify,
        executed_passes=list(args.executed_pass) or None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
