"""Replay-bundle descriptor assembly for run-manifest inspection surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from bioetl.application.services.control_plane.run_manifest_inspection_models import (
    RunManifestInspectionResult,
)

__all__ = [
    "RunReplayBundleDescriptor",
    "build_run_replay_bundle_descriptor",
]


def _dict_or_empty(value: object) -> dict[str, object]:
    """Return a plain dict for nested JSON payloads."""
    return dict(value) if isinstance(value, Mapping) else {}


def _list_of_dicts(value: object) -> list[dict[str, object]]:
    """Return a stable list of dict payloads."""
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _string_list(value: object) -> list[str]:
    """Return one stringified list view."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


@dataclass(frozen=True, slots=True)
class RunReplayBundleDescriptor:
    """Operator-facing replay descriptor for one supported run."""

    manifest_id: str
    run_id: str
    execution_fingerprint: str
    replay_capability: str | None
    exact_replay_eligible: bool
    replay_readiness_verdict: str | None
    exact_replay_support_boundary: str | None
    replay_family_contract: str | None
    required_persistence_profile: str | None
    bundle: dict[str, object]
    missing_requirements: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON/YAML-safe replay bundle payload."""
        return {
            "manifest_id": self.manifest_id,
            "run_id": self.run_id,
            "execution_fingerprint": self.execution_fingerprint,
            "replay_capability": self.replay_capability,
            "exact_replay_eligible": self.exact_replay_eligible,
            "replay_readiness_verdict": self.replay_readiness_verdict,
            "exact_replay_support_boundary": self.exact_replay_support_boundary,
            "replay_family_contract": self.replay_family_contract,
            "required_persistence_profile": self.required_persistence_profile,
            "missing_requirements": list(self.missing_requirements),
            "bundle": self.bundle,
        }


def build_run_replay_bundle_descriptor(
    result: RunManifestInspectionResult,
) -> RunReplayBundleDescriptor:
    """Build one deterministic replay-bundle descriptor from inspection output."""
    diagnostics = result.diagnostics
    manifest = result.manifest
    code_provenance = manifest.code_provenance
    persistence_profile = _dict_or_empty(diagnostics.get("persistence_profile"))
    produced_artifact_trace = _dict_or_empty(diagnostics.get("produced_artifact_trace"))
    identity_graph = (
        result.identity_graph
        if result.identity_graph
        else _dict_or_empty(diagnostics.get("identity_graph"))
    )
    replay_capability = diagnostics.get("replay_capability") or identity_graph.get(
        "replay_capability"
    )
    replay_readiness_verdict = diagnostics.get(
        "replay_readiness_verdict"
    ) or identity_graph.get("replay_readiness_verdict")
    exact_replay_support_boundary = diagnostics.get(
        "exact_replay_support_boundary"
    ) or identity_graph.get("exact_replay_support_boundary")
    replay_family_contract = diagnostics.get(
        "replay_family_contract"
    ) or identity_graph.get("replay_family_contract")
    exact_replay_eligible = diagnostics.get(
        "exact_replay_eligible",
        identity_graph.get("exact_replay_eligible", False),
    )
    required_profile = (
        persistence_profile.get("required_profile")
        or diagnostics.get("required_persistence_profile")
    )
    bundle = {
        "control_plane": {
            "manifest_id": manifest.manifest_id,
            "run_id": str(manifest.run_id),
            "schema_version": manifest.schema_version,
            "execution_fingerprint": manifest.execution_fingerprint,
            "ledger_event_count": len(result.ledger_entries),
            "event_family_counts": _dict_or_empty(diagnostics.get("event_family_counts")),
            "event_type_counts": _dict_or_empty(diagnostics.get("event_type_counts")),
        },
        "code_provenance": {
            "pipeline_version": code_provenance.pipeline_version,
            "git_commit": code_provenance.git_commit,
            "dependency_lock_hash": code_provenance.dependency_lock_hash,
            "config_hash": code_provenance.config_hash,
            "resolved_config_hash": code_provenance.resolved_config_hash,
            "effective_config_hash": code_provenance.effective_config_hash,
            "effective_config_artifact_id": (
                code_provenance.effective_config_artifact_id
            ),
            "contract_ref": code_provenance.contract_ref,
            "contract_version": code_provenance.contract_version,
            "contract_schema_hash": code_provenance.contract_schema_hash,
            "dq_policy_ref": code_provenance.dq_policy_ref,
            "rule_bundle_version": code_provenance.rule_bundle_version,
            "normalization_profile_ref": code_provenance.normalization_profile_ref,
            "normalization_profile_version": (
                code_provenance.normalization_profile_version
            ),
            "normalization_profile_hash": code_provenance.normalization_profile_hash,
            "dq_contract_compatibility_hash": (
                code_provenance.dq_contract_compatibility_hash
            ),
        },
        "replay_parentage": _dict_or_empty(diagnostics.get("replay_parentage")),
        "input_snapshots": _list_of_dicts(diagnostics.get("input_snapshots")),
        "artifact_refs": _list_of_dicts(diagnostics.get("artifact_refs")),
        "lineage_fragment_ids": _string_list(diagnostics.get("lineage_fragment_ids")),
        "produced_artifact_trace": produced_artifact_trace,
        "identity_graph": identity_graph,
        "replay_claims": {
            "replay_capability": replay_capability,
            "replay_readiness_verdict": replay_readiness_verdict,
            "exact_replay_eligible": bool(exact_replay_eligible),
            "exact_replay_support_boundary": exact_replay_support_boundary,
            "replay_family_contract": replay_family_contract,
            "historical_live_run_upgrade_state": diagnostics.get(
                "historical_live_run_upgrade_state"
            ),
            "broader_historical_exact_replay_state": diagnostics.get(
                "broader_historical_exact_replay_state"
            ),
        },
        "required_persistence_profile": required_profile,
    }
    missing_requirements = tuple(
        str(item) for item in produced_artifact_trace.get("missing_requirements", [])
    )
    return RunReplayBundleDescriptor(
        manifest_id=manifest.manifest_id,
        run_id=str(manifest.run_id),
        execution_fingerprint=manifest.execution_fingerprint,
        replay_capability=None if replay_capability is None else str(replay_capability),
        exact_replay_eligible=bool(exact_replay_eligible),
        replay_readiness_verdict=(
            None
            if replay_readiness_verdict is None
            else str(replay_readiness_verdict)
        ),
        exact_replay_support_boundary=(
            None
            if exact_replay_support_boundary is None
            else str(exact_replay_support_boundary)
        ),
        replay_family_contract=(
            None if replay_family_contract is None else str(replay_family_contract)
        ),
        required_persistence_profile=(
            None if required_profile is None else str(required_profile)
        ),
        bundle=bundle,
        missing_requirements=missing_requirements,
    )
