"""Reversible, bounded fault matrix for Docker stability promotion."""

from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .commands import (
    compose_command,
    manager_command,
    probe_command,
    remaining_seconds,
    volume_ids,
)
from .model import (
    FAULT_CASE_NAMES,
    FaultCase,
    FaultOperation,
    StackSpec,
    atomic_json,
    remember_evidence,
    updated_now,
)


def build_fault_cases() -> tuple[FaultCase, ...]:
    """Return the contract-required fault matrix in deterministic order."""
    cases = (
        FaultCase(
            "selected_service_termination",
            "service_unready",
            (FaultOperation("kill_service", "main", "bioetl"),),
            (FaultOperation("probe", "main", expected="cause:service_unready"),),
            (
                # Prefer start over recover: kill leaves a clean dead container;
                # force-recreate recover has repeatedly crashed Docker Desktop.
                FaultOperation(
                    "start", "main", expected="success", max_seconds=180.0
                ),
            ),
            max_seconds=360.0,
        ),
        FaultCase(
            "failed_health_readiness",
            "service_unready",
            (FaultOperation("pause_service", "main", "bioetl"),),
            (FaultOperation("probe", "main", expected="cause:service_unready"),),
            (
                FaultOperation("unpause_service", "main", "bioetl"),
                # After pause, health stays sticky; recover attempt>=2 force-recreates.
                FaultOperation("recover", "main", max_seconds=180.0),
            ),
            max_seconds=360.0,
        ),
        FaultCase(
            "occupied_required_port",
            "HOST_PORT_COLLISION",
            (
                FaultOperation("stop", "main"),
                FaultOperation("reserve_port", port=8081),
            ),
            (FaultOperation("start", "main", expected="finding:HOST_PORT_COLLISION"),),
            (
                FaultOperation("release_port", port=8081),
                # Allow Desktop socket flaps to reconnect within the restore budget.
                FaultOperation("recover", "main", max_seconds=180.0),
            ),
            max_seconds=360.0,
        ),
        FaultCase(
            "expected_image_identity_drift",
            "image_identity_drift",
            (),
            (
                FaultOperation(
                    "probe_image_drift",
                    "main",
                    "bioetl",
                    expected="cause:image_identity_drift",
                ),
            ),
            (),
        ),
        FaultCase(
            "interrupted_startup",
            "interrupted",
            (FaultOperation("stop", "main"),),
            (FaultOperation("interrupt_start", "main", expected="interrupted"),),
            (FaultOperation("start", "main", max_seconds=180.0),),
            max_seconds=360.0,
        ),
        FaultCase(
            "bounded_memory_pid_pressure",
            "bounded_pressure",
            (FaultOperation("bounded_pressure", "main", "bioetl", max_seconds=15.0),),
            (FaultOperation("probe", "main", expected="success"),),
            (
                FaultOperation("clear_pressure", "main", "bioetl", max_seconds=15.0),
                FaultOperation("probe", "main", expected="success"),
            ),
        ),
        FaultCase(
            "desktop_engine_restart",
            "desktop_restart",
            (FaultOperation("desktop_restart", max_seconds=180.0),),
            (
                FaultOperation("recover", "main", max_seconds=120.0),
                FaultOperation("recover", "monitoring", max_seconds=120.0),
                FaultOperation("probe", "main", max_seconds=30.0),
                FaultOperation("probe", "monitoring", max_seconds=30.0),
            ),
            (),
            max_seconds=480.0,
        ),
    )
    if tuple(case.name for case in cases) != FAULT_CASE_NAMES:
        raise AssertionError("fault matrix differs from the release contract")
    return cases


def operation_passed(result: Mapping[str, Any], expected: str) -> bool:
    """Match an operation against its exact expected classification."""
    if expected == "success":
        return int(result.get("returncode", 1)) == 0
    if expected == "interrupted":
        return bool(result.get("interrupted")) and int(result.get("returncode", 0)) != 0
    prefix, separator, value = expected.partition(":")
    if separator != ":":
        return False
    if prefix == "cause":
        return str(result.get("primary_cause")) == value
    if prefix == "finding":
        return value in {str(item) for item in result.get("preflight_findings", [])}
    return False


class HostFaultExecutor:
    """Execute only the explicitly scheduled, case-local fault primitives."""

    def __init__(
        self,
        *,
        runtime_origin: Path,
        contract: Path,
        evidence_dir: Path,
        bundle: Sequence[StackSpec],
        baselines: Mapping[str, Path],
    ) -> None:
        self.runtime_origin = runtime_origin
        self.contract = contract
        self.evidence_dir = evidence_dir
        self.specs = {spec.stack: spec for spec in bundle}
        self.baselines = baselines
        self._reserved_ports: dict[int, socket.socket] = {}

    def _spec(self, operation: FaultOperation) -> StackSpec:
        if operation.stack not in self.specs:
            raise ValueError(f"unknown release stack: {operation.stack}")
        return self.specs[str(operation.stack)]

    def execute(
        self,
        operation: FaultOperation,
        *,
        deadline: float,
        case_name: str,
        ordinal: int,
    ) -> dict[str, Any]:
        timeout = min(operation.max_seconds, remaining_seconds(deadline, reserve=0.2))
        evidence = self.evidence_dir / "faults" / case_name
        evidence.mkdir(parents=True, exist_ok=True)
        if operation.kind in {"start", "stop", "recover"}:
            spec = self._spec(operation)
            report_dir = evidence / f"manager-{ordinal:02d}-{operation.kind}"
            return manager_command(
                self.runtime_origin,
                operation.kind,
                spec,
                timeout,
                report_dir,
                contract=self.contract,
            )
        if operation.kind in {"kill_service", "pause_service", "unpause_service"}:
            spec = self._spec(operation)
            compose_action = {
                "kill_service": "kill",
                "pause_service": "pause",
                "unpause_service": "unpause",
            }[operation.kind]
            return compose_command(
                self.runtime_origin,
                spec,
                (compose_action, str(operation.service)),
                timeout,
            )
        if operation.kind in {"probe", "probe_image_drift"}:
            spec = self._spec(operation)
            output = evidence / f"probe-{ordinal:02d}-{spec.stack}.json"
            override = None
            if operation.kind == "probe_image_drift":
                override = (
                    str(operation.service),
                    "bioetl/fault-injection@sha256:" + "0" * 64,
                )
            return probe_command(
                self.runtime_origin,
                spec,
                output,
                timeout,
                contract=self.contract,
                baseline=self.baselines.get(spec.stack),
                expected_image_override=override,
            )
        if operation.kind == "reserve_port":
            port = int(operation.port or 0)
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", port))
            listener.listen(1)
            self._reserved_ports[port] = listener
            return {"returncode": 0, "port": port, "owner": "campaign"}
        if operation.kind == "release_port":
            port = int(operation.port or 0)
            listener = self._reserved_ports.pop(port, None)
            if listener is not None:
                listener.close()
            return {"returncode": 0, "port": port, "released": True}
        if operation.kind == "interrupt_start":
            spec = self._spec(operation)
            command = [
                "docker",
                "compose",
                "-p",
                spec.project,
                "-f",
                str(self.runtime_origin / spec.compose_file),
                "up",
                "-d",
                "--wait",
                *spec.required_services,
            ]
            started = time.monotonic()
            process = subprocess.Popen(
                command,
                cwd=self.runtime_origin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(min(1.0, timeout / 4))
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=min(5.0, timeout))
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=2.0)
            return {
                "command": command,
                "returncode": process.returncode,
                "interrupted": True,
                "duration_seconds": round(time.monotonic() - started, 3),
                "stdout": stdout[:4000],
                "stderr": stderr[:4000],
            }
        if operation.kind == "bounded_pressure":
            spec = self._spec(operation)
            # Keep the injected load intentionally small and time-bounded. Its purpose
            # is to exercise resource telemetry and cleanup, not breach the 80% gate.
            program = """import multiprocessing as m
import os
from pathlib import Path
import time

marker = Path('/tmp/bioetl-fault-pressure.pids')
buf = bytearray(16 * 1024 * 1024)
child = m.Process(target=time.sleep, args=(10,))
child.start()
marker.write_text(f"{os.getpid()} {child.pid}", encoding="ascii")
try:
    time.sleep(10)
    child.join()
    assert len(buf) == 16 * 1024 * 1024
finally:
    if child.is_alive():
        child.terminate()
        child.join(timeout=2)
    marker.unlink(missing_ok=True)
"""
            return compose_command(
                self.runtime_origin,
                spec,
                (
                    "exec",
                    "-T",
                    str(operation.service),
                    "python",
                    "-c",
                    program,
                ),
                timeout,
            )
        if operation.kind == "clear_pressure":
            spec = self._spec(operation)
            program = """import os
from pathlib import Path
import signal
import time

marker = Path('/tmp/bioetl-fault-pressure.pids')
pids = [int(value) for value in marker.read_text(encoding='ascii').split()] if marker.exists() else []
for pid in reversed(pids):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
    alive = []
    for pid in pids:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        alive.append(pid)
    if not alive:
        break
    time.sleep(0.1)
else:
    raise SystemExit('pressure workload did not terminate')
marker.unlink(missing_ok=True)
"""
            return compose_command(
                self.runtime_origin,
                spec,
                (
                    "exec",
                    "-T",
                    str(operation.service),
                    "python",
                    "-c",
                    program,
                ),
                timeout,
            )
        if operation.kind == "desktop_restart":
            # WSL `docker desktop restart` fails without /opt/docker-desktop backend.
            # Route through the Windows host CLI (same lane as RF-006 recovery).
            from .commands import desktop_engine_restart_command

            return desktop_engine_restart_command(self.runtime_origin, timeout)
        raise ValueError(f"unsupported fault operation: {operation.kind}")

    def close(self) -> None:
        for listener in self._reserved_ports.values():
            listener.close()
        self._reserved_ports.clear()


def execute_fault_case(
    case: FaultCase,
    executor: HostFaultExecutor,
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
) -> bool:
    """Execute and restore one fault under one global deadline."""
    if state.get("fault_cases", {}).get(case.name, {}).get("passed"):
        return True
    evidence_path = evidence_dir / "faults" / case.name / "case.json"
    if evidence_path.exists():
        raise FileExistsError(
            f"refusing to rerun an incomplete fault with retained evidence: {evidence_path}"
        )
    started = time.monotonic()
    deadline = started + case.max_seconds
    restore_budget = min(
        case.max_seconds * 0.4,
        sum(operation.max_seconds for operation in case.restore),
    )
    operation_deadline = deadline - restore_budget
    steps: list[dict[str, Any]] = []
    failures: list[str] = []
    before = {
        spec.project: sorted(volume_ids(executor.runtime_origin, spec))
        for spec in executor.specs.values()
    }
    ordinal = 0
    try:
        for phase, operations in (
            ("apply", case.apply),
            ("observe", case.observe),
        ):
            for operation in operations:
                ordinal += 1
                try:
                    result = executor.execute(
                        operation,
                        deadline=operation_deadline,
                        case_name=case.name,
                        ordinal=ordinal,
                    )
                    passed = operation_passed(result, operation.expected)
                except Exception as exc:  # evidence must survive every host failure
                    result = {
                        "returncode": 1,
                        "error": type(exc).__name__,
                        "message": str(exc),
                    }
                    passed = False
                steps.append(
                    {
                        "phase": phase,
                        "operation": operation.kind,
                        "expected": operation.expected,
                        "passed": passed,
                        "result": result,
                    }
                )
                if not passed:
                    failures.append(f"{phase}:{operation.kind}")
    finally:
        for operation in case.restore:
            ordinal += 1
            try:
                result = executor.execute(
                    operation,
                    deadline=deadline,
                    case_name=case.name,
                    ordinal=ordinal,
                )
                passed = operation_passed(result, operation.expected)
            except Exception as exc:
                result = {
                    "returncode": 1,
                    "error": type(exc).__name__,
                    "message": str(exc),
                }
                passed = False
            steps.append(
                {
                    "phase": "restore",
                    "operation": operation.kind,
                    "expected": operation.expected,
                    "passed": passed,
                    "result": result,
                }
            )
            if not passed:
                failures.append(f"restore:{operation.kind}")
        executor.close()
    try:
        after = {
            spec.project: sorted(volume_ids(executor.runtime_origin, spec))
            for spec in executor.specs.values()
        }
    except Exception as exc:
        after = {}
        failures.append(f"volume-capture:{type(exc).__name__}")
    if before != after:
        state["volume_loss"] = True
        failures.append("volume-identity")
    passed = not failures and time.monotonic() <= deadline
    incident_id = None
    if not passed:
        incident_id = f"fault-{case.name}"
        state.setdefault("incident_ids", []).append(incident_id)
        state["last_failure"] = incident_id
    atomic_json(
        evidence_path,
        {
            "schema_version": "bioetl-docker-fault-case-v1",
            "name": case.name,
            "classification": case.classification,
            "passed": passed,
            "failures": failures,
            "incident_id": incident_id,
            "volume_ids_before": before,
            "volume_ids_after": after,
            "steps": steps,
        },
        replace=False,
    )
    remember_evidence(state, evidence_path, evidence_dir)
    state.setdefault("fault_cases", {})[case.name] = {
        "passed": passed,
        "evidence": evidence_path.relative_to(evidence_dir).as_posix(),
    }
    updated_now(state)
    atomic_json(state_path, state)
    return passed
