"""Shared dataclasses for RunContext construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.types import RunID, RunType


@dataclass(frozen=True, slots=True)
class RunContextCreateInput:
    """Typed input bundle for ``RunContext.create``."""

    run_id: RunID
    run_type: RunType
    started_at: datetime
    provider: str
    entity: str
    transform_version: str | None = None
    transform_steps: tuple[str, ...] = ()
    pipeline_version: str | None = None
    git_commit: str | None = None
    dependency_lock_hash: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    manifest_id: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    normalization_profile_ref: str | None = None
    normalization_profile_version: str | None = None
    normalization_profile_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    execution_fingerprint: str | None = None


__all__ = ["RunContextCreateInput"]
