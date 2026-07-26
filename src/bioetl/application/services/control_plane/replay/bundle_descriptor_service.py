"""Replay-bundle descriptor assembly for run-manifest inspection surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.control_plane.manifest.inspection_result_model import (
    RunManifestInspectionResult,
)
from bioetl.application.services.control_plane.replay._bundle_descriptor_payloads import (
    build_replay_bundle,
    dict_or_empty,
    optional_string,
    resolve_identity_graph,
    resolve_replay_claims,
)

__all__ = [
    "RunReplayBundleDescriptorRecord",
    "build_run_replay_bundle_descriptor",
]


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
    persistence_profile = dict_or_empty(diagnostics.get("persistence_profile"))
    produced_artifact_trace = dict_or_empty(diagnostics.get("produced_artifact_trace"))
    identity_graph = resolve_identity_graph(result, diagnostics)
    claims = resolve_replay_claims(
        diagnostics,
        identity_graph,
        persistence_profile,
        replay_capability_default=manifest.replay_capability.value,
        requested_exact_replay_default=bool(
            manifest.launch_context.get("exact_replay")
        ),
    )
    bundle = build_replay_bundle(
        result,
        diagnostics,
        identity_graph,
        claims,
        produced_artifact_trace,
    )
    missing_requirement_payload = produced_artifact_trace.get(
        "missing_requirements", []
    )
    missing_requirements = (
        tuple(str(item) for item in missing_requirement_payload)
        if isinstance(missing_requirement_payload, list)
        else ()
    )
    return RunReplayBundleDescriptorRecord(
        manifest_id=manifest.manifest_id,
        run_id=str(manifest.run_id),
        execution_fingerprint=manifest.execution_fingerprint,
        replay_capability=optional_string(claims.replay_capability),
        exact_replay_eligible=claims.exact_replay_eligible,
        replay_readiness_verdict=optional_string(claims.replay_readiness_verdict),
        exact_replay_support_boundary=optional_string(
            claims.exact_replay_support_boundary
        ),
        replay_family_contract=optional_string(claims.replay_family_contract),
        required_persistence_profile=optional_string(claims.required_profile),
        bundle=bundle,
        missing_requirements=missing_requirements,
    )
