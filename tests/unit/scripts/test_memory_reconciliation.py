"""Crash, stale-plan and single-use recovery controls on disposable owner state."""

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ai.mcp import memory_reconciliation as recovery

pytestmark = pytest.mark.unit


@pytest.fixture
def fixture(tmp_path):
    locks = {}
    stamp = {"sha256": "0" * 64, "sequence": 0}

    def read(path, **_):
        return json.loads(path.read_bytes()) if path.exists() else None

    def write(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def lock(path):
        return locks.setdefault(str(path), threading.RLock())

    def identity(record, role):
        if record is None or role + "_pid" not in record:
            return "ABSENT"
        if record.get(role + "_state") == "UNKNOWN":
            return "UNKNOWN"
        return "ALIVE" if record[role + "_pid"] == os.getpid() else "DEAD"

    entry = {"id": "profile", "state": str(tmp_path)}
    value = {"profile": {"graph": str(tmp_path / "graph.json")}}
    state = SimpleNamespace(
        read=read, write=write, identity=identity, graph_stamp=lambda _: dict(stamp)
    )
    core = SimpleNamespace(
        LifetimeLock=lock, process_birth=lambda pid: 42 if pid == os.getpid() else None
    )
    owner = SimpleNamespace(state=state, core=core, HERE=tmp_path / "immutable-v2")

    def legacy(*_, **__):
        work = read(tmp_path / "work.json")
        status = read(tmp_path / "status.json")
        return (
            "SAFE_IDLE_RESTART"
            if work["phase"] == "idle" and work["generation"] == status["generation"]
            else "BLOCK_UNKNOWN_OUTCOME"
        )

    owner.legacy_recovery = legacy
    for name, record in {
        "profile": value,
        "active": {"pins": "v2"},
        "blocked": {"decision": "BLOCK_UNKNOWN_OUTCOME"},
        "status": {"generation": "a" * 32, "owner_pid": 123456, "owner_birth": 1},
        "work": {
            "schema": 2,
            "profile": "profile",
            "generation": "a" * 32,
            "phase": "starting",
            "mutating": False,
            "accepted_count": 0,
            "graph": stamp,
        },
    }.items():
        write(tmp_path / (name + ".json"), record)
    return owner, entry, value, stamp


def test_complete_recovery_lifecycle_and_ordinary_restart(fixture):
    owner, entry, value, stamp = fixture
    directory = Path(entry["state"])
    original = (directory / "blocked.json").read_bytes()
    proposed = recovery.plan(owner, entry, value)
    assert proposed["eligible"]
    recovery.apply(owner, entry, value, proposed)
    assert not recovery.blocked(owner, entry)
    assert recovery.decision(owner, entry, value) == "SAFE_RECONCILED_START"
    owner.state.write(
        directory / "owner-launch.json", {"owner_pid": os.getpid(), "owner_birth": 42}
    )
    generation = recovery.launch_generation(owner, entry, value)
    assert generation == proposed["new_generation"]
    owner.state.write(
        directory / "status.json",
        {"generation": generation, "owner_pid": os.getpid(), "owner_birth": 42},
    )
    owner.state.write(
        directory / "work.json",
        {
            "schema": 2,
            "profile": "profile",
            "generation": generation,
            "phase": "idle",
            "accepted_count": 0,
            "graph": stamp,
        },
    )
    recovery.observe(owner, entry, value, generation)
    assert not recovery.blocked(owner, entry)  # ensure returns the existing live owner.
    recovery.observe(owner, entry, value, generation, idle=True)
    assert recovery.coordination(owner, entry)["history"][-1]["phase"] == "IDLE"
    assert recovery.decision(owner, entry, value) == "SAFE_IDLE_RESTART"
    assert (directory / "blocked.json").read_bytes() == original


def test_repeated_apply_is_rejected_without_changes(fixture):
    owner, entry, value, _ = fixture
    proposed = recovery.plan(owner, entry, value)
    recovery.apply(owner, entry, value, proposed)
    path = Path(entry["state"]) / recovery.COORDINATION
    before = path.read_bytes()
    with pytest.raises(ValueError, match="already applied"):
        recovery.apply(owner, entry, value, proposed)
    assert path.read_bytes() == before


def test_stale_plan_never_changes_coordination(fixture):
    owner, entry, value, stamp = fixture
    proposed = recovery.plan(owner, entry, value)
    stamp["sequence"] = 1
    with pytest.raises(ValueError, match="Stale"):
        recovery.apply(owner, entry, value, proposed)
    assert not (Path(entry["state"]) / recovery.COORDINATION).exists()


def test_crash_before_commit_preserves_block_and_can_retry(fixture, monkeypatch):
    owner, entry, value, _ = fixture
    proposed = recovery.plan(owner, entry, value)
    original = owner.state.write

    def fail(*_):
        raise OSError("fixture power loss before atomic publish")

    monkeypatch.setattr(owner.state, "write", fail)
    with pytest.raises(OSError):
        recovery.apply(owner, entry, value, proposed)
    assert recovery.blocked(owner, entry)
    monkeypatch.setattr(owner.state, "write", original)
    recovery.apply(owner, entry, value, proposed)


def test_crash_after_launch_consumption_never_reuses_grant(fixture):
    owner, entry, value, _ = fixture
    proposed = recovery.plan(owner, entry, value)
    recovery.apply(owner, entry, value, proposed)
    recovery.launch_generation(owner, entry, value)
    assert (
        recovery.decision(owner, entry, value) == "BLOCK_RECONCILED_LAUNCH_INTERRUPTED"
    )
    recovery.record_block(owner, entry, "BLOCK_UNKNOWN_OUTCOME")
    again = recovery.plan(owner, entry, value)
    assert not again["eligible"] and again["block_id"] != proposed["block_id"]


def test_concurrent_apply_commits_exactly_one_grant(fixture):
    owner, entry, value, _ = fixture
    proposed = recovery.plan(owner, entry, value)

    def attempt(_):
        try:
            recovery.apply(owner, entry, value, proposed)
            return "committed"
        except ValueError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["committed", "refused"]
    assert len(recovery.coordination(owner, entry)["history"]) == 1


@pytest.mark.parametrize(
    "phase,count", [("busy", 1), ("uncertain", 1), ("starting", 1)]
)
def test_unknown_operation_is_not_replayed_even_with_valid_graph(fixture, phase, count):
    owner, entry, value, stamp = fixture
    path = Path(entry["state"]) / "work.json"
    work = owner.state.read(path)
    work.update(phase=phase, accepted_count=count, graph=stamp)
    owner.state.write(path, work)
    before = path.read_bytes()
    proposed = recovery.plan(owner, entry, value)
    assert not proposed["eligible"]
    with pytest.raises(ValueError):
        recovery.apply(owner, entry, value, proposed)
    assert path.read_bytes() == before


def test_legacy_starting_without_correlation_remains_blocked(fixture):
    owner, entry, value, _ = fixture
    path = Path(entry["state"]) / "work.json"
    work = owner.state.read(path)
    del work["schema"]
    del work["accepted_count"]
    owner.state.write(path, work)
    assert (
        recovery.plan(owner, entry, value)["reason"]
        == "BLOCK_INSUFFICIENT_LEGACY_EVIDENCE"
    )


def test_unknown_process_identity_is_not_permission_to_recover(fixture):
    owner, entry, value, _ = fixture
    path = Path(entry["state"]) / "status.json"
    status = owner.state.read(path)
    status["owner_state"] = "UNKNOWN"
    owner.state.write(path, status)
    assert (
        recovery.plan(owner, entry, value)["reason"] == "BLOCK_PROCESS_IDENTITY_UNKNOWN"
    )


@pytest.mark.parametrize(
    "field,value", [("old_generation", "b" * 32), ("eligible", False)]
)
def test_changed_reviewed_plan_fields_do_not_authorize_a_grant(fixture, field, value):
    owner, entry, descriptor, _ = fixture
    proposed = recovery.plan(owner, entry, descriptor)
    proposed[field] = value
    proposed["plan_id"] = recovery.digest(
        {k: v for k, v in proposed.items() if k != "plan_id"}
    )
    with pytest.raises(ValueError, match="Stale"):
        recovery.apply(owner, entry, descriptor, proposed)
    assert not (Path(entry["state"]) / recovery.COORDINATION).exists()


def test_successor_cannot_reuse_the_current_generation(fixture):
    owner, entry, value, _ = fixture
    proposed = recovery.plan(owner, entry, value)
    proposed["new_generation"] = proposed["old_generation"]
    proposed["plan_id"] = recovery.digest(
        {k: v for k, v in proposed.items() if k != "plan_id"}
    )
    with pytest.raises(ValueError, match="successor"):
        recovery.apply(owner, entry, value, proposed)


def test_successor_cannot_reuse_a_historical_generation(fixture):
    owner, entry, value, _ = fixture
    directory = Path(entry["state"])
    owner.state.write(
        directory / recovery.COORDINATION,
        {
            "schema": 2,
            "active_block": {"id": "new-block"},
            "history": [
                {
                    "plan_id": "historical-plan",
                    "block_id": "old-block",
                    "phase": "IDLE",
                    "old_generation": "b" * 32,
                    "new_generation": "c" * 32,
                }
            ],
        },
    )
    proposed = recovery.plan(owner, entry, value)
    assert proposed["eligible"]
    proposed["new_generation"] = "c" * 32
    proposed["plan_id"] = recovery.digest(
        {k: v for k, v in proposed.items() if k != "plan_id"}
    )
    with pytest.raises(ValueError, match="successor"):
        recovery.apply(owner, entry, value, proposed)


@pytest.mark.parametrize("counter", [False, -1, "0"])
def test_invalid_request_counter_is_not_a_startup_proof(fixture, counter):
    owner, entry, value, _ = fixture
    path = Path(entry["state"]) / "work.json"
    work = owner.state.read(path)
    work["accepted_count"] = counter
    owner.state.write(path, work)
    assert not recovery.plan(owner, entry, value)["eligible"]


def test_missing_owner_identity_is_unknown_instead_of_absent(fixture):
    owner, entry, value, _ = fixture
    path = Path(entry["state"]) / "status.json"
    previous = owner.state.read(path)
    del previous["owner_pid"]
    del previous["owner_birth"]
    owner.state.write(path, previous)
    assert (
        recovery.plan(owner, entry, value)["reason"] == "BLOCK_PROCESS_IDENTITY_UNKNOWN"
    )


def test_generation_waits_for_transition_lock_before_consuming_a_grant(
    fixture, monkeypatch
):
    owner, entry, value, _ = fixture
    proposed = recovery.plan(owner, entry, value)
    recovery.apply(owner, entry, value, proposed)
    original_lock = owner.core.LifetimeLock
    attempts = []

    def temporarily_busy(path):
        attempts.append(path)
        if len(attempts) <= 2:
            raise RuntimeError("Another owner holds the lifetime lock")
        return original_lock(path)

    monkeypatch.setattr(owner.core, "LifetimeLock", temporarily_busy)
    generation = recovery.launch_generation(owner, entry, value)
    assert generation == proposed["new_generation"]
    assert len(attempts) == 3
    assert recovery.coordination(owner, entry)["history"][-1]["phase"] == "LAUNCHING"


def test_lock_deadline_does_not_consume_the_recovery_grant(fixture, monkeypatch):
    owner, entry, value, _ = fixture
    proposed = recovery.plan(owner, entry, value)
    recovery.apply(owner, entry, value, proposed)
    path = Path(entry["state"]) / recovery.COORDINATION
    before = path.read_bytes()
    ticks = iter([0, 6])
    monkeypatch.setattr(recovery.time, "monotonic", lambda: next(ticks))

    def busy(_):
        raise RuntimeError("Another owner holds the lifetime lock")

    monkeypatch.setattr(owner.core, "LifetimeLock", busy)
    with pytest.raises(RuntimeError, match="Another owner"):
        recovery.launch_generation(owner, entry, value)
    assert path.read_bytes() == before


def test_exception_inside_a_transition_is_never_replayed(fixture):
    owner, entry, _, _ = fixture
    attempts = []
    with pytest.raises(RuntimeError, match="Another owner"):
        with recovery._transition_lock(owner, Path(entry["state"])):
            attempts.append(True)
            raise RuntimeError("Another owner holds the lifetime lock")
    assert attempts == [True]


@pytest.mark.parametrize("mutating", [True, None])
def test_idle_receipt_requires_an_explicit_nonmutating_flag(fixture, mutating):
    owner, entry, value, _ = fixture
    path = Path(entry["state"]) / "work.json"
    work = owner.state.read(path)
    work.update(
        phase="idle",
        accepted_count=1,
        request_id="completed-request",
        mutating=mutating,
    )
    owner.state.write(path, work)
    assert not recovery.plan(owner, entry, value)["eligible"]
    work["mutating"] = False
    owner.state.write(path, work)
    assert recovery.plan(owner, entry, value)["reason"] == "PROVEN_IDLE_RECEIPT"


def test_interrupted_successor_has_a_new_incident_and_cannot_reuse_the_old_grant(
    fixture,
):
    owner, entry, value, stamp = fixture
    directory = Path(entry["state"])
    owner.state.write(directory / "blocked.json", None)
    recovery.record_block(owner, entry, "BLOCK_UNKNOWN_OUTCOME")
    first = recovery.plan(owner, entry, value)
    recovery.apply(owner, entry, value, first)
    generation = recovery.launch_generation(owner, entry, value)
    owner.state.write(
        directory / "status.json",
        {"generation": generation, "owner_pid": 123456, "owner_birth": 1},
    )
    owner.state.write(
        directory / "work.json",
        {
            "schema": 2,
            "profile": entry["id"],
            "generation": generation,
            "phase": "starting",
            "mutating": False,
            "accepted_count": 0,
            "request_id": None,
            "graph": stamp,
        },
    )
    assert (
        recovery.decision(owner, entry, value) == "BLOCK_RECONCILED_LAUNCH_INTERRUPTED"
    )
    second = recovery.plan(owner, entry, value)
    assert second["eligible"] and second["block_id"].startswith("interrupted-")
    assert second["block_id"] != first["block_id"]
    assert second["new_generation"] not in {first["old_generation"], generation}
    with pytest.raises(ValueError, match="already applied"):
        recovery.apply(owner, entry, value, first)
    recovery.apply(owner, entry, value, second)
    assert recovery.decision(owner, entry, value) == "SAFE_RECONCILED_START"
    assert len(recovery.coordination(owner, entry)["history"]) == 2


def test_missing_successor_receipt_cannot_invent_an_incident(fixture):
    owner, entry, value, _ = fixture
    directory = Path(entry["state"])
    owner.state.write(directory / "blocked.json", None)
    recovery.record_block(owner, entry, "BLOCK_UNKNOWN_OUTCOME")
    recovery.apply(owner, entry, value, recovery.plan(owner, entry, value))
    generation = recovery.launch_generation(owner, entry, value)
    owner.state.write(
        directory / "status.json",
        {"generation": generation, "owner_pid": 123456, "owner_birth": 1},
    )
    proposed = recovery.plan(owner, entry, value)
    assert not proposed["eligible"] and proposed["block_id"] is None
