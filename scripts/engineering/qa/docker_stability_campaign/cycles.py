"""Bootstrap, reversible fault, and lifecycle-cycle campaign stages."""

from __future__ import annotations

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
        state["last_failure"] = "bootstrap-required-volumes"
        atomic_json(
            evidence_dir / "bootstrap" / "bootstrap.json",
            {
                "schema_version": "bioetl-docker-campaign-bootstrap-v1",
                "passed": False,
                "runtime_origin": str(runtime_origin),
                "volume_precondition": volume_precondition,
                "steps": steps,
            },
            replace=False,
        )
        index_and_save(state, state_path, evidence_dir)
        return False
    state["initial_volume_ids"] = bundle_volume_ids(runtime_origin, bundle)
    for spec in bundle:
        # Monitoring has multiple services and can need longer first-start budget
        # when Desktop is cold; main stays at 180s.
        start_timeout = 300.0 if str(spec.stack) == "monitoring" else 180.0
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
            continue
        result = manager_step(
            runtime_origin,
            contract,
            spec,
            "start",
            evidence_dir / "bootstrap" / f"manager-{spec.stack}",
            start_timeout,
        )
        steps.append({"stack": spec.stack, "action": "start", "result": result})
        if result["returncode"] != 0:
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
                {"stack": spec.stack, "action": "recover-after-start", "result": recover}
            )
            if recover["returncode"] != 0:
                state["last_failure"] = f"bootstrap-start-{spec.stack}"
                atomic_json(
                    evidence_dir / "bootstrap" / "bootstrap.json",
                    {"passed": False, "steps": steps},
                    replace=False,
                )
                index_and_save(state, state_path, evidence_dir)
                return False
    rows = live_compose_rows(runtime_origin)
    origins = compose_origin_findings(rows, bundle, runtime_origin)
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
    capacity = observe_docker_vm_reserve(state, runtime_origin)
    passed = (
        not origins and len(baselines) == len(bundle) and capacity["returncode"] == 0
    )
    atomic_json(
        evidence_dir / "bootstrap" / "bootstrap.json",
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
    before = bundle_volume_ids(runtime_origin, bundle)
    steps: list[dict[str, Any]] = []
    baselines: dict[str, Path] = {}
    initial_ids: dict[str, dict[str, str]] = {}
    failure: str | None = None
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
            failure = f"start-{spec.stack}"
            break
        probe = cycle_dir / f"probe-baseline-{spec.stack}.json"
        sample = probe_command(runtime_origin, spec, probe, 75.0, contract=contract)
        steps.append({"stack": spec.stack, "action": "baseline", "result": sample})
        if sample["returncode"] != 0:
            failure = f"baseline-{spec.stack}"
            break
        baseline = cycle_dir / f"baseline-{spec.stack}.json"
        try:
            initial_ids[spec.stack] = clean_baseline(probe, baseline)
        except ValueError:
            failure = f"restart-baseline-{spec.stack}"
            break
        baselines[spec.stack] = baseline
        record_probe(state, probe)
    if failure is None:
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
                failure = f"idempotent-{spec.stack}"
                break
            record_probe(state, probe)
            if probe_services(probe) != initial_ids[spec.stack]:
                state["image_or_project_drift"] = (
                    int(state.get("image_or_project_drift", 0)) + 1
                )
                failure = f"container-identity-{spec.stack}"
                break
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
    after = bundle_volume_ids(runtime_origin, bundle)
    capacity = observe_docker_vm_reserve(state, runtime_origin)
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


def run_cycles(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
) -> bool:
    while int(state["completed_cycles"]) < int(state["required_cycles"]):
        if not run_cycle(
            state, state_path, evidence_dir, runtime_origin, contract, bundle
        ):
            return False
    return True
