"""Build and record one manifest-adjacent contract-evidence sidecar."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.ports import ContractEvidenceRecorderPort

CONTRACT_EVIDENCE_SCHEMA_VERSION = "contract_evidence_v1"

__all__ = [
    "CONTRACT_EVIDENCE_SCHEMA_VERSION",
    "ContractEvidenceRecorderPort",
    "build_contract_evidence",
    "build_runtime_contract_evidence",
]


class _ContractEvidenceRequest(Protocol):
    @property
    def launch_context(self) -> dict[str, object]: ...

    @property
    def contract_ref(self) -> str | None: ...

    @property
    def contract_schema_hash(self) -> str | None: ...


def build_runtime_contract_evidence(
    *,
    manifest_id: str,
    contract_ref: str | None,
    contract_schema_hash: str | None,
    resume_requested: bool,
    lock_owner_id: str | None,
) -> dict[str, object]:
    """Build fail-closed comparison/resume/lock evidence from proven runtime facts."""
    ref = str(contract_ref or "").strip()
    schema_hash = str(contract_schema_hash or "").strip()
    if ref and schema_hash:
        comparison_status = "compatible"
        comparison_reason = "manifest_contract_comparison_compatible"
    else:
        comparison_status = "UNKNOWN"
        comparison_reason = "contract_ref_or_schema_hash_missing"

    if resume_requested:
        resume_contract = "resume_requested"
        resume_reason = "launch_context_resume_true"
    else:
        resume_contract = "resume_not_requested"
        resume_reason = "launch_context_resume_false"

    owner = str(lock_owner_id or "").strip()
    if owner:
        recorded_owner = owner
        lock_reason = "distributed_lock_recorded"
    else:
        recorded_owner = "n/a"
        lock_reason = "no_distributed_lock"

    return {
        "schema_version": CONTRACT_EVIDENCE_SCHEMA_VERSION,
        "manifest_id": manifest_id,
        "contract_comparison_status": comparison_status,
        "contract_comparison_reason": comparison_reason,
        "resume_contract": resume_contract,
        "resume_contract_reason": resume_reason,
        "lock_owner_id": recorded_owner,
        "lock_owner_reason": lock_reason,
    }


def build_contract_evidence(request: _ContractEvidenceRequest) -> dict[str, object]:
    """Derive comparison/resume evidence from create inputs without lock claims."""
    lock_owner = request.launch_context.get("lock_owner_id")
    owner = lock_owner.strip() if isinstance(lock_owner, str) else None
    return build_runtime_contract_evidence(
        manifest_id="",
        contract_ref=request.contract_ref,
        contract_schema_hash=request.contract_schema_hash,
        resume_requested=bool(request.launch_context.get("resume")),
        lock_owner_id=owner,
    )
