"""CLI orchestration for the resumable Docker stability campaign."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .cycles import bootstrap_campaign, run_cycles, run_fault_matrix
from .faults import build_fault_cases
from .model import (
    bundle_identity,
    canonical_runtime_origin,
    load_contract,
    load_json,
    new_state,
    release_bundle,
    validate_evidence_index,
)
from .promotion import finalize_campaign, run_recovery_trials, secret_fingerprint
from .soak import run_soak
from .stage_support import save_state

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RUNTIME_ORIGIN = Path(
    "/home/fedor/.local/share/bioetl-runtime/BioactivityDataAcquisition2"
)
DEFAULT_CONTRACT = Path("configs/quality/docker_runtime_contracts.yaml")
CONFIRM_TOKEN = "I_UNDERSTAND_THIS_INTERRUPTS_DOCKER_DESKTOP"
FINGERPRINT = re.compile(r"^[0-9A-F]{40,64}$")


def campaign_identity(
    *,
    runtime_origin: Path,
    contract: Path,
    contract_sha256: str,
    bundle: Sequence[Any],
    cycles: int,
    soak_hours: float,
    sample_seconds: float,
    recovery_trials: int,
    evidence_dir: Path,
    summary: Path,
    signing_fingerprint: str,
) -> dict[str, Any]:
    return {
        "runtime_origin": str(runtime_origin),
        "contract": str(contract),
        "contract_sha256": contract_sha256,
        "release_bundle": bundle_identity(bundle),
        "required_cycles": cycles,
        "required_soak_hours": soak_hours,
        "soak_sample_seconds": sample_seconds,
        "required_engine_recovery_trials": recovery_trials,
        "fault_cases": [case.name for case in build_fault_cases()],
        "evidence_dir": str(evidence_dir.resolve()),
        "summary": str(summary.resolve()),
        "signing_fingerprint": signing_fingerprint,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-origin", type=Path, default=DEFAULT_RUNTIME_ORIGIN)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--cycles", type=int, default=100)
    parser.add_argument("--soak-hours", type=float, default=72.0)
    parser.add_argument("--soak-sample-seconds", type=float, default=60.0)
    parser.add_argument("--engine-recovery-trials", type=int, default=10)
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
    parser.add_argument("--signing-fingerprint")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if not args.execute:
        raise ValueError("refusing to count evidence without --execute")
    if args.cycles < 100 or args.soak_hours < 72 or args.engine_recovery_trials < 10:
        raise ValueError("release thresholds cannot be reduced")
    if args.soak_sample_seconds < 1:
        raise ValueError("soak sample interval must be at least one second")
    if args.confirm_host_disruption != CONFIRM_TOKEN:
        raise ValueError("host disruption requires the exact scheduling token")
    if not args.signing_key or not args.signing_fingerprint:
        raise ValueError("an approved signing key and fingerprint are required")
    fingerprint = re.sub(r"\s+", "", args.signing_fingerprint).upper()
    if not FINGERPRINT.fullmatch(fingerprint):
        raise ValueError("signing fingerprint must be a full hexadecimal fingerprint")
    args.signing_fingerprint = fingerprint


def run(args: argparse.Namespace) -> bool:
    validate_args(args)
    runtime_origin = canonical_runtime_origin(args.runtime_origin)
    contract_path, contract_payload, contract_sha = load_contract(
        runtime_origin, args.contract
    )
    bundle = release_bundle(contract_payload)
    state_path = args.state.resolve()
    evidence_dir = args.evidence_dir.resolve()
    summary = args.summary.resolve()
    identity = campaign_identity(
        runtime_origin=runtime_origin,
        contract=contract_path,
        contract_sha256=contract_sha,
        bundle=bundle,
        cycles=args.cycles,
        soak_hours=args.soak_hours,
        sample_seconds=args.soak_sample_seconds,
        recovery_trials=args.engine_recovery_trials,
        evidence_dir=evidence_dir,
        summary=summary,
        signing_fingerprint=args.signing_fingerprint,
    )
    if not secret_fingerprint(
        runtime_origin, args.signing_key, args.signing_fingerprint
    ):
        raise ValueError(
            "approved secret signing key does not match the exact fingerprint"
        )
    state = load_json(state_path)
    if state:
        if state.get("campaign_identity") != identity:
            raise ValueError("cannot resume campaign with different immutable identity")
        validate_evidence_index(state, evidence_dir)
    else:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        if any(evidence_dir.iterdir()):
            raise ValueError("new campaign requires an empty evidence directory")
        if summary.exists() or summary.with_suffix(summary.suffix + ".asc").exists():
            raise ValueError("new campaign refuses existing promotion artifacts")
        state = new_state(cycles=args.cycles, soak_hours=args.soak_hours, bundle=bundle)
        state["required_engine_recovery_trials"] = args.engine_recovery_trials
        state["campaign_identity"] = identity
        save_state(state_path, state)
    if not bootstrap_campaign(
        state, state_path, evidence_dir, runtime_origin, contract_path, bundle
    ):
        return False
    if not run_fault_matrix(
        state, state_path, evidence_dir, runtime_origin, contract_path, bundle
    ):
        return False
    if not run_cycles(
        state, state_path, evidence_dir, runtime_origin, contract_path, bundle
    ):
        return False
    if not run_soak(
        state,
        state_path,
        evidence_dir,
        runtime_origin,
        contract_path,
        bundle,
        args.soak_sample_seconds,
    ):
        return False
    if not run_recovery_trials(
        state, state_path, evidence_dir, runtime_origin, contract_path, bundle
    ):
        return False
    return finalize_campaign(
        state,
        state_path,
        evidence_dir,
        runtime_origin,
        summary,
        args.signing_key,
        args.signing_fingerprint,
        bundle,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        passed = run(args)
    except (FileExistsError, KeyError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}),
            file=sys.stderr,
        )
        return 2
    return 0 if passed else 1
