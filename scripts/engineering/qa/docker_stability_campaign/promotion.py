"""Bounded Desktop recovery trials and immutable signed promotion evidence."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .commands import (
    bundle_volume_ids,
    desktop_recovery_diagnostic_bundle,
    observe_docker_vm_reserve,
    probe_command,
    record_probe,
    remaining_seconds,
    run_command,
)
from .model import (
    atomic_json,
    file_sha256,
    release_gates,
    validate_evidence_index,
)
from .stage_support import (
    clean_baseline,
    index_and_save,
    manager_step,
    probe_services,
)


def run_recovery_trials(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    contract: Path,
    bundle: Sequence[Any],
) -> bool:
    required = int(state["required_engine_recovery_trials"])
    while int(state["engine_recovery_trials"]) < required:
        number = int(state["engine_recovery_trials"]) + 1
        trial_dir = evidence_dir / "recovery" / f"trial-{number:03d}"
        before = bundle_volume_ids(runtime_origin, bundle)
        baselines: dict[str, Path] = {}
        pinned_ids: dict[str, dict[str, str]] = {}
        setup: list[dict[str, Any]] = []
        for spec in bundle:
            probe = trial_dir / f"probe-baseline-{spec.stack}.json"
            result = probe_command(runtime_origin, spec, probe, 75.0, contract=contract)
            setup.append({"stack": spec.stack, "result": result})
            if result["returncode"] != 0:
                state["last_failure"] = f"recovery-baseline-{number:03d}-{spec.stack}"
                index_and_save(state, state_path, evidence_dir)
                return False
            baseline = trial_dir / f"baseline-{spec.stack}.json"
            try:
                pinned_ids[spec.stack] = clean_baseline(probe, baseline)
            except ValueError:
                state["last_failure"] = f"recovery-restart-baseline-{number:03d}"
                index_and_save(state, state_path, evidence_dir)
                return False
            baselines[spec.stack] = baseline
        started = time.monotonic()
        deadline = started + 180.0
        steps: list[dict[str, Any]] = []
        interruption = run_command(
            ["docker", "desktop", "restart"],
            remaining_seconds(deadline, reserve=1.0),
            cwd=runtime_origin,
        )
        steps.append({"action": "desktop-restart", "result": interruption})
        clean = interruption["returncode"] == 0
        try:
            for spec in bundle:
                result = manager_step(
                    runtime_origin,
                    contract,
                    spec,
                    "recover",
                    trial_dir / f"manager-recover-{spec.stack}",
                    remaining_seconds(deadline, reserve=1.0),
                )
                steps.append({"stack": spec.stack, "action": "recover", "result": result})
                clean = clean and result["returncode"] == 0
            for spec in bundle:
                probe = trial_dir / f"probe-recovery-{spec.stack}.json"
                result = probe_command(
                    runtime_origin,
                    spec,
                    probe,
                    remaining_seconds(deadline, reserve=1.0),
                    contract=contract,
                    baseline=baselines[spec.stack],
                )
                steps.append({"stack": spec.stack, "action": "probe", "result": result})
                clean = clean and result["returncode"] == 0
                if probe.exists():
                    record_probe(state, probe)
                    clean = clean and probe_services(probe) == pinned_ids[spec.stack]
            after = bundle_volume_ids(
                runtime_origin,
                bundle,
                timeout=min(20.0, remaining_seconds(deadline, reserve=0.2)),
            )
            capacity = observe_docker_vm_reserve(
                state,
                runtime_origin,
                timeout=min(15.0, remaining_seconds(deadline, reserve=0.1)),
            )
            clean = clean and capacity["returncode"] == 0
        except (RuntimeError, TimeoutError) as exc:
            after = {}
            capacity = {"returncode": 1, "error": type(exc).__name__}
            steps.append({"action": "deadline", "error": type(exc).__name__})
            clean = False
        duration = time.monotonic() - started
        clean = clean and duration <= 180.0 and before == after
        incident_id = None if clean else f"engine-recovery-{number:03d}"
        post_trial_restore: list[dict[str, Any]] = []
        resolved = clean
        if incident_id:
            state.setdefault("incident_ids", []).append(incident_id)
            desktop_diagnostics = desktop_recovery_diagnostic_bundle(
                runtime_origin,
                trial_dir / "docker-desktop-recovery.json",
                180.0,
            )
            post_trial_restore.append(
                {
                    "action": "desktop-recovery-diagnostics",
                    "result": desktop_diagnostics,
                }
            )
            resolved = (
                desktop_diagnostics["returncode"] == 0
                and bool(desktop_diagnostics.get("diagnostic_bundle_present"))
            )
            for spec in bundle:
                repair = manager_step(
                    runtime_origin,
                    contract,
                    spec,
                    "recover",
                    trial_dir / f"post-trial-recover-{spec.stack}",
                    180.0,
                )
                post_trial_restore.append(
                    {"stack": spec.stack, "action": "recover", "result": repair}
                )
                resolved = resolved and repair["returncode"] == 0
                verification = trial_dir / f"post-trial-probe-{spec.stack}.json"
                verified = probe_command(
                    runtime_origin,
                    spec,
                    verification,
                    75.0,
                    contract=contract,
                    baseline=baselines[spec.stack],
                )
                post_trial_restore.append(
                    {"stack": spec.stack, "action": "probe", "result": verified}
                )
                resolved = resolved and verified["returncode"] == 0
                if verification.exists():
                    record_probe(state, verification)
            try:
                after = bundle_volume_ids(runtime_origin, bundle)
            except RuntimeError:
                after = {}
                resolved = False
            resolved = resolved and before == after
        if before != after:
            state["volume_loss"] = True
        atomic_json(
            trial_dir / "trial.json",
            {
                "schema_version": "bioetl-docker-engine-recovery-v2",
                "trial": number,
                "success": clean,
                "incident_id": incident_id,
                "duration_seconds": round(duration, 3),
                "setup": setup,
                "steps": steps,
                "post_trial_restore": post_trial_restore,
                "incident_resolved": resolved,
                "capacity": capacity,
                "volume_ids_before": before,
                "volume_ids_after": after,
            },
            replace=False,
        )
        state["engine_recovery_trials"] = number
        state["engine_recovery_successes"] = int(
            state["engine_recovery_successes"]
        ) + int(clean)
        state["last_failure"] = None if resolved else incident_id
        index_and_save(state, state_path, evidence_dir)
        if not resolved:
            return False
    return True


def secret_fingerprint(runtime_origin: Path, signing_key: str, expected: str) -> bool:
    result = run_command(
        [
            "gpg",
            "--batch",
            "--with-colons",
            "--fingerprint",
            "--list-secret-keys",
            signing_key,
        ],
        30.0,
        cwd=runtime_origin,
    )
    fingerprints = {
        line.split(":")[9].upper()
        for line in str(result["stdout"]).splitlines()
        if line.startswith("fpr:") and len(line.split(":")) > 9
    }
    return result["returncode"] == 0 and expected.upper() in fingerprints


def sign_and_verify(
    runtime_origin: Path,
    summary: Path,
    signing_key: str,
    fingerprint: str,
) -> tuple[Path, bool, dict[str, Any]]:
    signature = summary.with_suffix(summary.suffix + ".asc")
    if signature.exists():
        raise FileExistsError(f"refusing to replace detached signature: {signature}")
    signed = run_command(
        [
            "gpg",
            "--batch",
            "--armor",
            "--detach-sign",
            "--local-user",
            signing_key,
            "--output",
            str(signature),
            str(summary),
        ],
        60.0,
        cwd=runtime_origin,
    )
    verified = run_command(
        [
            "gpg",
            "--batch",
            "--status-fd",
            "1",
            "--verify",
            str(signature),
            str(summary),
        ],
        60.0,
        cwd=runtime_origin,
    )
    expected = fingerprint.upper()
    valid = signed["returncode"] == 0 and verified["returncode"] == 0 and any(
        line.startswith("[GNUPG:] VALIDSIG ")
        and line.split()[2].upper() == expected
        for line in str(verified["stdout"]).splitlines()
    )
    return signature, valid, {"sign": signed, "verify": verified}


def finalize_campaign(
    state: dict[str, Any],
    state_path: Path,
    evidence_dir: Path,
    runtime_origin: Path,
    summary: Path,
    signing_key: str,
    signing_fingerprint: str,
    bundle: Sequence[Any],
) -> bool:
    state["final_volume_ids"] = bundle_volume_ids(runtime_origin, bundle)
    if state["initial_volume_ids"] != state["final_volume_ids"]:
        state["volume_loss"] = True
    index_and_save(state, state_path, evidence_dir)
    validate_evidence_index(state, evidence_dir)
    gates = release_gates(state, signature_exists=False)
    operational = all(
        passed for name, passed in gates.items() if name != "detached_signature_present"
    )
    atomic_json(
        summary,
        {
            "schema_version": "bioetl-docker-stability-summary-v2",
            "campaign_identity": state["campaign_identity"],
            "state": state,
            "raw_evidence_sha256": state["evidence_sha256"],
            "operational_release_gates": {
                name: value
                for name, value in gates.items()
                if name != "detached_signature_present"
            },
            "operational_promotion_passed": operational,
        },
        replace=False,
    )
    if not operational:
        return False
    signature, valid, signing = sign_and_verify(
        runtime_origin, summary, signing_key, signing_fingerprint
    )
    full_gates = release_gates(state, signature_exists=valid)
    atomic_json(
        summary.with_suffix(summary.suffix + ".verification.json"),
        {
            "schema_version": "bioetl-docker-stability-signature-verification-v1",
            "summary_sha256": file_sha256(summary),
            "signature_sha256": file_sha256(signature) if signature.exists() else None,
            "signing_fingerprint": signing_fingerprint,
            "signing": signing,
            "release_gates": full_gates,
            "promotion_passed": all(full_gates.values()),
        },
        replace=False,
    )
    return all(full_gates.values())
