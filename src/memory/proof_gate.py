"""Authorization-gated EvidenceStore ingestion for Proof-or-Stop results."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from memory.evidence import EvidenceEvent, EvidenceStore
from memory.records import (
    ActorIdentity,
    RecordEnvelope,
    RecordType,
    TrustLevel,
)
from memory.scope import RepositoryScope

_SAFE_RECORD_COMPONENT = re.compile(r"[^a-zA-Z0-9._-]+")


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


def _require_authority(*, actor: str, memory_mode: str | None) -> None:
    effective_mode = memory_mode or os.environ.get("BIOETL_AI_MEMORY_MODE")
    if effective_mode != "read-write":
        raise ProofIngestionAuthorizationError(
            "Proof-or-Stop ingestion requires BIOETL_AI_MEMORY_MODE=read-write"
        )
    if not actor.strip():
        raise ProofIngestionAuthorizationError(
            "Proof-or-Stop ingestion requires a non-empty actor identity"
        )
    configured_actor = os.environ.get("BIOETL_AI_AGENT")
    if configured_actor and configured_actor != actor:
        raise ProofIngestionAuthorizationError(
            "actor does not match BIOETL_AI_AGENT authorization context"
        )


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
    actor: str,
    runtime: str,
    model: str | None = None,
    memory_mode: str | None = None,
) -> list[str]:
    """Append receipt and gate evidence after explicit authorization.

    The adapter intentionally exposes no DecisionRecord or override path.
    """
    _require_authority(actor=actor, memory_mode=memory_mode)
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
    digests: list[str] = []

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
            },
        )
        digests.append(store.append_evidence(event))

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
            "outcome": verification["outcome"],
            "claim_qualified": verification["claim_qualified"],
            "errors": verification.get("errors", []),
            "degradations": verification.get("degradations", []),
        },
    )
    digests.append(store.append_evidence(gate_event))
    return digests
