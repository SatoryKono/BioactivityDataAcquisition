"""Generation-bound recovery grants for the versioned Memory owner.

Legacy blocked/work records are retained. A graph stamp alone cannot prove an
unknown request outcome. Only a v2 startup journal with zero accepted requests,
or a complete idle receipt, can authorize a reviewed transition. No operation
is replayed by this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from contextlib import ExitStack, contextmanager
from pathlib import Path

COORDINATION = "recovery-v2.json"


@contextmanager
def _transition_lock(owner, directory):
    """Wait for bounded control-plane contention, never repeat an entered body."""
    deadline = time.monotonic() + 5
    with ExitStack() as stack:
        while True:
            try:
                stack.enter_context(
                    owner.core.LifetimeLock(directory / "transition.lock")
                )
                break
            except RuntimeError as error:
                if (
                    str(error) != "Another owner holds the lifetime lock"
                    or time.monotonic() >= deadline
                ):
                    raise
                time.sleep(0.025)
        yield


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def records(owner, entry):
    directory = Path(entry["state"])
    return {
        name: owner.state.read(directory / (name + ".json"), max_bytes=32 * 1024 * 1024)
        for name in ("profile", "active", "blocked", "status", "owner-launch", "work")
    }


def coordination(owner, entry):
    value = owner.state.read(Path(entry["state"]) / COORDINATION)
    if value is None:
        return {"schema": 2, "history": [], "active_block": None}
    if value.get("schema") != 2 or not isinstance(value.get("history"), list):
        raise ValueError("Unsupported recovery coordination format")
    return value


def process_identities(owner, observed):
    states = {
        role: owner.state.identity(observed["status"], role)
        for role in ("owner", "gateway", "backend")
    }
    states["launch"] = owner.state.identity(observed["owner-launch"], "owner")
    if observed["status"] is not None and states["owner"] == "ABSENT":
        states["owner"] = "UNKNOWN"
    if observed["owner-launch"] is not None and states["launch"] == "ABSENT":
        states["launch"] = "UNKNOWN"
    return states


def process_verdict(owner, observed, *, self_owner=False):
    states = process_identities(owner, observed)
    if "UNKNOWN" in states.values():
        return "BLOCK_PROCESS_IDENTITY_UNKNOWN"
    for record, state in (
        (observed["status"], states["owner"]),
        (observed["owner-launch"], states["launch"]),
    ):
        if state == "ALIVE" and not (self_owner and record["owner_pid"] == os.getpid()):
            return "BLOCK_OWNER_ACTIVE"
    if "ALIVE" in (states["gateway"], states["backend"]):
        return "BLOCK_SURVIVING_PROCESS"
    return None


def _interrupted_launch_block(observed, coord):
    last = coord["history"][-1] if coord["history"] else {}
    work, status = observed["work"] or {}, observed["status"] or {}
    if (
        last.get("phase") == "LAUNCHING"
        and status.get("generation") == last.get("new_generation")
        and work.get("generation") == status.get("generation")
        and work.get("schema") == 2
        and work.get("profile") == last["snapshot"]["profile"]
        and work.get("graph") == last["snapshot"]["graph"]
        and work.get("phase") == "starting"
        and type(work.get("accepted_count")) is int
        and work["accepted_count"] == 0
        and work.get("request_id") is None
        and work.get("mutating") is False
    ):
        return "interrupted-" + digest(
            {"grant": last["id"], "generation": last["new_generation"]}
        )
    return None


def block_identity(observed, coord):
    active = coord.get("active_block")
    if active:
        return active["id"]
    if coord["history"] and coord["history"][-1]["phase"] == "LAUNCHING":
        return _interrupted_launch_block(observed, coord)
    if observed["blocked"] is not None:
        return "legacy-" + digest(
            {k: observed[k] for k in ("blocked", "status", "work")}
        )
    return None


def snapshot(owner, entry, value):
    observed = records(owner, entry)
    return {
        "profile": entry["id"],
        "version": str(owner.HERE),
        "records": {name: digest(record) for name, record in observed.items()},
        "graph": owner.state.graph_stamp(value),
        "coordination": digest(coordination(owner, entry)),
    }, observed


def _receipt_verdict(bound, work, previous, coord, entry, block):
    if not block:
        return "BLOCK_NOT_BLOCKED"
    elif any(item["block_id"] == block for item in coord["history"]):
        return "BLOCK_ALREADY_RESOLVED"
    elif (
        work.get("schema") != 2
        or work.get("profile") != entry["id"]
        or work.get("generation") != previous.get("generation")
        or not isinstance(previous.get("generation"), str)
        or re.fullmatch("[0-9a-f]{32}", previous["generation"]) is None
    ):
        return "BLOCK_INSUFFICIENT_LEGACY_EVIDENCE"
    elif (
        coord["history"]
        and coord["history"][-1]["phase"] == "LAUNCHING"
        and previous.get("generation") != coord["history"][-1]["new_generation"]
    ):
        return "BLOCK_INCOMPLETE_SUCCESSOR_HISTORY"
    elif work.get("graph") != bound["graph"]:
        return "BLOCK_GRAPH_RECEIPT_MISMATCH"
    elif (
        work.get("phase") == "starting"
        and type(work.get("accepted_count")) is int
        and work["accepted_count"] == 0
        and work.get("request_id") is None
        and work.get("mutating") is False
    ):
        return "PROVEN_STARTUP_WITHOUT_REQUESTS"
    elif (
        work.get("phase") == "idle"
        and type(work.get("accepted_count")) is int
        and work["accepted_count"] >= 0
        and work.get("mutating") is False
    ):
        return "PROVEN_IDLE_RECEIPT"
    else:
        return "BLOCK_UNKNOWN_OUTCOME"


def plan(owner, entry, value):
    bound, observed = snapshot(owner, entry, value)
    coord = coordination(owner, entry)
    work, previous = observed["work"] or {}, observed["status"] or {}
    reason = process_verdict(owner, observed)
    block = block_identity(observed, coord)
    if reason is None:
        reason = _receipt_verdict(bound, work, previous, coord, entry, block)
    eligible = reason in {"PROVEN_STARTUP_WITHOUT_REQUESTS", "PROVEN_IDLE_RECEIPT"}
    result = {
        "schema": 2,
        "snapshot": bound,
        "block_id": block,
        "reason": reason,
        "eligible": eligible,
        "old_generation": previous.get("generation"),
        "new_generation": uuid.uuid4().hex if eligible else None,
    }
    result["plan_id"] = digest(result)
    return result


def identify_interrupted_launch(owner, entry, value):
    """Publish only an incident, allowing an older reconciler to plan a grant."""
    directory = Path(entry["state"])
    with _transition_lock(owner, directory):
        with owner.core.LifetimeLock(
            Path(value["profile"]["graph"]).with_name(".memory.service-owner.lock")
        ):
            coord = coordination(owner, entry)
            proposed = plan(owner, entry, value)
            if (
                coord.get("active_block") is not None
                or not proposed["eligible"]
                or proposed["reason"] != "PROVEN_STARTUP_WITHOUT_REQUESTS"
                or not str(proposed["block_id"]).startswith("interrupted-")
            ):
                raise ValueError(
                    "No proven interrupted startup incident; state preserved"
                )
            coord["active_block"] = {
                "id": proposed["block_id"],
                "reason": "BLOCK_RECONCILED_LAUNCH_INTERRUPTED",
                "records": proposed["snapshot"]["records"],
            }
            owner.state.write(directory / COORDINATION, coord)
            return coord["active_block"]


def apply(owner, entry, value, proposed):
    directory = Path(entry["state"])
    with _transition_lock(owner, directory):
        graph_lock = Path(value["profile"]["graph"]).with_name(
            ".memory.service-owner.lock"
        )
        with owner.core.LifetimeLock(graph_lock):
            coord = coordination(owner, entry)
            if any(
                item["plan_id"] == proposed.get("plan_id") for item in coord["history"]
            ):
                raise ValueError("Recovery plan already applied; no changes")
            checked = plan(owner, entry, value)
            if (
                proposed.get("schema") != 2
                or not checked["eligible"]
                or set(proposed) != set(checked)
                or proposed.get("eligible") is not True
                or checked["snapshot"] != proposed.get("snapshot")
                or checked["block_id"] != proposed.get("block_id")
                or checked["reason"] != proposed.get("reason")
                or checked["old_generation"] != proposed.get("old_generation")
                or digest({k: v for k, v in proposed.items() if k != "plan_id"})
                != proposed.get("plan_id")
            ):
                raise ValueError("Stale or unsupported recovery plan; no changes")
            generation = proposed.get("new_generation")
            used = {checked["old_generation"]}
            used.update(
                item[key]
                for item in coord["history"]
                for key in ("old_generation", "new_generation")
            )
            if (
                not isinstance(generation, str)
                or len(generation) != 32
                or any(ch not in "0123456789abcdef" for ch in generation)
                or generation in used
            ):
                raise ValueError("Invalid successor generation")
            grant = {
                "id": uuid.uuid4().hex,
                "plan_id": proposed["plan_id"],
                "block_id": proposed["block_id"],
                "old_generation": proposed["old_generation"],
                "new_generation": generation,
                "snapshot": proposed["snapshot"],
                "phase": "RESOLVED",
            }
            coord["history"].append(grant)
            coord["active_block"] = None
            # One atomic publication is the commit boundary. No legacy file is deleted.
            owner.state.write(directory / COORDINATION, coord)
            return grant


def blocked(owner, entry):
    coord = coordination(owner, entry)
    if coord.get("active_block"):
        return True
    observed = records(owner, entry)
    raw = observed["blocked"]
    if raw is None:
        return False
    raw_hash = digest(raw)
    return not any(
        item["snapshot"]["records"]["blocked"] == raw_hash for item in coord["history"]
    )


def decision(owner, entry, value, *, self_owner=False):
    if blocked(owner, entry):
        return "BLOCK_UNRESOLVED_INCIDENT"
    coord = coordination(owner, entry)
    last = coord["history"][-1] if coord["history"] else None
    observed = records(owner, entry)
    if last and last["phase"] == "RESOLVED":
        reason = process_verdict(owner, observed, self_owner=self_owner)
        expected = last["snapshot"]
        if reason:
            return reason
        if owner.state.graph_stamp(value) != expected["graph"] or any(
            digest(observed[name]) != expected["records"][name]
            for name in ("profile", "active", "blocked", "status", "work")
        ):
            return "BLOCK_RECOVERY_EVIDENCE_DRIFT"
        return "SAFE_RECONCILED_START"
    if last and last["phase"] == "LAUNCHING":
        return "BLOCK_RECONCILED_LAUNCH_INTERRUPTED"
    return owner.legacy_recovery(entry, value, self_owner=self_owner)


def launch_generation(owner, entry, value):
    directory = Path(entry["state"])
    with _transition_lock(owner, directory):
        coord = coordination(owner, entry)
        last = coord["history"][-1] if coord["history"] else None
        if not last or last["phase"] in {"RUNNING", "IDLE"}:
            return uuid.uuid4().hex
        if decision(owner, entry, value, self_owner=True) != "SAFE_RECONCILED_START":
            raise ValueError("Recovery launch refused")
        birth = owner.core.process_birth(os.getpid())
        if birth is None:
            raise ValueError("Recovery owner identity unknown")
        last.update(phase="LAUNCHING", owner_pid=os.getpid(), owner_birth=birth)
        owner.state.write(directory / COORDINATION, coord)
        return last["new_generation"]


def observe(owner, entry, value, generation, *, idle=False):
    directory = Path(entry["state"])
    with _transition_lock(owner, directory):
        coord = coordination(owner, entry)
        last = coord["history"][-1] if coord["history"] else None
        if not last or last["new_generation"] != generation:
            return
        phase = "IDLE" if idle else "RUNNING"
        if last["phase"] == phase:
            return
        if last.get("owner_pid") != os.getpid() or owner.core.process_birth(
            os.getpid()
        ) != last.get("owner_birth"):
            raise ValueError("Recovery generation owner changed")
        work = owner.state.read(directory / "work.json") or {}
        if (
            work.get("schema") != 2
            or work.get("profile") != entry["id"]
            or work.get("generation") != generation
            or (
                idle
                and (
                    work.get("phase") != "idle"
                    or work.get("graph") != owner.state.graph_stamp(value)
                )
            )
        ):
            raise ValueError("Recovery generation has no idle receipt")
        last["phase"] = phase
        owner.state.write(directory / COORDINATION, coord)


def record_block(owner, entry, reason):
    directory = Path(entry["state"])
    with _transition_lock(owner, directory):
        coord = coordination(owner, entry)
        coord["active_block"] = {
            "id": uuid.uuid4().hex,
            "reason": reason,
            "records": {k: digest(v) for k, v in records(owner, entry).items()},
        }
        owner.state.write(directory / COORDINATION, coord)
