"""Pytest plugin for immutable per-pass receipts.

Collection is recorded after marker deselection and is not derived from
JUnit or from executed outcomes. Each file is one invocation: pass, worker,
and attempt. The xdist controller does not write a combined receipt.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

ALLOWED_ENV_VARS = frozenset(
    {
        "CI",
        "GITHUB_ACTIONS",
        "PYTEST_XDIST_WORKER",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
    }
)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_SECRET_KEY_RE = re.compile(
    r"(SECRET|TOKEN|PASSWORD|PASSWD|PWD|CREDENTIAL|PRIVATE|PAT|_KEY|AUTH|URL|DSN|URI)",
    re.IGNORECASE,
)
_CRASH_OBSERVATION = re.compile(
    r"(^\[gw\d+\]\s+node down:\s+\S"
    r"|^replacing crashed worker gw\d+"
    r"|^worker gw\d+ crashed\b"
    r"|^maximum crashed workers reached:"
    r"|^xdist\.[\w.]*(?:internal error|Interrupted)\b)",
    re.IGNORECASE,
)
_MAXFAIL_OBSERVATION = re.compile(r"stopping after \d+ failures", re.IGNORECASE)
_OUTPUT_PREFIXES = (
    "reports/",
    ".pytest_cache/",
    "htmlcov/",
    ".mypy_cache/",
    ".ruff_cache/",
)
_SCHEMA_VERSION = 1


def _safe_id(value: str, label: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise ValueError(f"unsafe receipt {label}")
    return value


def _git_output(repo_root: Path, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def git_head(repo_root: Path) -> str:
    """Return HEAD or ``unknown`` when git cannot answer."""
    output = _git_output(repo_root, "rev-parse", "HEAD")
    if output is None:
        return "unknown"
    return output.strip() or "unknown"


def _porcelain_entries(repo_root: Path) -> list[tuple[str, str]] | None:
    output = _git_output(
        repo_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if output is None:
        return None
    parts = output.split("\0")
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if len(entry) < 4:
            continue
        status = entry[:2]
        entries.append((status, entry[3:]))
        if "R" in status or "C" in status:
            if index < len(parts) and parts[index]:
                entries.append((status, parts[index]))
                index += 1
    return entries


def _normalize_repo_path(path: str) -> str:
    """Drop a single ``./`` prefix without stripping a hidden-directory dot."""
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_run_output(
    path: str,
    status: str,
    receipt_dir: Path | None,
    repo_root: Path,
) -> bool:
    """Ignore this run's untracked outputs, not edits to tracked inputs."""
    normalized = _normalize_repo_path(path)
    if receipt_dir is not None:
        try:
            relative = receipt_dir.resolve().relative_to(repo_root.resolve())
        except ValueError:
            relative = None
        if relative is not None:
            prefix = _normalize_repo_path(relative.as_posix())
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return status == "??"
    if status != "??":
        return False
    if normalized == ".coverage" or normalized.startswith(".coverage."):
        return True
    return normalized.startswith(_OUTPUT_PREFIXES)


def source_snapshot(repo_root: Path, receipt_dir: Path | None = None) -> dict[str, Any]:
    """Bind a receipt to HEAD plus measured dirty paths.

    Untracked run outputs (reports, coverage, the receipt directory) are not
    measured-source changes. A modified tracked file, including one under
    ``reports/``, stays dirty. A dirty measured tree is not a clean HEAD.
    When git cannot read status, cleanliness stays unknown instead of true.
    """
    head = git_head(repo_root)
    entries = _porcelain_entries(repo_root)
    if entries is None:
        return {
            "head": head,
            "clean": None,
            "measured_dirty_paths": None,
        }
    dirty = sorted(
        {
            path
            for status, path in entries
            if path and not _is_run_output(path, status, receipt_dir, repo_root)
        }
    )
    return {
        "head": head,
        "clean": not dirty,
        "measured_dirty_paths": dirty,
    }


def allowed_environment(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return the receipt environment allowlist."""
    source = os.environ if env is None else env
    return {key: source[key] for key in sorted(ALLOWED_ENV_VARS) if key in source}


def redact_secrets(text: str, env: Mapping[str, str] | None = None) -> str:
    """Remove secret-bearing environment values from observed text."""
    redacted = text
    source = os.environ if env is None else env
    for key, value in source.items():
        if len(value) < 6 or _SECRET_KEY_RE.search(key) is None:
            continue
        redacted = redacted.replace(value, "[REDACTED]")
    return redacted


def receipt_dedupe_key(payload: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
    """Identity of one invocation. Attempts and passes stay distinct."""
    return (
        str(payload["run_id"]),
        str(payload["attempt"]),
        str(payload["pass"]),
        str(payload["role"]),
        str(payload["worker"]),
    )


def dedupe_receipts(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse identical receipts for one key. Conflicts fail closed."""
    grouped: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for payload in payloads:
        key = receipt_dedupe_key(payload)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = payload
            continue
        if existing != payload:
            raise ValueError(f"conflicting receipts for {key}")
    return [grouped[key] for key in sorted(grouped)]


def _resolve_dir(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if any(part == ".." for part in candidate.parts):
        raise ValueError("receipt dir must not contain '..'")
    return candidate.resolve()


def write_receipt_file(directory: Path, payload: Mapping[str, Any]) -> Path:
    """Atomically create ``receipt.json`` once. Existing files stay unchanged."""
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / "receipt.json"
    if final.exists():
        return final
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        dir=directory,
        prefix=".receipt.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(tmp_name, final)
        except FileExistsError:
            return final
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
    if not final.exists():
        raise OSError(f"receipt was not created: {final}")
    final.chmod(stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    return final


def _phase_outcome(report: Any) -> str:
    outcome = str(getattr(report, "outcome", ""))
    when = str(getattr(report, "when", ""))
    # Empty wasxfail is still an xfail; pytest uses hasattr, not truthiness.
    if hasattr(report, "wasxfail"):
        if outcome == "skipped":
            return "xfailed"
        if outcome == "passed":
            return "xpassed"
    if outcome == "failed" and when in {"setup", "teardown"}:
        return "error"
    return outcome


def terminal_outcome(phases: Mapping[str, str | None]) -> str:
    """Resolve one node. A failed teardown is not a pass."""
    setup = phases.get("setup")
    call = phases.get("call")
    teardown = phases.get("teardown")
    if setup == "error":
        return "setup_error"
    if teardown == "error" and (
        call in {"xfailed", "xpassed"} or setup in {"xfailed", "xpassed"}
    ):
        return "teardown_error"
    if setup == "xfailed" or call == "xfailed":
        return "xfailed"
    if call == "xpassed" or setup == "xpassed":
        return "xpassed"
    if call == "failed":
        return "failed"
    if teardown == "error":
        return "teardown_error"
    if call == "skipped" or setup == "skipped":
        return "skipped"
    if call == "passed":
        if teardown in {None, "skipped", "xfailed"}:
            return {None: "error", "skipped": "skipped", "xfailed": "xfailed"}[teardown]
        return "passed"
    return "error"


def _merge_phase(existing: str | None, new: str) -> str:
    """Keep an earlier failure when a later report for the same phase passes.

    ``unittest`` subtests emit a failed call report and then a passed report
    for the parent node. The failure stays the phase outcome.
    """
    if existing in {"failed", "error"} and new not in {"failed", "error"}:
        return existing
    return new


def _source_diverged(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    """True when HEAD moves or measured dirt appears or is restored.

    Two clean snapshots with empty dirty lists still diverge when a test
    commits or switches checkout. Collection ran on the starting HEAD.
    """
    if before.get("head") != after.get("head"):
        return True
    before_paths = before.get("measured_dirty_paths")
    after_paths = after.get("measured_dirty_paths")
    if isinstance(before_paths, list) and isinstance(after_paths, list):
        return set(before_paths) != set(after_paths)
    if before.get("clean") is False and after.get("clean") is not False:
        return True
    return before.get("clean") is True and after.get("clean") is not True


def _source_for_receipt(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, Any]:
    """Keep the starting dirty set when the run restores tracked files.

    A final clean snapshot must not replace an initial dirty one. The executed
    nodeids would otherwise be reported as the committed HEAD.
    """
    before_paths = before.get("measured_dirty_paths")
    after_paths = after.get("measured_dirty_paths")
    if isinstance(before_paths, list) and isinstance(after_paths, list):
        merged = dict(after)
        paths = sorted(set(before_paths) | set(after_paths))
        merged["measured_dirty_paths"] = paths
        if paths:
            merged["clean"] = False
        return _keep_starting_head(before, merged)
    if before.get("clean") is False and after.get("clean") is not False:
        return dict(before)
    return _keep_starting_head(before, dict(after))


def _keep_starting_head(
    before: Mapping[str, Any], snapshot: dict[str, Any]
) -> dict[str, Any]:
    """Report the HEAD that collection and the tests actually ran on."""
    if before.get("head") != snapshot.get("head"):
        snapshot["head"] = before.get("head")
    return snapshot


def _final_exit_code(session: Any, exitstatus: Any) -> int:
    """Return the exit code after other sessionfinish hooks have rewritten it."""
    return int(getattr(session, "exitstatus", exitstatus))


def _phases_finished(phases: Mapping[str, str | None]) -> bool:
    """A node is finished only after its terminal phase.

    A setup error or a setup-time skip/xfail ends the node. Any call still
    needs its teardown report; a missing teardown is an interrupted run.
    """
    setup = phases.get("setup")
    call = phases.get("call")
    teardown = phases.get("teardown")
    if setup == "error":
        return True
    if call is None:
        return setup in {"skipped", "xfailed", "xpassed"}
    return teardown is not None


def _occurrence_values(value: object) -> list[dict[str, str | None]]:
    """One phase map, or one map per duplicate nodeid."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _finished_occurrences(value: object) -> int:
    return sum(1 for phases in _occurrence_values(value) if _phases_finished(phases))


def _open_occurrence(
    bucket: list[dict[str, str | None]], when: str
) -> dict[str, str | None]:
    """Start a new occurrence when a second setup arrives for the same nodeid.

    ``--keep-duplicates`` reuses the nodeid. A later ``call`` report for one
    occurrence, including a unittest subtest, stays on the open occurrence.
    """
    if when == "setup" and bucket and bucket[-1].get("setup") is not None:
        bucket.append(_blank_phases())
    if not bucket:
        bucket.append(_blank_phases())
    return bucket[-1]


def _render_phases(phases: Mapping[str, str | None]) -> dict[str, Any]:
    return {
        "setup": phases.get("setup"),
        "call": phases.get("call"),
        "teardown": phases.get("teardown"),
        "terminal": terminal_outcome(phases),
    }


def _is_xdist_worker(config: Any) -> bool:
    """True only for a real xdist worker, not an inherited worker env."""
    return getattr(config, "workerinput", None) is not None


def _is_xdist_controller(config: Any) -> bool:
    """True only when this process distributes work and does not execute it."""
    if _is_xdist_worker(config):
        return False
    if not config.pluginmanager.hasplugin("xdist"):
        return False
    workers = getattr(config.option, "numprocesses", None)
    if workers not in (None, 0, "0", "no"):
        return True
    transports = getattr(config.option, "tx", None) or []
    return bool(transports)


def _blank_phases() -> dict[str, str | None]:
    return {"setup": None, "call": None, "teardown": None}


class ReceiptPlugin:
    """Collect one immutable receipt for this pytest process."""

    def __init__(
        self,
        receipt_dir: str,
        run_id: str,
        attempt: str,
        pass_name: str,
        expected_sha: str | None,
        repo_root: str | None,
    ) -> None:
        self.receipt_dir = _resolve_dir(receipt_dir)
        self.run_id = _safe_id(run_id, "run_id")
        self.attempt = _safe_id(attempt, "attempt")
        self.pass_name = _safe_id(pass_name, "pass")
        self.expected_sha = expected_sha
        self.repo_root = Path(repo_root).resolve() if repo_root else Path.cwd()
        self.worker_id = _safe_id("master", "worker")
        self.write_receipt = True
        self.collection_observed = False
        self.selected_nodeids: list[str] = []
        self.deselected_nodeids: list[str] = []
        self.collection_errors: list[str] = []
        self.results: dict[str, dict[str, str | None]] = {}
        self.source = source_snapshot(self.repo_root, self.receipt_dir)
        self.source_diverged = False
        head = str(self.source["head"])
        if self.expected_sha and head != self.expected_sha:
            message = f"Checkout SHA mismatch! Expected {self.expected_sha}, got {head}"
            write_runner_terminal_receipt(
                receipt_dir=self.receipt_dir,
                run_id=self.run_id,
                attempt=self.attempt,
                pass_name=self.pass_name,
                repo_root=self.repo_root,
                exit_code=3,
                terminal_kind="sha_mismatch",
                observed_error=message,
            )
            raise RuntimeError(message)

    def pytest_configure(self, config: Any) -> None:
        if _is_xdist_worker(config):
            self.worker_id = _safe_id(
                os.environ.get("PYTEST_XDIST_WORKER") or "master",
                "worker",
            )
        self.write_receipt = not _is_xdist_controller(config)

    def pytest_deselected(self, items: list[Any]) -> None:
        for item in items:
            nodeid = str(getattr(item, "nodeid", item))
            if nodeid not in self.deselected_nodeids:
                self.deselected_nodeids.append(nodeid)
        self.deselected_nodeids.sort()

    def pytest_collection_finish(self, session: Any) -> None:
        self.collection_observed = True
        self.selected_nodeids = sorted(str(item.nodeid) for item in session.items)

    def pytest_collectreport(self, report: Any) -> None:
        if report.failed:
            self.collection_errors.append(str(report.nodeid))

    def pytest_runtest_logreport(self, report: Any) -> None:
        if not self.write_receipt:
            return
        nodeid = str(report.nodeid)
        when = str(report.when)
        current = self.results.get(nodeid)
        if not isinstance(current, list):
            current = _occurrence_values(current)
            self.results[nodeid] = current
        phases = _open_occurrence(current, when)
        phases[when] = _merge_phase(phases.get(when), _phase_outcome(report))

    def _unfinished_selected(self) -> list[str]:
        needed: dict[str, int] = {}
        for nodeid in self.selected_nodeids:
            needed[nodeid] = needed.get(nodeid, 0) + 1
        return [
            nodeid
            for nodeid, count in needed.items()
            if _finished_occurrences(self.results.get(nodeid)) < count
        ]

    def _stop_was_requested(self, session: Any) -> bool:
        if getattr(session, "shouldstop", False) or getattr(
            session, "shouldfail", False
        ):
            return True
        maxfail = getattr(session.config.option, "maxfail", 0) or 0
        failed = getattr(session, "testsfailed", 0) or 0
        return bool(maxfail) and failed >= maxfail

    def _early_stop(self, session: Any) -> bool:
        """True only when a stop request left selected occurrences unfinished.

        ``--maxfail=1`` on the last selected test still finishes that test.
        The threshold alone is not an early stop.
        """
        return self._stop_was_requested(session) and bool(self._unfinished_selected())

    def _assigned_nodeids(self, session: Any) -> list[str] | None:
        """Shard assigned to this xdist worker, including tests still queued."""
        config = session.config
        if not _is_xdist_worker(config):
            return None
        interactor = next(
            (
                plugin
                for plugin in config.pluginmanager.get_plugins()
                if type(plugin).__name__ == "WorkerInteractor"
            ),
            None,
        )
        if interactor is None:
            return self._recorded_nodeids()
        pending: list[str] = []
        items = list(getattr(session, "items", []))
        torun = getattr(interactor, "torun", None)
        if torun is not None and hasattr(torun, "lock"):
            with torun.lock() as queued:
                for item in queued:
                    if isinstance(item, int) and 0 <= item < len(items):
                        pending.append(str(items[item].nodeid))
        assigned = [*self._recorded_nodeids(), *pending]
        next_index = getattr(interactor, "nextitem_index", None)
        if isinstance(next_index, int) and 0 <= next_index < len(items):
            next_nodeid = str(items[next_index].nodeid)
            if not self._current_occurrence_open(next_nodeid):
                assigned.append(next_nodeid)
        return sorted(assigned)

    def _recorded_nodeids(self) -> list[str]:
        recorded: list[str] = []
        for nodeid in sorted(self.results):
            recorded.extend([nodeid] * len(_occurrence_values(self.results[nodeid])))
        return recorded

    def _current_occurrence_open(self, nodeid: str) -> bool:
        occurrences = _occurrence_values(self.results.get(nodeid))
        if not occurrences:
            return False
        return not _phases_finished(occurrences[-1])

    def _completeness(self, early_stop: bool) -> str:
        if self.collection_errors or not self.collection_observed:
            return "unknown"
        missing = self._unfinished_selected()
        if early_stop or missing or getattr(self, "source_diverged", False):
            return "incomplete"
        return "complete"

    def _collection_payload(self) -> dict[str, Any]:
        if not self.collection_observed:
            return {"status": "unknown"}
        status = "error" if self.collection_errors else "observed"
        return {
            "status": status,
            "selected": len(self.selected_nodeids),
            "selected_nodeids": list(self.selected_nodeids),
            "deselected": len(self.deselected_nodeids),
            "deselected_nodeids": list(self.deselected_nodeids),
            "errors": list(self.collection_errors),
        }

    def _result_payload(self) -> dict[str, Any]:
        rendered: dict[str, Any] = {}
        for nodeid in sorted(self.results):
            items = [
                _render_phases(phases)
                for phases in _occurrence_values(self.results[nodeid])
            ]
            rendered[nodeid] = items[0] if len(items) == 1 else items
        return rendered

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_sessionfinish(self, session: Any, exitstatus: Any) -> Iterator[None]:
        """Write the receipt after every other sessionfinish wrapper.

        ``tryfirst`` runs this post-yield last, so the receipt stores the
        exit status left by wrappers that also use ``tryfirst``.
        """
        yield
        if not self.write_receipt:
            return
        assigned = self._assigned_nodeids(session)
        if assigned is not None:
            self.selected_nodeids = assigned
        finished = source_snapshot(self.repo_root, self.receipt_dir)
        self.source_diverged = _source_diverged(self.source, finished)
        self.source = _source_for_receipt(self.source, finished)
        early_stop = self._early_stop(session)
        payload: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "role": "worker",
            "run_id": self.run_id,
            "attempt": self.attempt,
            "pass": self.pass_name,
            "worker": self.worker_id,
            "exit_code": _final_exit_code(session, exitstatus),
            "early_stop": early_stop,
            "completeness": self._completeness(early_stop),
            "collection": self._collection_payload(),
            "results": self._result_payload(),
            "source": self.source,
            "environment": allowed_environment(),
        }
        target = (
            self.receipt_dir
            / self.run_id
            / self.attempt
            / self.pass_name
            / self.worker_id
        )
        write_receipt_file(target, payload)


def validate_receipt_ids(run_id: str, attempt: str) -> None:
    """Raise ValueError when a receipt id is not one safe path segment."""
    _safe_id(run_id, "run_id")
    _safe_id(attempt, "attempt")


def _clip_observed_error(text: str, limit: int = 4000) -> str:
    """Keep a crash line that pytest prints after a long quiet log.

    The first 4000 characters of a ``-q`` run are progress marks. The node-down
    line is at the end, so a long observation keeps that tail and any earlier
    crash line that the tail would drop.
    """
    redacted = redact_secrets(text)
    if len(redacted) <= limit:
        return redacted
    matched = [
        line
        for line in redacted.splitlines()
        if _CRASH_OBSERVATION.search(line) and not _MAXFAIL_OBSERVATION.search(line)
    ]
    tail = redacted[-limit:]
    if not matched or "\n".join(matched) in tail:
        return tail
    prefix = "\n".join(matched)
    if len(prefix) >= limit:
        return prefix[-limit:]
    room = limit - len(prefix) - 1
    return prefix if room <= 0 else f"{prefix}\n{redacted[-room:]}"


def write_runner_terminal_receipt(
    *,
    receipt_dir: Path,
    run_id: str,
    attempt: str,
    pass_name: str,
    repo_root: Path,
    exit_code: int,
    terminal_kind: str,
    observed_error: str,
) -> Path:
    """Record a timeout, crash, SHA mismatch, or aborted pass.

    Collection and node outcomes stay unknown. The observed error is redacted.
    """
    directory = _resolve_dir(str(receipt_dir))
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "role": "runner",
        "run_id": _safe_id(run_id, "run_id"),
        "attempt": _safe_id(attempt, "attempt"),
        "pass": _safe_id(pass_name, "pass"),
        "worker": "runner",
        "exit_code": exit_code,
        "early_stop": True,
        "terminal_kind": terminal_kind,
        "observed_error": _clip_observed_error(observed_error),
        "completeness": "unknown",
        "collection": {"status": "unknown"},
        "results": None,
        "source": source_snapshot(repo_root, directory),
        "environment": allowed_environment(),
    }
    target = directory / payload["run_id"] / payload["attempt"] / pass_name / "runner"
    return write_receipt_file(target, payload)


def pytest_addoption(parser: Any) -> None:
    parser.addoption("--receipt-dir", action="store", default=None)
    parser.addoption("--receipt-run-id", action="store", default="local")
    parser.addoption("--receipt-attempt", action="store", default="1")
    parser.addoption("--receipt-pass", action="store", default="direct")
    parser.addoption("--receipt-expected-sha", action="store", default=None)
    parser.addoption("--receipt-repo-root", action="store", default=None)


def pytest_configure(config: Any) -> None:
    receipt_dir = config.getoption("--receipt-dir")
    if not receipt_dir:
        return
    plugin = ReceiptPlugin(
        receipt_dir,
        config.getoption("--receipt-run-id"),
        config.getoption("--receipt-attempt"),
        config.getoption("--receipt-pass"),
        config.getoption("--receipt-expected-sha"),
        config.getoption("--receipt-repo-root"),
    )
    config.pluginmanager.register(plugin, "bioetl_receipt_plugin")
    plugin.pytest_configure(config)
