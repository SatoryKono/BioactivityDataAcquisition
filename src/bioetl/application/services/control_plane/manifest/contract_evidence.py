"""Build and record one manifest-adjacent contract-evidence sidecar."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from bioetl.application.services.control_plane.manifest.models import (
    RunManifestCreateSpec,
)

__all__ = [
    "ContractEvidenceRecorderPort",
    "build_contract_evidence",
]


@runtime_checkable
class ContractEvidenceRecorderPort(Protocol):
    """Persist one forensic contract-evidence sidecar per manifest."""

    def record(self, manifest_id: str, evidence: Mapping[str, object]) -> None:
        """Write one deterministic sidecar for ``manifest_id``."""
        ...


def build_contract_evidence(request: RunManifestCreateSpec) -> dict[str, object]:
    """Derive fail-closed comparison/resume/lock evidence from create inputs."""
    contract_ref = str(request.contract_ref or "").strip()
    schema_hash = str(request.contract_schema_hash or "").strip()
    if contract_ref and schema_hash:
        comparison_status = "compatible"
        comparison_reason = "manifest_contract_comparison_compatible"
    else:
        comparison_status = "UNKNOWN"
        comparison_reason = "contract_ref_or_schema_hash_missing"

    resume_requested = bool(request.launch_context.get("resume"))
    if resume_requested:
        resume_contract = "resume_requested"
        resume_reason = "launch_context_resume_true"
    else:
        resume_contract = "resume_not_requested"
        resume_reason = "launch_context_resume_false"

    lock_owner = request.launch_context.get("lock_owner_id")
    if isinstance(lock_owner, str) and lock_owner.strip():
        lock_owner_id = lock_owner.strip()
        lock_reason = "distributed_lock_recorded"
    else:
        lock_owner_id = "n/a"
        lock_reason = "no_distributed_lock"

    return {
        "contract_comparison_status": comparison_status,
        "contract_comparison_reason": comparison_reason,
        "resume_contract": resume_contract,
        "resume_contract_reason": resume_reason,
        "lock_owner_id": lock_owner_id,
        "lock_owner_reason": lock_reason,
    }
