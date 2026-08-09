"""Authorization-gated EvidenceStore ingestion for Proof-or-Stop results."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from memory.evidence import EvidenceEvent, EvidenceStore
from memory.proof import ProofError, VerificationResult, verify_bundle
from memory.records import (
    ActorIdentity,
    RecordEnvelope,
    RecordType,
    TrustLevel,
)
from memory.scope import RepositoryScope
from memory.security import UnsafeMemoryContentError, inspect_memory_content

_SAFE_RECORD_COMPONENT = re.compile(r"[^a-zA-Z0-9._-]+")
_INGESTION_REJECTION_PREFIXES = (
    "schema:",
    "tampered_",
    "cross_scope:",
    "stale_bundle:",
    "stale_receipt:",
    "policy_drift",
    "command_set_drift",
    "acceptance_policy_drift:",
    "duplicate_receipt_id",
    "unknown_evidence_kind:",
    "unauthorized_producer:",
    "command_not_authorized:",
    "failed_reported_as_pass:",
    "missing_skip_reason:",
    "missing_follow_up:",
    "attestation_mismatch:",
    "unsupported_trust_tier:",
    "untrusted_execution:",
)


class ProofIngestionAuthorizationError(PermissionError):
    """Raised before any write when ingestion authority is absent."""


def _record_component(value: str) -> str:
    component = _SAFE_RECORD_COMPONENT.sub("-", value.strip()).strip(".-")
    return component[:96] or "unknown"


def _trust_level(trust_tier: str) -> TrustLevel:
    if trust_tier == "independent_evaluator":
        return TrustLevel.REVIEWED_EXTERNAL
    if trust_tier in {"ci", "local_single_host"}:
        return TrustLevel.TRUSTED_REPOSITORY
    return TrustLevel.UNTRUSTED


def _require_authority(*, actor: str, runtime: str, memory_mode: str | None) -> None:
    effective_mode = memory_mode or os.environ.get("BIOETL_AI_MEMORY_MODE")
    if effective_mode != "read-write":
        raise ProofIngestionAuthorizationError(
            "Proof-or-Stop ingestion requires BIOETL_AI_MEMORY_MODE=read-write"
        )
    if not actor.strip():
        raise ProofIngestionAuthorizationError(
            "Proof-or-Stop ingestion requires a non-empty actor identity"
        )
    if not runtime.strip():
        raise ProofIngestionAuthorizationError(
            "Proof-or-Stop ingestion requires a non-empty runtime identity"
        )
    configured_actor = os.environ.get("BIOETL_AI_AGENT")
    if configured_actor and configured_actor != actor:
        raise ProofIngestionAuthorizationError(
            "actor does not match BIOETL_AI_AGENT authorization context"
        )
    configured_runtime = os.environ.get("BIOETL_AI_RUNTIME")
    if configured_runtime and configured_runtime != runtime:
        raise ProofIngestionAuthorizationError(
            "runtime does not match BIOETL_AI_RUNTIME authorization context"
        )


def _require_live_scope(
    *, bundle: dict[str, Any], repo_root: Path, expected_task_id: str
) -> None:
    if str(bundle.get("task_id")) != expected_task_id:
        raise ProofError("cross_scope:task_id")
    live = RepositoryScope.discover(repo_root, task_id=expected_task_id)
    repository = bundle.get("repository", {})
    source = bundle.get("source", {})
    expected = {
        "repo_id": live.repo_id,
        "branch": live.branch,
        "worktree_id": live.worktree_id,
        "head_sha": live.git_commit,
    }
    actual = {
        "repo_id": str(repository.get("repo_id", "")),
        "branch": str(repository.get("branch", "")),
        "worktree_id": str(repository.get("worktree_id", "")),
        "head_sha": str(source.get("head_sha", "")),
    }
    mismatches = [field for field in expected if actual[field] != expected[field]]
    if mismatches:
        raise ProofError("cross_scope:" + ",".join(sorted(mismatches)))


def _require_verification_binding(
    *,
    bundle: dict[str, Any],
    verification: dict[str, Any],
    result: VerificationResult,
) -> None:
    binding = {
        "bundle_digest": bundle.get("bundle_digest"),
        "claim": bundle.get("claim"),
        "run_id": bundle.get("run_id"),
    }
    for field, expected in binding.items():
        if verification.get(field) != expected:
            raise ProofError(f"verification_binding_mismatch:{field}")
    for field, expected in result.to_dict().items():
        if verification.get(field) != expected:
            raise ProofError(f"verification_result_mismatch:{field}")
    rejected = [
        error
        for error in result.errors
        if error.startswith(_INGESTION_REJECTION_PREFIXES)
    ]
    if rejected:
        raise ProofError("bundle_not_ingestible:" + ",".join(sorted(rejected)))


def _preflight_events(events: list[EvidenceEvent]) -> None:
    for event in events:
        rendered = json.dumps(event.content_payload(), sort_keys=True)
        findings = inspect_memory_content(rendered)
        if findings:
            raise UnsafeMemoryContentError(findings)


def _envelope(
    *,
    bundle: dict[str, Any],
    actor: ActorIdentity,
    record_id: str,
    source_refs: tuple[str, ...],
    source_hashes: dict[str, str],
) -> RecordEnvelope:
    repository = bundle["repository"]
    source = bundle["source"]
    return RecordEnvelope.create(
        record_id=record_id,
        record_type=RecordType.EVIDENCE,
        repo_id=str(repository["repo_id"]),
        git_commit=str(source["head_sha"]),
        branch=str(repository["branch"]),
        worktree_id=str(repository["worktree_id"]),
        task_id=str(bundle["task_id"]),
        actor=actor,
        source_refs=source_refs,
        source_hashes=source_hashes,
        trust=_trust_level(str(bundle["trust_tier"])),
    )


def ingest_bundle(
    *,
    bundle: dict[str, Any],
    verification: dict[str, Any],
    storage_root: Path,
    repo_root: Path,
    expected_task_id: str,
    policy: dict[str, Any],
    schema: dict[str, Any],
    actor: str,
    runtime: str,
    model: str | None = None,
    memory_mode: str | None = None,
) -> list[str]:
    """Append receipt and gate evidence after explicit authorization.

    The adapter intentionally exposes no DecisionRecord or override path.
    """
    _require_authority(actor=actor, runtime=runtime, memory_mode=memory_mode)
    _require_live_scope(
        bundle=bundle, repo_root=repo_root, expected_task_id=expected_task_id
    )
    result = verify_bundle(
        bundle=bundle,
        repo_root=repo_root,
        policy=policy,
        schema=schema,
        check_current_source=True,
    )
    _require_verification_binding(
        bundle=bundle, verification=verification, result=result
    )
    repository = bundle["repository"]
    source = bundle["source"]
    scope = RepositoryScope(
        repo_id=str(repository["repo_id"]),
        git_commit=str(source["head_sha"]),
        branch=str(repository["branch"]),
        worktree_id=str(repository["worktree_id"]),
        task_id=str(bundle["task_id"]),
    )
    store = EvidenceStore(scope.namespace_path(storage_root))
    identity = ActorIdentity(runtime=runtime, agent=actor, model=model)
    run_id = _record_component(str(bundle["run_id"]))
    events: list[EvidenceEvent] = []

    for receipt in bundle["receipts"]:
        receipt_id = _record_component(str(receipt["receipt_id"]))
        envelope = _envelope(
            bundle=bundle,
            actor=identity,
            record_id=f"proof-receipt-{run_id}-{receipt_id}",
            source_refs=(
                f"proof-or-stop:{bundle['run_id']}",
                f"receipt:{receipt['receipt_id']}",
            ),
            source_hashes={
                "bundle": str(bundle["bundle_digest"]),
                "receipt": str(receipt["receipt_digest"]),
                "output": str(receipt["output_digest"]),
            },
        )
        event = EvidenceEvent(
            envelope=envelope,
            evidence_kind="proof_or_stop_receipt",
            observation=(
                f"{receipt['evidence_kind']} receipt from {receipt['producer']} "
                f"reported {receipt['status']}"
            ),
            command=str(receipt["command"]),
            result={
                "status": receipt["status"],
                "exit_code": receipt["exit_code"],
                "skip_reason": receipt.get("skip_reason"),
                "follow_up": receipt.get("follow_up"),
                "bundle_actor": bundle["actor"],
                "bundle_runtime": bundle["runtime"],
                "bundle_trust_tier": bundle["trust_tier"],
                "bundle_digest": bundle["bundle_digest"],
                "receipt_digest": receipt["receipt_digest"],
                "output_digest": receipt["output_digest"],
            },
        )
        events.append(event)

    gate_envelope = _envelope(
        bundle=bundle,
        actor=identity,
        record_id=f"proof-gate-{run_id}",
        source_refs=(f"proof-or-stop:{bundle['run_id']}",),
        source_hashes={"bundle": str(bundle["bundle_digest"])},
    )
    gate_event = EvidenceEvent(
        envelope=gate_envelope,
        evidence_kind="proof_or_stop_gate",
        observation=(
            f"Proof-or-Stop outcome {verification['outcome']} for claim "
            f"{bundle['claim']}"
        ),
        result={
            "outcome": result.outcome,
            "claim_qualified": result.claim_qualified,
            "errors": list(result.errors),
            "degradations": list(result.degradations),
            "bundle_actor": bundle["actor"],
            "bundle_runtime": bundle["runtime"],
            "bundle_trust_tier": bundle["trust_tier"],
            "bundle_digest": bundle["bundle_digest"],
        },
    )
    events.append(gate_event)
    _preflight_events(events)
    return [store.append_evidence(event) for event in events]
