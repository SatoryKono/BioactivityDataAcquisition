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
A close-error marker beside the receipt overrides ``io_error`` on the
finalized line.

Completeness is not the row count or pytest's exit code. ``complete``
requires an intact controller receipt, intact worker receipts for every
forwarded origin, and an explained terminal state for every selected
instance. Setup-terminal outcomes still need a teardown report.
Deselected nodeids are removed before that match. Repeated nodeids stay
separate instances. A complete run may still contain failures.
``GITHUB_RUN_ATTEMPT`` is the workflow attempt, not a retry inside this
runner. Reconciliation keeps the latest invocation of each pass, or the
invocation recorded for this process, and the workers that share it.
The verdict stores those invocation ids, and ``--verify`` uses them
instead of ranking the directory again. A controller receipt without
``session_finish`` is not complete. A
damaged receipt with no authoritative pass and invocation blocks the
whole directory. Receipt bytes must be strict UTF-8. Every event must
carry integer ``schema_version`` equal to ``SCHEMA_VERSION``; a missing
or different version damages the receipt. A close-error marker that is
empty, unreadable, or not valid UTF-8 also damages it. Redaction tokens
are keyed outside the receipt. A later session-finish hook that raises
or changes the exit status is stored as ``hook_error`` and keeps the
pass from being complete. An intermediate ``rerun`` report is an attempt,
not a damaged classification. A controller ``session_finish`` counts only
when ``exitstatus`` is an integer. A direct pytest session without a runner
pass name is an authoritative ``unspecified`` pass. A phase that only one
duplicate recorded is not copied onto the other duplicate.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

SCHEMA_VERSION = 1
JOURNAL_COMPLETENESS_EXIT = 4
GIT_SHA_TIMEOUT_SECONDS = 10.0
_SECRET_KEY = re.compile(
    r"(?i)(secret|token|password|passwd|api[_-]?key|access[_-]?key|"
    r"credential|authorization)"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:^|[^A-Za-z0-9])"
    r"(token|secret|password|passwd|api[_-]?key|access[_-]?key|"
    r"authorization|credential)"
    r"""['"]?\s*[:=]\s*(?:"([^"]*)"|'([^']*)'|([^\s,;\]"']+))"""
)
_REDACTION_KEY_ENV = "BIOETL_JOURNAL_REDACTION_KEY"
_REDACTION_KEY_MIN_LENGTH = 32
_REDACTION_KEY: str | None = None
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SECRET_PREFIX = re.compile(
    r"(?:ghp_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9]+|"
    r"xox[baprs]-[A-Za-z0-9-]+|AKIA[A-Z0-9]{16})"
)
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
_FAILURE_CLASSIFICATIONS = frozenset({"failed", "setup_error", "teardown_error"})
_WHEN_CLASSIFICATIONS = {
    "setup": frozenset({"passed", "skipped", "setup_error", "xfail", "rerun"}),
    "call": frozenset({"passed", "failed", "skipped", "xfail", "xpass", "rerun"}),
    "teardown": frozenset({"passed", "skipped", "teardown_error", "rerun"}),
}
_TEARDOWN_SUCCESS = frozenset({"passed", "skipped"})
_HEX_32 = re.compile(r"^[0-9a-f]{32}$")
_PATH_TOKEN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_AUTHORITATIVE_PASS_NAMES = frozenset({"parallel", "serial", "fallback"})
_RECEIPT_FILENAME = re.compile(
    r"^receipt_(?P<pass_name>parallel|serial|fallback|unspecified)_"
    r"(?P<invocation>[0-9a-f]{32})_"
    r"(?P<role>controller|worker)_(?P<worker>.+)_"
    r"(?P<file_id>[0-9a-f]{32})\.jsonl$"
)


def pytest_addoption(parser: Any) -> None:
    parser.addoption(
        "--event-journal-dir",
        action="store",
        default=None,
        help="Directory for pytest event-journal receipts",
    )


def ensure_redaction_key() -> str:
    """Return the process-local HMAC key for redaction tokens.

    A long BIOETL_JOURNAL_REDACTION_KEY is reused. Otherwise the process
    keeps one generated key. The key is not written into receipts.
    """
    global _REDACTION_KEY
    current = os.environ.get(_REDACTION_KEY_ENV, "")
    if len(current) >= _REDACTION_KEY_MIN_LENGTH:
        _REDACTION_KEY = current
        return current
    if _REDACTION_KEY is not None and len(_REDACTION_KEY) >= _REDACTION_KEY_MIN_LENGTH:
        return _REDACTION_KEY
    _REDACTION_KEY = secrets.token_hex(32)
    return _REDACTION_KEY


def publish_redaction_key() -> None:
    """Expose the process key to child processes spawned after configure."""
    os.environ[_REDACTION_KEY_ENV] = ensure_redaction_key()


def _adopt_worker_redaction_key(config: Any) -> None:
    """Reuse the controller key shipped in xdist ``workerinput``."""
    global _REDACTION_KEY
    workerinput = getattr(config, "workerinput", None)
    if not isinstance(workerinput, dict):
        return
    key = workerinput.get(_REDACTION_KEY_ENV)
    if isinstance(key, str) and len(key) >= _REDACTION_KEY_MIN_LENGTH:
        os.environ[_REDACTION_KEY_ENV] = key
        _REDACTION_KEY = key


def _redaction_token(secret: str) -> str:
    digest = hmac.new(
        ensure_redaction_key().encode("utf-8"),
        secret.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:12]
    return f"[redacted:{digest}]"


def _assigned_secret(match: re.Match[str]) -> tuple[int, str]:
    for index in (2, 3, 4):
        value = match.group(index)
        if value is not None:
            return index, value
    return 4, ""


def _replace_assignment(match: re.Match[str]) -> str:
    index, value = _assigned_secret(match)
    prefix = match.group(0)[: match.start(index) - match.start(0)]
    suffix = match.group(0)[match.end(index) - match.start(0) :]
    return prefix + _redaction_token(value) + suffix


def _replace_prefix(match: re.Match[str]) -> str:
    return _redaction_token(match.group(0))


def _secret_values() -> tuple[str, ...]:
    values = {
        value
        for key, value in os.environ.items()
        if len(value) >= 8 and _SECRET_KEY.search(key) is not None
    }
    return tuple(sorted(values, key=len, reverse=True))


def _redact_text(text: str, secrets: tuple[str, ...]) -> str:
    redacted = text
    for secret in secrets:
        if secret and secret in redacted:
            redacted = redacted.replace(secret, _redaction_token(secret))
    redacted = _SECRET_ASSIGNMENT.sub(_replace_assignment, redacted)
    return _SECRET_PREFIX.sub(_replace_prefix, redacted)


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
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
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


def _redact_secret_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redaction_token(value)
    if isinstance(value, dict):
        return {str(key): _redact_secret_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_secret_value(item) for item in value]
    if value is None:
        return None
    return _redaction_token(str(value))


def _redact_structured(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            if _SECRET_KEY.search(name) is not None:
                redacted[name] = _redact_secret_value(item)
            else:
                redacted[name] = _redact_structured(item, secrets)
        return redacted
    if isinstance(value, list):
        return [_redact_structured(item, secrets) for item in value]
    if isinstance(value, str):
        return _redact_text(value, secrets)
    return value


def _redacted_matrix(raw: str, secrets: tuple[str, ...]) -> Any:
    parsed = _parse_matrix(raw)
    if not isinstance(parsed, dict):
        return None
    return _redact_structured(parsed, secrets)


def _matrix_env_text(raw: str, secrets: tuple[str, ...]) -> str:
    redacted = _redacted_matrix(raw, secrets)
    if redacted is None:
        return _redact_text(raw, secrets)
    return json.dumps(redacted, sort_keys=True, ensure_ascii=True)


def _safe_env(secrets: tuple[str, ...]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key in sorted(_SAFE_ENV_KEYS):
        if key not in os.environ:
            continue
        raw = os.environ[key]
        if key == "BIOETL_JOURNAL_MATRIX":
            redacted[key] = _matrix_env_text(raw, secrets)
            continue
        redacted[key] = _redact_text(raw, secrets)
    return redacted


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
        "matrix": _redacted_matrix(matrix_raw, secrets),
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
        if not _arm_close_marker(self.path):
            self._mark_io_error("close_marker_failed")
            return
        self.record(
            "journal_finalized",
            {"prior_line_count": self._line_count, "io_error": self._io_error},
        )
        if self._closed or self._io_error:
            return
        if not self._close_receipt():
            return
        _disarm_close_marker(self.path)

    def _close_receipt(self) -> bool:
        if self._file is None or self._closed:
            self._closed = True
            return True
        try:
            self._file.close()
        except OSError as exc:
            self._closed = True
            self._io_error = f"close_failed:{exc.errno}"
            sys.stderr.write(f"EventJournal: close_failed:{exc.errno}\n")
            _record_close_error(self.path, exc.errno)
            return False
        self._closed = True
        return True

    def record_selected(self, items: list[Any]) -> None:
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
        payload: dict[str, Any] = {
            "nodeid": str(report.nodeid),
            "when": str(report.when),
            "classification": classification,
            "retry_index": int(retry_index),
            "wasxfail": wasxfail is not None,
            "subtest": type(report).__name__ == "SubtestReport",
        }
        origin = _origin_worker(report)
        if origin is not None:
            payload["origin_worker"] = origin
        self.record("outcome", payload)


def _origin_worker(report: Any) -> str | None:
    """Worker id stamped by xdist on a controller-forwarded report."""
    node = getattr(report, "node", None)
    if node is None:
        return None
    gateway = getattr(node, "gateway", None)
    gateway_id = getattr(gateway, "id", None)
    if isinstance(gateway_id, str) and gateway_id:
        return gateway_id
    if isinstance(node, str) and node:
        return node
    return None


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


def _register_collection_hook(config: Any, plugin: EventJournalPlugin) -> None:
    """Record the collection after marker deselection has changed ``items``."""
    import pytest

    class _CollectionHook:
        def __init__(self, owner: EventJournalPlugin) -> None:
            self._owner = owner

        @pytest.hookimpl(hookwrapper=True, tryfirst=True)
        def pytest_collection_modifyitems(
            self,
            session: Any,
            config: Any,
            items: list[Any],
        ) -> Any:
            _ = (session, config)
            outcome = yield
            outcome.get_result()
            self._owner.record_selected(items)

    hook_plugin = _CollectionHook(plugin)
    config.pluginmanager.register(hook_plugin, "event_journal_collection_hook")
    _promote_collection_hook(config, hook_plugin)


def _promote_collection_hook(config: Any, hook_plugin: Any) -> None:
    """Re-register the recorder so its post-yield runs after other wrappers."""
    import pytest

    class _Promote:
        @pytest.hookimpl(hookwrapper=True, tryfirst=True)
        def pytest_collection(self, session: Any) -> Any:
            _ = session
            manager = config.pluginmanager
            if manager.is_registered(hook_plugin):
                manager.unregister(name="event_journal_collection_hook")
                manager.register(hook_plugin, "event_journal_collection_hook")
            yield

    config.pluginmanager.register(_Promote(), "event_journal_collection_promote")


def _session_finish_payload(
    session: Any, exitstatus: int, outcome: Any
) -> dict[str, Any]:
    """Read the exit status after the other session-finish hooks have run."""
    final = getattr(session, "exitstatus", exitstatus)
    try:
        final_status = int(final)
    except (TypeError, ValueError):
        final_status = 1
    try:
        initial_status = int(exitstatus)
    except (TypeError, ValueError):
        initial_status = final_status
    hook_failed = getattr(outcome, "excinfo", None) is not None
    if hook_failed and final_status == 0:
        final_status = 1
    payload: dict[str, Any] = {"exitstatus": final_status}
    if hook_failed or final_status != initial_status:
        payload["hook_error"] = True
    return payload


def _register_session_finish_hook(config: Any, plugin: EventJournalPlugin) -> None:
    """Record session finish, then finalize after pytest_unconfigure."""
    import pytest

    class _UnconfigureHook:
        def __init__(self, owner: EventJournalPlugin) -> None:
            self._owner = owner

        @pytest.hookimpl(hookwrapper=True, tryfirst=True)
        def pytest_unconfigure(self, config: Any) -> Any:
            _ = config
            outcome = yield
            if getattr(outcome, "excinfo", None) is not None:
                self._owner.record("unconfigure_error", {"hook_error": True})
            self._owner.finalize()
            outcome.get_result()

    class _SessionFinishHook:
        def __init__(
            self, owner: EventJournalPlugin, unconfigure: _UnconfigureHook
        ) -> None:
            self._owner = owner
            self._unconfigure = unconfigure

        @pytest.hookimpl(hookwrapper=True, tryfirst=True)
        def pytest_sessionfinish(self, session: Any, exitstatus: int) -> Any:
            outcome = yield
            self._owner.record(
                "session_finish",
                _session_finish_payload(session, exitstatus, outcome),
            )
            manager = session.config.pluginmanager
            if manager.is_registered(self._unconfigure):
                manager.unregister(self._unconfigure)
                manager.register(self._unconfigure, "event_journal_unconfigure_hook")
            outcome.get_result()

    unconfigure = _UnconfigureHook(plugin)
    config.pluginmanager.register(unconfigure, "event_journal_unconfigure_hook")
    config.pluginmanager.register(
        _SessionFinishHook(plugin, unconfigure),
        "event_journal_session_finish_hook",
    )


def _path_token(value: str, *, pattern: re.Pattern[str], fallback: str) -> str:
    if value in {".", ".."} or "/" in value or "\\" in value:
        return fallback
    if pattern.fullmatch(value):
        return value
    return fallback


def _receipt_path(directory: Path, identity: dict[str, Any]) -> Path:
    """Build a receipt path that cannot leave ``directory``."""
    role = identity.get("role")
    if role not in {"controller", "worker"}:
        role = "controller"
    pass_name = _path_token(
        str(identity.get("pass_name") or ""),
        pattern=re.compile(r"^(?:parallel|serial|fallback|unspecified)$"),
        fallback="unspecified",
    )
    invocation = _path_token(
        str(identity.get("invocation_id") or ""),
        pattern=_HEX_32,
        fallback=hashlib.sha256(
            str(identity.get("invocation_id") or "").encode("utf-8")
        ).hexdigest()[:32],
    )
    worker = _path_token(
        str(identity.get("worker_id") or ""),
        pattern=_PATH_TOKEN,
        fallback="worker" if role == "worker" else "controller",
    )
    filename = (
        f"receipt_{pass_name}_{invocation}_{role}_{worker}_{uuid.uuid4().hex}.jsonl"
    )
    return directory / filename


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node: Any) -> None:
    """Pass one redaction key to each xdist worker before it starts."""
    publish_redaction_key()
    workerinput = getattr(node, "workerinput", None)
    if isinstance(workerinput, dict):
        workerinput[_REDACTION_KEY_ENV] = ensure_redaction_key()


def pytest_configure(config: Any) -> None:
    _adopt_worker_redaction_key(config)
    journal_dir = config.getoption("--event-journal-dir")
    if not journal_dir:
        return
    publish_redaction_key()
    secrets = _secret_values()
    actual_sha, sha_error = measure_checkout_sha()
    identity = _identity_from_env(actual_sha=actual_sha, secrets=secrets)
    directory = Path(str(journal_dir))
    plugin = EventJournalPlugin(config, _receipt_path(directory, identity), identity)
    if plugin._file is None:
        return
    config.pluginmanager.register(plugin, "event_journal_plugin")
    _register_collection_hook(config, plugin)
    _register_session_finish_hook(config, plugin)
    plugin.record(
        "session_start",
        {
            "selection": _selection_from_config(config, secrets),
            "sha_error": sha_error,
            "safe_env": _safe_env(secrets),
            "allow_no_tests": os.environ.get("BIOETL_JOURNAL_ALLOW_NO_TESTS") == "1",
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


def _marker_path(path: Path) -> Path:
    return path.with_name(path.name + ".close_error")


def _arm_close_marker(path: Path) -> bool:
    try:
        _marker_path(path).write_text("pending\n", encoding="utf-8", newline="\n")
    except OSError:
        return False
    return True


def _record_close_error(path: Path, errno: int | None) -> None:
    try:
        _marker_path(path).write_text(
            f"close_failed:{errno}\n",
            encoding="utf-8",
            newline="\n",
        )
    except OSError:
        return


def _disarm_close_marker(path: Path) -> None:
    try:
        _marker_path(path).unlink(missing_ok=True)
    except OSError as exc:
        _record_close_error(path, exc.errno)


def _marker_io_error(path: Path) -> str | None:
    marker = _marker_path(path)
    if not marker.is_file():
        return None
    try:
        raw = marker.read_bytes()
    except OSError:
        return "close_marker_unreadable"
    try:
        text = raw.decode("utf-8").strip()
    except UnicodeDecodeError:
        return "close_marker_invalid_utf8"
    if text:
        return text
    return "close_marker_present"


def _recorded_io_error(events: list[dict[str, Any]]) -> str | None:
    for event in events:
        if event.get("event") != "journal_finalized":
            continue
        value = event.get("io_error")
        if isinstance(value, str) and value:
            return value
        return None
    return None


def _receipt_io_error(path: Path, events: list[dict[str, Any]]) -> str | None:
    marker_error = _marker_io_error(path)
    if marker_error is not None:
        return marker_error
    return _recorded_io_error(events)


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _optional_str(event: dict[str, Any], field: str) -> bool:
    value = event.get(field)
    return value is None or isinstance(value, str)


def _optional_bool(event: dict[str, Any], field: str) -> bool:
    value = event.get(field)
    return value is None or type(value) is bool


def _classification_allowed(event: dict[str, Any]) -> bool:
    classification = event.get("classification")
    when = event.get("when")
    if classification is None and when is None:
        return True
    if not isinstance(classification, str) or not isinstance(when, str):
        return False
    allowed = _WHEN_CLASSIFICATIONS.get(when)
    return allowed is not None and classification in allowed


def _optional_count(event: dict[str, Any], field: str) -> bool:
    value = event.get(field)
    return value is None or _is_non_negative_int(value)


def _identity_well_formed(event: dict[str, Any]) -> bool:
    identity = event.get("identity")
    return identity is None or isinstance(identity, dict)


def _nodeids_well_formed(event: dict[str, Any]) -> bool:
    nodeids = event.get("nodeids")
    if nodeids is None:
        return True
    if not isinstance(nodeids, list):
        return False
    return all(isinstance(nodeid, str) for nodeid in nodeids)


def _outcome_fields_well_formed(event: dict[str, Any]) -> bool:
    return (
        _optional_str(event, "nodeid")
        and _optional_str(event, "when")
        and _optional_str(event, "classification")
        and _classification_allowed(event)
        and _optional_bool(event, "subtest")
        and _optional_str(event, "origin_worker")
        and _optional_count(event, "retry_index")
        and _optional_count(event, "instance_ordinal")
        and _optional_count(event, "exitstatus")
    )


def _schema_supported(event: dict[str, Any]) -> bool:
    version = event.get("schema_version")
    return type(version) is int and version == SCHEMA_VERSION


def _event_is_well_formed(event: dict[str, Any]) -> bool:
    if not isinstance(event.get("event"), str):
        return False
    return (
        _schema_supported(event)
        and _identity_well_formed(event)
        and _nodeids_well_formed(event)
        and _outcome_fields_well_formed(event)
    )


def _parse_receipt_line(line: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict) and _event_is_well_formed(parsed):
        return parsed
    return None


def _invalid_utf8_receipt(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "events": [],
        "truncated": True,
        "finalized": False,
        "io_error": "invalid_utf8",
    }


def _load_receipt(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    truncated = bool(raw) and not raw.endswith(b"\n")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return _invalid_utf8_receipt(path)
    events: list[dict[str, Any]] = []
    parse_error = False
    for line in text.splitlines():
        if not line.strip():
            continue
        parsed = _parse_receipt_line(line)
        if parsed is None:
            parse_error = True
            continue
        events.append(parsed)
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
        "io_error": _receipt_io_error(path, events),
    }


def _unreadable_receipt(path: Path, errno: int | None) -> dict[str, Any]:
    return {
        "path": str(path),
        "events": [],
        "truncated": True,
        "finalized": False,
        "io_error": f"receipt_unreadable:{errno}",
    }


def _group_receipts(journal_dir: Path) -> list[dict[str, Any]]:
    try:
        if not journal_dir.is_dir():
            return []
        paths = sorted(journal_dir.glob("receipt_*.jsonl"))
    except OSError as exc:
        return [_unreadable_receipt(journal_dir, exc.errno)]
    receipts: list[dict[str, Any]] = []
    for path in paths:
        try:
            receipts.append(_load_receipt(path))
        except OSError as exc:
            receipts.append(_unreadable_receipt(path, exc.errno))
    return receipts


def _filename_identity(path: str) -> tuple[str, str] | None:
    match = _RECEIPT_FILENAME.fullmatch(Path(path).name)
    if match is None:
        return None
    return match.group("pass_name"), match.group("invocation")


def _pass_of(receipt: dict[str, Any]) -> str:
    for event in receipt["events"]:
        identity = _event_identity(event)
        name = identity.get("pass_name")
        if isinstance(name, str) and name:
            return name
    parsed = _filename_identity(str(receipt.get("path") or ""))
    if parsed is not None:
        return parsed[0]
    return "unspecified"


def _note_controller_event(
    event: dict[str, Any],
    collections: list[list[str]],
    errors: list[str],
) -> None:
    kind = event.get("event")
    nodeids = event.get("nodeids")
    if kind == "collection_finished" and isinstance(nodeids, list):
        collections.append(sorted(str(nodeid) for nodeid in nodeids))
        return
    if kind == "collection_error":
        errors.append(str(event.get("nodeid") or ""))


def _unique_collection(
    collections: list[list[str]],
) -> tuple[list[str] | None, bool]:
    if not collections:
        return None, False
    unique = {tuple(nodeids) for nodeids in collections}
    if len(unique) != 1:
        return None, True
    return list(unique.pop()), False


def _deselected_nodeids(events: list[dict[str, Any]]) -> list[str]:
    """Count deselection once per nodeid across controller and workers.

    ``collection_finished`` is already the final list, so these ids are not
    removed again. Worker copies of the same deselection do not multiply.
    """
    controller: Counter[str] = Counter()
    workers: dict[str, Counter[str]] = {}
    for event in events:
        if event.get("event") != "deselected":
            continue
        nodeids = event.get("nodeids")
        if not isinstance(nodeids, list):
            continue
        counts = Counter(str(nodeid) for nodeid in nodeids)
        identity = _event_identity(event)
        if identity.get("role") == "worker":
            worker_id = str(identity.get("worker_id") or "")
            workers.setdefault(worker_id, Counter()).update(counts)
            continue
        controller.update(counts)
    merged = Counter(controller)
    for counts in workers.values():
        for nodeid, count in counts.items():
            merged[nodeid] = max(merged[nodeid], count)
    return sorted(merged.elements())


def _controller_collection(
    events: list[dict[str, Any]],
) -> tuple[list[str] | None, list[str], list[str], bool]:
    """Return controller nodeids, deselected nodeids, errors, and conflict.

    Worker collection lists are ignored so per-worker collection cannot be
    summed into extra tests. Deselection is counted, not subtracted: the
    recorded collection is the list that remains after the collection hooks.
    """
    collections: list[list[str]] = []
    errors: list[str] = []
    for event in events:
        identity = _event_identity(event)
        if identity.get("role") != "controller":
            continue
        _note_controller_event(event, collections, errors)
    selected, conflict = _unique_collection(collections)
    return selected, _deselected_nodeids(events), sorted(set(errors)), conflict


def _selected_nodeids(
    events: list[dict[str, Any]],
    *,
    allow_worker_collection: bool,
) -> tuple[list[str] | None, list[str], list[str], bool]:
    selected, deselected, errors, conflict = _controller_collection(events)
    if selected is None and allow_worker_collection and not conflict:
        selected = _repeated_worker_collection(events)
    return selected, deselected, errors, conflict


def _repeated_worker_collection(events: list[dict[str, Any]]) -> list[str] | None:
    """Use one worker collection only when every worker reported that same set.

    The caller uses that list only beside an intact controller receipt whose
    collections did not conflict. Differing per-worker subsets are not unioned.
    """
    collections: list[tuple[str, ...]] = []
    for event in events:
        identity = _event_identity(event)
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


def _group_outcome_rows(
    events: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str, int], list[dict[str, Any]]], list[str]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    reasons: list[str] = []
    for event in events:
        if event.get("event") != "outcome":
            continue
        retry_index = event.get("retry_index", 0)
        if retry_index is None:
            retry_index = 0
        if not _is_non_negative_int(retry_index):
            reasons.append("malformed_outcome")
            continue
        identity = _event_identity(event)
        key = (
            str(event.get("nodeid") or ""),
            str(event.get("when") or ""),
            retry_index,
        )
        grouped[key].append(
            {
                "role": identity.get("role"),
                "worker_id": identity.get("worker_id"),
                "classification": event.get("classification"),
                "subtest": event.get("subtest") is True,
            }
        )
    return grouped, reasons


def _phase_reports(pool: list[dict[str, Any]]) -> list[str]:
    """Keep one classification per copy, including copies on other workers.

    Workers that report the same classification are not a conflict. Each
    worker's rows stay in the count so ``--keep-duplicates`` across ``-n``
    still matches the selected copies.
    """
    by_worker: dict[str, list[str]] = defaultdict(list)
    for row in pool:
        by_worker[str(row.get("worker_id"))].append(str(row.get("classification")))
    merged: list[str] = []
    for group in by_worker.values():
        merged.extend(group)
    return merged


def _collapse_outcome_pool(
    pool: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Merge subtest reports. Distinct copies keep their own classifications."""
    if any(row.get("subtest") for row in pool):
        parents = [row for row in pool if not row.get("subtest")]
        if len({row["classification"] for row in parents}) > 1:
            return None
        ranked = parents + [row for row in pool if row.get("subtest")]
        worst = max(
            ranked,
            key=lambda row: (
                row["classification"] in _FAILURE_CLASSIFICATIONS,
                str(row["classification"]),
            ),
        )
        count = len(parents) if parents else 1
        base = parents[0] if parents else pool[0]
        return {
            **base,
            "subtest": False,
            "classification": worst["classification"],
            "classifications": [str(worst["classification"])] * count,
            "count": count,
        }
    reports = _phase_reports(pool)
    if not reports:
        return None
    unique = set(reports)
    return {
        **pool[0],
        "classification": reports[0] if len(unique) == 1 else None,
        "classifications": reports,
        "count": len(reports),
    }


def _dedup_outcomes(
    events: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str, int], dict[str, Any]], list[str]]:
    """Collapse controller redelivery when the originating worker also reported.

    Key is ``(nodeid, when, retry_index)``. A later pytest retry keeps its own
    index and is not merged into the earlier attempt. Identical reports of one
    key count as separate item instances. Different classifications of one
    selected copy conflict; different copies of one nodeid stay separate.
    """
    grouped, reasons = _group_outcome_rows(events)
    chosen: dict[tuple[str, str, int], dict[str, Any]] = {}
    for key, rows in grouped.items():
        workers = [row for row in rows if row["role"] == "worker"]
        controllers = [row for row in rows if row["role"] == "controller"]
        pool = workers or controllers
        collapsed = _collapse_outcome_pool(pool)
        if collapsed is None:
            reasons.append("conflicting_outcome")
            continue
        chosen[key] = collapsed
    return chosen, sorted(set(reasons))


def _terminal_states(
    selected: list[str],
    outcomes: dict[tuple[str, str, int], dict[str, Any]],
    events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    by_node: dict[str, dict[int, dict[str, list[str]]]] = defaultdict(dict)
    workers: dict[tuple[str, int], str] = {}
    for (nodeid, when, retry_index), row in outcomes.items():
        phase = by_node[nodeid].setdefault(retry_index, {})
        recorded = row.get("classifications")
        if not isinstance(recorded, list) or not recorded:
            recorded = [str(row.get("classification"))]
        phase[when] = [str(item) for item in recorded]
        if row["role"] == "worker":
            workers[(nodeid, retry_index)] = str(row["worker_id"])
        else:
            workers.setdefault((nodeid, retry_index), str(row["worker_id"]))
    terminals: list[dict[str, Any]] = []
    missing: list[str] = []
    gap_reasons: list[str] = []
    for nodeid, copies in Counter(selected).items():
        attempts = by_node.get(nodeid) or {}
        retry_index = max(attempts) if attempts else 0
        phase_lists = attempts.get(retry_index, {})
        if _mixed_copies_conflict(phase_lists, copies):
            gap_reasons.append("conflicting_outcome")
            continue
        worker_id = workers.get((nodeid, retry_index), "controller")
        if _phases_are_uniform(phase_lists):
            phases = {when: items[0] for when, items in phase_lists.items() if items}
            explained, classification = _explain_phases(phases)
            available = _phase_copies(outcomes, nodeid, retry_index, phases, explained)
            emitted = min(available, copies)
            if available < copies:
                missing.extend([nodeid] * (copies - available))
                if classification == "missing_teardown":
                    gap_reasons.append("missing_teardown")
            _append_terminals(
                terminals,
                nodeid=nodeid,
                copies=emitted,
                phases=phases,
                classification=classification,
                retry_index=retry_index,
                worker_id=worker_id,
                attempt_count=len(attempts),
            )
            continue
        if any(len(items) != copies for items in phase_lists.values()):
            instances = _ordered_instances(events, nodeid, retry_index)
            if len(instances) != copies:
                gap_reasons.append("conflicting_outcome")
                continue
            for phases in instances:
                explained, classification = _explain_phases(phases)
                if not explained:
                    missing.append(nodeid)
                    if classification == "missing_teardown":
                        gap_reasons.append("missing_teardown")
                    continue
                _append_terminals(
                    terminals,
                    nodeid=nodeid,
                    copies=1,
                    phases=phases,
                    classification=classification,
                    retry_index=retry_index,
                    worker_id=worker_id,
                    attempt_count=len(attempts),
                )
            continue
        for index in range(copies):
            phases = _bundle_at(phase_lists, index, copies)
            explained, classification = _explain_phases(phases)
            if not explained:
                missing.append(nodeid)
                if classification == "missing_teardown":
                    gap_reasons.append("missing_teardown")
                continue
            _append_terminals(
                terminals,
                nodeid=nodeid,
                copies=1,
                phases=phases,
                classification=classification,
                retry_index=retry_index,
                worker_id=worker_id,
                attempt_count=len(attempts),
            )
    terminals.sort(key=lambda item: (str(item["nodeid"]), str(item["classification"])))
    return terminals, missing, sorted(set(gap_reasons))


def _phases_are_uniform(phases: dict[str, list[str]]) -> bool:
    return all(len(set(items)) <= 1 for items in phases.values())


def _mixed_copies_conflict(phases: dict[str, list[str]], copies: int) -> bool:
    """Different results conflict only when they do not match selected copies."""
    mixed_lengths = [len(items) for items in phases.values() if len(set(items)) > 1]
    if any(length != copies for length in mixed_lengths):
        return True
    return len(set(mixed_lengths)) > 1


def _bundle_at(phases: dict[str, list[str]], index: int, copies: int) -> dict[str, str]:
    bundle: dict[str, str] = {}
    for when, items in phases.items():
        if not items:
            continue
        if len(set(items)) == 1 and len(items) >= copies:
            bundle[when] = items[0]
        elif index < len(items):
            bundle[when] = items[index]
    return bundle


def _ordered_instances(
    events: list[dict[str, Any]], nodeid: str, retry_index: int
) -> list[dict[str, str]]:
    """Rebuild each selected copy from event order.

    A later setup starts another copy. A phase that is absent on one copy
    stays absent instead of being copied from a shorter list.
    """
    rows: list[tuple[str, str, str, str]] = []
    for event in events:
        if event.get("event") != "outcome" or event.get("subtest") is True:
            continue
        if str(event.get("nodeid") or "") != nodeid:
            continue
        retry = event.get("retry_index", 0)
        if retry is None:
            retry = 0
        if not _is_non_negative_int(retry) or retry != retry_index:
            continue
        identity = _event_identity(event)
        rows.append(
            (
                str(identity.get("role") or ""),
                str(identity.get("worker_id") or ""),
                str(event.get("when") or ""),
                str(event.get("classification") or ""),
            )
        )
    workers = [row for row in rows if row[0] == "worker"]
    chosen = workers or rows
    by_worker: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for _role, worker, when, classification in chosen:
        by_worker[worker].append((when, classification))
    sequences = list(by_worker.values())
    if not sequences:
        return []
    sequence = (
        sequences[0]
        if all(item == sequences[0] for item in sequences[1:])
        else [item for seq in sequences for item in seq]
    )
    instances: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for when, classification in sequence:
        if current is None or when == "setup" or when in current:
            current = {}
            instances.append(current)
        current[when] = classification
    return instances


def _phase_copies(
    outcomes: dict[tuple[str, str, int], dict[str, Any]],
    nodeid: str,
    retry_index: int,
    phases: dict[str, str],
    explained: bool,
) -> int:
    if not explained or not phases:
        return 0
    return min(
        int(outcomes[(nodeid, when, retry_index)].get("count") or 0) for when in phases
    )


def _append_terminals(
    terminals: list[dict[str, Any]],
    *,
    nodeid: str,
    copies: int,
    phases: dict[str, str],
    classification: str,
    retry_index: int,
    worker_id: str,
    attempt_count: int,
) -> None:
    row = {
        "nodeid": nodeid,
        "classification": classification,
        "call_classification": phases.get("call"),
        "retry_index": retry_index,
        "worker_id": worker_id,
        "attempt_count": attempt_count,
    }
    terminals.extend(dict(row) for _copy in range(copies))


def _explain_phases(phases: dict[str, str]) -> tuple[bool, str]:
    call = phases.get("call")
    setup = phases.get("setup")
    teardown = phases.get("teardown")
    if call in _CALL_CLASSIFICATIONS:
        if teardown is None:
            return False, "missing_teardown"
        if teardown == "teardown_error":
            return True, "teardown_error"
        if teardown not in _TEARDOWN_SUCCESS:
            return False, "unexplained"
        return True, call
    if setup in _SETUP_TERMINAL and call is None:
        if teardown is None:
            return False, "missing_teardown"
        if teardown == "teardown_error":
            return True, "teardown_error"
        if teardown not in _TEARDOWN_SUCCESS:
            return False, "unexplained"
        return True, setup
    return False, "unexplained"


def _empty_session_state() -> dict[str, Any]:
    return {
        "selection": {},
        "exitstatus": None,
        "sha_error": None,
        "mismatch": False,
        "actual": None,
        "expected": None,
        "allow_no_tests": False,
    }


def _remember_mismatch(event: dict[str, Any], state: dict[str, Any]) -> None:
    state["mismatch"] = True
    actual = event.get("actual")
    expected = event.get("expected")
    if actual:
        state["actual"] = actual
    if expected:
        state["expected"] = expected


def _remember_start(
    event: dict[str, Any],
    identity: dict[str, Any],
    state: dict[str, Any],
) -> None:
    raw_selection = event.get("selection")
    if isinstance(raw_selection, dict):
        state["selection"] = raw_selection
    state["sha_error"] = event.get("sha_error")
    state["actual"] = identity.get("actual_checkout_sha")
    state["expected"] = identity.get("expected_checkout_sha")
    state["allow_no_tests"] = event.get("allow_no_tests") is True


def _apply_session_event(event: dict[str, Any], state: dict[str, Any]) -> None:
    identity = _event_identity(event)
    kind = event.get("event")
    if kind == "checkout_mismatch":
        _remember_mismatch(event, state)
    if identity.get("role") != "controller":
        return
    if kind == "session_start":
        _remember_start(event, identity, state)
        return
    if kind != "session_finish":
        return
    status = event.get("exitstatus")
    if isinstance(status, int):
        state["exitstatus"] = status


def _session_finish_reasons(events: list[dict[str, Any]]) -> list[str]:
    for event in events:
        if event.get("event") == "session_finish" and event.get("hook_error") is True:
            return ["session_finish_error"]
    return []


def _missing_controller_finish(events: list[dict[str, Any]]) -> list[str]:
    """Require a controller session_finish before a pass can be complete."""
    saw_controller = False
    for event in events:
        if _event_identity(event).get("role") != "controller":
            continue
        saw_controller = True
        if event.get("event") == "session_finish":
            return []
    if saw_controller:
        return ["missing_session_finish"]
    return []


def _malformed_session_finish(events: list[dict[str, Any]]) -> list[str]:
    """A controller finish proves completion only with a real integer status."""
    for event in events:
        if _event_identity(event).get("role") != "controller":
            continue
        if event.get("event") != "session_finish":
            continue
        if type(event.get("exitstatus")) is not int:
            return ["malformed_session_finish"]
    return []


def _pytest_exit_reasons(flags: dict[str, Any]) -> list[str]:
    status = flags.get("exitstatus")
    if type(status) is not int or status in (0, 1):
        return []
    if status == 5 and flags.get("allow_no_tests") is True:
        return []
    return ["pytest_abnormal_exit"]


def _unconfigure_reasons(events: list[dict[str, Any]]) -> list[str]:
    for event in events:
        if event.get("event") == "unconfigure_error":
            return ["unconfigure_error"]
    return []


def _session_flags(events: list[dict[str, Any]]) -> dict[str, Any]:
    state = _empty_session_state()
    for event in events:
        _apply_session_event(event, state)
    return {
        "selection": state["selection"],
        "exitstatus": state["exitstatus"],
        "allow_no_tests": state["allow_no_tests"],
        "sha_error": state["sha_error"],
        "mismatch": state["mismatch"],
        "actual_checkout_sha": state["actual"],
        "expected_checkout_sha": state["expected"],
    }


_DAMAGE_REASONS = frozenset(
    {
        "truncated_jsonl",
        "missing_terminal_event",
        "journal_io_error",
        "checkout_sha_unmeasured",
        "malformed_session_finish",
    }
)


def _receipt_damage_reasons(receipts: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    if any(item["truncated"] for item in receipts):
        reasons.append("truncated_jsonl")
    if any(not item["finalized"] for item in receipts):
        reasons.append("missing_terminal_event")
    if any(item.get("io_error") for item in receipts):
        reasons.append("journal_io_error")
    return reasons


def _sha_mismatch(flags: dict[str, Any]) -> bool:
    if flags["mismatch"]:
        return True
    expected = flags["expected_checkout_sha"]
    actual = flags["actual_checkout_sha"]
    return bool(expected and actual and expected != actual)


def _checkout_reasons(flags: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if _sha_mismatch(flags):
        reasons.append("checkout_sha_mismatch")
    expected = flags["expected_checkout_sha"]
    if expected and not flags["actual_checkout_sha"]:
        reasons.append("checkout_sha_unmeasured")
    return reasons


def _is_damaged(reasons: list[str]) -> bool:
    return any(reason in _DAMAGE_REASONS for reason in reasons)


def _early_stop(selection: dict[str, Any]) -> bool:
    if selection.get("exitfirst"):
        return True
    maxfail = selection.get("maxfail")
    return isinstance(maxfail, int) and maxfail > 0


def _missing_controller(
    selected: list[str] | None,
    reasons: list[str],
    damaged: bool,
    collection_errors: list[str],
) -> bool:
    if selected is not None:
        return False
    if "checkout_sha_mismatch" in reasons or damaged or collection_errors:
        return False
    return True


def _selection_gap_reasons(
    *,
    selected: list[str] | None,
    missing: list[str],
    selection: dict[str, Any],
    collection_errors: list[str],
    collection_conflict: bool,
    damaged: bool,
    reasons: list[str],
) -> list[str]:
    extra: list[str] = []
    collect_only = bool(selection.get("collect_only"))
    if collect_only:
        extra.append("collect_only")
    if collection_errors:
        extra.append("collection_error")
    if collection_conflict:
        extra.append("conflicting_collection")
    if missing and not collect_only:
        extra.append("unexplained_selected_tests")
        if _early_stop(selection):
            extra.append("early_stop")
    if _missing_controller(selected, reasons, damaged, collection_errors):
        extra.append("missing_controller_collection")
    return extra


def _verdict_status(reasons: list[str]) -> str:
    if (
        _is_damaged(reasons)
        or "conflicting_outcome" in reasons
        or "conflicting_collection" in reasons
        or "missing_controller_collection" in reasons
        or "missing_worker_receipt" in reasons
        or "malformed_outcome" in reasons
    ):
        return "unknown"
    if (
        "checkout_sha_mismatch" in reasons
        or "collect_only" in reasons
        or "collection_error" in reasons
        or "unexplained_selected_tests" in reasons
        or "missing_teardown" in reasons
        or "session_finish_error" in reasons
        or "missing_session_finish" in reasons
        or "pytest_abnormal_exit" in reasons
        or "unconfigure_error" in reasons
    ):
        return "incomplete"
    return "complete"


def _tests_passed(status: str, terminals: list[dict[str, Any]]) -> bool | None:
    if status != "complete":
        return None
    return all(
        item["classification"] not in _FAILURE_CLASSIFICATIONS for item in terminals
    )


def _event_identity(event: dict[str, Any]) -> dict[str, Any]:
    identity = event.get("identity")
    if isinstance(identity, dict):
        return identity
    return {}


def _receipt_intact(receipt: dict[str, Any]) -> bool:
    return not (
        receipt.get("truncated")
        or not receipt.get("finalized")
        or receipt.get("io_error")
    )


def _intact_controller_receipt(receipts: list[dict[str, Any]]) -> bool:
    for receipt in receipts:
        if not _receipt_intact(receipt):
            continue
        for event in receipt["events"]:
            if _event_identity(event).get("role") == "controller":
                return True
    return False


def _worker_ids(receipt: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for event in receipt["events"]:
        identity = _event_identity(event)
        worker = identity.get("worker_id")
        if identity.get("role") == "worker" and isinstance(worker, str) and worker:
            found.add(worker)
    return found


def _intact_worker_ids(receipts: list[dict[str, Any]]) -> set[str]:
    found: set[str] = set()
    for receipt in receipts:
        if _receipt_intact(receipt):
            found.update(_worker_ids(receipt))
    return found


def _outcome_origins(events: list[dict[str, Any]]) -> set[str]:
    origins: set[str] = set()
    for event in events:
        if event.get("event") != "outcome":
            continue
        origin = event.get("origin_worker")
        if isinstance(origin, str) and origin:
            origins.add(origin)
    return origins


def _missing_origin_workers(
    receipts: list[dict[str, Any]], events: list[dict[str, Any]]
) -> list[str]:
    return sorted(_outcome_origins(events) - _intact_worker_ids(receipts))


def reconcile_pass(receipts: list[dict[str, Any]], *, pass_name: str) -> dict[str, Any]:
    """Reconcile one runner pass. See module docstring for the status rules."""
    if not receipts:
        return _pass_verdict(
            pass_name=pass_name,
            status="unknown",
            reasons=["missing_receipt"],
            tests_passed=None,
        )
    reasons = _receipt_damage_reasons(receipts)
    events = [event for item in receipts for event in item["events"]]
    flags = _session_flags(events)
    reasons.extend(_checkout_reasons(flags))
    reasons.extend(_session_finish_reasons(events))
    reasons.extend(_missing_controller_finish(events))
    reasons.extend(_malformed_session_finish(events))
    reasons.extend(_pytest_exit_reasons(flags))
    reasons.extend(_unconfigure_reasons(events))
    selected, deselected, collection_errors, collection_conflict = _selected_nodeids(
        events,
        allow_worker_collection=_intact_controller_receipt(receipts),
    )
    outcomes, outcome_reasons = _dedup_outcomes(events)
    reasons.extend(outcome_reasons)
    if _missing_origin_workers(receipts, events):
        reasons.append("missing_worker_receipt")
    terminals: list[dict[str, Any]] = []
    missing: list[str] = []
    if selected is not None:
        terminals, missing, gap_reasons = _terminal_states(selected, outcomes, events)
        reasons.extend(gap_reasons)
    reasons.extend(
        _selection_gap_reasons(
            selected=selected,
            missing=missing,
            selection=flags["selection"],
            collection_errors=collection_errors,
            collection_conflict=collection_conflict,
            damaged=_is_damaged(reasons),
            reasons=reasons,
        )
    )
    status = _verdict_status(reasons)
    return _pass_verdict(
        pass_name=pass_name,
        status=status,
        reasons=sorted(set(reasons)),
        tests_passed=_tests_passed(status, terminals),
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
        identity = _event_identity(event)
        value = identity.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def _first_identity_value(events: list[dict[str, Any]], field: str) -> Any:
    for event in events:
        identity = _event_identity(event)
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
    if not authoritative and present == {"unspecified"}:
        authoritative.append("unspecified")
    return authoritative, superseded


def _invocation_of(receipt: dict[str, Any]) -> str:
    for event in receipt["events"]:
        identity = _event_identity(event)
        value = identity.get("invocation_id")
        if isinstance(value, str) and value:
            return value
    parsed = _filename_identity(str(receipt.get("path") or ""))
    if parsed is not None:
        return parsed[1]
    return ""


def _receipt_is_damaged(receipt: dict[str, Any]) -> bool:
    return bool(
        receipt["truncated"] or not receipt["finalized"] or receipt.get("io_error")
    )


def _unattributed_damage(receipt: dict[str, Any]) -> bool:
    if not _receipt_is_damaged(receipt):
        return False
    if _pass_of(receipt) not in _AUTHORITATIVE_PASS_NAMES:
        return True
    return not _invocation_of(receipt)


def _has_unattributed_damage(receipts: list[dict[str, Any]]) -> bool:
    return any(_unattributed_damage(item) for item in receipts)


def _pinned_invocations(
    receipts: list[dict[str, Any]],
    expected_invocations: dict[str, str] | None,
) -> dict[str, str]:
    """Return the invocation map a later verify must reuse."""
    expected = {
        name: invocation
        for name, invocation in (expected_invocations or {}).items()
        if isinstance(name, str) and isinstance(invocation, str) and invocation
    }
    if expected:
        return expected
    pinned: dict[str, str] = {}
    for receipt in receipts:
        name = _pass_of(receipt)
        invocation = _invocation_of(receipt)
        if name and invocation and name not in pinned:
            pinned[name] = invocation
    return pinned


def _receipts_for_reconciliation(
    receipts: list[dict[str, Any]],
    expected_invocations: dict[str, str] | None,
) -> list[dict[str, Any]]:
    expected = {
        name: invocation
        for name, invocation in (expected_invocations or {}).items()
        if invocation
    }
    if not expected:
        return _latest_invocation_receipts(receipts)
    return [
        receipt
        for receipt in receipts
        if expected.get(_pass_of(receipt)) == _invocation_of(receipt)
    ]


def _session_started_at(receipt: dict[str, Any]) -> str:
    for event in receipt["events"]:
        if event.get("event") != "session_start":
            continue
        stamp = event.get("timestamp")
        if isinstance(stamp, str):
            return stamp
        return ""
    return ""


def _invocation_rank(
    group: list[dict[str, Any]], invocation_id: str
) -> tuple[str, str]:
    stamp = max((_session_started_at(item) for item in group), default="")
    return stamp, invocation_id


def _latest_invocation_receipts(
    receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep every worker of the newest invocation for each pass."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        grouped[(_pass_of(receipt), _invocation_of(receipt))].append(receipt)
    chosen: dict[str, tuple[str, str]] = {}
    for (pass_name, invocation_id), group in grouped.items():
        rank = _invocation_rank(group, invocation_id)
        current = chosen.get(pass_name)
        if current is None or rank > current:
            chosen[pass_name] = rank
    selected = {
        pass_name: invocation_id
        for pass_name, (_stamp, invocation_id) in chosen.items()
    }
    return [
        receipt
        for receipt in receipts
        if _invocation_of(receipt) == selected[_pass_of(receipt)]
    ]


def reconcile_directory(
    journal_dir: Path,
    *,
    executed_passes: list[str],
    expected_invocations: dict[str, str] | None = None,
) -> dict[str, Any]:
    loaded = _group_receipts(journal_dir)
    unattributed = _has_unattributed_damage(loaded)
    receipts = _receipts_for_reconciliation(loaded, expected_invocations)
    by_pass: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        by_pass[_pass_of(receipt)].append(receipt)
    names = list(dict.fromkeys([*executed_passes, *sorted(by_pass)]))
    passes = {
        name: reconcile_pass(by_pass.get(name, []), pass_name=name) for name in names
    }
    runner_passes = {"parallel", "fallback", "serial"}
    authoritative_input = [name for name in executed_passes if name in runner_passes]
    if not authoritative_input:
        authoritative_input = [name for name in names if name in runner_passes]
    if not authoritative_input and set(names) == {"unspecified"}:
        authoritative_input = ["unspecified"]
    authoritative, superseded = authoritative_pass_names(authoritative_input)
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
    if unattributed:
        status = "unknown"
        tests_passed = None
        reasons = sorted({*reasons, "unattributed_receipt_damage"})
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reasons": reasons,
        "tests_passed": tests_passed,
        "authoritative_passes": authoritative,
        "superseded_passes": superseded,
        "executed_passes": executed_passes,
        "expected_invocations": _pinned_invocations(receipts, expected_invocations),
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


def _read_stored_verdict(path: Path) -> dict[str, Any] | None:
    """Return the stored verdict object, or None when it cannot be trusted."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        stored = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(stored, dict):
        return None
    return stored


def _stored_expected_invocations(stored: dict[str, Any]) -> dict[str, str] | None:
    """Return pinned invocations.

    An absent field returns an empty map so verification keeps the
    latest-invocation ranking. ``None`` means the field is malformed.
    """
    if "expected_invocations" not in stored:
        return {}
    raw = stored["expected_invocations"]
    if not isinstance(raw, dict):
        return None
    parsed: dict[str, str] = {}
    for name, invocation in raw.items():
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(invocation, str)
            or not invocation
        ):
            return None
        parsed[name] = invocation
    return parsed


def verify_directory(
    journal_dir: Path, *, executed_passes: list[str] | None = None
) -> int:
    verdict_path = journal_dir / "journal-verdict.json"
    executed = executed_passes
    invocations: dict[str, str] | None = None
    if executed is None and verdict_path.exists() and not verdict_path.is_file():
        sys.stderr.write(
            "EventJournal completeness unknown: stored_verdict_unreadable\n"
        )
        return JOURNAL_COMPLETENESS_EXIT
    if executed is None and verdict_path.is_file():
        stored = _read_stored_verdict(verdict_path)
        if stored is None:
            sys.stderr.write(
                "EventJournal completeness unknown: stored_verdict_unreadable\n"
            )
            return JOURNAL_COMPLETENESS_EXIT
        raw_passes = stored.get("executed_passes")
        executed = (
            [str(item) for item in raw_passes] if isinstance(raw_passes, list) else []
        )
        invocations = _stored_expected_invocations(stored)
        if invocations is None:
            sys.stderr.write(
                "EventJournal completeness unknown: stored_verdict_unreadable\n"
            )
            return JOURNAL_COMPLETENESS_EXIT
    verdict = reconcile_directory(
        journal_dir,
        executed_passes=executed or [],
        expected_invocations=invocations,
    )
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
