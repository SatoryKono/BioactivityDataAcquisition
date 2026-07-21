"""Continuous, gap-sensitive soak stage (minimum 7.2 hours for RF-008)."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .commands import observe_docker_vm_reserve, probe_command, record_probe
from .model import atomic_json, load_json
from .stage_support import (
    clean_baseline,
    index_and_save,
    manager_step,
    probe_services,
    save_state,
)


def reset_soak_window(state: dict[str, Any], now: float) -> None:
    if state.get("soak_started_at") is not None:
        state["soak_interruptions"] = int(state.get("soak_interruptions", 0)) + 1
    state["soak_generation"] = int(state.get("soak_generation", 0)) + 1
    state["soak_started_at"] = now
    state["soak_last_sample_at"] = None
    state["soak_observed_seconds"] = 0.0
    state["soak_samples_current_window"] = 0
    state["soak_window_interrupted"] = False


def _load_or_create_baselines(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    soak_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
) -> tuple[dict[str, Path], dict[str, dict[str, str]]] | None:
    baselines: dict[str, Path] = {}
    pinned_ids: dict[str, dict[str, str]] = {}
    for spec in bundle:
        baseline = soak_dir / f"baseline-{spec.stack}.json"
        if baseline.exists():
            pinned = load_json(baseline)
            pinned_ids[spec.stack] = {
                str(key): str(value)
                for key, value in pinned.get("container_ids", {}).items()
            }
            if not pinned_ids[spec.stack]:
                state["soak_window_interrupted"] = True
                state["last_failure"] = f"soak-baseline-invalid-{spec.stack}"
                index_and_save(state, state_path, evidence_dir)
                return None
            baselines[spec.stack] = baseline
            continue
        baseline_probe = soak_dir / f"probe-baseline-{spec.stack}.json"
        result = probe_command(
            runtime_origin, spec, baseline_probe, 75.0, contract=contract
        )
        if result["returncode"] != 0:
            state["soak_window_interrupted"] = True
            state["last_failure"] = f"soak-baseline-{spec.stack}"
            index_and_save(state, state_path, evidence_dir)
            return None
        try:
            pinned_ids[spec.stack] = clean_baseline(baseline_probe, baseline)
        except ValueError:
            state["soak_window_interrupted"] = True
            state["last_failure"] = f"soak-restart-baseline-{spec.stack}"
            index_and_save(state, state_path, evidence_dir)
            return None
        baselines[spec.stack] = baseline
        record_probe(state, baseline_probe)
    return baselines, pinned_ids


def run_soak(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
    sample_seconds: float,
) -> bool:
    required = float(state["required_soak_hours"]) * 3600
    if float(state.get("soak_observed_seconds", 0.0)) >= required:
        return True
    now = time.time()
    allowed_gap = max(120.0, sample_seconds * 2.0)
    last = state.get("soak_last_sample_at")
    if state.get("soak_started_at") is None or (
        last is not None and now - float(last) > allowed_gap
    ):
        reset_soak_window(state, now)
    generation = int(state["soak_generation"])
    soak_dir = evidence_dir / "soak" / f"window-{generation:03d}"
    for spec in bundle:
        result = manager_step(
            runtime_origin,
            contract,
            spec,
            "start",
            soak_dir / f"manager-start-{spec.stack}",
            180.0,
        )
        if result["returncode"] != 0:
            state["soak_window_interrupted"] = True
            state["last_failure"] = f"soak-start-{spec.stack}"
            index_and_save(state, state_path, evidence_dir)
            return False
    prepared = _load_or_create_baselines(
        state,
        state_path,
        evidence_dir,
        soak_dir,
        runtime_origin,
        contract,
        bundle,
    )
    if prepared is None:
        return False
    baselines, pinned_ids = prepared
    index_and_save(state, state_path, evidence_dir)
    sequence = int(state.get("soak_samples_current_window", 0))
    while float(state["soak_observed_seconds"]) < required:
        sampled_at = time.time()
        previous = state.get("soak_last_sample_at")
        if previous is not None and sampled_at - float(previous) > allowed_gap:
            state["soak_window_interrupted"] = True
            index_and_save(state, state_path, evidence_dir)
            reset_soak_window(state, sampled_at)
            save_state(state_path, state)
            return run_soak(
                state,
                state_path,
                evidence_dir,
                runtime_origin,
                contract,
                bundle,
                sample_seconds,
            )
        sequence += 1
        sample_steps: list[dict[str, Any]] = []
        clean = True
        for spec in bundle:
            output = soak_dir / f"probe-{sequence:07d}-{spec.stack}.json"
            result = probe_command(
                runtime_origin,
                spec,
                output,
                75.0,
                contract=contract,
                baseline=baselines[spec.stack],
            )
            sample_steps.append({"stack": spec.stack, "result": result})
            if (
                result["returncode"] != 0
                or probe_services(output) != pinned_ids[spec.stack]
            ):
                clean = False
            if output.exists():
                record_probe(state, output)
        capacity = observe_docker_vm_reserve(state, runtime_origin)
        clean = clean and capacity["returncode"] == 0
        atomic_json(
            soak_dir / f"sample-{sequence:07d}.json",
            {
                "sample": sequence,
                "sampled_at": sampled_at,
                "clean": clean,
                "capacity": capacity,
                "steps": sample_steps,
            },
            replace=False,
        )
        if not clean:
            state["soak_window_interrupted"] = True
            state["last_failure"] = f"soak-sample-{sequence:07d}"
            index_and_save(state, state_path, evidence_dir)
            return False
        if previous is not None:
            state["soak_observed_seconds"] = float(state["soak_observed_seconds"]) + (
                sampled_at - float(previous)
            )
        state["soak_last_sample_at"] = sampled_at
        state["soak_samples_current_window"] = sequence
        state["last_failure"] = None
        index_and_save(state, state_path, evidence_dir)
        if float(state["soak_observed_seconds"]) < required:
            time.sleep(
                min(sample_seconds, required - float(state["soak_observed_seconds"]))
            )
    return True
