"""Anchor-context helpers for composite checkpoint orchestration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from bioetl.domain.normalization import normalize_runtime_anchor_payload

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort


@dataclass(frozen=True, slots=True)
class ExpectedCheckpointContext:
    """Expected runtime anchors used to validate checkpoint resume safety."""

    effective_config_hash: str = ""
    effective_config_artifact_id: str = ""
    execution_fingerprint: str = ""
    dq_contract_compatibility_hash: str = ""
    contract_ref: str = ""
    contract_version: str = ""
    manifest_id: str = ""
    composite_run_identity: str = ""


def create_expected_checkpoint_context(
    *,
    effective_config_hash: str | None,
    effective_config_artifact_id: str | None = None,
    execution_fingerprint: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    contract_ref: str | None,
    contract_version: str | None,
    manifest_id: str | None,
    composite_run_identity: str,
) -> ExpectedCheckpointContext:
    """Normalize nullable runtime anchors into a comparable checkpoint context."""
    normalized = normalize_runtime_anchor_payload(
        {
            "effective_config_hash": effective_config_hash,
            "effective_config_artifact_id": effective_config_artifact_id,
            "execution_fingerprint": execution_fingerprint,
            "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
            "contract_ref": contract_ref,
            "contract_version": contract_version,
            "manifest_id": manifest_id,
            "composite_run_identity": composite_run_identity,
        }
    )
    return ExpectedCheckpointContext(
        effective_config_hash=normalized["effective_config_hash"] or "",
        effective_config_artifact_id=normalized["effective_config_artifact_id"] or "",
        execution_fingerprint=normalized["execution_fingerprint"] or "",
        dq_contract_compatibility_hash=(
            normalized["dq_contract_compatibility_hash"] or ""
        ),
        contract_ref=normalized["contract_ref"] or "",
        contract_version=normalized["contract_version"] or "",
        manifest_id=normalized["manifest_id"] or "",
        composite_run_identity=normalized["composite_run_identity"] or "",
    )


def _coalesce_expected_anchor(current: str, expected: str) -> str:
    """Prefer the persisted checkpoint anchor and fall back to the runtime one."""
    return current or expected


def _build_merged_anchor_payload(
    *,
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointContext,
) -> dict[str, str]:
    """Return the raw anchor payload before normalization."""
    return {
        "effective_config_hash": _coalesce_expected_anchor(
            state.effective_config_hash,
            anchors.effective_config_hash,
        ),
        "effective_config_artifact_id": _coalesce_expected_anchor(
            state.effective_config_artifact_id,
            anchors.effective_config_artifact_id,
        ),
        "execution_fingerprint": _coalesce_expected_anchor(
            state.execution_fingerprint,
            anchors.execution_fingerprint,
        ),
        "dq_contract_compatibility_hash": _coalesce_expected_anchor(
            state.dq_contract_compatibility_hash,
            anchors.dq_contract_compatibility_hash,
        ),
        "contract_ref": _coalesce_expected_anchor(
            state.contract_ref,
            anchors.contract_ref,
        ),
        "contract_version": _coalesce_expected_anchor(
            state.contract_version,
            anchors.contract_version,
        ),
        "manifest_id": _coalesce_expected_anchor(
            state.manifest_id,
            anchors.manifest_id,
        ),
        "composite_run_identity": _coalesce_expected_anchor(
            state.composite_run_identity,
            anchors.composite_run_identity,
        ),
    }


def merge_expected_anchors(
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointContext,
) -> CompositeCheckpointState:
    """Fill empty checkpoint anchors with the expected runtime anchor values."""
    merged = normalize_runtime_anchor_payload(
        _build_merged_anchor_payload(state=state, anchors=anchors)
    )
    return replace(
        state,
        effective_config_hash=merged["effective_config_hash"] or "",
        effective_config_artifact_id=(merged["effective_config_artifact_id"] or ""),
        execution_fingerprint=merged["execution_fingerprint"] or "",
        dq_contract_compatibility_hash=(merged["dq_contract_compatibility_hash"] or ""),
        contract_ref=merged["contract_ref"] or "",
        contract_version=merged["contract_version"] or "",
        manifest_id=merged["manifest_id"] or "",
        composite_run_identity=merged["composite_run_identity"] or "",
    )


def fresh_checkpoint_state(
    *,
    composite_name: str,
    run_id: str,
    anchors: ExpectedCheckpointContext,
    clock: ClockPort | None = None,
    created_at: datetime | None = None,
) -> CompositeCheckpointState:
    """Create a fresh checkpoint state for a new composite execution."""
    resolved_created_at = created_at
    if resolved_created_at is None:
        resolved_created_at = (
            clock.now() if clock is not None else MISSING_RUNTIME_TIMESTAMP
        )
    return CompositeCheckpointState(
        composite_name=composite_name,
        run_id=run_id,
        effective_config_hash=anchors.effective_config_hash,
        effective_config_artifact_id=anchors.effective_config_artifact_id,
        execution_fingerprint=anchors.execution_fingerprint,
        dq_contract_compatibility_hash=anchors.dq_contract_compatibility_hash,
        contract_ref=anchors.contract_ref,
        contract_version=anchors.contract_version,
        manifest_id=anchors.manifest_id,
        composite_run_identity=anchors.composite_run_identity,
        last_event_id=None,
        last_event_occurred_at=None,
        created_at=resolved_created_at,
    )
