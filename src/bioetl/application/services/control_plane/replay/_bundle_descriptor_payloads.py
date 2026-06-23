"""Payload assembly helpers for replay-bundle descriptors."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from bioetl.application.services.control_plane.manifest.inspection_result_model import (
    RunManifestInspectionResult,
)
from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
    resolve_replay_taxonomy_projection,
)


def dict_or_empty(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list_of_dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def optional_string(value: object) -> str | None:
    return None if value is None else str(value)


def _build_code_provenance_dict(code_provenance: object) -> dict[str, object]:
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


def resolve_identity_graph(
    result: RunManifestInspectionResult,
    diagnostics: Mapping[str, object],
) -> dict[str, object]:
    """Return the canonical identity graph payload."""
    return (
        result.identity_graph
        if result.identity_graph
        else dict_or_empty(diagnostics.get("identity_graph"))
    )


def resolve_replay_claims(
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
    manifest = result.manifest
    return {
        "manifest_id": manifest.manifest_id,
        "run_id": str(manifest.run_id),
        "schema_version": manifest.schema_version,
        "execution_fingerprint": manifest.execution_fingerprint,
        "ledger_event_count": len(result.ledger_entries),
        "event_family_counts": dict_or_empty(diagnostics.get("event_family_counts")),
        "event_type_counts": dict_or_empty(diagnostics.get("event_type_counts")),
    }


def _build_replay_claims_bundle(
    diagnostics: Mapping[str, object],
    claims: ReplayClaimSnapshot,
) -> dict[str, object]:
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


def build_replay_bundle(
    result: RunManifestInspectionResult,
    diagnostics: Mapping[str, object],
    identity_graph: Mapping[str, object],
    claims: ReplayClaimSnapshot,
    produced_artifact_trace: Mapping[str, object],
) -> dict[str, object]:
    return {
        "control_plane": _build_control_plane_bundle(result, diagnostics),
        "code_provenance": _build_code_provenance_dict(result.manifest.code_provenance),
        "replay_parentage": dict_or_empty(diagnostics.get("replay_parentage")),
        "input_snapshots": _list_of_dicts(diagnostics.get("input_snapshots")),
        "artifact_refs": _list_of_dicts(diagnostics.get("artifact_refs")),
        "lineage_fragment_ids": _string_list(diagnostics.get("lineage_fragment_ids")),
        "produced_artifact_trace": dict(produced_artifact_trace),
        "identity_graph": dict(identity_graph),
        "replay_claims": _build_replay_claims_bundle(diagnostics, claims),
        "required_persistence_profile": claims.required_profile,
    }
