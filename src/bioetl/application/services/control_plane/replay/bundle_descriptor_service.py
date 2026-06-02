"""Replay-bundle descriptor assembly for run-manifest inspection surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from bioetl.application.services.control_plane.manifest.inspection_models import (
    RunManifestInspectionResult,
)
from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
    resolve_replay_taxonomy_projection,
)

__all__ = [
    "RunReplayBundleDescriptorRecord",
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


def _optional_string(value: object) -> str | None:
    """Return a string payload when present."""
    return None if value is None else str(value)


def _build_code_provenance_dict(code_provenance: object) -> dict[str, object]:
    """Return the replay bundle's code-provenance mapping."""
    payload: dict[str, object] = {
        "pipeline_version": getattr(code_provenance, "pipeline_version", None),
        "git_commit": getattr(code_provenance, "git_commit", None),
        "dependency_lock_hash": getattr(code_provenance, "dependency_lock_hash", None),
        "config_hash": getattr(code_provenance, "config_hash", None),
        "resolved_config_hash": getattr(code_provenance, "resolved_config_hash", None),
        "effective_config_hash": getattr(
            code_provenance, "effective_config_hash", None
        ),
        "effective_config_artifact_id": getattr(
            code_provenance,
            "effective_config_artifact_id",
            None,
        ),
        "contract_ref": getattr(code_provenance, "contract_ref", None),
        "contract_version": getattr(code_provenance, "contract_version", None),
        "contract_schema_hash": getattr(code_provenance, "contract_schema_hash", None),
        "dq_policy_ref": getattr(code_provenance, "dq_policy_ref", None),
        "rule_bundle_version": getattr(code_provenance, "rule_bundle_version", None),
        "normalization_profile_ref": getattr(
            code_provenance,
            "normalization_profile_ref",
            None,
        ),
        "normalization_profile_version": getattr(
            code_provenance,
            "normalization_profile_version",
            None,
        ),
        "normalization_profile_hash": getattr(
            code_provenance,
            "normalization_profile_hash",
            None,
        ),
        "dq_contract_compatibility_hash": getattr(
            code_provenance,
            "dq_contract_compatibility_hash",
            None,
        ),
    }
    return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True, slots=True)
class ReplayClaimSnapshot:
    """Normalized replay-claim values extracted from diagnostics."""

    replay_capability: object
    replay_readiness_verdict: object
    exact_replay_support_boundary: object
    replay_family_contract: object
    exact_replay_eligible: bool
    required_profile: object


def _resolve_identity_graph(
    result: RunManifestInspectionResult,
    diagnostics: Mapping[str, object],
) -> dict[str, object]:
    """Return the canonical identity graph payload."""
    return (
        result.identity_graph
        if result.identity_graph
        else _dict_or_empty(diagnostics.get("identity_graph"))
    )


def _resolve_replay_claims(
    diagnostics: Mapping[str, object],
    identity_graph: Mapping[str, object],
    persistence_profile: Mapping[str, object],
    *,
    replay_capability_default: object,
    requested_exact_replay_default: object,
) -> ReplayClaimSnapshot:
    """Resolve replay claims from diagnostics and identity-graph fallbacks."""
    replay_taxonomy = resolve_replay_taxonomy_projection(
        diagnostics,
        fallback=identity_graph,
        defaults={
            "replay_capability": replay_capability_default,
            "requested_exact_replay": requested_exact_replay_default,
        },
    )
    return ReplayClaimSnapshot(
        replay_capability=replay_taxonomy.get("replay_capability"),
        replay_readiness_verdict=replay_taxonomy.get("replay_readiness_verdict"),
        exact_replay_support_boundary=replay_taxonomy.get(
            "exact_replay_support_boundary"
        ),
        replay_family_contract=replay_taxonomy.get("replay_family_contract"),
        exact_replay_eligible=bool(replay_taxonomy.get("exact_replay_eligible", False)),
        required_profile=persistence_profile.get("required_profile")
        or diagnostics.get("required_persistence_profile"),
    )


def _build_control_plane_bundle(
    result: RunManifestInspectionResult,
    diagnostics: Mapping[str, object],
) -> dict[str, object]:
    """Build control-plane replay bundle data."""
    manifest = result.manifest
    return {
        "manifest_id": manifest.manifest_id,
        "run_id": str(manifest.run_id),
        "schema_version": manifest.schema_version,
        "execution_fingerprint": manifest.execution_fingerprint,
        "ledger_event_count": len(result.ledger_entries),
        "event_family_counts": _dict_or_empty(diagnostics.get("event_family_counts")),
        "event_type_counts": _dict_or_empty(diagnostics.get("event_type_counts")),
    }


def _build_code_provenance_bundle(
    result: RunManifestInspectionResult,
) -> dict[str, object]:
    """Build code-provenance replay bundle data."""
    return _build_code_provenance_dict(result.manifest.code_provenance)


def _build_replay_claims_bundle(
    diagnostics: Mapping[str, object],
    claims: ReplayClaimSnapshot,
) -> dict[str, object]:
    """Build replay-claim replay bundle data."""
    return {
        "replay_capability": claims.replay_capability,
        "replay_readiness_verdict": claims.replay_readiness_verdict,
        "exact_replay_eligible": claims.exact_replay_eligible,
        "exact_replay_support_boundary": claims.exact_replay_support_boundary,
        "replay_family_contract": claims.replay_family_contract,
        "historical_live_run_upgrade_state": diagnostics.get(
            "historical_live_run_upgrade_state"
        ),
        "broader_historical_exact_replay_state": diagnostics.get(
            "broader_historical_exact_replay_state"
        ),
    }


def _build_replay_bundle(
    result: RunManifestInspectionResult,
    diagnostics: Mapping[str, object],
    identity_graph: Mapping[str, object],
    claims: ReplayClaimSnapshot,
    produced_artifact_trace: Mapping[str, object],
) -> dict[str, object]:
    """Assemble the operator-facing replay bundle."""
    return {
        "control_plane": _build_control_plane_bundle(result, diagnostics),
        "code_provenance": _build_code_provenance_bundle(result),
        "replay_parentage": _dict_or_empty(diagnostics.get("replay_parentage")),
        "input_snapshots": _list_of_dicts(diagnostics.get("input_snapshots")),
        "artifact_refs": _list_of_dicts(diagnostics.get("artifact_refs")),
        "lineage_fragment_ids": _string_list(diagnostics.get("lineage_fragment_ids")),
        "produced_artifact_trace": dict(produced_artifact_trace),
        "identity_graph": dict(identity_graph),
        "replay_claims": _build_replay_claims_bundle(diagnostics, claims),
        "required_persistence_profile": claims.required_profile,
    }


@dataclass(frozen=True, slots=True)
class RunReplayBundleDescriptorRecord:
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
) -> RunReplayBundleDescriptorRecord:
    """Build one deterministic replay-bundle descriptor from inspection output."""
    diagnostics = result.diagnostics
    manifest = result.manifest
    persistence_profile = _dict_or_empty(diagnostics.get("persistence_profile"))
    produced_artifact_trace = _dict_or_empty(diagnostics.get("produced_artifact_trace"))
    identity_graph = _resolve_identity_graph(result, diagnostics)
    claims = _resolve_replay_claims(
        diagnostics,
        identity_graph,
        persistence_profile,
        replay_capability_default=manifest.replay_capability.value,
        requested_exact_replay_default=bool(
            manifest.launch_context.get("exact_replay")
        ),
    )
    bundle = _build_replay_bundle(
        result,
        diagnostics,
        identity_graph,
        claims,
        produced_artifact_trace,
    )
    missing_requirements = tuple(
        str(item) for item in produced_artifact_trace.get("missing_requirements", [])
    )
    return RunReplayBundleDescriptorRecord(
        manifest_id=manifest.manifest_id,
        run_id=str(manifest.run_id),
        execution_fingerprint=manifest.execution_fingerprint,
        replay_capability=_optional_string(claims.replay_capability),
        exact_replay_eligible=claims.exact_replay_eligible,
        replay_readiness_verdict=_optional_string(claims.replay_readiness_verdict),
        exact_replay_support_boundary=_optional_string(
            claims.exact_replay_support_boundary
        ),
        replay_family_contract=_optional_string(claims.replay_family_contract),
        required_persistence_profile=_optional_string(claims.required_profile),
        bundle=bundle,
        missing_requirements=missing_requirements,
    )
