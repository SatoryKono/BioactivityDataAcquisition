"""Receipt journal completeness, identity, and failure isolation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from scripts.engineering.ci.pytest_event_journal import (
    authoritative_pass_names,
    reconcile_directory,
    reconcile_pass,
)

pytestmark = pytest.mark.architecture

_ROOT = Path(__file__).resolve().parents[3]


def _identity(
    *,
    role: str,
    worker_id: str,
    pass_name: str = "parallel",
    invocation_id: str = "inv-1",
    actual: str = "a" * 40,
    expected: str | None = None,
    attempt: str = "1",
) -> dict[str, Any]:
    return {
        "workflow_run_id": "run-1",
        "workflow_run_attempt": attempt,
        "job": "serial-coverage",
        "matrix": None,
        "actual_checkout_sha": actual,
        "expected_checkout_sha": expected,
        "invocation_id": invocation_id,
        "pass_name": pass_name,
        "worker_id": worker_id,
        "role": role,
    }


def _write_receipt(
    directory: Path,
    events: list[dict[str, Any]],
    *,
    name: str = "receipt_test.jsonl",
    truncate: bool = False,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(event, sort_keys=True, ensure_ascii=True) for event in events]
    payload = ("\n".join(lines) + ("\n" if lines and not truncate else "")).encode(
        "utf-8"
    )
    if truncate and lines:
        payload = payload[: max(1, len(payload) // 2)]
    (directory / name).write_bytes(payload)


def _finalized(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        *events,
        {
            "event": "journal_finalized",
            "prior_line_count": len(events),
            "io_error": None,
        },
    ]


def _start(identity: dict[str, Any], **selection: Any) -> dict[str, Any]:
    base = {
        "collect_only": False,
        "exitfirst": False,
        "maxfail": 0,
        "args": ["test_sample.py"],
        "marker": "",
    }
    base.update(selection)
    return {
        "event": "session_start",
        "identity": identity,
        "selection": base,
        "sha_error": None,
    }


def _collected(identity: dict[str, Any], nodeids: list[str]) -> dict[str, Any]:
    return {"event": "collection_finished", "identity": identity, "nodeids": nodeids}


def _outcome(
    identity: dict[str, Any],
    nodeid: str,
    when: str,
    classification: str,
    *,
    retry_index: int = 0,
) -> dict[str, Any]:
    return {
        "event": "outcome",
        "identity": identity,
        "nodeid": nodeid,
        "when": when,
        "classification": classification,
        "retry_index": retry_index,
        "wasxfail": classification in {"xfail", "xpass"},
    }


def _phases(
    identity: dict[str, Any], nodeid: str, call: str, *, retry_index: int = 0
) -> list[dict[str, Any]]:
    setup = "passed" if call not in {"setup_error", "skipped", "xfail"} else call
    events = [_outcome(identity, nodeid, "setup", setup, retry_index=retry_index)]
    if call not in {"setup_error", "skipped"}:
        events.append(_outcome(identity, nodeid, "call", call, retry_index=retry_index))
    events.append(
        _outcome(identity, nodeid, "teardown", "passed", retry_index=retry_index)
    )
    return events


def _controller_pass(
    nodeids: list[str],
    calls: dict[str, str],
    *,
    pass_name: str = "parallel",
    invocation_id: str = "inv-1",
    **selection: Any,
) -> list[dict[str, Any]]:
    identity = _identity(
        role="controller",
        worker_id="controller",
        pass_name=pass_name,
        invocation_id=invocation_id,
    )
    events = [_start(identity, **selection), _collected(identity, nodeids)]
    for nodeid, call in calls.items():
        events.extend(_phases(identity, nodeid, call))
    events.append({"event": "session_finish", "identity": identity, "exitstatus": 0})
    return _finalized(events)


def test_record_count_and_exit_code_are_not_completeness_proof(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    events = _finalized(
        [
            _start(identity),
            _collected(identity, ["test_sample.py::test_a", "test_sample.py::test_b"]),
            *_phases(identity, "test_sample.py::test_a", "failed"),
            *[
                _outcome(identity, "test_sample.py::test_a", "call", "failed")
                for _ in range(20)
            ],
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "incomplete"
    assert "unexplained_selected_tests" in verdict["reasons"]
    assert verdict["tests_passed"] is None
    assert verdict["selected_count"] == 2


def test_early_stop_and_maxfail_leave_the_next_test_unexplained(tmp_path: Path) -> None:
    for flag, selection in (
        ("exitfirst", {"exitfirst": True}),
        ("maxfail", {"maxfail": 1}),
    ):
        directory = tmp_path / flag
        events = _controller_pass(
            ["test_sample.py::test_a", "test_sample.py::test_b"],
            {"test_sample.py::test_a": "failed"},
            **selection,
        )
        _write_receipt(directory, events)
        verdict = reconcile_pass(_load(directory), pass_name="parallel")
        assert verdict["status"] == "incomplete"
        assert "early_stop" in verdict["reasons"]
        assert verdict["unexplained"] == ["test_sample.py::test_b"]


def test_ordinary_failure_keeps_the_following_test(tmp_path: Path) -> None:
    events = _controller_pass(
        ["test_sample.py::test_a", "test_sample.py::test_b"],
        {"test_sample.py::test_a": "failed", "test_sample.py::test_b": "passed"},
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is False
    assert {item["nodeid"] for item in verdict["terminals"]} == {
        "test_sample.py::test_a",
        "test_sample.py::test_b",
    }


def test_retry_index_is_not_workflow_attempt_and_does_not_add_tests(
    tmp_path: Path,
) -> None:
    identity = _identity(role="controller", worker_id="controller", attempt="3")
    events = _finalized(
        [
            _start(identity),
            _collected(identity, ["test_sample.py::test_a"]),
            *_phases(identity, "test_sample.py::test_a", "failed", retry_index=0),
            *_phases(identity, "test_sample.py::test_a", "passed", retry_index=1),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete"
    assert verdict["selected_count"] == 1
    assert verdict["tests_passed"] is True
    assert verdict["terminals"][0]["retry_index"] == 1
    assert verdict["terminals"][0]["attempt_count"] == 2
    assert verdict["workflow_run_attempt"] == "3"


def test_worker_collection_and_controller_redelivery_are_not_summed(
    tmp_path: Path,
) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker_a = _identity(role="worker", worker_id="gw0")
    worker_b = _identity(role="worker", worker_id="gw1")
    node_a = "test_sample.py::test_a"
    node_b = "test_sample.py::test_b"
    events = [
        _start(controller),
        _collected(controller, [node_a, node_b]),
        _collected(worker_a, [node_a, node_b]),
        _collected(worker_b, [node_a, node_b]),
        *_phases(worker_a, node_a, "passed"),
        *_phases(controller, node_a, "passed"),
        *_phases(worker_b, node_b, "passed"),
        *_phases(controller, node_b, "passed"),
        {"event": "session_finish", "identity": controller, "exitstatus": 0},
    ]
    _write_receipt(tmp_path, _finalized(events), name="receipt_controller.jsonl")
    _write_receipt(
        tmp_path,
        _finalized([_start(worker_a), _collected(worker_a, [node_a, node_b])]),
        name="receipt_gw0.jsonl",
    )
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    parallel = verdict["passes"]["parallel"]
    assert parallel["selected_count"] == 2
    assert parallel["status"] == "complete"
    assert len(parallel["terminals"]) == 2
    assert {item["worker_id"] for item in parallel["terminals"]} == {"gw0", "gw1"}


def test_disagreeing_worker_collections_are_not_unioned(tmp_path: Path) -> None:
    worker_a = _identity(role="worker", worker_id="gw0")
    worker_b = _identity(role="worker", worker_id="gw1")
    events = _finalized(
        [
            _start(worker_a),
            _collected(worker_a, ["test_sample.py::test_a"]),
            *_phases(worker_a, "test_sample.py::test_a", "passed"),
            _start(worker_b),
            _collected(worker_b, ["test_sample.py::test_b"]),
            *_phases(worker_b, "test_sample.py::test_b", "passed"),
            {"event": "session_finish", "identity": worker_a, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert "missing_controller_collection" in verdict["reasons"]
    assert verdict["selected_count"] == 0


def test_conflicting_worker_outcomes_are_unknown(tmp_path: Path) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker_a = _identity(role="worker", worker_id="gw0")
    worker_b = _identity(role="worker", worker_id="gw1")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(controller),
            _collected(controller, [nodeid]),
            *_phases(worker_a, nodeid, "passed"),
            *_phases(worker_b, nodeid, "failed"),
            {"event": "session_finish", "identity": controller, "exitstatus": 1},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert "conflicting_outcome" in verdict["reasons"]


def test_fallback_supersedes_incomplete_parallel_and_keeps_serial(
    tmp_path: Path,
) -> None:
    parallel = tmp_path / "parallel"
    _write_receipt(
        parallel,
        _controller_pass(
            ["test_sample.py::test_a", "test_sample.py::test_b"],
            {"test_sample.py::test_a": "failed"},
            exitfirst=True,
        ),
        name="receipt_parallel.jsonl",
    )
    _write_receipt(
        parallel,
        _controller_pass(
            ["test_sample.py::test_a", "test_sample.py::test_b"],
            {"test_sample.py::test_a": "failed", "test_sample.py::test_b": "passed"},
            pass_name="fallback",
            invocation_id="inv-fallback",
        ),
        name="receipt_fallback.jsonl",
    )
    _write_receipt(
        parallel,
        _controller_pass(
            ["test_sample.py::test_serial"],
            {"test_sample.py::test_serial": "passed"},
            pass_name="serial",
            invocation_id="inv-serial",
        ),
        name="receipt_serial.jsonl",
    )
    authoritative, superseded = authoritative_pass_names(
        ["parallel", "fallback", "serial"]
    )
    assert authoritative == ["fallback", "serial"]
    assert superseded == ["parallel"]
    verdict = reconcile_directory(
        parallel, executed_passes=["parallel", "fallback", "serial"]
    )
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is False
    assert verdict["superseded_passes"] == ["parallel"]
    assert verdict["passes"]["fallback"]["selected_count"] == 2
    assert verdict["passes"]["serial"]["selected_count"] == 1


def test_truncated_missing_and_sha_mismatch_block_complete(tmp_path: Path) -> None:
    missing = reconcile_pass([], pass_name="parallel")
    assert missing["status"] == "unknown"
    assert missing["reasons"] == ["missing_receipt"]

    truncated_dir = tmp_path / "truncated"
    identity = _identity(role="controller", worker_id="controller")
    _write_receipt(
        truncated_dir,
        [_start(identity), _collected(identity, ["test_sample.py::test_a"])],
        truncate=True,
    )
    truncated = reconcile_pass(_load(truncated_dir), pass_name="parallel")
    assert truncated["status"] == "unknown"
    assert "truncated_jsonl" in truncated["reasons"]

    mismatch_dir = tmp_path / "mismatch"
    mismatch_identity = _identity(
        role="controller",
        worker_id="controller",
        actual="a" * 40,
        expected="b" * 40,
    )
    _write_receipt(
        mismatch_dir,
        _finalized(
            [
                _start(mismatch_identity),
                {
                    "event": "checkout_mismatch",
                    "identity": mismatch_identity,
                    "reason": "sha_mismatch",
                    "actual": "a" * 40,
                    "expected": "b" * 40,
                },
            ]
        ),
    )
    mismatch = reconcile_pass(_load(mismatch_dir), pass_name="parallel")
    assert mismatch["status"] == "incomplete"
    assert "checkout_sha_mismatch" in mismatch["reasons"]
    assert mismatch["tests_passed"] is None


def test_setup_teardown_skip_and_xfail_classifications(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeids = [
        "test_sample.py::test_setup",
        "test_sample.py::test_call",
        "test_sample.py::test_teardown",
        "test_sample.py::test_skip",
        "test_sample.py::test_xfail",
        "test_sample.py::test_xpass",
    ]
    events = [
        _start(identity),
        _collected(identity, nodeids),
        _outcome(identity, nodeids[0], "setup", "setup_error"),
        _outcome(identity, nodeids[0], "teardown", "passed"),
        *_phases(identity, nodeids[1], "failed"),
        _outcome(identity, nodeids[2], "setup", "passed"),
        _outcome(identity, nodeids[2], "call", "passed"),
        _outcome(identity, nodeids[2], "teardown", "teardown_error"),
        _outcome(identity, nodeids[3], "setup", "skipped"),
        _outcome(identity, nodeids[3], "teardown", "passed"),
        _outcome(identity, nodeids[4], "setup", "passed"),
        _outcome(identity, nodeids[4], "call", "xfail"),
        _outcome(identity, nodeids[4], "teardown", "passed"),
        _outcome(identity, nodeids[5], "setup", "passed"),
        _outcome(identity, nodeids[5], "call", "xpass"),
        _outcome(identity, nodeids[5], "teardown", "passed"),
        {"event": "session_finish", "identity": identity, "exitstatus": 1},
    ]
    _write_receipt(tmp_path, _finalized(events))
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is False
    classes = {item["nodeid"]: item["classification"] for item in verdict["terminals"]}
    assert classes[nodeids[0]] == "setup_error"
    assert classes[nodeids[1]] == "failed"
    assert classes[nodeids[2]] == "teardown_error"
    assert classes[nodeids[3]] == "skipped"
    assert classes[nodeids[4]] == "xfail"
    assert classes[nodeids[5]] == "xpass"


def test_collect_only_is_incomplete_even_with_exit_zero(tmp_path: Path) -> None:
    events = _controller_pass(
        ["test_sample.py::test_a"],
        {},
        collect_only=True,
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "incomplete"
    assert "collect_only" in verdict["reasons"]


def _load(directory: Path) -> list[dict[str, Any]]:
    from scripts.engineering.ci.pytest_event_journal import _group_receipts

    return _group_receipts(directory)


def _run_journal(
    tmp_path: Path,
    body: str,
    extra: list[str],
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    journal = tmp_path / "journal"
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(body, encoding="utf-8")
    child_env = os.environ.copy()
    child_env.pop("EXPECTED_CHECKOUT_SHA", None)
    child_env["BIOETL_JOURNAL_INVOCATION_ID"] = "inv-live"
    child_env["BIOETL_JOURNAL_PASS"] = "parallel"
    child_env["BIOETL_JOURNAL_JOB"] = "serial-coverage"
    child_env["PYTHONPATH"] = str(_ROOT)
    child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    if env:
        child_env.update(env)
    from scripts.engineering.ci.pytest_event_journal import (
        _REDACTION_KEY_MIN_LENGTH,
        ensure_redaction_key,
    )

    current_key = child_env.get("BIOETL_JOURNAL_REDACTION_KEY", "")
    if len(current_key) < _REDACTION_KEY_MIN_LENGTH:
        child_env["BIOETL_JOURNAL_REDACTION_KEY"] = ensure_redaction_key()
    return subprocess.run(
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
            "scripts.engineering.ci.pytest_event_journal",
            f"--event-journal-dir={journal}",
            *extra,
        ],
        cwd=_ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )


def _live_verdict(tmp_path: Path) -> dict[str, Any]:
    return reconcile_directory(tmp_path / "journal", executed_passes=["parallel"])


def test_live_failure_runs_the_next_test_and_hides_no_secret(tmp_path: Path) -> None:
    secret = "do-not-leak-me-token"
    result = _run_journal(
        tmp_path,
        "def test_fail():\n    assert False\n\ndef test_next():\n    assert True\n",
        [],
        {
            "SUPER_SECRET_TOKEN": secret,
            "GITHUB_RUN_ID": "12345",
            "GITHUB_RUN_ATTEMPT": "7",
        },
    )
    assert result.returncode != 0
    verdict = _live_verdict(tmp_path)
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is False
    assert verdict["passes"]["parallel"]["selected_count"] == 2
    blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "journal").glob("receipt_*.jsonl")
    )
    assert secret not in blob
    assert "SUPER_SECRET_TOKEN" not in blob
    assert "12345" in blob
    assert verdict["passes"]["parallel"]["workflow_run_attempt"] == "7"


def test_live_exitfirst_and_maxfail_are_incomplete(tmp_path: Path) -> None:
    body = "def test_fail():\n    assert False\n\ndef test_next():\n    assert True\n"
    stopped = _run_journal(tmp_path / "x", body, ["-x"])
    assert stopped.returncode != 0
    stopped_verdict = reconcile_directory(
        tmp_path / "x" / "journal", executed_passes=["parallel"]
    )
    assert stopped_verdict["status"] == "incomplete"
    assert any("early_stop" in reason for reason in stopped_verdict["reasons"])

    limited = _run_journal(tmp_path / "maxfail", body, ["--maxfail=1"])
    assert limited.returncode != 0
    limited_verdict = reconcile_directory(
        tmp_path / "maxfail" / "journal", executed_passes=["parallel"]
    )
    assert limited_verdict["status"] == "incomplete"


def test_live_collection_setup_teardown_skip_xfail_and_collect_only(
    tmp_path: Path,
) -> None:
    collected = _run_journal(
        tmp_path / "collect",
        "import missing_collection_module\n\ndef test_ok():\n    pass\n",
        [],
    )
    assert collected.returncode != 0
    collected_verdict = reconcile_directory(
        tmp_path / "collect" / "journal", executed_passes=["parallel"]
    )
    assert collected_verdict["status"] == "incomplete"
    assert any("collection_error" in reason for reason in collected_verdict["reasons"])

    setup = _run_journal(
        tmp_path / "setup",
        "import pytest\n"
        "@pytest.fixture\n"
        "def boom():\n"
        "    raise RuntimeError('setup boom')\n"
        "def test_setup(boom):\n"
        "    pass\n"
        "def test_next():\n"
        "    pass\n",
        [],
    )
    assert setup.returncode != 0
    setup_verdict = reconcile_directory(
        tmp_path / "setup" / "journal", executed_passes=["parallel"]
    )
    assert setup_verdict["status"] == "complete"
    assert setup_verdict["tests_passed"] is False

    teardown = _run_journal(
        tmp_path / "teardown",
        "import pytest\n"
        "@pytest.fixture\n"
        "def boom():\n"
        "    yield\n"
        "    raise RuntimeError('teardown boom')\n"
        "def test_body(boom):\n"
        "    pass\n",
        [],
    )
    assert teardown.returncode != 0
    teardown_verdict = reconcile_directory(
        tmp_path / "teardown" / "journal", executed_passes=["parallel"]
    )
    assert teardown_verdict["status"] == "complete"
    assert teardown_verdict["passes"]["parallel"]["terminals"][0]["classification"] == (
        "teardown_error"
    )

    marked = _run_journal(
        tmp_path / "marks",
        "import pytest\n"
        "@pytest.mark.skip\n"
        "def test_skip():\n"
        "    pass\n"
        "@pytest.mark.xfail\n"
        "def test_xfail():\n"
        "    assert False\n",
        [],
    )
    assert marked.returncode == 0
    marked_verdict = reconcile_directory(
        tmp_path / "marks" / "journal", executed_passes=["parallel"]
    )
    assert marked_verdict["status"] == "complete"
    assert marked_verdict["tests_passed"] is True
    classes = {
        item["classification"]
        for item in marked_verdict["passes"]["parallel"]["terminals"]
    }
    assert classes == {"skipped", "xfail"}

    collect_only = _run_journal(
        tmp_path / "collect-only",
        "def test_ok():\n    pass\n",
        ["--collect-only"],
    )
    assert collect_only.returncode == 0
    collect_verdict = reconcile_directory(
        tmp_path / "collect-only" / "journal", executed_passes=["parallel"]
    )
    assert collect_verdict["status"] == "incomplete"
    assert any("collect_only" in reason for reason in collect_verdict["reasons"])


def test_disk_error_does_not_replace_the_test_result(tmp_path: Path) -> None:
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("blocked", encoding="utf-8")
    journal = blocked / "journal"
    test_file = tmp_path / "test_disk.py"
    test_file.write_text("def test_fail():\n    assert False\n", encoding="utf-8")
    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = str(_ROOT)
    child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    child_env["BIOETL_JOURNAL_INVOCATION_ID"] = "inv-disk"
    child_env["BIOETL_JOURNAL_PASS"] = "parallel"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "--noconftest",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:benchmark",
            "-o",
            "addopts=",
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
    assert result.returncode != 0
    assert "AssertionError" in result.stdout or "assert False" in result.stdout
    assert "EventJournal:" in result.stderr
    assert "test_fail" in result.stdout
    assert (
        reconcile_directory(journal, executed_passes=["parallel"])["status"]
        == "unknown"
    )


def test_sha_mismatch_is_not_a_successful_run(tmp_path: Path) -> None:
    result = _run_journal(
        tmp_path,
        "def test_ok():\n    pass\n",
        [],
        {"EXPECTED_CHECKOUT_SHA": "b" * 40},
    )
    assert result.returncode != 0
    assert (
        "EventJournal SHA mismatch" in result.stdout
        or "EventJournal SHA mismatch" in result.stderr
    )
    verdict = _live_verdict(tmp_path)
    assert verdict["status"] != "complete"
    assert any("checkout_sha_mismatch" in reason for reason in verdict["reasons"])


def test_xdist_race_attributes_workers_without_double_counting(tmp_path: Path) -> None:
    result = _run_journal(
        tmp_path,
        "def test_ok1():\n    pass\n\ndef test_ok2():\n    pass\n",
        ["-p", "xdist", "-n", "2"],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    verdict = _live_verdict(tmp_path)
    parallel = verdict["passes"]["parallel"]
    assert verdict["status"] == "complete", verdict["reasons"]
    assert parallel["selected_count"] == 2
    assert len(parallel["terminals"]) == 2
    assert {item["worker_id"] for item in parallel["terminals"]} <= {"gw0", "gw1"}
    assert "controller" not in {item["worker_id"] for item in parallel["terminals"]}
    raw_calls = []
    worker_collection_items = 0
    for path in (tmp_path / "journal").glob("receipt_*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("event") == "outcome" and event.get("when") == "call":
                raw_calls.append(event)
            if event.get("event") == "collection_finished" and (
                (event.get("identity") or {}).get("role") == "worker"
            ):
                worker_collection_items += len(event.get("nodeids") or [])
    assert len(raw_calls) > len(parallel["terminals"])
    assert worker_collection_items > parallel["selected_count"]
    assert any(
        (event.get("identity") or {}).get("role") == "controller" for event in raw_calls
    )


def test_runner_keeps_test_failure_distinct_from_journal_status(tmp_path: Path) -> None:
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "def test_fail():\n    assert False\n\ndef test_next():\n    assert True\n",
        encoding="utf-8",
    )
    reports = tmp_path / "reports"
    journal = tmp_path / "journal"
    result = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "engineering" / "ci" / "run_pytest_resilient.py"),
            "--target",
            str(test_file),
            "--reports-dir",
            str(reports),
            "--journal-dir",
            str(journal),
            "--parallel-addopts",
            "-q --tb=line --noconftest -o addopts=",
            "--skip-serial-pass",
            "--parallel-timeout-seconds",
            "60",
        ],
        cwd=_ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(_ROOT),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    verdict = json.loads((journal / "journal-verdict.json").read_text(encoding="utf-8"))
    assert verdict["status"] == "complete"
    assert verdict["tests_passed"] is False
    assert verdict["test_exit_code"] == 1
    assert "parallel" in verdict["executed_passes"]


def test_deselected_tests_are_not_required_to_finish(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    kept = "test_sample.py::test_serial"
    dropped = "test_sample.py::test_other"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [kept, dropped]),
            {"event": "deselected", "identity": identity, "nodeids": [dropped]},
            *_phases(identity, kept, "passed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete"
    assert verdict["selected_count"] == 1
    assert verdict["deselected_count"] == 1
    assert verdict["unexplained"] == []


def test_live_marker_expression_records_the_selected_test(tmp_path: Path) -> None:
    result = _run_journal(
        tmp_path,
        "import pytest\n\n"
        "@pytest.mark.serial\n"
        "def test_serial():\n"
        "    pass\n\n"
        "def test_other():\n"
        "    pass\n",
        ["-m", "serial"],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    verdict = _live_verdict(tmp_path)
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["passes"]["parallel"]["selected_count"] == 1
    assert verdict["passes"]["parallel"]["deselected_count"] == 1


def test_token_in_a_function_name_stays_a_distinct_nodeid(tmp_path: Path) -> None:
    result = _run_journal(
        tmp_path,
        "def test_token_alpha():\n    pass\n\ndef test_token_beta():\n    pass\n",
        [],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    verdict = _live_verdict(tmp_path)
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["passes"]["parallel"]["selected_count"] == 2
    blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "journal").glob("receipt_*.jsonl")
    )
    assert "test_token_alpha" in blob
    assert "test_token_beta" in blob
    assert blob.count("[redacted:") == 0


def test_assignment_redacts_only_the_secret_value() -> None:
    from scripts.engineering.ci.pytest_event_journal import _redact_text

    raw = "tests/test_mcp_token_configuration.py::test_reads[token=super-secret-value]"
    redacted = _redact_text(raw, ())
    assert "test_mcp_token_configuration.py::test_reads" in redacted
    assert "token=" in redacted
    assert "super-secret-value" not in redacted
    assert redacted.endswith("]")


def test_credential_prefixes_stay_out_of_the_journal(tmp_path: Path) -> None:
    import hashlib
    import re

    from scripts.engineering.ci.pytest_event_journal import (
        _redaction_token,
        ensure_redaction_key,
    )

    first = "AKIAIOSFODNN7EXAMPLE"
    second = "AKIABBBBBBBBBBBBBBBB"
    result = _run_journal(
        tmp_path,
        "import pytest\n\n"
        "@pytest.mark.parametrize(\n"
        '    "credential",\n'
        f'    ["{first}", "{second}"],\n'
        ")\n"
        "def test_reads(credential: str) -> None:\n"
        "    assert credential\n",
        [],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    verdict = _live_verdict(tmp_path)
    parallel = verdict["passes"]["parallel"]
    assert verdict["status"] == "complete", verdict["reasons"]
    assert parallel["selected_count"] == 2
    assert len(parallel["terminals"]) == 2
    blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "journal").glob("receipt_*.jsonl")
    )
    assert first not in blob
    assert second not in blob
    assert "test_reads" in blob
    assert _redaction_token(first) in blob
    assert _redaction_token(second) in blob
    assert _redaction_token(first) != _redaction_token(second)
    tokens = set(re.findall(r"\[redacted:[0-9a-f]{12}\]", blob))
    assert len(tokens) >= 2
    for secret in (first, second):
        unsalted = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]
        assert unsalted not in blob
    assert ensure_redaction_key() not in blob
    assert "BIOETL_JOURNAL_REDACTION_KEY" not in blob


def test_access_key_env_value_is_removed_from_nodeids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.engineering.ci.pytest_event_journal import _redact_text, _secret_values

    secret = "access-key-value-not-stored"
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", secret)
    redacted = _redact_text(
        f"tests/test_sample.py::test_reads[{secret}]", _secret_values()
    )
    assert secret not in redacted
    assert "tests/test_sample.py::test_reads" in redacted


def test_latest_invocation_does_not_conflict_with_an_older_pass(
    tmp_path: Path,
) -> None:
    old = _controller_pass(
        ["test_sample.py::test_a"],
        {"test_sample.py::test_a": "failed"},
        invocation_id="inv-old",
    )
    new = _controller_pass(
        ["test_sample.py::test_a"],
        {"test_sample.py::test_a": "passed"},
        invocation_id="inv-new",
    )
    old[0]["timestamp"] = "2026-10-16T00:00:00+00:00"
    new[0]["timestamp"] = "2026-10-16T01:00:00+00:00"
    _write_receipt(tmp_path, old, name="receipt_old.jsonl")
    _write_receipt(tmp_path, new, name="receipt_new.jsonl")
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    parallel = verdict["passes"]["parallel"]
    assert verdict["status"] == "complete", verdict["reasons"]
    assert "conflicting_outcome" not in parallel["reasons"]
    assert verdict["tests_passed"] is True
    assert parallel["invocation_id"] == "inv-new"


class _CloseDenied:
    def __init__(self, wrapped: Any) -> None:
        self._wrapped = wrapped

    def write(self, data: str) -> int:
        return self._wrapped.write(data)

    def flush(self) -> None:
        self._wrapped.flush()

    def fileno(self) -> int:
        return self._wrapped.fileno()

    def close(self) -> None:
        raise OSError(13, "denied")


def test_close_error_marker_blocks_a_finalized_receipt(tmp_path: Path) -> None:
    from scripts.engineering.ci.pytest_event_journal import (
        EventJournalPlugin,
        _load_receipt,
    )

    path = tmp_path / "receipt_close.jsonl"
    plugin = EventJournalPlugin(
        None,
        path,
        _identity(role="controller", worker_id="controller"),
    )
    real = plugin._file
    assert real is not None
    plugin._file = _CloseDenied(real)
    try:
        plugin.record("session_start", {"selection": {}})
        plugin.finalize()
    finally:
        real.close()
    marker = path.with_name(path.name + ".close_error")
    assert marker.read_text(encoding="utf-8").strip() == "close_failed:13"
    loaded = _load_receipt(path)
    finalized = [
        event for event in loaded["events"] if event.get("event") == "journal_finalized"
    ]
    assert finalized[-1]["io_error"] is None
    assert loaded["io_error"] == "close_failed:13"
    verdict = reconcile_pass([loaded], pass_name="parallel")
    assert "journal_io_error" in verdict["reasons"]
    assert verdict["status"] != "complete"


def test_verdict_write_error_preserves_the_pytest_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal
    from scripts.engineering.ci import run_pytest_resilient

    seen: list[dict[str, Any]] = []

    def _deny(path: Path, payload: dict[str, Any]) -> None:
        _ = path
        seen.append(
            {
                "status": payload["status"],
                "tests_passed": payload["tests_passed"],
                "reasons": list(payload["reasons"]),
            }
        )
        raise PermissionError(13, "denied")

    monkeypatch.setattr(journal, "atomic_write_json", _deny)
    journal_dir = tmp_path / "journal"
    _write_receipt(
        journal_dir,
        _controller_pass(
            ["test_sample.py::test_a"],
            {"test_sample.py::test_a": "passed"},
        ),
    )
    reports = tmp_path / "reports"
    reports.mkdir()
    failed = run_pytest_resilient._finish_run(
        reports_dir=reports,
        summary_lines=[],
        journal_dir=journal_dir,
        executed_passes=["parallel"],
        test_rc=1,
    )
    failed_verdict = seen[-1]
    seen.clear()
    passed = run_pytest_resilient._finish_run(
        reports_dir=reports,
        summary_lines=[],
        journal_dir=journal_dir,
        executed_passes=["parallel"],
        test_rc=0,
    )
    passed_verdict = seen[-1]
    seen.clear()
    incomplete = run_pytest_resilient._finish_run(
        reports_dir=reports,
        summary_lines=[],
        journal_dir=tmp_path / "empty-journal",
        executed_passes=["parallel"],
        test_rc=0,
    )
    empty_verdict = seen[-1]
    assert failed == 1
    assert passed == 4
    assert incomplete == 4
    assert failed_verdict["status"] == "incomplete"
    assert failed_verdict["tests_passed"] is None
    assert "verdict_write_failed" in failed_verdict["reasons"]
    assert passed_verdict["status"] == "incomplete"
    assert passed_verdict["tests_passed"] is None
    assert empty_verdict["status"] == "unknown"
    assert "verdict_write_failed" in empty_verdict["reasons"]


def test_verdict_directory_parent_file_stays_a_controlled_exit(tmp_path: Path) -> None:
    from scripts.engineering.ci import run_pytest_resilient

    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    journal_dir = blocker / "journal"
    assert (
        run_pytest_resilient._finish_run(
            reports_dir=reports,
            summary_lines=[],
            journal_dir=journal_dir,
            executed_passes=["parallel"],
            test_rc=0,
        )
        == 4
    )
    assert (
        run_pytest_resilient._finish_run(
            reports_dir=reports,
            summary_lines=[],
            journal_dir=journal_dir,
            executed_passes=["parallel"],
            test_rc=1,
        )
        == 1
    )


def test_call_without_teardown_is_not_complete(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_call"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            _outcome(identity, nodeid, "setup", "passed"),
            _outcome(identity, nodeid, "call", "passed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "incomplete"
    assert "missing_teardown" in verdict["reasons"]
    assert "unexplained_selected_tests" in verdict["reasons"]
    assert verdict["tests_passed"] is None


def test_serial_coverage_journal_fits_the_job_timeout() -> None:
    workflow = (_ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )
    serial = workflow.split("  serial-coverage:\n", 1)[1].split(
        "\n  coverage-verify:", 1
    )[0]
    assert "timeout-minutes: 15" in serial
    assert "--parallel-timeout-seconds 660" in serial
    assert "--no-fallback" in serial
    assert "pytest-event-journal-serial-coverage" in serial
    assert "if: ${{ always() && !cancelled() }}" in serial


def _named_receipt(
    pass_name: str,
    invocation: str,
    role: str,
    worker: str,
    file_id: str,
) -> str:
    return f"receipt_{pass_name}_{invocation}_{role}_{worker}_{file_id}.jsonl"


def test_skipped_setup_without_teardown_is_incomplete(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_skip"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            _outcome(identity, nodeid, "setup", "skipped"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "incomplete"
    assert verdict["tests_passed"] is None
    assert "missing_teardown" in verdict["reasons"]


def test_skipped_setup_teardown_error_is_not_a_pass(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_skip"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            _outcome(identity, nodeid, "setup", "skipped"),
            _outcome(identity, nodeid, "teardown", "teardown_error"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["terminals"][0]["classification"] == "teardown_error"
    assert verdict["tests_passed"] is not True
    assert not (verdict["status"] == "complete" and verdict["tests_passed"] is True)


def test_xfail_setup_teardown_error_is_not_a_pass(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_xfail"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            _outcome(identity, nodeid, "setup", "xfail"),
            _outcome(identity, nodeid, "teardown", "teardown_error"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["terminals"][0]["classification"] == "teardown_error"
    assert verdict["tests_passed"] is not True


def test_truncated_worker_filename_blocks_its_invocation(tmp_path: Path) -> None:
    invocation = "a" * 32
    good = _controller_pass(
        ["test_sample.py::test_a"],
        {"test_sample.py::test_a": "passed"},
        invocation_id=invocation,
    )
    _write_receipt(
        tmp_path,
        good,
        name=_named_receipt(
            "parallel", invocation, "controller", "controller", "b" * 32
        ),
    )
    damaged = tmp_path / _named_receipt(
        "parallel", invocation, "worker", "gw_0", "c" * 32
    )
    damaged.write_bytes(b"{")
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert verdict["status"] == "unknown"
    assert verdict["tests_passed"] is None
    assert any(reason.startswith("parallel:") for reason in verdict["reasons"])


def test_older_damaged_invocation_does_not_hide_the_latest(tmp_path: Path) -> None:
    old_invocation = "1" * 32
    new_invocation = "2" * 32
    (
        tmp_path / _named_receipt("parallel", old_invocation, "worker", "gw0", "3" * 32)
    ).write_bytes(b"{")
    new = _controller_pass(
        ["test_sample.py::test_a"],
        {"test_sample.py::test_a": "passed"},
        invocation_id=new_invocation,
    )
    new[0]["timestamp"] = "2026-10-17T00:00:00+00:00"
    _write_receipt(
        tmp_path,
        new,
        name=_named_receipt(
            "parallel", new_invocation, "controller", "controller", "4" * 32
        ),
    )
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["tests_passed"] is True
    assert verdict["passes"]["parallel"]["invocation_id"] == new_invocation


def test_unattributed_damaged_receipt_blocks_a_complete_pass(tmp_path: Path) -> None:
    _write_receipt(
        tmp_path,
        _controller_pass(
            ["test_sample.py::test_a"],
            {"test_sample.py::test_a": "passed"},
        ),
        name="receipt_new.jsonl",
    )
    (tmp_path / "receipt_garbage.jsonl").write_bytes(b"")
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert verdict["status"] == "unknown"
    assert verdict["tests_passed"] is None
    assert "unattributed_receipt_damage" in verdict["reasons"]


def test_unreadable_receipt_stays_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci.pytest_event_journal import _group_receipts

    journal = tmp_path / "journal"
    journal.mkdir()
    invocation = "d" * 32
    path = journal / _named_receipt(
        "parallel", invocation, "controller", "controller", "e" * 32
    )
    path.write_bytes(b"{}\n")
    original = Path.read_bytes

    def _deny(self: Path) -> bytes:
        if self.name == path.name:
            raise OSError(13, "denied")
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", _deny)
    loaded = _group_receipts(journal)
    assert loaded[0]["io_error"] == "receipt_unreadable:13"
    assert loaded[0]["truncated"] is True
    assert loaded[0]["finalized"] is False
    verdict = reconcile_directory(journal, executed_passes=["parallel"])
    assert verdict["status"] == "unknown"
    assert verdict["tests_passed"] is None


def test_receipt_listing_failure_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(self: Path, pattern: str) -> list[Path]:
        _ = (self, pattern)
        raise OSError(5, "io")

    monkeypatch.setattr(Path, "glob", _boom)
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert verdict["status"] == "unknown"
    assert "unattributed_receipt_damage" in verdict["reasons"]


def test_directory_receipt_path_does_not_escape(tmp_path: Path) -> None:
    invocation = "a" * 32
    folder = tmp_path / _named_receipt(
        "parallel", invocation, "worker", "gw0", "b" * 32
    )
    folder.mkdir()
    verdict = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert verdict["status"] == "unknown"
    assert any("journal_io_error" in reason for reason in verdict["reasons"])


def test_expected_invocation_rejects_an_older_complete_receipt(tmp_path: Path) -> None:
    _write_receipt(
        tmp_path,
        _controller_pass(
            ["test_sample.py::test_a"],
            {"test_sample.py::test_a": "passed"},
            invocation_id="inv-old",
        ),
        name="receipt_old.jsonl",
    )
    current = "f" * 32
    bound = reconcile_directory(
        tmp_path,
        executed_passes=["parallel"],
        expected_invocations={"parallel": current},
    )
    assert bound["status"] == "unknown"
    assert any("missing_receipt" in reason for reason in bound["reasons"])
    assert bound["tests_passed"] is None
    latest = reconcile_directory(tmp_path, executed_passes=["parallel"])
    assert latest["status"] == "complete"
    assert latest["passes"]["parallel"]["invocation_id"] == "inv-old"


def test_finish_run_binds_the_current_invocation(tmp_path: Path) -> None:
    from scripts.engineering.ci import run_pytest_resilient

    journal = tmp_path / "journal"
    _write_receipt(
        journal,
        _controller_pass(
            ["test_sample.py::test_a"],
            {"test_sample.py::test_a": "passed"},
            invocation_id="inv-old",
        ),
        name="receipt_old.jsonl",
    )
    reports = tmp_path / "reports"
    reports.mkdir()
    current = {"parallel": "f" * 32}
    assert (
        run_pytest_resilient._finish_run(
            reports_dir=reports,
            summary_lines=[],
            journal_dir=journal,
            executed_passes=["parallel"],
            test_rc=0,
            expected_invocations=current,
        )
        == 4
    )
    assert (
        run_pytest_resilient._finish_run(
            reports_dir=reports,
            summary_lines=[],
            journal_dir=journal,
            executed_passes=["parallel"],
            test_rc=1,
            expected_invocations=current,
        )
        == 1
    )


def test_matrix_values_are_redacted_before_identity_and_safe_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.engineering.ci.pytest_event_journal import (
        _identity_from_env,
        _redaction_token,
        _safe_env,
        _secret_values,
    )

    password = "swordfish-secret"
    nested = "nested-api-key-value"
    raw = json.dumps(
        {
            "password": password,
            "wrapped": {"api_key": nested, "label": "public"},
            "note": f"token = {password}",
        }
    )
    monkeypatch.setenv("BIOETL_JOURNAL_MATRIX", raw)
    secrets = _secret_values()
    matrix = _identity_from_env(actual_sha=None, secrets=secrets)["matrix"]
    assert matrix["password"] == _redaction_token(password)
    assert matrix["wrapped"]["api_key"] == _redaction_token(nested)
    assert matrix["wrapped"]["label"] == "public"
    assert password not in matrix["note"]
    blob = _safe_env(secrets)["BIOETL_JOURNAL_MATRIX"]
    assert password not in blob
    assert nested not in blob
    assert _redaction_token(password) in blob
    assert _redaction_token(nested) in blob


def test_journal_child_env_prepends_the_repo_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.engineering.ci.run_pytest_resilient import (
        _REPO_ROOT,
        _journal_child_env,
    )

    already = "already-entry"
    other = "other-entry"
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join((already, other)))
    env = _journal_child_env("parallel", "abc123")
    parts = env["PYTHONPATH"].split(os.pathsep)
    assert parts[0] == str(_REPO_ROOT)
    assert parts[1:] == [already, other]
    assert env["BIOETL_JOURNAL_PASS"] == "parallel"
    assert env["BIOETL_JOURNAL_INVOCATION_ID"] == "abc123"
    monkeypatch.delenv("PYTHONPATH", raising=False)
    assert _journal_child_env("serial", "def456")["PYTHONPATH"] == str(_REPO_ROOT)


def test_run_pass_forwards_repo_root_on_pythonpath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from scripts.engineering.ci import pytest_abort_diagnostic_adapter as adapter
    from scripts.engineering.ci.run_pytest_resilient import _REPO_ROOT, _run_pass

    captured: dict[str, Any] = {}

    class _Adapter:
        def __init__(self, *_args: Any, **kwargs: Any) -> None:
            captured["env"] = kwargs.get("child_env")

        def run(
            self,
            command: list[str],
            junit_path: Path,
            diagnostic_dir: Path,
            *,
            base: Path,
        ) -> Any:
            _ = (command, junit_path, diagnostic_dir, base)
            return SimpleNamespace(
                status="COMPLETED",
                wrapper_exit_code=0,
                stdout_file="",
                stderr_file="",
                diagnostics_persisted=False,
                manifest_file="",
            )

    monkeypatch.setattr(adapter, "PytestAbortDiagnosticAdapter", _Adapter)
    already = "already-entry"
    monkeypatch.setenv("PYTHONPATH", already)
    result = _run_pass(
        name="parallel",
        base_command=[sys.executable, "-m", "pytest"],
        target="tests/sample.py",
        marker_expr="not serial",
        addopts=["-q"],
        reports_dir=tmp_path / "reports",
        journal_dir=tmp_path / "journal",
        timeout_seconds=None,
        executed_passes=[],
    )
    assert result.invocation_id
    child_env = captured["env"]
    assert child_env is not None
    assert child_env["PYTHONPATH"].split(os.pathsep) == [
        str(_REPO_ROOT),
        already,
    ]
    assert child_env["BIOETL_JOURNAL_INVOCATION_ID"] == result.invocation_id
    assert child_env["BIOETL_JOURNAL_PASS"] == "parallel"
    key = child_env.get("BIOETL_JOURNAL_REDACTION_KEY") or ""
    assert len(key) >= 32


def test_quoted_assignment_redacts_the_enclosed_value() -> None:
    from scripts.engineering.ci.pytest_event_journal import _redact_text

    raw = '--payload={"password":"swordfish"}'
    redacted = _redact_text(raw, ())
    assert "swordfish" not in redacted
    assert redacted.startswith('--payload={"password":"')
    assert redacted.endswith('"}')
    assert "[redacted:" in redacted
    empty = "--payload={'password':''}"
    redacted_empty = _redact_text(empty, ())
    assert redacted_empty.endswith("'}")
    assert "[redacted:" in redacted_empty
    assert "''" not in redacted_empty


def test_redaction_token_is_not_an_unsalted_digest() -> None:
    import hashlib

    from scripts.engineering.ci.pytest_event_journal import _redaction_token

    secret = "swordfish"
    unsalted = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]
    token = _redaction_token(secret)
    assert token == _redaction_token(secret)
    assert token != f"[redacted:{unsalted}]"
    assert secret not in token


def test_duplicate_nodeid_is_not_reused(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid, nodeid]),
            *_phases(identity, nodeid, "failed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 1},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["selected_count"] == 2
    assert verdict["status"] == "incomplete"
    assert "unexplained_selected_tests" in verdict["reasons"]


def test_worker_collection_without_controller_is_unknown(tmp_path: Path) -> None:
    worker_a = _identity(role="worker", worker_id="gw0")
    worker_b = _identity(role="worker", worker_id="gw1")
    node_a = "test_sample.py::test_a"
    node_b = "test_sample.py::test_b"
    events = _finalized(
        [
            _start(worker_a),
            _collected(worker_a, [node_a, node_b]),
            *_phases(worker_a, node_a, "passed"),
            _start(worker_b),
            _collected(worker_b, [node_a, node_b]),
            *_phases(worker_b, node_b, "passed"),
            {"event": "session_finish", "identity": worker_a, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert "missing_controller_collection" in verdict["reasons"]
    assert verdict["tests_passed"] is None
    assert verdict["selected_count"] == 0


def test_invalid_utf8_receipt_is_damaged(tmp_path: Path) -> None:
    path = tmp_path / "receipt_bad.jsonl"
    path.write_bytes(b"\xff\n")
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert verdict["tests_passed"] is None


def test_malformed_identity_does_not_escape_reconciliation(tmp_path: Path) -> None:
    events = _finalized(
        [
            {"event": "session_start", "identity": "corrupted", "selection": {}},
            {"event": "session_finish", "identity": "corrupted", "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"


def test_missing_origin_worker_receipt_is_unknown(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    outcomes = _phases(identity, nodeid, "passed")
    for event in outcomes:
        event["origin_worker"] = "gw0"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            *outcomes,
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert "missing_worker_receipt" in verdict["reasons"]


def test_checkout_sha_command_uses_repository_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    seen: dict[str, list[str]] = {}

    def _fake(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout="a" * 40 + "\n", stderr="")

    monkeypatch.setattr(journal.subprocess, "run", _fake)
    sha, error = journal.measure_checkout_sha()
    assert error is None
    assert sha == "a" * 40
    assert seen["argv"][:3] == ["git", "-C", str(journal._REPO_ROOT)]


def test_extra_outcome_copies_do_not_exceed_selected_count(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            *_phases(identity, nodeid, "passed"),
            *_phases(identity, nodeid, "passed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["selected_count"] == 1
    assert len(verdict["terminals"]) == 1
    assert verdict["tests_passed"] is True


def test_two_selected_copies_with_two_phase_sets_are_complete(tmp_path: Path) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid, nodeid]),
            *_phases(identity, nodeid, "passed"),
            *_phases(identity, nodeid, "passed"),
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["selected_count"] == 2
    assert len(verdict["terminals"]) == 2
    assert verdict["tests_passed"] is True


def test_intact_controller_without_collection_uses_worker_list(
    tmp_path: Path,
) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker = _identity(role="worker", worker_id="gw0")
    nodeid = "test_sample.py::test_a"
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(controller),
                {"event": "session_finish", "identity": controller, "exitstatus": 0},
            ]
        ),
        name="receipt_controller.jsonl",
    )
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(worker),
                _collected(worker, [nodeid]),
                *_phases(worker, nodeid, "passed"),
                {"event": "session_finish", "identity": worker, "exitstatus": 0},
            ]
        ),
        name="receipt_worker.jsonl",
    )
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["selected_count"] == 1
    assert verdict["tests_passed"] is True


def test_conflicting_controller_collections_do_not_use_workers(
    tmp_path: Path,
) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker = _identity(role="worker", worker_id="gw0")
    node_a = "test_sample.py::test_a"
    node_b = "test_sample.py::test_b"
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(controller),
                _collected(controller, [node_a]),
                _collected(controller, [node_b]),
                {"event": "session_finish", "identity": controller, "exitstatus": 0},
            ]
        ),
        name="receipt_controller.jsonl",
    )
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(worker),
                _collected(worker, [node_a, node_b]),
                *_phases(worker, node_a, "passed"),
                *_phases(worker, node_b, "passed"),
                {"event": "session_finish", "identity": worker, "exitstatus": 0},
            ]
        ),
        name="receipt_worker.jsonl",
    )
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert verdict["selected_count"] == 0
    assert "conflicting_collection" in verdict["reasons"]
    assert verdict["tests_passed"] is None


def test_forwarded_origin_with_worker_receipt_is_complete(tmp_path: Path) -> None:
    controller = _identity(role="controller", worker_id="controller")
    worker = _identity(role="worker", worker_id="gw0")
    nodeid = "test_sample.py::test_a"
    controller_outcomes = _phases(controller, nodeid, "passed")
    for event in controller_outcomes:
        event["origin_worker"] = "gw0"
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(controller),
                _collected(controller, [nodeid]),
                *controller_outcomes,
                {"event": "session_finish", "identity": controller, "exitstatus": 0},
            ]
        ),
        name="receipt_controller.jsonl",
    )
    _write_receipt(
        tmp_path,
        _finalized(
            [
                _start(worker),
                _collected(worker, [nodeid]),
                *_phases(worker, nodeid, "passed"),
                {"event": "session_finish", "identity": worker, "exitstatus": 0},
            ]
        ),
        name="receipt_worker.jsonl",
    )
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["selected_count"] == 1
    assert len(verdict["terminals"]) == 1
    assert verdict["terminals"][0]["worker_id"] == "gw0"
    assert verdict["tests_passed"] is True


def test_utf8_error_inside_a_complete_receipt_is_unknown(tmp_path: Path) -> None:
    events = _controller_pass(
        ["test_sample.py::test_a"],
        {"test_sample.py::test_a": "passed"},
    )
    _write_receipt(tmp_path, events)
    path = tmp_path / "receipt_test.jsonl"
    raw = bytearray(path.read_bytes())
    marker = b"serial-coverage"
    index = raw.find(marker)
    assert index >= 0
    raw[index] = 255
    path.write_bytes(bytes(raw))
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert verdict["tests_passed"] is None


@pytest.mark.parametrize("bad_retry", ["unknown", "0", True, -1])
def test_bad_retry_index_is_unknown(tmp_path: Path, bad_retry: Any) -> None:
    identity = _identity(role="controller", worker_id="controller")
    nodeid = "test_sample.py::test_a"
    phases = _phases(identity, nodeid, "passed")
    phases[0]["retry_index"] = bad_retry
    events = _finalized(
        [
            _start(identity),
            _collected(identity, [nodeid]),
            *phases,
            {"event": "session_finish", "identity": identity, "exitstatus": 0},
        ]
    )
    _write_receipt(tmp_path, events)
    verdict = reconcile_pass(_load(tmp_path), pass_name="parallel")
    assert verdict["status"] == "unknown"
    assert verdict["tests_passed"] is None


def test_checkout_sha_from_another_directory_uses_repository_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    monkeypatch.chdir(tmp_path)
    sha, error = journal.measure_checkout_sha()
    assert error is None
    expected = subprocess.run(
        ["git", "-C", str(journal._REPO_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert sha == expected


def test_redaction_key_is_process_local_until_publish() -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    env_name = journal._REDACTION_KEY_ENV
    previous_env = os.environ.get(env_name)
    previous_key = journal._REDACTION_KEY
    os.environ.pop(env_name, None)
    journal._REDACTION_KEY = None
    try:
        os.environ[env_name] = "x" * 16
        first = journal.ensure_redaction_key()
        assert len(first) >= journal._REDACTION_KEY_MIN_LENGTH
        assert os.environ[env_name] == "x" * 16
        assert journal.ensure_redaction_key() == first
        journal.publish_redaction_key()
        assert os.environ[env_name] == first
    finally:
        journal._REDACTION_KEY = previous_key
        if previous_env is None:
            os.environ.pop(env_name, None)
        else:
            os.environ[env_name] = previous_env


def test_safe_env_excludes_the_redaction_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    key = "ab" * 32
    previous = journal._REDACTION_KEY
    monkeypatch.setenv(journal._REDACTION_KEY_ENV, key)
    try:
        safe = journal._safe_env(())
    finally:
        journal._REDACTION_KEY = previous
    assert journal._REDACTION_KEY_ENV not in safe
    assert all(key not in value for value in safe.values())


@pytest.mark.parametrize("payload", [b"{", b"[1]", b'"text"', b"\xff"])
def test_malformed_stored_verdict_is_a_controlled_exit(
    tmp_path: Path, payload: bytes
) -> None:
    from scripts.engineering.ci.pytest_event_journal import (
        JOURNAL_COMPLETENESS_EXIT,
        verify_directory,
    )

    journal = tmp_path / "journal"
    journal.mkdir()
    (journal / "journal-verdict.json").write_bytes(payload)
    assert verify_directory(journal) == JOURNAL_COMPLETENESS_EXIT


def test_late_session_finish_failure_is_not_complete(tmp_path: Path) -> None:
    plugin = tmp_path / "late_session_hook.py"
    plugin.write_text(
        "import pytest\n\n"
        "@pytest.hookimpl(trylast=True)\n"
        "def pytest_sessionfinish(session, exitstatus):\n"
        "    raise RuntimeError('late session finish')\n",
        encoding="utf-8",
    )
    result = _run_journal(
        tmp_path / "run",
        "def test_ok():\n    pass\n",
        ["-p", "late_session_hook"],
        {"PYTHONPATH": os.pathsep.join((str(tmp_path), str(_ROOT)))},
    )
    assert result.returncode != 0
    verdict = _live_verdict(tmp_path / "run")
    assert verdict["status"] != "complete"
    assert verdict["tests_passed"] is not True
    blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "run" / "journal").glob("*.jsonl")
    )
    assert '"hook_error": true' in blob


def test_late_session_finish_status_change_is_not_complete(tmp_path: Path) -> None:
    plugin = tmp_path / "late_session_hook.py"
    plugin.write_text(
        "import pytest\n\n"
        "@pytest.hookimpl(trylast=True)\n"
        "def pytest_sessionfinish(session, exitstatus):\n"
        "    session.exitstatus = 1\n",
        encoding="utf-8",
    )
    result = _run_journal(
        tmp_path / "run",
        "def test_ok():\n    pass\n",
        ["-p", "late_session_hook"],
        {"PYTHONPATH": os.pathsep.join((str(tmp_path), str(_ROOT)))},
    )
    assert result.returncode != 0
    verdict = _live_verdict(tmp_path / "run")
    assert verdict["status"] != "complete"
    assert verdict["tests_passed"] is not True

