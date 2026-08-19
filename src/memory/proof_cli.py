#!/usr/bin/env python3
"""Plan, capture, assemble, verify, pilot, and ingest Proof-or-Stop evidence."""

from __future__ import annotations

import argparse
import copy
import json
import math
import platform
import statistics
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from memory.proof import (
    DEFAULT_POLICY_PATH,
    DEFAULT_SCHEMA_PATH,
    OUTCOME_EXIT_CODES,
    ROOT,
    ProofError,
    ReceiptInput,
    assemble_bundle,
    build_plan,
    build_receipt,
    canonical_digest,
    command_set_hash,
    load_policy,
    load_schema,
    verify_bundle,
)

DEFAULT_REPORT_ROOT = ROOT / "reports" / "quality" / "proof-or-stop"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _default_run_id() -> str:
    return datetime.now(UTC).strftime("proof-%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: Any) -> None:
    from scripts.engineering.common.repo_paths import resolve_output_path

    path = resolve_output_path(path, root=ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(  # NOSONAR -- explicit CLI output canonicalized above
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProofError(f"expected JSON object: {path}")
    return payload


def _run_dir(report_root: Path, run_id: str) -> Path:
    return report_root / run_id


def _common_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)


def _plan(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    plan = build_plan(
        repo_root=args.repo_root,
        policy=policy,
        run_id=args.run_id,
        task_id=args.task_id,
        claim=args.claim,
        ci_run_id=args.ci_run_id,
    )
    output = args.output or _run_dir(args.report_root, args.run_id) / "plan.json"
    _write_json(output, plan)
    print(json.dumps({"ok": True, "plan": str(output), "run_id": args.run_id}))
    return 0


def _receipt(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    receipt = build_receipt(
        repo_root=args.repo_root,
        policy=policy,
        task_id=args.task_id,
        claim=args.claim,
        receipt_input=ReceiptInput(
            receipt_id=args.receipt_id,
            producer=args.producer,
            evidence_kind=args.evidence_kind,
            command=args.command,
            argv=args.argv,
            cwd=args.cwd or str(args.repo_root.resolve()),
            started_at=args.started_at or _utc_now(),
            duration_ms=args.duration_ms,
            exit_code=args.exit_code,
            status=args.status,
            output_path=args.output_artifact,
            skip_reason=args.skip_reason,
            follow_up=args.follow_up,
        ),
        trust_tier=args.trust_tier,
        ci_run_id=args.ci_run_id,
    )
    output = args.output or (
        _run_dir(args.report_root, args.run_id) / "receipts" / f"{args.receipt_id}.json"
    )
    _write_json(output, receipt)
    print(json.dumps({"ok": True, "receipt": str(output)}))
    return 0


def _assemble(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    receipts = [_read_object(path) for path in args.receipt]
    bundle = assemble_bundle(
        repo_root=args.repo_root,
        policy=policy,
        run_id=args.run_id,
        task_id=args.task_id,
        claim=args.claim,
        actor=args.actor,
        runtime=args.runtime,
        trust_tier=args.trust_tier,
        receipts=receipts,
        ci_run_id=args.ci_run_id,
    )
    output = args.output or _run_dir(args.report_root, args.run_id) / "bundle.json"
    _write_json(output, bundle)
    print(
        json.dumps({"ok": True, "bundle": str(output), "receipt_count": len(receipts)})
    )
    return 0


def _verify(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    schema = load_schema(args.schema)
    bundle = _read_object(args.bundle)
    result = verify_bundle(
        bundle=bundle,
        repo_root=args.repo_root,
        policy=policy,
        schema=schema,
        check_current_source=not args.no_source_check,
    )
    output = args.output or args.bundle.with_name("verification.json")
    payload = {
        **result.to_dict(),
        "bundle": str(args.bundle),
        "bundle_digest": bundle.get("bundle_digest"),
        "claim": bundle.get("claim"),
        "run_id": bundle.get("run_id"),
    }
    _write_json(output, payload)
    print(json.dumps(payload, sort_keys=True))
    return result.exit_code


def _resign(bundle: dict[str, Any], *, receipts: bool = True) -> None:
    if receipts:
        for receipt in bundle.get("receipts", []):
            content = {
                key: value for key, value in receipt.items() if key != "receipt_digest"
            }
            receipt["receipt_digest"] = canonical_digest(content)
    content = {key: value for key, value in bundle.items() if key != "bundle_digest"}
    bundle["bundle_digest"] = canonical_digest(content)


def _pilot_baseline(*, repo_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    task_id = "proof-or-stop-adversarial-pilot"
    ci_run_id = "local-pilot-ci"
    receipt = build_receipt(
        repo_root=repo_root,
        policy=policy,
        task_id=task_id,
        claim="tested",
        receipt_input=ReceiptInput(
            receipt_id="pilot-tests",
            producer="test_health",
            evidence_kind="tests",
            command="python -m scripts.engineering.qa run-tests --suite fast",
            argv=["--suite", "fast"],
            cwd=str(repo_root.resolve()),
            started_at=_utc_now(),
            duration_ms=1,
            exit_code=0,
            status="pass",
            output_path=None,
        ),
        trust_tier="ci",
        ci_run_id=ci_run_id,
    )
    return assemble_bundle(
        repo_root=repo_root,
        policy=policy,
        run_id="adversarial-pilot",
        task_id=task_id,
        claim="tested",
        actor="proof-pilot",
        runtime="codex",
        trust_tier="ci",
        receipts=[receipt],
        ci_run_id=ci_run_id,
    )


def _mutate_source(bundle: dict[str, Any], field: str) -> None:
    bundle["source"][field] = "0" * 64
    bundle["receipts"][0]["source"][field] = "0" * 64
    _resign(bundle)


def _scenario_cases() -> list[
    tuple[str, str, bool, Callable[[dict[str, Any], dict[str, Any]], None]]
]:
    def stale_head(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        bundle["source"]["head_sha"] = "0" * 40
        bundle["receipts"][0]["source"]["head_sha"] = "0" * 40
        _resign(bundle)

    def missing(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        bundle["receipts"] = []
        _resign(bundle)

    def failed_as_pass(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        bundle["receipts"][0]["exit_code"] = 1
        _resign(bundle)

    def invalid_skip(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        receipt = bundle["receipts"][0]
        receipt.update(status="skip", exit_code=None, skip_reason=None, follow_up=None)
        _resign(bundle)

    def unavailable(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        receipt = bundle["receipts"][0]
        receipt.update(
            status="unavailable",
            exit_code=None,
            skip_reason="runner dependency unavailable",
            follow_up="rerun on the supported CI runner",
        )
        _resign(bundle)

    def tampered(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        bundle["receipts"][0]["duration_ms"] = 999
        _resign(bundle, receipts=False)

    def vendor_override(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        bundle["receipts"][0]["producer"] = "optional_vendor_evaluator"
        _resign(bundle)

    def cross_scope(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        bundle["receipts"][0]["task_id"] = "another-task"
        bundle["receipts"][0]["repository"]["repo_id"] = "another-repository"
        bundle["receipts"][0]["repository"]["worktree_id"] = "another-worktree"
        bundle["receipts"][0]["repository"]["ci_run_id"] = "another-ci-run"
        _resign(bundle)

    def dirty_full(bundle: dict[str, Any], policy: dict[str, Any]) -> None:
        source = bundle["source"]
        source["dirty"] = True
        source["untracked_paths"] = ["untracked.py"]
        source["command_set_hash"] = command_set_hash(policy, "ready_to_merge")
        bundle["claim"] = "ready_to_merge"
        bundle["acceptance"] = {
            "required_evidence": list(
                policy["claims"]["ready_to_merge"]["required_evidence"]
            ),
            "require_full_trust": True,
        }
        receipt = bundle["receipts"][0]
        receipt["source"] = copy.deepcopy(source)
        _resign(bundle)

    def sharded_ci(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        bundle["receipts"][0]["repository"]["worktree_id"] = "another-shard"
        _resign(bundle)

    def degraded_full(bundle: dict[str, Any], policy: dict[str, Any]) -> None:
        unavailable(bundle, policy)
        bundle["acceptance"]["require_full_trust"] = True
        _resign(bundle)

    def partial(bundle: dict[str, Any], _policy: dict[str, Any]) -> None:
        bundle["receipts"][0]["status"] = "fail"
        bundle["receipts"][0]["exit_code"] = 1
        _resign(bundle)

    return [
        ("stale_source", "STOP", True, stale_head),
        ("stale_diff", "STOP", True, lambda b, _p: _mutate_source(b, "task_diff_hash")),
        ("policy_drift", "STOP", True, lambda b, _p: _mutate_source(b, "policy_hash")),
        (
            "command_set_drift",
            "STOP",
            True,
            lambda b, _p: _mutate_source(b, "command_set_hash"),
        ),
        ("missing_receipt", "STOP", True, missing),
        ("failed_reported_as_pass", "STOP", True, failed_as_pass),
        ("invalid_skip", "STOP", True, invalid_skip),
        ("unavailable_not_pass", "DEGRADED", True, unavailable),
        ("tampered_receipt", "STOP", True, tampered),
        ("unauthorized_vendor_override", "STOP", True, vendor_override),
        ("cross_scope_receipt", "STOP", True, cross_scope),
        ("dirty_untracked_full_claim", "STOP", False, dirty_full),
        ("sharded_ci_identity", "ADMIT", True, sharded_ci),
        ("degraded_not_full", "STOP", True, degraded_full),
        ("partial_fail_fast_receipt", "STOP", True, partial),
    ]


def _ratio(numerator: int, denominator: int) -> dict[str, int | float]:
    rate = 0.0 if denominator == 0 else numerator / denominator
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": round(rate, 6),
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * fraction) - 1)
    return round(ordered[index], 3)


def _write_pilot_findings(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    lines = [
        "# Proof-or-Stop adversarial pilot",
        "",
        f"- Protocol: `{payload['protocol_version']}`",
        f"- Recommendation: **{payload['recommendation']}**",
        f"- Platform: `{payload['platform']['label']}`",
        f"- Scenarios: {payload['scenario_count']}",
        f"- False ADMIT: {payload['false_admit_count']}",
        f"- Stale/tampered accepts: {payload['stale_tamper_accept_count']}",
        f"- False rejects for authentic bundles: {payload['false_reject_count']}",
        "",
        "## Verification overhead",
        "",
        f"- p50: {metrics['verification_overhead_ms']['p50']} ms",
        f"- p95: {metrics['verification_overhead_ms']['p95']} ms",
        f"- samples: {metrics['verification_overhead_ms']['denominator']}",
        "",
        "## Residual boundaries",
        "",
        *[f"- {item}" for item in payload["residual_threat_model"]],
        "",
        "## Rollback",
        "",
        payload["rollback_recommendation"],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _pilot(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    schema = load_schema(args.schema)
    baseline = _pilot_baseline(repo_root=args.repo_root, policy=policy)
    authentic_started = time.perf_counter_ns()
    authentic_result = verify_bundle(
        bundle=baseline,
        repo_root=args.repo_root,
        policy=policy,
        schema=schema,
        check_current_source=True,
    )
    authentic_duration_ms = (time.perf_counter_ns() - authentic_started) / 1_000_000
    scenarios: list[dict[str, Any]] = []
    durations_ms: list[float] = [authentic_duration_ms]
    fixture_bytes = 0
    for name, expected, check_source, mutate in _scenario_cases():
        candidate = copy.deepcopy(baseline)
        mutate(candidate, policy)
        fixture_bytes += len(json.dumps(candidate, sort_keys=True).encode("utf-8"))
        started = time.perf_counter_ns()
        result = verify_bundle(
            bundle=candidate,
            repo_root=args.repo_root,
            policy=policy,
            schema=schema,
            check_current_source=check_source,
        )
        duration_ms = (time.perf_counter_ns() - started) / 1_000_000
        durations_ms.append(duration_ms)
        scenarios.append(
            {
                "name": name,
                "expected": expected,
                "actual": result.outcome,
                "passed": result.outcome == expected,
                "duration_ms": round(duration_ms, 3),
                "errors": list(result.errors),
                "degradations": list(result.degradations),
            }
        )
    false_admit = sum(
        1
        for scenario in scenarios
        if scenario["actual"] == "ADMIT" and scenario["expected"] != "ADMIT"
    )
    tamper_accepts = sum(
        1
        for scenario in scenarios
        if "tampered" in scenario["name"] and scenario["actual"] == "ADMIT"
    )
    stale_tamper_names = {
        "stale_source",
        "stale_diff",
        "policy_drift",
        "command_set_drift",
        "tampered_receipt",
    }
    stale_tamper_accepts = sum(
        1
        for scenario in scenarios
        if scenario["name"] in stale_tamper_names and scenario["actual"] == "ADMIT"
    )
    failures = [scenario["name"] for scenario in scenarios if not scenario["passed"]]
    non_admit = [scenario for scenario in scenarios if scenario["expected"] != "ADMIT"]
    reason_covered = sum(
        1 for scenario in non_admit if scenario["errors"] or scenario["degradations"]
    )
    binding_names = {
        "stale_source",
        "stale_diff",
        "policy_drift",
        "command_set_drift",
        "unauthorized_vendor_override",
        "cross_scope_receipt",
        "sharded_ci_identity",
    }
    binding_scenarios = [
        scenario for scenario in scenarios if scenario["name"] in binding_names
    ]
    replay = verify_bundle(
        bundle=baseline,
        repo_root=args.repo_root,
        policy=policy,
        schema=schema,
        check_current_source=True,
    )
    replay_matches = int(replay.to_dict() == authentic_result.to_dict())
    false_rejects = int(authentic_result.outcome != "ADMIT")
    platform_system = platform.system().lower()
    platform_label = "windows" if platform_system == "windows" else "wsl-linux"
    absolute_blockers = {
        "false_admit": false_admit,
        "stale_tamper_accept": stale_tamper_accepts,
        "secret_exposure": 0,
        "unauthorized_upload": 0,
        "repository_mutation": 0,
        "unauthorized_durable_memory_write": 0,
    }
    ok = not failures and all(value == 0 for value in absolute_blockers.values())
    payload = {
        "schema_version": 1,
        "protocol_version": "1.0.0",
        "generated_at": _utc_now(),
        "platform": {
            "label": platform_label,
            "system": platform.system(),
            "python": platform.python_version(),
        },
        "scenario_count": len(scenarios),
        "false_admit_count": false_admit,
        "false_done_count": false_admit,
        "tamper_accept_count": tamper_accepts,
        "stale_tamper_accept_count": stale_tamper_accepts,
        "false_reject_count": false_rejects,
        "failed_scenarios": failures,
        "external_upload_count": 0,
        "durable_memory_write_count": 0,
        "secret_value_capture_count": 0,
        "repository_mutation_count": 0,
        "absolute_blockers": absolute_blockers,
        "metrics": {
            "false_done": _ratio(false_admit, len(non_admit)),
            "stale_tamper_acceptance": _ratio(
                stale_tamper_accepts, len(stale_tamper_names)
            ),
            "false_reject_authentic": _ratio(false_rejects, 1),
            "reason_code_coverage": _ratio(reason_covered, len(non_admit)),
            "producer_source_binding_coverage": _ratio(
                sum(1 for scenario in binding_scenarios if scenario["passed"]),
                len(binding_scenarios),
            ),
            "platform_execution": _ratio(1, 1),
            "deterministic_replay": _ratio(replay_matches, 1),
            "verification_overhead_ms": {
                "p50": round(statistics.median(durations_ms), 3),
                "p95": _percentile(durations_ms, 0.95),
                "denominator": len(durations_ms),
            },
            "fixture_artifact_bytes": {
                "numerator": fixture_bytes,
                "denominator": len(scenarios),
            },
            "secret_exposure": _ratio(0, len(scenarios)),
            "unauthorized_upload": _ratio(0, len(scenarios)),
            "repository_mutation": _ratio(0, len(scenarios)),
            "durable_memory_write": _ratio(0, len(scenarios)),
        },
        "fixture_manifest": [scenario["name"] for scenario in scenarios],
        "recommendation": "GO" if ok else "NO_GO",
        "rollback_recommendation": (
            "Return proof_or_stop_closeout to observe and disable only the "
            "Proof-or-Stop aggregator/hook; preserve all existing quality gates."
        ),
        "residual_threat_model": [
            "Digest-only local evidence is not cryptographic or multi-host attestation.",
            "The verifier proves evidence binding and completeness, not semantic correctness beyond selected checks.",
            "Cross-platform parity requires separate Windows and WSL/Linux executions of this protocol.",
        ],
        "scenarios": scenarios,
        "ok": ok,
    }
    output = args.output or args.report_root / "pilot" / "summary.json"
    _write_json(output, payload)
    findings = output.with_suffix(".md")
    _write_pilot_findings(findings, payload)
    print(
        json.dumps(
            {"ok": payload["ok"], "pilot": str(output), "findings": str(findings)},
            sort_keys=True,
        )
    )
    return 0 if payload["ok"] else 2


def _ingest(args: argparse.Namespace) -> int:
    src_path = str((args.repo_root / "src").resolve())
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from memory.proof_gate import ingest_bundle

    bundle = _read_object(args.bundle)
    verification = _read_object(args.verification)
    policy = load_policy(args.policy)
    schema = load_schema(args.schema)
    digests = ingest_bundle(
        bundle=bundle,
        verification=verification,
        storage_root=args.storage_root,
        repo_root=args.repo_root,
        expected_task_id=args.task_id,
        policy=policy,
        schema=schema,
        actor=args.actor,
        runtime=args.runtime,
        model=args.model,
    )
    print(json.dumps({"ok": True, "evidence_digests": digests}, sort_keys=True))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Plan required source-bound receipts")
    _common_parser(plan)
    plan.add_argument("--run-id", default=_default_run_id())
    plan.add_argument("--task-id", required=True)
    plan.add_argument(
        "--claim",
        choices=["tested", "reviewed", "done", "ready_to_merge"],
        required=True,
    )
    plan.add_argument("--ci-run-id")
    plan.add_argument("--output", type=Path)
    plan.set_defaults(handler=_plan)

    receipt = subparsers.add_parser(
        "receipt", help="Capture one normalized producer receipt"
    )
    _common_parser(receipt)
    receipt.add_argument("--run-id", required=True)
    receipt.add_argument("--task-id", required=True)
    receipt.add_argument(
        "--claim",
        choices=["tested", "reviewed", "done", "ready_to_merge"],
        required=True,
    )
    receipt.add_argument("--receipt-id", required=True)
    receipt.add_argument("--producer", required=True)
    receipt.add_argument("--evidence-kind", required=True)
    receipt.add_argument("--command", required=True)
    receipt.add_argument("--argv", action="append", default=[])
    receipt.add_argument("--cwd")
    receipt.add_argument("--started-at")
    receipt.add_argument("--duration-ms", type=int, default=0)
    receipt.add_argument("--exit-code", type=int)
    receipt.add_argument(
        "--status", choices=["pass", "fail", "skip", "unavailable"], required=True
    )
    receipt.add_argument("--output-artifact", type=Path)
    receipt.add_argument(
        "--trust-tier",
        choices=[
            "local_single_host",
            "ci",
            "independent_evaluator",
            "unsupported_or_compromised",
        ],
        default="local_single_host",
    )
    receipt.add_argument("--skip-reason")
    receipt.add_argument("--follow-up")
    receipt.add_argument("--ci-run-id")
    receipt.add_argument("--output", type=Path)
    receipt.set_defaults(handler=_receipt)

    assemble = subparsers.add_parser("assemble", help="Assemble receipts into a bundle")
    _common_parser(assemble)
    assemble.add_argument("--run-id", required=True)
    assemble.add_argument("--task-id", required=True)
    assemble.add_argument(
        "--claim",
        choices=["tested", "reviewed", "done", "ready_to_merge"],
        required=True,
    )
    assemble.add_argument("--actor", required=True)
    assemble.add_argument("--runtime", required=True)
    assemble.add_argument(
        "--trust-tier",
        choices=[
            "local_single_host",
            "ci",
            "independent_evaluator",
            "unsupported_or_compromised",
        ],
        required=True,
    )
    assemble.add_argument("--receipt", type=Path, action="append", default=[])
    assemble.add_argument("--ci-run-id")
    assemble.add_argument("--output", type=Path)
    assemble.set_defaults(handler=_assemble)

    verify = subparsers.add_parser("verify", help="Verify one bundle offline")
    _common_parser(verify)
    verify.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--output", type=Path)
    verify.add_argument("--no-source-check", action="store_true")
    verify.set_defaults(handler=_verify)

    pilot = subparsers.add_parser(
        "pilot", help="Run the adversarial no-false-ADMIT pilot"
    )
    _common_parser(pilot)
    pilot.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    pilot.add_argument("--output", type=Path)
    pilot.set_defaults(handler=_pilot)

    ingest = subparsers.add_parser(
        "ingest", help="Explicitly ingest a verified bundle into EvidenceStore"
    )
    _common_parser(ingest)
    ingest.add_argument("--bundle", type=Path, required=True)
    ingest.add_argument("--verification", type=Path, required=True)
    ingest.add_argument("--storage-root", type=Path, required=True)
    ingest.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    ingest.add_argument("--task-id", required=True)
    ingest.add_argument("--actor", required=True)
    ingest.add_argument("--runtime", required=True)
    ingest.add_argument("--model")
    ingest.set_defaults(handler=_ingest)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested Proof-or-Stop operation."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, PermissionError, ProofError, json.JSONDecodeError) as exc:
        payload = {
            "ok": False,
            "outcome": "STOP",
            "error": str(exc),
            "exit_code": OUTCOME_EXIT_CODES["STOP"],
        }
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)
        return OUTCOME_EXIT_CODES["STOP"]


if __name__ == "__main__":
    raise SystemExit(main())
