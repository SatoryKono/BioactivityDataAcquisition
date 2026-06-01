"""Derived context builder for effective-config artifacts."""

from __future__ import annotations

from bioetl.application.services.control_plane.effective_config.provenance_support import (
    build_source_class_provenance,
)
from bioetl.application.services.control_plane.effective_config.support import (
    SemanticIdentityPayloadContext,
    build_dq_components,
    build_effective_execution_config,
    build_execution_environment_snapshot,
    build_resolved_config_snapshot,
    build_runtime_override_snapshot,
    build_semantic_identity_payload,
    compute_source_fingerprint,
    extract_contract_refs,
    resolve_resolution_policy,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    ConfigSourceRef,
)
from bioetl.domain.types import JsonDict

__all__ = ["build_effective_config_context"]


def build_effective_config_context(
    *,
    pipeline_name: str,
    pipeline_kind: str,
    resolved_config: JsonDict,
    runtime_overrides: JsonDict,
    source_refs: list[ConfigSourceRef],
    dq_config: DQConfig | None,
    resolution_policy: ConfigResolutionPolicy | None,
    required_persistence_profile: str,
    normalization_profile_ref: str | None,
    normalization_profile_version: str | None,
    normalization_profile_hash: str | None,
) -> dict[str, object]:
    """Build derived snapshots and semantic payload context for one artifact."""
    resolved_policy = resolve_resolution_policy(resolution_policy)
    resolved_snapshot = build_resolved_config_snapshot(
        pipeline_kind=pipeline_kind,
        resolved_config=resolved_config,
    )
    overrides_snapshot = build_runtime_override_snapshot(runtime_overrides)
    execution_environment = build_execution_environment_snapshot(
        runtime_overrides,
        required_persistence_profile=required_persistence_profile,
    )
    effective_snapshot = build_effective_execution_config(
        resolved_config=resolved_config,
        runtime_overrides=runtime_overrides,
    )
    dq_policy_refs, dq_policy_snapshots, dq_rule_bundle_versions = build_dq_components(
        dq_config
    )
    dq_contract_compatibility_hash = (
        "no_dq_policies"
        if not dq_policy_refs
        else ":".join(
            sorted(
                ref.policy_hash
                for ref in dq_policy_refs
                if ref.policy_hash is not None and ref.policy_hash
            )
        )
        or "no_dq_policy_hashes"
    )
    source_fingerprint = compute_source_fingerprint(source_refs)
    contract_refs = extract_contract_refs(dq_config)
    source_class_provenance = build_source_class_provenance()
    semantic_identity_payload = build_semantic_identity_payload(
        request=SemanticIdentityPayloadContext(
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            source_refs=source_refs,
            source_class_provenance=source_class_provenance,
            resolution_policy=resolved_policy,
            resolved_config=resolved_snapshot,
            runtime_overrides=overrides_snapshot,
            execution_environment=execution_environment,
            effective_execution_config=effective_snapshot,
            resolved_config_hash=resolved_snapshot.config_hash,
            effective_config_hash=effective_snapshot.effective_hash,
            source_fingerprint=source_fingerprint,
            contract_refs=contract_refs,
            normalization_profile_ref=normalization_profile_ref,
            normalization_profile_version=normalization_profile_version,
            normalization_profile_hash=normalization_profile_hash,
            dq_policy_refs=dq_policy_refs,
            dq_rule_bundle_versions=dq_rule_bundle_versions,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            dq_policy_snapshots=dq_policy_snapshots,
        ),
    )
    return {
        "contract_refs": contract_refs,
        "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
        "dq_policy_refs": dq_policy_refs,
        "dq_policy_snapshots": dq_policy_snapshots,
        "dq_rule_bundle_versions": dq_rule_bundle_versions,
        "effective_snapshot": effective_snapshot,
        "execution_environment": execution_environment,
        "overrides_snapshot": overrides_snapshot,
        "resolved_policy": resolved_policy,
        "resolved_snapshot": resolved_snapshot,
        "semantic_identity_payload": semantic_identity_payload,
        "source_class_provenance": source_class_provenance,
        "source_fingerprint": source_fingerprint,
    }
