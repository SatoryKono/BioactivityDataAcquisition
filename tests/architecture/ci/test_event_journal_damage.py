"""Schema, marker, xdist, and outcome regressions for the pytest journal."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from scripts.engineering.ci.pytest_event_journal import (
    reconcile_directory,
    reconcile_pass,
    verify_directory,
)

_SPEC = importlib.util.spec_from_file_location(
    "event_journal_helpers",
    Path(__file__).with_name("test_event_journal.py"),
)
assert _SPEC is not None and _SPEC.loader is not None
_HELPERS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_HELPERS)
_ROOT = _HELPERS._ROOT
_collected = _HELPERS._collected
_finalized = _HELPERS._finalized
_identity = _HELPERS._identity
_live_verdict = _HELPERS._live_verdict
_load = _HELPERS._load
_named_receipt = _HELPERS._named_receipt
_outcome = _HELPERS._outcome
_phases = _HELPERS._phases
_run_journal = _HELPERS._run_journal
_start = _HELPERS._start
_write_receipt = _HELPERS._write_receipt

pytestmark = pytest.mark.architecture


def test_same_classification_from_two_workers_is_not_a_conflict(
    tmp_path: Path,
) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker_a = _identity(role="worker", worker_id="gw0")
    worker_b = _identity(role="worker", worker_id="gw1")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(controller),
            _start(worker_a),
            _start(worker_b),
            _collected(worker_a, [nodeid]),
            _collected(worker_b, [nodeid]),
            _collected(controller, [nodeid]),
            *_phases(worker_a, nodeid, "passed"),
            *_phases(worker_b, nodeid, "passed"),
            {"event": "session_finish", "identity": controller, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "conflicting_outcome" not in verdict["reasons"]
    assert verdict["status"] == "complete"
    assert verdict["selected_count"] == 1
    assert verdict["tests_passed"] is True


def test_duplicate_copies_on_different_workers_stay_complete(tmp_path: Path) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker_a = _identity(role="worker", worker_id="gw0")
    worker_b = _identity(role="worker", worker_id="gw1")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(controller),
            _start(worker_a),
            _start(worker_b),
            _collected(worker_a, [nodeid, nodeid]),
            _collected(worker_b, [nodeid, nodeid]),
            _collected(controller, [nodeid, nodeid]),
            *_phases(worker_a, nodeid, "passed"),
            *_phases(worker_b, nodeid, "passed"),
            {"event": "session_finish", "identity": controller, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "conflicting_outcome" not in verdict["reasons"]
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["tests_passed"] is True
    assert [item["classification"] for item in verdict["terminals"]] == [
        "passed",
        "passed",
    ]


def test_unsupported_schema_version_is_unknown(tmp_path: Path) -> None:
    name = _named_receipt("parallel", "a" * 32, "controller", "controller", "b" * 32)
    event = {
        "event": "journal_finalized",
        "schema_version": 2,
        "identity": _identity(role="controller", worker_id="controller"),
        "prior_line_count": 0,
        "io_error": None,
    }
    (tmp_path / name).write_text(json.dumps(event) + "\n", encoding="utf-8")
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert verdict["status"] == "unknown"


def test_invalid_utf8_close_marker_is_unknown(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    name = _named_receipt("parallel", "c" * 32, "controller", "controller", "d" * 32)
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            *_phases(identity, nodeid, "passed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events, name=name)
    (tmp_path / name).with_name(name + ".close_error").write_bytes(b"\xff\n")
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert verdict["status"] == "unknown"


_ABSENT_SCHEMA = "absent"


def _passing_named_receipt(directory: Path, name: str) -> Path:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            *_phases(identity, nodeid, "passed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(directory, events, name=name)
    return directory / name


def _rewrite_schema(path: Path, version: Any) -> None:
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if version == _ABSENT_SCHEMA:
            event.pop("schema_version", None)
        else:
            event["schema_version"] = version
        lines.append(json.dumps(event, sort_keys=True, ensure_ascii=True))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _assert_directory_is_not_verified(directory: Path) -> None:
    from scripts.engineering.ci.pytest_event_journal import (
        JOURNAL_COMPLETENESS_EXIT,
        main,
        verify_directory,
    )

    verdict = reconcile_directory(directory, executed_passes=["parallel"])
    assert verdict["status"] == "unknown"
    assert verdict["tests_passed"] is not True
    assert (
        verify_directory(directory, executed_passes=["parallel"])
        == JOURNAL_COMPLETENESS_EXIT
    )
    assert (
        main(["--verify", str(directory), "--executed-pass", "parallel"])
        == JOURNAL_COMPLETENESS_EXIT
    )


@pytest.mark.parametrize("version", [_ABSENT_SCHEMA, 2, "1", 1.0, True])
def test_bad_schema_version_fails_verification(tmp_path: Path, version: Any) -> None:
    name = _named_receipt("parallel", "e" * 32, "controller", "controller", "f" * 32)
    path = _passing_named_receipt(tmp_path, name)
    _rewrite_schema(path, version)
    before = path.read_bytes()
    _assert_directory_is_not_verified(tmp_path)
    assert path.read_bytes() == before


def test_supported_schema_version_still_verifies(tmp_path: Path) -> None:
    from scripts.engineering.ci.pytest_event_journal import verify_directory

    name = _named_receipt("parallel", "1" * 32, "controller", "controller", "2" * 32)
    path = _passing_named_receipt(tmp_path, name)
    before = path.read_bytes()
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is True
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 0
    assert path.read_bytes() == before


def _marker_case(tmp_path: Path, payload: bytes) -> tuple[Path, str]:
    name = _named_receipt("parallel", "9" * 32, "controller", "controller", "8" * 32)
    receipt = _passing_named_receipt(tmp_path, name)
    marker = receipt.with_name(name + ".close_error")
    marker.write_bytes(payload)
    return receipt, name


@pytest.mark.parametrize(
    ("payload", "io_error"),
    [
        (b"\xff\n", "close_marker_invalid_utf8"),
        (b"", "close_marker_present"),
        (b"\n", "close_marker_present"),
    ],
)
def test_close_marker_damage_fails_verification(
    tmp_path: Path, payload: bytes, io_error: str
) -> None:
    receipt, _name = _marker_case(tmp_path, payload)
    before = receipt.read_bytes()
    _assert_directory_is_not_verified(tmp_path)
    loaded = _load(tmp_path)
    assert loaded[0]["io_error"] == io_error
    assert receipt.read_bytes() == before


def test_close_marker_read_error_fails_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt, _name = _marker_case(tmp_path, b"pending\n")
    before = receipt.read_bytes()
    original = Path.read_bytes

    def guarded(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self.name.endswith(".close_error"):
            raise OSError(13, "denied")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    _assert_directory_is_not_verified(tmp_path)
    loaded = _load(tmp_path)
    assert loaded[0]["io_error"] == "close_marker_unreadable"
    assert receipt.read_bytes() == before


def test_xdist_workers_share_the_controller_redaction_key(tmp_path: Path) -> None:
    journal = tmp_path / "journal"
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "import pytest\n\n"
        "@pytest.mark.parametrize('password', ['swordfish'])\n"
        "def test_reads(password: str) -> None:\n"
        "    assert password == 'swordfish'\n",
        encoding="utf-8",
    )
    child_env = os.environ.copy()
    child_env.pop("EXPECTED_CHECKOUT_SHA", None)
    child_env.pop("BIOETL_JOURNAL_REDACTION_KEY", None)
    child_env["BIOETL_JOURNAL_INVOCATION_ID"] = "inv-xdist"
    child_env["BIOETL_JOURNAL_PASS"] = "parallel"
    child_env["BIOETL_JOURNAL_JOB"] = "serial-coverage"
    child_env["PYTHONPATH"] = str(_ROOT)
    child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    child_env["PASSWORD"] = "swordfish"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "--noconftest",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
            "-p",
            "xdist",
            "-n",
            "2",
            "-p",
            "scripts.engineering.ci.pytest_event_journal",
            f"--event-journal-dir={journal}",
        ],
        cwd=_ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    verdict = reconcile_directory(journal, executed_passes=["parallel"])
    assert verdict["status"] == "complete", verdict
    assert verdict["tests_passed"] is True
    blob = "\n".join(
        path.read_text(encoding="utf-8") for path in journal.glob("*.jsonl")
    )
    assert "swordfish" not in blob
    assert "BIOETL_JOURNAL_REDACTION_KEY" not in blob


def test_non_strict_xpass_is_not_a_failure(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_xpass"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            *_phases(identity, nodeid, "xpass"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is True


def test_remaining_duplicate_is_kept_when_one_copy_is_deselected(
    tmp_path: Path,
) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            {"event": "deselected", "identity": identity, "nodeids": [nodeid]},
            *_phases(identity, nodeid, "failed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 1},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["selected_count"] == 1
    assert verdict["deselected_count"] == 1
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is False


def test_worker_deselection_is_counted_once(tmp_path: Path) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker_a = _identity(role="worker", worker_id="gw0")
    worker_b = _identity(role="worker", worker_id="gw1")
    kept = "test_sample.py::test_kept"
    dropped = "test_sample.py::test_other"
    events = _finalized(
        [
            _start(controller),
            _start(worker_a),
            _start(worker_b),
            _collected(worker_a, [kept]),
            _collected(worker_b, [kept]),
            _collected(controller, [kept]),
            {"event": "deselected", "identity": worker_a, "nodeids": [dropped]},
            {"event": "deselected", "identity": worker_b, "nodeids": [dropped]},
            *_phases(controller, kept, "passed"),
            {"event": "session_finish", "identity": controller, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["selected_count"] == 1
    assert verdict["deselected_count"] == 1
    assert verdict["status"] == "complete"


def test_unknown_classification_is_not_complete(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            _outcome(identity, nodeid, "setup", "passed"),
            _outcome(identity, nodeid, "call", "passed"),
            _outcome(identity, nodeid, "teardown", "CORRUPTED"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert verdict["tests_passed"] is not True


def test_internal_pytest_exit_is_incomplete(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            *_phases(identity, nodeid, "passed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 3},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "incomplete"
    assert "pytest_abnormal_exit" in verdict["reasons"]
    assert verdict["tests_passed"] is None


def test_subtest_failure_is_not_a_conflicting_outcome(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::TestCase::test_parent"
    failed = _outcome(identity, nodeid, "call", "failed")
    failed["subtest"] = True
    passed = _outcome(identity, nodeid, "call", "passed")
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            _outcome(identity, nodeid, "setup", "passed"),
            passed,
            failed,
            _outcome(identity, nodeid, "teardown", "passed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 1},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "conflicting_outcome" not in verdict["reasons"]
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is False


def test_journal_filename_cannot_escape_the_directory(tmp_path: Path) -> None:
    result = _run_journal(
        tmp_path,
        "def test_ok():\n    pass\n",
        [],
        {
            "BIOETL_JOURNAL_PASS": "../../../escape",
            "BIOETL_JOURNAL_INVOCATION_ID": "../not-hex",
            "PYTEST_XDIST_WORKER": "..\\gw",
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr
    journal = tmp_path / "journal"
    receipts = list(journal.glob("*.jsonl"))
    assert receipts
    assert all(path.parent == journal for path in receipts)
    assert not (tmp_path.parent / "escape").exists()


def test_restored_collection_item_stays_in_the_verdict(tmp_path: Path) -> None:
    plugin = tmp_path / "restore_item.py"
    plugin.write_text(
        "import pytest\n\n"
        "@pytest.hookimpl(hookwrapper=True, tryfirst=True)\n"
        "def pytest_collection_modifyitems(session, config, items):\n"
        "    saved = list(items)\n"
        "    items.clear()\n"
        "    yield\n"
        "    items[:] = saved\n",
        encoding="utf-8",
    )
    result = _run_journal(
        tmp_path / "run",
        "def test_fails():\n    assert False\n",
        ["-p", "restore_item"],
        {"PYTHONPATH": os.pathsep.join((str(tmp_path), str(_ROOT)))},
    )
    assert result.returncode != 0
    verdict = _live_verdict(tmp_path / "run")
    assert verdict["passes"]["parallel"]["selected_count"] == 1
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is False


def test_duplicate_parents_with_subtests_keep_their_count(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::TestCase::test_parent"
    subtest = _outcome(identity, nodeid, "call", "passed")
    subtest["subtest"] = True
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid, nodeid]),
            *_phases(identity, nodeid, "passed"),
            *_phases(identity, nodeid, "passed"),
            subtest,
            dict(subtest),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "unexplained_selected_tests" not in verdict["reasons"]
    assert "conflicting_outcome" not in verdict["reasons"]
    assert verdict["status"] == "complete"
    assert verdict["selected_count"] == 2
    assert verdict["tests_passed"] is True


def test_allowed_empty_collection_accepts_exit_five(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    start = _start(identity)
    start["allow_no_tests"] = True
    events = _finalized(
        [
            start,
            _collected(identity, []),
            {"event": "session_finish", "identity": identity, "exitstatus": 5},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "pytest_abnormal_exit" not in verdict["reasons"]
    assert verdict["status"] == "complete"

    blocked = _finalized(
        [
            _start(identity),
            _collected(identity, []),
            {"event": "session_finish", "identity": identity, "exitstatus": 5},
        ]
    )
    _write_receipt(tmp_path / "blocked", blocked)
    blocked_verdict = reconcile_pass(_load(tmp_path / "blocked"), pass_name="parallel")
    assert blocked_verdict["status"] == "incomplete"
    assert "pytest_abnormal_exit" in blocked_verdict["reasons"]


def test_unconfigure_error_is_not_a_complete_pass(tmp_path: Path) -> None:
    plugin = tmp_path / "unconfigure_boom.py"
    plugin.write_text(
        "def pytest_unconfigure(config):\n    raise RuntimeError('unconfigure boom')\n",
        encoding="utf-8",
    )
    result = _run_journal(
        tmp_path / "run",
        "def test_ok():\n    pass\n",
        ["-p", "unconfigure_boom"],
        {"PYTHONPATH": os.pathsep.join((str(tmp_path), str(_ROOT)))},
    )
    assert result.returncode != 0
    verdict = _live_verdict(tmp_path / "run")
    assert verdict["status"] != "complete"
    assert verdict["tests_passed"] is not True


def test_missing_controller_session_finish_is_incomplete(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            *_phases(identity, nodeid, "passed"),
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "incomplete"
    assert "missing_session_finish" in verdict["reasons"]
    assert verdict["tests_passed"] is None
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 4


def test_verify_reuses_the_invocation_stored_in_the_verdict(tmp_path: Path) -> None:
    from scripts.engineering.ci import run_pytest_resilient

    old = "a" * 32
    current = "b" * 32
    identity = _identity(role="controller", worker_id="controller", invocation_id=old)
    nodeid = "test_sample.py::test_a"
    start = _start(identity)
    start["timestamp"] = "2026-10-17T00:00:00+00:00"
    _write_receipt(
        tmp_path,
        _finalized(
            [
                start,
                _collected(identity, [nodeid]),
                *_phases(identity, nodeid, "passed"),
                {"event": "session_finish", "identity": identity, "exitstatus": 0},
            ]
        ),
        name=_named_receipt("parallel", old, "controller", "controller", "c" * 32),
    )
    damaged = _named_receipt("parallel", current, "controller", "controller", "d" * 32)
    (tmp_path / damaged).write_bytes(b'{"event": "trunc')
    reports = tmp_path / "reports"
    reports.mkdir()
    assert (
        run_pytest_resilient._finish_run(
            reports_dir=reports,
            summary_lines=[],
            journal_dir=tmp_path,
            executed_passes=["parallel"],
            test_rc=0,
            expected_invocations={"parallel": current},
        )
        == 4
    )
    stored = json.loads((tmp_path / "journal-verdict.json").read_text(encoding="utf-8"))
    assert stored["expected_invocations"] == {"parallel": current}
    assert verify_directory(tmp_path) == 4
    latest = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert latest["status"] == "unknown"
    assert "ambiguous_damaged_invocation" in latest["reasons"]
    assert latest["passes"]["parallel"]["invocation_id"] == old


@pytest.mark.parametrize("status", ["absent", "0", 1.0, True])
def test_session_finish_without_integer_exitstatus_is_unknown(
    tmp_path: Path, status: object
) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    finish: dict[str, Any] = {"event": "session_finish", "identity": identity}
    if status != "absent":
        finish["exitstatus"] = status
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            *_phases(identity, nodeid, "passed"),
            finish,
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert verdict["tests_passed"] is not True
    if status == "absent":
        assert "malformed_session_finish" in verdict["reasons"]
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 4


def test_duplicate_nodeids_keep_different_outcomes(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid, nodeid]),
            *_phases(identity, nodeid, "passed"),
            *_phases(identity, nodeid, "failed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 1},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "conflicting_outcome" not in verdict["reasons"]
    assert verdict["status"] == "complete"
    assert verdict["selected_count"] == 2
    assert verdict["tests_passed"] is False
    assert sorted(item["classification"] for item in verdict["terminals"]) == [
        "failed",
        "passed",
    ]
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 0


def test_intermediate_rerun_keeps_the_final_attempt(tmp_path: Path) -> None:
    from scripts.engineering.ci.pytest_event_journal import (
        _classification_allowed,
        _classify_report,
    )

    class _Report:
        when = "call"
        failed = False
        skipped = False
        passed = False
        outcome = "rerun"

    assert _classify_report(_Report(), None) == "rerun"
    assert _classification_allowed({"when": "call", "classification": "rerun"}) is True
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"

    def attempt(when: str, classification: str, retry_index: int) -> dict[str, Any]:
        event = _outcome(identity, nodeid, when, classification)
        event["retry_index"] = retry_index
        return event

    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            attempt("setup", "passed", 0),
            attempt("call", "rerun", 0),
            attempt("teardown", "passed", 0),
            attempt("setup", "passed", 1),
            attempt("call", "passed", 1),
            attempt("teardown", "passed", 1),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "conflicting_outcome" not in verdict["reasons"]
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["tests_passed"] is True
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 0


def test_setup_error_copy_does_not_inherit_the_other_call(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid, nodeid]),
            *_phases(identity, nodeid, "setup_error"),
            *_phases(identity, nodeid, "passed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 1},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "conflicting_outcome" not in verdict["reasons"]
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["tests_passed"] is False
    assert sorted(item["classification"] for item in verdict["terminals"]) == [
        "passed",
        "setup_error",
    ]
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 0


def test_standalone_unspecified_pass_is_authoritative(tmp_path: Path) -> None:
    result = _run_journal(
        tmp_path,
        "def test_ok():\n    pass\n",
        [],
        {"BIOETL_JOURNAL_PASS": ""},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    journal = tmp_path / "journal"
    verdict = reconcile_directory(journal, executed_passes=[])
    assert verdict["authoritative_passes"] == ["unspecified"]
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is True
    assert verify_directory(journal) == 0


@pytest.mark.parametrize("final_retries", [(0, 1), (1, 0), (1, 2), (2, 1)])
@pytest.mark.parametrize("damaged", [False, True])
def test_duplicate_occurrences_keep_their_own_final_retry(
    tmp_path: Path, final_retries: tuple[int, int], damaged: bool
) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_duplicate"
    events = [_start(identity), _collected(identity, [nodeid, nodeid])]
    for occurrence, final_retry in enumerate(final_retries):
        for retry in range(final_retry + 1):
            classification = "rerun" if retry < final_retry else "passed"
            phases = _phases(identity, nodeid, classification, retry_index=retry)
            if damaged and occurrence == 0 and retry == final_retry:
                phases = phases[:-1]
            events.extend(phases)
    events.append({"event": "session_finish", "identity": identity, "exitstatus": 0})
    _write_receipt(tmp_path, _finalized(events))
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == ("incomplete" if damaged else "complete")
    assert verdict["tests_passed"] is (None if damaged else True)
    if not damaged:
        assert sorted(row["retry_index"] for row in verdict["terminals"]) == sorted(
            final_retries
        )
        assert sorted(row["attempt_count"] for row in verdict["terminals"]) == sorted(
            retry + 1 for retry in final_retries
        )
    else:
        assert "missing_teardown" in verdict["reasons"]


@pytest.mark.parametrize("damage", ["unfinished_rerun", "retry_gap", "extra_copy"])
def test_duplicate_retry_damage_cannot_claim_completeness(
    tmp_path: Path, damage: str
) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_duplicate"
    events = [
        _start(identity),
        _collected(identity, [nodeid, nodeid]),
        *_phases(identity, nodeid, "passed"),
        *_phases(identity, nodeid, "rerun"),
    ]
    retry = 2 if damage == "retry_gap" else 1
    final = "rerun" if damage == "unfinished_rerun" else "passed"
    events.extend(_phases(identity, nodeid, final, retry_index=retry))
    if damage == "extra_copy":
        events.extend(_phases(identity, nodeid, "passed"))
    events.append({"event": "session_finish", "identity": identity, "exitstatus": 0})
    _write_receipt(tmp_path, _finalized(events))
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] != "complete"
    assert verdict["tests_passed"] is None


def test_worker_duplicate_retries_preserve_failed_occurrences(tmp_path: Path) -> None:
    controller = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_duplicate"
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(controller),
                _collected(controller, [nodeid, nodeid]),
                {"event": "session_finish", "identity": controller, "exitstatus": 1},
            ]
        ),
        name="receipt_controller.jsonl",
    )
    for index, retry in enumerate((0, 1)):
        worker = _identity(role="worker", worker_id=f"gw{index}")
        events = [_start(worker), _collected(worker, [nodeid, nodeid])]
        if retry:
            events.extend(_phases(worker, nodeid, "rerun"))
        phases = _phases(
            worker, nodeid, "failed" if index == 0 else "passed", retry_index=retry
        )
        events.extend(phases)
        events.append({"event": "session_finish", "identity": worker, "exitstatus": 1})
        _write_receipt(
            tmp_path, _finalized(events), name=f"receipt_worker{index}.jsonl"
        )
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["tests_passed"] is False
    assert {(row["worker_id"], row["retry_index"]) for row in verdict["terminals"]} == {
        ("gw0", 0),
        ("gw1", 1),
    }


@pytest.mark.parametrize("fails", [False, True])
def test_runner_preserves_both_receipt_producers(tmp_path: Path, fails: bool) -> None:
    test_file = tmp_path / "test_both.py"
    test_file.write_text(
        "import os\ndef test_both():\n"
        "    assert os.environ['BIOETL_MERGE_ENV'] == 'kept'\n"
        f"    assert {not fails!r}\n",
        encoding="utf-8",
    )
    journal = tmp_path / "journal"
    receipts = tmp_path / "receipts"
    env = {
        **os.environ,
        "BIOETL_MERGE_ENV": "kept",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    env.pop("EXPECTED_CHECKOUT_SHA", None)
    result = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/engineering/ci/run_pytest_resilient.py"),
            "--target",
            str(test_file),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--journal-dir",
            str(journal),
            "--receipt-dir",
            str(receipts),
            "--receipt-run-id",
            "combined",
            "--receipt-attempt",
            "1",
            "--parallel-marker",
            "not slow",
            "--parallel-addopts",
            "-q --noconftest -o addopts= -p no:cacheprovider",
            "--parallel-timeout-seconds",
            "0",
            "--no-fallback",
            "--skip-serial-pass",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=45,
    )
    assert result.returncode == int(fails), result.stdout + result.stderr
    verdict = json.loads((journal / "journal-verdict.json").read_text(encoding="utf-8"))
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is (not fails)
    payload = json.loads(
        (receipts / "combined/1/parallel/master/receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["completeness"] == "complete"
    assert payload["exit_code"] == int(fails)


def test_duplicate_copies_finish_on_different_retries(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"

    def attempt(when: str, classification: str, retry_index: int) -> dict[str, Any]:
        event = _outcome(identity, nodeid, when, classification)
        event["retry_index"] = retry_index
        return event

    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid, nodeid]),
            *_phases(identity, nodeid, "passed", retry_index=0),
            attempt("setup", "passed", 0),
            attempt("call", "rerun", 0),
            attempt("teardown", "passed", 0),
            *_phases(identity, nodeid, "passed", retry_index=1),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "unexplained_selected_tests" not in verdict["reasons"]
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["selected_count"] == 2
    assert verdict["tests_passed"] is True
    assert sorted(item["retry_index"] for item in verdict["terminals"]) == [0, 1]
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 0


def _complete_review_receipt(directory: Path) -> Path:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    _write_receipt(
        directory,
        _finalized(
            [
                _start(identity),
                _collected(identity, [nodeid]),
                *_phases(identity, nodeid, "passed"),
                {"event": "session_finish", "identity": identity, "exitstatus": 0},
            ]
        ),
    )
    return directory / "receipt_test.jsonl"


@pytest.mark.parametrize(
    "damage",
    [
        "missing_start",
        "duplicate_start",
        "early_finish",
        "identity",
        "missing_identity",
        "float_count",
        "bool_count",
        "invalid_timestamp",
        "future_timestamp",
    ],
)
def test_review_receipt_corruption_never_proves_success(
    tmp_path: Path, damage: str
) -> None:
    path = _complete_review_receipt(tmp_path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if damage == "missing_start":
        rows.pop(0)
    elif damage == "duplicate_start":
        rows.insert(1, dict(rows[0]))
    elif damage == "early_finish":
        rows.insert(1, rows.pop(-2))
    elif damage == "identity":
        rows[3]["identity"]["invocation_id"] = "different-invocation"
    elif damage == "missing_identity":
        rows[3].pop("identity")
    elif damage == "invalid_timestamp":
        rows[0]["timestamp"] = "zzz"
    elif damage == "future_timestamp":
        rows[0]["timestamp"] = "9999-01-01T00:00:00+00:00"
    rows[-1]["prior_line_count"] = len(rows) - 1
    if damage == "float_count":
        rows[-1]["prior_line_count"] = float(len(rows) - 1)
    elif damage == "bool_count":
        rows[-1]["prior_line_count"] = True
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 4


def test_review_valid_receipt_is_complete(tmp_path: Path) -> None:
    _complete_review_receipt(tmp_path)
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 0


def test_review_forwarded_worker_disagreement_is_unknown(tmp_path: Path) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker = _identity(role="worker", worker_id="gw0")
    nodeid = "test_sample.py::test_a"
    forwarded = _phases(controller, nodeid, "failed")
    for row in forwarded:
        row["origin_worker"] = "gw0"
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(controller),
                _collected(controller, [nodeid]),
                *_phases(worker, nodeid, "passed"),
                *forwarded,
                {"event": "session_finish", "identity": controller, "exitstatus": 1},
            ]
        ),
    )
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert "conflicting_outcome" in verdict["reasons"]
    assert verdict["tests_passed"] is not True


def test_review_duplicate_subtests_keep_parent_outcomes(tmp_path: Path) -> None:
    result = _run_journal(
        tmp_path,
        """import unittest
count = 0
class TestCopies(unittest.TestCase):
    def test_copy(self):
        global count
        count += 1
        with self.subTest(value=1):
            self.assertTrue(True)
        self.assertEqual(count, 2)
""",
        [str(tmp_path / "test_sample.py"), "--keep-duplicates"],
    )
    assert result.returncode == 1
    verdict = _live_verdict(tmp_path)
    assert verdict["status"] == "complete", verdict
    assert verdict["tests_passed"] is False


def test_review_teardown_xfail_is_complete(tmp_path: Path) -> None:
    result = _run_journal(
        tmp_path,
        """import pytest
@pytest.fixture
def cleanup():
    yield
    pytest.xfail('expected teardown')
def test_ok(cleanup):
    pass
""",
        [],
    )
    assert result.returncode == 0, result.stderr
    assert _live_verdict(tmp_path)["status"] == "complete"


def test_review_standalone_workers_share_generated_invocation(tmp_path: Path) -> None:
    result = _run_journal(
        tmp_path,
        "def test_a(): pass\ndef test_b(): pass\n",
        ["-p", "xdist.plugin", "-n", "2"],
        {"BIOETL_JOURNAL_INVOCATION_ID": ""},
    )
    assert result.returncode == 0, result.stderr
    assert _live_verdict(tmp_path)["status"] == "complete"
    identities = {
        row["identity"]["invocation_id"]
        for path in (tmp_path / "journal").glob("*.jsonl")
        for row in map(json.loads, path.read_text().splitlines())
    }
    assert len(identities) == 1


def test_review_outer_cmdline_failure_never_proves_success(tmp_path: Path) -> None:
    plugin = tmp_path / "cmdline_boom.py"
    plugin.write_text(
        "import pytest\n@pytest.hookimpl(hookwrapper=True, tryfirst=True)\ndef pytest_cmdline_main(config):\n    yield\n    raise RuntimeError('late cmdline failure')\n"
    )
    result = _run_journal(
        tmp_path / "run",
        "def test_ok(): pass\n",
        [],
        {
            "PYTHONPATH": os.pathsep.join((str(tmp_path), str(_ROOT))),
            "PYTEST_PLUGINS": "cmdline_boom",
        },
    )
    assert result.returncode != 0
    assert _live_verdict(tmp_path / "run")["tests_passed"] is not True


def test_review_old_unspecified_damage_is_attributed(tmp_path: Path) -> None:
    stale = _named_receipt(
        "unspecified", "a" * 32, "controller", "controller", "b" * 32
    )
    (tmp_path / stale).write_bytes(b'{"event":')
    result = _run_journal(
        tmp_path / "new",
        "def test_ok(): pass\n",
        [],
        {"BIOETL_JOURNAL_PASS": "unspecified"},
    )
    assert result.returncode == 0
    for path in (tmp_path / "new" / "journal").glob("*.jsonl"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    assert verify_directory(tmp_path, executed_passes=["unspecified"]) == 4


def test_review_duplicate_workers_keep_their_own_identity(tmp_path: Path) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker_a = _identity(role="worker", worker_id="gw0")
    worker_b = _identity(role="worker", worker_id="gw1")
    nodeid = "test_sample.py::test_a"
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(controller),
                _start(worker_a),
                _start(worker_b),
                _collected(worker_a, [nodeid, nodeid]),
                _collected(worker_b, [nodeid, nodeid]),
                _collected(controller, [nodeid, nodeid]),
                *_phases(worker_a, nodeid, "passed"),
                *_phases(worker_b, nodeid, "passed"),
                {"event": "session_finish", "identity": controller, "exitstatus": 0},
            ]
        ),
    )
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete"
    assert {row["worker_id"] for row in verdict["terminals"]} == {"gw0", "gw1"}


@pytest.mark.parametrize("chain", ["failed_then_passed", "missing_zero", "gap"])
def test_followup_single_retry_chain_rejects_invalid_history(
    tmp_path: Path, chain: str
) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    prior = (
        []
        if chain == "missing_zero"
        else _phases(
            identity, nodeid, "failed" if chain == "failed_then_passed" else "rerun"
        )
    )
    last = 2 if chain == "gap" else 1
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(identity),
                _collected(identity, [nodeid]),
                *prior,
                *_phases(identity, nodeid, "passed", retry_index=last),
                {"event": "session_finish", "identity": identity, "exitstatus": 0},
            ]
        ),
    )
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 4


def test_followup_unselected_outcome_is_unknown(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(identity),
                _collected(identity, [nodeid]),
                *_phases(identity, nodeid, "passed"),
                *_phases(identity, "test_sample.py::test_b", "failed"),
                {"event": "session_finish", "identity": identity, "exitstatus": 1},
            ]
        ),
    )
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 4


@pytest.mark.parametrize("failing,forced", [(True, 0), (False, 1)])
def test_followup_cmdline_result_mismatch_never_proves_completion(
    tmp_path: Path, failing: bool, forced: int
) -> None:
    plugin = tmp_path / "cmdline_override.py"
    plugin.write_text(
        "import pytest\n@pytest.hookimpl(hookwrapper=True, tryfirst=True)\ndef pytest_cmdline_main(config):\n    outcome = yield\n    outcome.force_result("
        + str(forced)
        + ")\n"
    )
    result = _run_journal(
        tmp_path / "run",
        "def test_sample(): assert " + str(not failing) + "\n",
        [],
        {
            "PYTHONPATH": os.pathsep.join((str(tmp_path), str(_ROOT))),
            "PYTEST_PLUGINS": "cmdline_override",
        },
    )
    assert result.returncode == forced
    assert _live_verdict(tmp_path / "run")["status"] != "complete"
