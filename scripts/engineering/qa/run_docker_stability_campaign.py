#!/usr/bin/env python3
"""Run resumable, evidence-driven optional Docker stability campaigns."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
MANAGER = ROOT / "scripts/ops/runtime/docker/runtime_manager.py"
PROBE = ROOT / "scripts/ops/runtime/docker/docker_runtime_probe.py"
CONFIRM_TOKEN = "I_UNDERSTAND_THIS_INTERRUPTS_DOCKER_DESKTOP"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Campaign state must be a JSON object")
    return value


def _run(command: Sequence[str], timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            "command": list(command),
            "returncode": 127,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": "",
            "stderr": str(exc)[:2000],
        }
    return {
        "command": list(command),
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
        "stdout": completed.stdout[:2000],
        "stderr": completed.stderr[:2000],
    }


def _volume_ids(project: str) -> set[str]:
    result = _run(
        [
            "docker",
            "volume",
            "ls",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.Name}}",
        ],
        15,
    )
    if result["returncode"] != 0:
        raise RuntimeError("Unable to capture named-volume identity")
    return {line for line in str(result["stdout"]).splitlines() if line}


def new_state(
    *, stack: str, project: str, cycles: int, soak_hours: float
) -> dict[str, Any]:
    return {
        "schema_version": "bioetl-docker-stability-campaign-state-v1",
        "stack": stack,
        "project": project,
        "required_cycles": cycles,
        "required_soak_hours": soak_hours,
        "completed_cycles": 0,
        "cycle_failures": 0,
        "soak_started_at": None,
        "soak_last_sample_at": None,
        "soak_observed_seconds": 0.0,
        "soak_interruptions": 0,
        "engine_recovery_trials": 0,
        "engine_recovery_successes": 0,
        "volume_loss": False,
        "probe_samples": 0,
        "probe_failures": 0,
        "max_resource_ratio": 0.0,
        "restart_count_delta": 0,
        "oom_kills": 0,
        "unhealthy_samples": 0,
        "disk_reserve_breaches": 0,
        "image_or_project_drift": 0,
        "last_failure": None,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def release_gates(state: dict[str, Any], *, signature_exists: bool) -> dict[str, bool]:
    required_seconds = float(state["required_soak_hours"]) * 3600
    trials = int(state.get("engine_recovery_trials", 0))
    successes = int(state.get("engine_recovery_successes", 0))
    return {
        "cycles_complete": int(state["completed_cycles"])
        >= int(state["required_cycles"]),
        "cycles_clean": int(state["cycle_failures"]) == 0,
        "soak_complete": float(state["soak_observed_seconds"]) >= required_seconds,
        "soak_continuous": int(state.get("soak_interruptions", 0)) == 0,
        "engine_recovery_99_of_100": trials >= 100 and successes / trials >= 0.99,
        "volumes_preserved": not bool(state["volume_loss"]),
        "all_probe_samples_clean": int(state.get("probe_failures", 0)) == 0
        and int(state.get("probe_samples", 0)) > 0,
        "resource_peak_below_80_percent": float(state.get("max_resource_ratio", 0.0))
        < 0.8,
        "restart_delta_zero": int(state.get("restart_count_delta", 0)) == 0,
        "oom_kills_zero": int(state.get("oom_kills", 0)) == 0,
        "unhealthy_zero": int(state.get("unhealthy_samples", 0)) == 0,
        "disk_reserve_preserved": int(state.get("disk_reserve_breaches", 0)) == 0,
        "identity_drift_zero": int(state.get("image_or_project_drift", 0)) == 0,
        "detached_signature_present": signature_exists,
        "no_unresolved_failure": state.get("last_failure") is None,
    }


def _manager(action: str, stack: str, timeout: float) -> dict[str, Any]:
    return _run(
        [
            sys.executable,
            str(MANAGER),
            action,
            "--stack",
            stack,
            "--timeout",
            str(timeout),
        ],
        timeout + 15,
    )


def _sample_probe(stack: str, output: Path) -> dict[str, Any]:
    return _run(
        [sys.executable, str(PROBE), "--stack", stack, "--output", str(output)],
        75,
    )


def _record_probe(state: dict[str, Any], path: Path) -> None:
    report = _load(path)
    slo = report.get("slo", {})
    state["probe_samples"] = int(state.get("probe_samples", 0)) + 1
    state["probe_failures"] = int(state.get("probe_failures", 0)) + int(
        not bool(report.get("summary", {}).get("ok"))
    )
    ratios = [
        float(value)
        for row in report.get("resources", [])
        for key, value in row.items()
        if key.endswith("_limit_ratio")
    ]
    state["max_resource_ratio"] = max(
        [float(state.get("max_resource_ratio", 0.0)), *ratios]
    )
    state["restart_count_delta"] = max(
        int(state.get("restart_count_delta", 0)),
        int(slo.get("restart_count_delta", 0)),
    )
    state["oom_kills"] = max(
        int(state.get("oom_kills", 0)), int(slo.get("oom_kills", 0))
    )
    state["unhealthy_samples"] = int(state.get("unhealthy_samples", 0)) + int(
        not bool(slo.get("required_services_ready", False))
    )
    state["disk_reserve_breaches"] = int(state.get("disk_reserve_breaches", 0)) + int(
        not bool(slo.get("disk_reserve_ok", False))
    )
    state["image_or_project_drift"] = int(state.get("image_or_project_drift", 0)) + int(
        bool(slo.get("image_identity_drift")) or bool(slo.get("project_origin_drift"))
    )


def run_cycle(state: dict[str, Any], state_path: Path, evidence_dir: Path) -> bool:
    number = int(state["completed_cycles"]) + 1
    before = _volume_ids(str(state["project"]))
    probe_path = evidence_dir / f"probe-cycle-{number:03d}.json"
    steps = [
        _manager("start", str(state["stack"]), 180),
        _manager("start", str(state["stack"]), 180),
        _manager("status", str(state["stack"]), 30),
        _sample_probe(str(state["stack"]), probe_path),
        _manager("stop", str(state["stack"]), 60),
        _manager("stop", str(state["stack"]), 60),
    ]
    after = _volume_ids(str(state["project"]))
    if probe_path.is_file():
        _record_probe(state, probe_path)
    ok = all(step["returncode"] == 0 for step in steps) and before == after
    _atomic_json(
        evidence_dir / f"cycle-{number:03d}.json",
        {
            "cycle": number,
            "ok": ok,
            "volume_ids_before": sorted(before),
            "volume_ids_after": sorted(after),
            "steps": steps,
        },
    )
    if ok:
        state["completed_cycles"] = number
    else:
        state["cycle_failures"] = int(state["cycle_failures"]) + 1
        state["volume_loss"] = before != after
        state["last_failure"] = f"cycle-{number:03d}"
    state["updated_at"] = datetime.now(UTC).isoformat()
    _atomic_json(state_path, state)
    return ok


def _sign(summary: Path, key: str) -> Path:
    result = _run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--armor",
            "--detach-sign",
            "--local-user",
            key,
            str(summary),
        ],
        60,
    )
    if result["returncode"] != 0:
        raise RuntimeError("Detached GPG signature failed")
    return summary.with_suffix(summary.suffix + ".asc")


def _signature_valid(summary: Path, signature: Path) -> bool:
    if not signature.is_file():
        return False
    result = _run(["gpg", "--batch", "--verify", str(signature), str(summary)], 60)
    return result["returncode"] == 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", default="main")
    parser.add_argument("--project", default="bioetl-main")
    parser.add_argument("--cycles", type=int, default=100)
    parser.add_argument("--soak-hours", type=float, default=72.0)
    parser.add_argument("--soak-sample-seconds", type=float, default=60.0)
    parser.add_argument("--engine-recovery-trials", type=int, default=100)
    parser.add_argument("--confirm-host-disruption", default="")
    parser.add_argument(
        "--state",
        type=Path,
        default=ROOT / "reports/quality/docker-stability-campaign-state.json",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=ROOT / "reports/quality/docker-stability-raw",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=ROOT / "reports/quality/docker-stability-summary.json",
    )
    parser.add_argument("--signing-key")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.execute:
        print("Refusing to count evidence without --execute", file=sys.stderr)
        return 2
    if args.cycles < 100 or args.soak_hours < 72 or args.engine_recovery_trials < 100:
        print("Release thresholds cannot be reduced", file=sys.stderr)
        return 2
    if args.soak_sample_seconds < 1:
        print("Soak sample interval must be at least one second", file=sys.stderr)
        return 2
    if args.confirm_host_disruption != CONFIRM_TOKEN:
        print(
            "Host recovery trials require explicit operator scheduling token",
            file=sys.stderr,
        )
        return 2
    if not args.signing_key:
        print("A detached GPG signing key is required for promotion evidence", file=sys.stderr)
        return 2
    state = _load(args.state) or new_state(
        stack=args.stack,
        project=args.project,
        cycles=args.cycles,
        soak_hours=args.soak_hours,
    )
    if (state["stack"], state["project"]) != (args.stack, args.project):
        raise ValueError("Cannot resume a campaign with different stack/project")
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    while int(state["completed_cycles"]) < int(state["required_cycles"]):
        if not run_cycle(state, args.state, args.evidence_dir):
            return 1

    if state["soak_started_at"] is None:
        state["soak_started_at"] = time.time()
        state["soak_last_sample_at"] = None
        _atomic_json(args.state, state)
    start = _manager("start", args.stack, 180)
    if start["returncode"] != 0:
        state["last_failure"] = "soak-start"
        _atomic_json(args.state, state)
        return 1
    previous_sample_at = state.get("soak_last_sample_at")
    if previous_sample_at is not None:
        gap = time.time() - float(previous_sample_at)
        if gap > max(120.0, args.soak_sample_seconds * 2):
            state["soak_interruptions"] = int(state.get("soak_interruptions", 0)) + 1
            state["soak_observed_seconds"] = 0.0
            state["soak_started_at"] = time.time()
    required_seconds = float(state["required_soak_hours"]) * 3600
    while float(state["soak_observed_seconds"]) < required_seconds:
        interval_started = time.monotonic()
        sample = (
            args.evidence_dir
            / f"probe-soak-{int(state['soak_observed_seconds']):09d}.json"
        )
        result = _sample_probe(args.stack, sample)
        if sample.is_file():
            _record_probe(state, sample)
        if result["returncode"] != 0:
            state["last_failure"] = sample.name
            _atomic_json(args.state, state)
            return 1
        state["soak_last_sample_at"] = time.time()
        _atomic_json(args.state, state)
        time.sleep(
            min(
                args.soak_sample_seconds,
                max(0.0, required_seconds - state["soak_observed_seconds"]),
            )
        )
        state["soak_observed_seconds"] = float(
            state["soak_observed_seconds"]
        ) + (time.monotonic() - interval_started)
        _atomic_json(args.state, state)

    # Engine interruption is deliberately delegated to the supported Desktop
    # helper. Every trial remains bounded and diagnostics-preserving.
    for trial in range(
        int(state["engine_recovery_trials"]), args.engine_recovery_trials
    ):
        trial_started = time.monotonic()
        before = _volume_ids(args.project)
        interruption = _run(["docker", "desktop", "restart"], 180)
        remaining = max(1.0, 180.0 - (time.monotonic() - trial_started))
        recovery = (
            _manager("recover", args.stack, remaining)
            if interruption["returncode"] == 0
            else {"returncode": 1, "stderr": "interruption failed"}
        )
        status = (
            _manager("status", args.stack, min(30.0, remaining))
            if recovery["returncode"] == 0
            else {"returncode": 1, "stderr": "recovery failed"}
        )
        trial_probe = args.evidence_dir / f"probe-recovery-{trial + 1:03d}.json"
        probe = (
            _sample_probe(args.stack, trial_probe)
            if status["returncode"] == 0
            else {"returncode": 1, "stderr": "status failed"}
        )
        if trial_probe.is_file():
            _record_probe(state, trial_probe)
        after = _volume_ids(args.project)
        duration = time.monotonic() - trial_started
        success = (
            interruption["returncode"] == 0
            and recovery["returncode"] == 0
            and status["returncode"] == 0
            and probe["returncode"] == 0
            and duration <= 180
            and before == after
        )
        result = {
            "interruption": interruption,
            "recovery": recovery,
            "status": status,
            "probe": probe,
            "returncode": 0 if success else 1,
            "duration_seconds": round(duration, 3),
            "volume_ids_before": sorted(before),
            "volume_ids_after": sorted(after),
        }
        state["engine_recovery_trials"] = trial + 1
        state["engine_recovery_successes"] = int(
            state["engine_recovery_successes"]
        ) + int(success)
        state["volume_loss"] = bool(state["volume_loss"]) or before != after
        _atomic_json(
            args.evidence_dir / f"engine-recovery-{trial + 1:03d}.json", result
        )
        _atomic_json(args.state, state)

    raw_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(args.evidence_dir.glob("*.json"))
    }
    signature_path = args.summary.with_suffix(args.summary.suffix + ".asc")
    gates = release_gates(state, signature_exists=False)
    summary = {
        "schema_version": "bioetl-docker-stability-summary-v1",
        "state": state,
        "raw_evidence_sha256": raw_hashes,
        "release_gates": gates,
        "promotion_passed": all(gates.values()),
    }
    _atomic_json(args.summary, summary)
    _sign(args.summary, args.signing_key)
    gates = release_gates(
        state, signature_exists=_signature_valid(args.summary, signature_path)
    )
    summary["release_gates"] = gates
    summary["promotion_passed"] = all(gates.values())
    _atomic_json(args.summary, summary)
    _sign(args.summary, args.signing_key)
    if not _signature_valid(args.summary, signature_path):
        summary["release_gates"]["detached_signature_present"] = False
        summary["promotion_passed"] = False
        _atomic_json(args.summary, summary)
    return 0 if summary["promotion_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
