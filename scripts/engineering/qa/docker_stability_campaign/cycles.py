"""Bootstrap, reversible fault, and lifecycle-cycle campaign stages."""

from __future__ import annotations

import os
import shutil
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .commands import (
    bundle_volume_ids,
    live_compose_rows,
    observe_docker_vm_reserve,
    probe_command,
    record_probe,
    required_volume_precondition,
)
from .faults import HostFaultExecutor, build_fault_cases, execute_fault_case
from .model import atomic_json, compose_origin_findings
from .stage_support import (
    clean_baseline,
    index_and_save,
    manager_step,
    probe_services,
    save_state,
)

# Sibling lock files younger than this are treated as held by an active worker.
_CYCLE_LOCK_STALE_SECONDS = 3600.0
_MAX_CAMPAIGN_CYCLES = 1_000
_BOOTSTRAP_JSON = "bootstrap.json"


def _acquire_cycle_lock(cycle_dir: Path) -> int | None:
    """Try to acquire exclusive sibling lock; return fd or None if active peer."""
    lock_path = Path(f"{cycle_dir}.lock")
    try:
        return os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = time.time() - lock_path.stat().st_mtime
        except OSError:
            return None
        if age < _CYCLE_LOCK_STALE_SECONDS:
            return None
        try:
            lock_path.unlink(missing_ok=True)
            return os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, OSError):
            return None


def _release_cycle_lock(cycle_dir: Path, fd: int | None) -> None:
    if fd is None:
        return
    lock_path = Path(f"{cycle_dir}.lock")
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass


def _remove_incomplete_cycle_under_lock(cycle_dir: Path) -> None:
    """Drop incomplete cycle evidence after exclusive lock is held."""
    if cycle_dir.exists() and not (cycle_dir / "cycle.json").exists():
        shutil.rmtree(cycle_dir)


def _bootstrap_start_timeout(spec: Any) -> float:
    # Monitoring has multiple services and can need longer first-start budget
    # when Desktop is cold; main stays at 180s.
    return 300.0 if str(spec.stack) == "monitoring" else 180.0


def _bootstrap_persist_and_fail(
    *,
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    failure: str,
    payload: dict[str, Any],
) -> bool:
    """Persist a bootstrap failure payload and return False."""
    state["last_failure"] = failure
    atomic_json(
        evidence_dir / "bootstrap" / _BOOTSTRAP_JSON,
        payload,
        replace=False,
    )
    index_and_save(state, state_path, evidence_dir)
    return False


def _bootstrap_start_one_stack(
    *,
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    steps: list[dict[str, Any]],
    spec: Any,
) -> bool:
    """Start one stack during bootstrap; return False on hard failure."""
    start_timeout = _bootstrap_start_timeout(spec)
    probe_path = evidence_dir / "bootstrap" / f"probe-prestart-{spec.stack}.json"
    prestart = probe_command(
        runtime_origin,
        spec,
        probe_path,
        45.0,
        contract=contract,
    )
    steps.append(
        {
            "stack": spec.stack,
            "action": "probe-prestart",
            "result": prestart,
        }
    )
    if prestart.get("returncode") == 0 and prestart.get("summary_ok"):
        # Stack already green: skip compose start churn that can flap Desktop.
        steps.append(
            {
                "stack": spec.stack,
                "action": "start",
                "result": {
                    "returncode": 0,
                    "skipped": True,
                    "reason": "prestart_probe_ok",
                },
            }
        )
        return True
    result = manager_step(
        runtime_origin,
        contract,
        spec,
        "start",
        evidence_dir / "bootstrap" / f"manager-{spec.stack}",
        start_timeout,
    )
    steps.append({"stack": spec.stack, "action": "start", "result": result})
    if result["returncode"] == 0:
        return True
    # One bounded recover retry absorbs transient daemon flaps after start.
    recover = manager_step(
        runtime_origin,
        contract,
        spec,
        "recover",
        evidence_dir / "bootstrap" / f"manager-recover-{spec.stack}",
        start_timeout,
    )
    steps.append(
        {
            "stack": spec.stack,
            "action": "recover-after-start",
            "result": recover,
        }
    )
    if recover["returncode"] == 0:
        return True
    return _bootstrap_persist_and_fail(
        state=state,
        state_path=state_path,
        evidence_dir=evidence_dir,
        failure=f"bootstrap-start-{spec.stack}",
        payload={"passed": False, "steps": steps},
    )


def _bootstrap_probe_baselines(
    *,
    state: dict[str, Any],
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
    steps: list[dict[str, Any]],
    origins: list[str],
) -> dict[str, str]:
    """Probe each stack and write clean baselines; append origin findings on fail."""
    baselines: dict[str, str] = {}
    for spec in bundle:
        probe = evidence_dir / "bootstrap" / f"probe-{spec.stack}.json"
        result = probe_command(
            runtime_origin,
            spec,
            probe,
            75.0,
            contract=contract,
        )
        steps.append({"stack": spec.stack, "action": "probe", "result": result})
        if result["returncode"] != 0:
            state["last_failure"] = f"bootstrap-probe-{spec.stack}"
            origins.append(f"{spec.project}: initial probe failed")
            continue
        baseline = evidence_dir / "bootstrap" / f"baseline-{spec.stack}.json"
        clean_baseline(probe, baseline)
        baselines[spec.stack] = baseline.relative_to(evidence_dir).as_posix()
        record_probe(state, probe)
    return baselines


def bootstrap_campaign(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
) -> bool:
    if state.get("bootstrap_complete"):
        return True
    steps: list[dict[str, Any]] = []
    volume_precondition = required_volume_precondition(runtime_origin, bundle)
    if not volume_precondition["passed"]:
        return _bootstrap_persist_and_fail(
            state=state,
            state_path=state_path,
            evidence_dir=evidence_dir,
            failure="bootstrap-required-volumes",
            payload={
                "schema_version": "bioetl-docker-campaign-bootstrap-v1",
                "passed": False,
                "runtime_origin": str(runtime_origin),
                "volume_precondition": volume_precondition,
                "steps": steps,
            },
        )
    state["initial_volume_ids"] = bundle_volume_ids(runtime_origin, bundle)
    for spec in bundle:
        if not _bootstrap_start_one_stack(
            state=state,
            state_path=state_path,
            evidence_dir=evidence_dir,
            runtime_origin=runtime_origin,
            contract=contract,
            steps=steps,
            spec=spec,
        ):
            return False
    rows = live_compose_rows(runtime_origin)
    origins = compose_origin_findings(rows, bundle, runtime_origin)
    baselines = _bootstrap_probe_baselines(
        state=state,
        evidence_dir=evidence_dir,
        runtime_origin=runtime_origin,
        contract=contract,
        bundle=bundle,
        steps=steps,
        origins=origins,
    )
    capacity = observe_docker_vm_reserve(state, runtime_origin)
    passed = (
        not origins and len(baselines) == len(bundle) and capacity["returncode"] == 0
    )
    atomic_json(
        evidence_dir / "bootstrap" / _BOOTSTRAP_JSON,
        {
            "schema_version": "bioetl-docker-campaign-bootstrap-v1",
            "passed": passed,
            "runtime_origin": str(runtime_origin),
            "volume_precondition": volume_precondition,
            "compose_rows": rows,
            "origin_findings": origins,
            "baselines": baselines,
            "capacity": capacity,
            "steps": steps,
        },
        replace=False,
    )
    state["bootstrap_complete"] = passed
    state["bootstrap_baselines"] = baselines
    state["last_failure"] = None if passed else "bootstrap"
    index_and_save(state, state_path, evidence_dir)
    return passed


def run_fault_matrix(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
) -> bool:
    baselines = {
        stack: evidence_dir / relative
        for stack, relative in state.get("bootstrap_baselines", {}).items()
    }
    for case in build_fault_cases():
        executor = HostFaultExecutor(
            runtime_origin=runtime_origin,
            contract=contract,
            evidence_dir=evidence_dir,
            bundle=bundle,
            baselines=baselines,
        )
        if not execute_fault_case(case, executor, state, state_path, evidence_dir):
            index_and_save(state, state_path, evidence_dir)
            return False
        index_and_save(state, state_path, evidence_dir)
    state["last_failure"] = None
    save_state(state_path, state)
    return True


def run_cycle(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
) -> bool:
    number = int(state["completed_cycles"]) + 1
    cycle_dir = evidence_dir / "cycles" / f"cycle-{number:03d}"
    # Exclusive lock: never rmtree a cycle tree owned by an active peer process.
    lock_fd = _acquire_cycle_lock(cycle_dir)
    if lock_fd is None:
        state["last_failure"] = f"cycle-lock-busy-{number:03d}"
        save_state(state_path, state)
        return False
    try:
        os.write(lock_fd, f"{os.getpid()}\n".encode())
        _remove_incomplete_cycle_under_lock(cycle_dir)
        cycle_dir.mkdir(parents=True, exist_ok=True)
        return _run_cycle_body(
            state=state,
            state_path=state_path,
            evidence_dir=evidence_dir,
            runtime_origin=runtime_origin,
            contract=contract,
            bundle=bundle,
            number=number,
            cycle_dir=cycle_dir,
        )
    finally:
        _release_cycle_lock(cycle_dir, lock_fd)


def _cycle_start_and_baseline(
    *,
    state: dict[str, Any],
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
    cycle_dir: Path,
    steps: list[dict[str, Any]],
    baselines: dict[str, Path],
    initial_ids: dict[str, dict[str, str]],
) -> str | None:
    """Start stacks and capture baselines; return failure code or None."""
    for spec in bundle:
        result = manager_step(
            runtime_origin,
            contract,
            spec,
            "start",
            cycle_dir / f"manager-start-{spec.stack}",
            180.0,
        )
        steps.append({"stack": spec.stack, "action": "start", "result": result})
        if result["returncode"] != 0:
            return f"start-{spec.stack}"
        probe = cycle_dir / f"probe-baseline-{spec.stack}.json"
        sample = probe_command(runtime_origin, spec, probe, 75.0, contract=contract)
        steps.append({"stack": spec.stack, "action": "baseline", "result": sample})
        if sample["returncode"] != 0:
            return f"baseline-{spec.stack}"
        baseline = cycle_dir / f"baseline-{spec.stack}.json"
        try:
            initial_ids[spec.stack] = clean_baseline(probe, baseline)
        except ValueError:
            return f"restart-baseline-{spec.stack}"
        baselines[spec.stack] = baseline
        record_probe(state, probe)
    return None


def _cycle_idempotent_start(
    *,
    state: dict[str, Any],
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
    cycle_dir: Path,
    steps: list[dict[str, Any]],
    baselines: dict[str, Path],
    initial_ids: dict[str, dict[str, str]],
) -> str | None:
    """Re-start stacks idempotently and verify container identity."""
    for spec in bundle:
        result = manager_step(
            runtime_origin,
            contract,
            spec,
            "start",
            cycle_dir / f"manager-idempotent-{spec.stack}",
            180.0,
        )
        probe = cycle_dir / f"probe-idempotent-{spec.stack}.json"
        sample = probe_command(
            runtime_origin,
            spec,
            probe,
            75.0,
            contract=contract,
            baseline=baselines[spec.stack],
        )
        steps.extend(
            (
                {
                    "stack": spec.stack,
                    "action": "idempotent-start",
                    "result": result,
                },
                {
                    "stack": spec.stack,
                    "action": "idempotent-probe",
                    "result": sample,
                },
            )
        )
        if result["returncode"] != 0 or sample["returncode"] != 0:
            return f"idempotent-{spec.stack}"
        record_probe(state, probe)
        if probe_services(probe) != initial_ids[spec.stack]:
            state["image_or_project_drift"] = (
                int(state.get("image_or_project_drift", 0)) + 1
            )
            return f"container-identity-{spec.stack}"
    return None


def _cycle_stop_stacks(
    *,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
    cycle_dir: Path,
    steps: list[dict[str, Any]],
    failure: str | None,
) -> str | None:
    """Stop stacks twice (idempotent stop); preserve first failure if any."""
    for spec in reversed(bundle):
        for ordinal in (1, 2):
            result = manager_step(
                runtime_origin,
                contract,
                spec,
                "stop",
                cycle_dir / f"manager-stop-{spec.stack}-{ordinal}",
                60.0,
            )
            steps.append(
                {"stack": spec.stack, "action": f"stop-{ordinal}", "result": result}
            )
            if result["returncode"] != 0 and failure is None:
                failure = f"stop-{spec.stack}-{ordinal}"
    return failure


def _finalize_cycle_result(
    *,
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    cycle_dir: Path,
    number: int,
    failure: str | None,
    before: dict[str, Any],
    after: dict[str, Any],
    capacity: dict[str, Any],
    steps: list[dict[str, Any]],
) -> bool:
    """Write cycle.json, update state counters, return pass/fail."""
    if before != after:
        state["volume_loss"] = True
        failure = failure or "volume-identity"
    if capacity["returncode"] != 0:
        failure = failure or "docker-vm-capacity"
    passed = failure is None
    atomic_json(
        cycle_dir / "cycle.json",
        {
            "schema_version": "bioetl-docker-stability-cycle-v2",
            "cycle": number,
            "passed": passed,
            "failure": failure,
            "volume_ids_before": before,
            "volume_ids_after": after,
            "capacity": capacity,
            "steps": steps,
        },
        replace=False,
    )
    if passed:
        state["completed_cycles"] = number
        state["last_failure"] = None
    else:
        state["cycle_failures"] = int(state.get("cycle_failures", 0)) + 1
        state["last_failure"] = f"cycle-{number:03d}:{failure}"
    index_and_save(state, state_path, evidence_dir)
    return passed


def _run_cycle_body(
    *,
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
    number: int,
    cycle_dir: Path,
) -> bool:
    before = bundle_volume_ids(runtime_origin, bundle)
    steps: list[dict[str, Any]] = []
    baselines: dict[str, Path] = {}
    initial_ids: dict[str, dict[str, str]] = {}
    failure = _cycle_start_and_baseline(
        state=state,
        runtime_origin=runtime_origin,
        contract=contract,
        bundle=bundle,
        cycle_dir=cycle_dir,
        steps=steps,
        baselines=baselines,
        initial_ids=initial_ids,
    )
    if failure is None:
        failure = _cycle_idempotent_start(
            state=state,
            runtime_origin=runtime_origin,
            contract=contract,
            bundle=bundle,
            cycle_dir=cycle_dir,
            steps=steps,
            baselines=baselines,
            initial_ids=initial_ids,
        )
    failure = _cycle_stop_stacks(
        runtime_origin=runtime_origin,
        contract=contract,
        bundle=bundle,
        cycle_dir=cycle_dir,
        steps=steps,
        failure=failure,
    )
    after = bundle_volume_ids(runtime_origin, bundle)
    capacity = observe_docker_vm_reserve(state, runtime_origin)
    return _finalize_cycle_result(
        state=state,
        state_path=state_path,
        evidence_dir=evidence_dir,
        cycle_dir=cycle_dir,
        number=number,
        failure=failure,
        before=before,
        after=after,
        capacity=capacity,
        steps=steps,
    )


def run_cycles(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
) -> bool:
    required_cycles = min(
        max(int(state["required_cycles"]), 0),
        _MAX_CAMPAIGN_CYCLES,
    )
    while int(state["completed_cycles"]) < required_cycles:
        if not run_cycle(
            state, state_path, evidence_dir, runtime_origin, contract, bundle
        ):
            return False
    return True
