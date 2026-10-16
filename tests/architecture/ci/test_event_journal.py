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
        *_phases(identity, nodeids[1], "failed"),
        _outcome(identity, nodeids[2], "setup", "passed"),
        _outcome(identity, nodeids[2], "call", "passed"),
        _outcome(identity, nodeids[2], "teardown", "teardown_error"),
        _outcome(identity, nodeids[3], "setup", "skipped"),
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
    from scripts.engineering.ci.pytest_event_journal import _redaction_token

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
    assert _redaction_token(first) in blob
    assert _redaction_token(second) in blob
    assert _redaction_token(first) != _redaction_token(second)


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

    def _deny(path: Path, payload: dict[str, Any]) -> None:
        _ = (path, payload)
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
    passed = run_pytest_resilient._finish_run(
        reports_dir=reports,
        summary_lines=[],
        journal_dir=journal_dir,
        executed_passes=["parallel"],
        test_rc=0,
    )
    incomplete = run_pytest_resilient._finish_run(
        reports_dir=reports,
        summary_lines=[],
        journal_dir=tmp_path / "empty-journal",
        executed_passes=["parallel"],
        test_rc=0,
    )
    assert failed == 1
    assert passed == 4
    assert incomplete == 4


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
    assert "timeout-minutes: 20" in serial
    assert "--parallel-timeout-seconds 840" in serial
    assert "--no-fallback" in serial
    assert "pytest-event-journal-serial-coverage" in serial
    assert "if: ${{ always() && !cancelled() }}" in serial
