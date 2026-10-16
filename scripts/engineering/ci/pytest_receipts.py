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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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
    r"(SECRET|TOKEN|PASSWORD|PASSWD|PWD|CREDENTIAL|PRIVATE|PAT|_KEY)",
    re.IGNORECASE,
)
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


def _porcelain_paths(repo_root: Path) -> list[str]:
    output = _git_output(
        repo_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if output is None:
        return []
    parts = output.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if len(entry) < 4:
            continue
        path = entry[3:]
        paths.append(path)
        if "R" in entry[:2] or "C" in entry[:2]:
            if index < len(parts) and parts[index]:
                paths.append(parts[index])
                index += 1
    return paths


def _is_run_output(path: str, receipt_dir: Path | None, repo_root: Path) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    if normalized == ".coverage" or normalized.startswith(".coverage."):
        return True
    if normalized.startswith(_OUTPUT_PREFIXES):
        return True
    if receipt_dir is None:
        return False
    try:
        relative = receipt_dir.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return False
    prefix = relative.as_posix()
    return normalized == prefix or normalized.startswith(prefix + "/")


def source_snapshot(repo_root: Path, receipt_dir: Path | None = None) -> dict[str, Any]:
    """Bind a receipt to HEAD plus measured dirty paths.

    Run outputs (reports, coverage, the receipt directory) are not treated as
    changes to the measured sources. A dirty measured tree is not described as
    a clean HEAD.
    """
    dirty = sorted(
        path
        for path in _porcelain_paths(repo_root)
        if path and not _is_run_output(path, receipt_dir, repo_root)
    )
    return {
        "head": git_head(repo_root),
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
    temporary = directory / ".receipt.json.tmp"
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, final)
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
    if setup == "xfailed" or call == "xfailed":
        return "xfailed"
    if call == "xpassed" or setup == "xpassed":
        if teardown == "error":
            return "teardown_error"
        return "xpassed"
    if call == "failed":
        return "failed"
    if teardown == "error":
        return "teardown_error"
    if call == "skipped" or setup == "skipped":
        return "skipped"
    if call == "passed":
        return "passed"
    return "error"


def _is_xdist_controller(config: Any) -> bool:
    if getattr(config, "workerinput", None) is not None:
        return False
    if os.environ.get("PYTEST_XDIST_WORKER"):
        return False
    if not config.pluginmanager.hasplugin("xdist"):
        return False
    dist = getattr(config.option, "dist", "no")
    workers = getattr(config.option, "numprocesses", None)
    if dist in (None, "no") and workers in (None, 0, "0"):
        return False
    return True


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
        self.worker_id = _safe_id(
            os.environ.get("PYTEST_XDIST_WORKER", "master"),
            "worker",
        )
        self.write_receipt = True
        self.collection_observed = False
        self.selected_nodeids: list[str] = []
        self.deselected_nodeids: list[str] = []
        self.collection_errors: list[str] = []
        self.results: dict[str, dict[str, str | None]] = {}
        self.source = source_snapshot(self.repo_root, self.receipt_dir)
        head = str(self.source["head"])
        if self.expected_sha and head != self.expected_sha:
            raise RuntimeError(
                f"Checkout SHA mismatch! Expected {self.expected_sha}, got {head}"
            )

    def pytest_configure(self, config: Any) -> None:
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
        phases = self.results.setdefault(str(report.nodeid), _blank_phases())
        phases[str(report.when)] = _phase_outcome(report)

    def _early_stop(self, session: Any) -> bool:
        if getattr(session, "shouldstop", False) or getattr(
            session, "shouldfail", False
        ):
            return True
        maxfail = getattr(session.config.option, "maxfail", 0) or 0
        failed = getattr(session, "testsfailed", 0) or 0
        return bool(maxfail) and failed >= maxfail

    def _completeness(self, early_stop: bool) -> str:
        if self.collection_errors or not self.collection_observed:
            return "unknown"
        missing = [
            nodeid for nodeid in self.selected_nodeids if nodeid not in self.results
        ]
        if early_stop and missing:
            return "incomplete"
        if missing:
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
            phases = self.results[nodeid]
            rendered[nodeid] = {
                "setup": phases.get("setup"),
                "call": phases.get("call"),
                "teardown": phases.get("teardown"),
                "terminal": terminal_outcome(phases),
            }
        return rendered

    def pytest_sessionfinish(self, session: Any, exitstatus: Any) -> None:
        if not self.write_receipt:
            return
        early_stop = self._early_stop(session)
        payload: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "role": "worker",
            "run_id": self.run_id,
            "attempt": self.attempt,
            "pass": self.pass_name,
            "worker": self.worker_id,
            "exit_code": int(exitstatus),
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
    """Record a timeout, crash, or aborted pass without inventing collection."""
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
        "observed_error": redact_secrets(observed_error)[:4000],
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
