"""Private snapshot publication and crashed conversion worker recovery."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.ai.mcp import safe_markdownify as markdownify

pytestmark = pytest.mark.unit


def test_partial_snapshot_write_is_cleaned_without_creating_a_worker(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        markdownify,
        "core",
        SimpleNamespace(
            STATE=tmp_path,
            Job=lambda: pytest.fail("worker created after failed snapshot"),
            process_birth=lambda _: 42,
            write_json=lambda path, value: path.write_text(
                json.dumps(value), encoding="utf-8"
            ),
        ),
    )
    original = markdownify.Path.write_bytes

    def partial(path, value):
        original(path, value[:1])
        raise OSError("disk full")

    monkeypatch.setattr(markdownify.Path, "write_bytes", partial)
    with pytest.raises(OSError, match="disk full"):
        markdownify._convert_bytes({"converter": "unused"}, ".pdf", b"synthetic input")
    assert list(tmp_path.iterdir()) == []


def test_worker_attachment_failure_reaps_only_the_child_created_here(
    tmp_path, monkeypatch
):
    owned, child = Mock(), Mock(pid=77)
    owned.attach.side_effect = RuntimeError("job attachment failed")
    child.poll.return_value = None
    monkeypatch.setattr(
        markdownify,
        "core",
        SimpleNamespace(
            STATE=tmp_path,
            Job=lambda: owned,
            WINDOWS_HIDE=0,
            process_birth=lambda _: 42,
            write_json=lambda path, value: path.write_text(
                json.dumps(value), encoding="utf-8"
            ),
        ),
    )
    monkeypatch.setattr(markdownify.subprocess, "Popen", lambda *args, **kwargs: child)
    with pytest.raises(RuntimeError, match="attachment"):
        markdownify._convert_bytes(
            {"converter": "fixture-converter"}, ".html", b"synthetic"
        )
    owned.close.assert_called_once()
    child.terminate.assert_called_once()
    child.wait.assert_called_once_with(timeout=markdownify.WORKER_CLEANUP_SECONDS)
    assert list(tmp_path.iterdir()) == []


def test_conversion_reclaims_a_deferred_snapshot_only_after_child_exits(
    tmp_path, monkeypatch
):
    owned, child = Mock(), Mock(pid=77)
    child.poll.return_value = None
    child.wait.side_effect = [
        markdownify.subprocess.TimeoutExpired("fixture", 90),
        markdownify.subprocess.TimeoutExpired("fixture", 10),
    ]
    current_birth = [42]
    monkeypatch.setattr(
        markdownify,
        "core",
        SimpleNamespace(
            STATE=tmp_path,
            Job=lambda: owned,
            WINDOWS_HIDE=0,
            process_birth=lambda _: current_birth[0],
            write_json=lambda path, data: path.write_text(
                json.dumps(data), encoding="utf-8"
            ),
            read_json=lambda path: json.loads(path.read_bytes()),
        ),
    )
    monkeypatch.setattr(
        markdownify, "scope", SimpleNamespace(physical=lambda path, **_: path)
    )
    monkeypatch.setattr(
        markdownify,
        "psutil",
        SimpleNamespace(pid_exists=lambda _: current_birth[0] is not None),
    )
    monkeypatch.setattr(markdownify.subprocess, "Popen", lambda *args, **kwargs: child)
    with pytest.raises(markdownify.subprocess.TimeoutExpired):
        markdownify._convert_bytes(
            {"converter": "fixture-converter"}, ".html", b"synthetic"
        )
    [job] = tmp_path.iterdir()
    assert (job / markdownify.PENDING_CLEANUP).is_file()
    with pytest.raises(PermissionError, match="remains pending"):
        markdownify._retry_pending_jobs()
    assert (job / "input.html").is_file()
    current_birth[0] = None
    markdownify._retry_pending_jobs()
    assert not job.exists()


@pytest.mark.parametrize("observed_birth", [None, 42])
def test_pending_worker_cannot_accumulate_more_document_snapshots(
    tmp_path, monkeypatch, observed_birth
):
    original = markdownify.subprocess.TimeoutExpired("synthetic", 90)
    child, owned = Mock(pid=77), Mock()
    child.poll.return_value = None
    child.wait.side_effect = [
        original,
        markdownify.subprocess.TimeoutExpired("synthetic", 10),
    ]
    current = [42]
    monkeypatch.setattr(
        markdownify,
        "core",
        SimpleNamespace(
            STATE=tmp_path,
            Job=lambda: owned,
            WINDOWS_HIDE=0,
            process_birth=lambda _: current[0],
            write_json=lambda path, value: path.write_text(
                json.dumps(value), encoding="utf-8"
            ),
            read_json=lambda path: json.loads(path.read_bytes()),
        ),
    )
    monkeypatch.setattr(
        markdownify, "psutil", SimpleNamespace(pid_exists=lambda _: True)
    )
    start = Mock(return_value=child)
    monkeypatch.setattr(markdownify.subprocess, "Popen", start)
    with pytest.raises(markdownify.subprocess.TimeoutExpired) as error:
        markdownify._convert_bytes(
            {"converter": "fixture"}, ".html", b"synthetic document"
        )
    assert error.value is original
    [job] = tmp_path.iterdir()
    before = {p.name: p.read_bytes() for p in job.iterdir()}
    current[0] = observed_birth
    with pytest.raises(PermissionError, match="remains pending"):
        markdownify._convert_bytes({"converter": "fixture"}, ".html", b"next document")
    assert {p.name: p.read_bytes() for p in job.iterdir()} == before
    assert list(tmp_path.iterdir()) == [job]
    start.assert_called_once()
    child.terminate.assert_called_once()
    current[0] = 43
    sentinel = tmp_path / "foreign-process-data"
    sentinel.write_bytes(b"preserved")
    markdownify._retry_pending_jobs()
    assert not job.exists() and sentinel.read_bytes() == b"preserved"
    child.terminate.assert_called_once()


@pytest.mark.parametrize(
    "change",
    [
        "missing_identity",
        "job_not_closed",
        "unknown_file",
        "missing_marker",
        "linked_file",
    ],
)
def test_unqualified_cleanup_records_preserve_document_and_foreign_data(
    tmp_path, monkeypatch, change
):
    import os

    job = tmp_path / ("job-" + "a" * 32)
    job.mkdir()
    (job / "input.html").write_bytes(b"synthetic document")
    record = {
        "schema": 1,
        "job": job.name,
        "snapshot": "input.html",
        "worker_pid": 77,
        "worker_birth": 1,
        "job_closed": True,
    }
    if change == "missing_identity":
        record.pop("worker_pid")
    if change == "job_not_closed":
        record["job_closed"] = False
    if change == "unknown_file":
        (job / "unowned.txt").write_bytes(b"preserved")
    if change == "linked_file":
        os.link(job / "input.html", tmp_path / "foreign-link")
    if change != "missing_marker":
        (job / markdownify.PENDING_CLEANUP).write_text(
            json.dumps(record), encoding="utf-8"
        )
    before = {p.name: p.read_bytes() for p in job.iterdir()}
    monkeypatch.setattr(
        markdownify,
        "core",
        SimpleNamespace(
            STATE=tmp_path,
            process_birth=lambda _: 2,
            read_json=lambda path: json.loads(path.read_bytes()),
            write_json=lambda *args: pytest.fail("Unqualified cleanup wrote state"),
        ),
    )
    with pytest.raises(PermissionError):
        markdownify._retry_pending_jobs()
    assert {p.name: p.read_bytes() for p in job.iterdir()} == before


def _worker_fixture(tmp_path, monkeypatch, *, owner_state="DEAD", worker_state="DEAD"):
    import os

    runner = os.getpid()
    owner_pid, worker_pid = runner + 1, runner + 2
    states = {runner: "ALIVE", owner_pid: owner_state, worker_pid: worker_state}
    assert set(states.values()).issubset({"ALIVE", "DEAD", "UNKNOWN"})
    core = SimpleNamespace(
        STATE=tmp_path,
        owner_pid=owner_pid,
        worker_pid=worker_pid,
        process_birth=lambda pid: 42 if states.get(pid) == "ALIVE" else None,
        read_json=lambda path: json.loads(path.read_bytes()),
        write_json=lambda path, value: path.write_text(
            json.dumps(value), encoding="utf-8"
        ),
    )
    monkeypatch.setattr(markdownify, "core", core)
    monkeypatch.setattr(
        markdownify,
        "psutil",
        SimpleNamespace(pid_exists=lambda pid: states.get(pid) in {"ALIVE", "UNKNOWN"}),
    )
    return core


@pytest.mark.parametrize("phase", ["PREPARED", "SPAWNING", "RUNNING", "CLEANUP"])
@pytest.mark.parametrize("runner_pid", [77, 78])
def test_crashed_worker_jobs_are_reclaimed_from_durable_phases_only(
    tmp_path, monkeypatch, phase, runner_pid
):
    with monkeypatch.context() as patch:
        patch.setattr(markdownify.os, "getpid", lambda: runner_pid)
        core = _worker_fixture(tmp_path, patch)
        job = tmp_path / ("job-" + "b" * 32)
        job.mkdir()
        snapshot = job / "input.html"
        snapshot.write_bytes(b"synthetic document")
        record = {
            "schema": 2,
            "job": job.name,
            "snapshot": snapshot.name,
            "owner_pid": core.owner_pid,
            "owner_birth": 42,
            "worker_pid": None
            if phase in {"PREPARED", "SPAWNING"}
            else core.worker_pid,
            "worker_birth": None if phase in {"PREPARED", "SPAWNING"} else 42,
            "job_closed": False,
            "phase": phase,
        }
        core.write_json(job / markdownify.PENDING_CLEANUP, record)
        foreign = tmp_path / "foreign"
        foreign.write_bytes(b"preserved")
        markdownify._retry_pending_jobs()
        assert not job.exists() and foreign.read_bytes() == b"preserved"


@pytest.mark.parametrize("phase", ["PREPARED", "SPAWNING", "RUNNING", "CLEANUP"])
@pytest.mark.parametrize("unknown", [False, True])
def test_live_or_unknown_worker_journal_is_retained(
    tmp_path, monkeypatch, phase, unknown
):
    identity = "UNKNOWN" if unknown else "ALIVE"
    core = _worker_fixture(
        tmp_path, monkeypatch, owner_state=identity, worker_state=identity
    )
    job = tmp_path / ("job-" + "b" * 32)
    job.mkdir()
    snapshot = job / "input.html"
    snapshot.write_bytes(b"synthetic document")
    record = {
        "schema": 2,
        "job": job.name,
        "snapshot": snapshot.name,
        "owner_pid": core.owner_pid,
        "owner_birth": 42,
        "worker_pid": None if phase in {"PREPARED", "SPAWNING"} else core.worker_pid,
        "worker_birth": None if phase in {"PREPARED", "SPAWNING"} else 42,
        "job_closed": False,
        "phase": phase,
    }
    core.write_json(job / markdownify.PENDING_CLEANUP, record)
    before = {path.name: path.read_bytes() for path in job.iterdir()}
    with pytest.raises(PermissionError, match="remains pending"):
        markdownify._retry_pending_jobs()
    assert {path.name: path.read_bytes() for path in job.iterdir()} == before


def test_job_journal_exists_before_the_first_document_write(tmp_path, monkeypatch):
    core = _worker_fixture(tmp_path, monkeypatch)
    original = Path.write_bytes
    observed = []

    def write(path, raw):
        record = core.read_json(path.parent / markdownify.PENDING_CLEANUP)
        observed.append(record["phase"])
        assert record["worker_pid"] is None
        original(path, raw)
        raise OSError("injected document write failure")

    core.Job = lambda: pytest.fail("Worker was launched after snapshot failure")
    monkeypatch.setattr(Path, "write_bytes", write)
    with pytest.raises(OSError, match="document write"):
        markdownify._convert_bytes({"converter": "unused"}, ".html", b"synthetic")
    assert observed == ["PREPARED"] and list(tmp_path.iterdir()) == []


def test_worker_execution_and_cleanup_reserve_time_for_the_next_rpc(
    tmp_path, monkeypatch
):
    core = _worker_fixture(
        tmp_path, monkeypatch, owner_state="ALIVE", worker_state="ALIVE"
    )
    clock, waits = [0.0], []
    child, job = Mock(pid=core.worker_pid), Mock()
    child.poll.return_value = None
    core.Job = lambda: job
    core.WINDOWS_HIDE = 0

    def wait(*, timeout):
        waits.append(timeout)
        clock[0] += timeout
        raise markdownify.subprocess.TimeoutExpired("synthetic", timeout)

    child.wait.side_effect = wait

    def release(_nonce):
        [directory] = tmp_path.iterdir()
        record = core.read_json(directory / markdownify.PENDING_CLEANUP)
        assert record["phase"] == "RUNNING" and record["worker_pid"] == child.pid

    child.stdin.write.side_effect = release
    retry = markdownify._retry_pending_jobs

    def prepare():
        retry()
        clock[0] += 11  # Validation/recovery consumes the same execution budget.

    monkeypatch.setattr(markdownify, "_retry_pending_jobs", prepare)
    monkeypatch.setattr(markdownify.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(markdownify.subprocess, "Popen", lambda *args, **kwargs: child)
    with pytest.raises(markdownify.subprocess.TimeoutExpired):
        markdownify._convert_bytes({"converter": "fixture"}, ".html", b"synthetic")
    assert waits == [
        markdownify.WORKER_SECONDS - 11,
        markdownify.WORKER_CLEANUP_SECONDS,
    ]
    assert clock[0] < 100 - 10
    [directory] = tmp_path.iterdir()
    assert core.read_json(directory / markdownify.PENDING_CLEANUP)["phase"] == "CLEANUP"
    child.stdin.write.assert_called_once()


def test_interrupted_atomic_job_publication_before_input_does_not_block_recovery(
    tmp_path, monkeypatch
):
    core = _worker_fixture(tmp_path, monkeypatch)
    job = tmp_path / ("job-" + "c" * 32)
    job.mkdir()
    (job / (markdownify.PENDING_CLEANUP + "." + "a" * 32 + ".pending")).write_bytes(
        b'{"partial":'
    )
    markdownify._retry_pending_jobs()
    assert not job.exists()


@pytest.mark.parametrize("known_temporary", [True, False])
def test_worker_recovery_recognizes_only_its_own_atomic_record_namespace(
    tmp_path, monkeypatch, known_temporary
):
    core = _worker_fixture(tmp_path, monkeypatch)
    job = tmp_path / ("job-" + "c" * 32)
    job.mkdir()
    (job / "input.html").write_bytes(b"synthetic document")
    record = {
        "schema": 2,
        "job": job.name,
        "snapshot": "input.html",
        "owner_pid": core.owner_pid,
        "owner_birth": 42,
        "worker_pid": core.worker_pid,
        "worker_birth": 42,
        "job_closed": True,
        "phase": "CLEANUP",
    }
    core.write_json(job / markdownify.PENDING_CLEANUP, record)
    name = (
        markdownify.PENDING_CLEANUP
        + "."
        + ("a" * 32 if known_temporary else "foreign")
        + ".pending"
    )
    (job / name).write_bytes(b"partial control record")
    before = {path.name: path.read_bytes() for path in job.iterdir()}
    if known_temporary:
        markdownify._retry_pending_jobs()
        assert not job.exists()
    else:
        with pytest.raises(PermissionError, match="unowned files"):
            markdownify._retry_pending_jobs()
        assert {path.name: path.read_bytes() for path in job.iterdir()} == before


@pytest.mark.parametrize("interruption", range(1, 5))
def test_interrupted_erasure_retains_the_journal_until_all_documents_are_gone(
    tmp_path, monkeypatch, interruption
):
    core = _worker_fixture(tmp_path, monkeypatch)
    job = tmp_path / ("job-" + "c" * 32)
    job.mkdir()
    (job / "input.html").write_bytes(b"synthetic document")
    (job / markdownify.WORKER_OUTPUT).write_bytes(b"synthetic output")
    (job / (markdownify.PENDING_CLEANUP + "." + "d" * 32 + ".pending")).write_bytes(
        b"partial control record"
    )
    core.write_json(
        job / markdownify.PENDING_CLEANUP,
        {
            "schema": 2,
            "job": job.name,
            "snapshot": "input.html",
            "owner_pid": core.owner_pid,
            "owner_birth": 42,
            "worker_pid": core.worker_pid,
            "worker_birth": 42,
            "job_closed": True,
            "phase": "CLEANUP",
        },
    )
    original = Path.unlink
    removed = []

    def interrupted(path, *args, **kwargs):
        original(path, *args, **kwargs)
        removed.append(path.name)
        if len(removed) == interruption:
            raise InterruptedError("simulated crash after unlink")

    original_iterdir = Path.iterdir

    def journal_first(path):
        entries = list(original_iterdir(path))
        if path == job:
            entries.sort(key=lambda item: item.name != markdownify.PENDING_CLEANUP)
        return iter(entries)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "iterdir", journal_first)
        patch.setattr(Path, "unlink", interrupted)
        with pytest.raises(InterruptedError):
            markdownify._erase_worker_job(job, "input.html")
    remaining = {path.name for path in job.iterdir()}
    if remaining & {"input.html", markdownify.WORKER_OUTPUT}:
        assert markdownify.PENDING_CLEANUP in remaining
    if interruption == 4:
        assert removed[-1] == markdownify.PENDING_CLEANUP
    markdownify._retry_pending_jobs()
    assert not job.exists()
