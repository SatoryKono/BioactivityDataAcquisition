"""Bind the optional target classification dependency before execution starts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.target_classification import (
    TargetClassificationSession,
)
from bioetl.application.services.target_classification_scope import (
    TARGET_CLASSIFICATION_DEPENDENCY_KEY,
    get_target_classification_dependency,
)
from bioetl.application.services.workflow.control_plane.mutation_plan import (
    WorkflowMutationPlan,
    build_workflow_mutation_plan,
)
from bioetl.composition.target_workflow_mutation import (
    validate_workflow_target_mutations,
)
from bioetl.composition.runtime_builders.config_access import (
    load_pipeline_config,
    get_settings,
)
from bioetl.domain.control_plane import RunInputSnapshotRef, RunSourceRef
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.filtering.silver_config import FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS
from bioetl.infrastructure.adapters.iuphar import (
    IupharTargetClassificationAdapter,
    LocalTargetClassificationEvidenceStore,
    LoadedIupharProfile,
    load_profile,
)
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.target_classification_profile import (
    resolve_target_classification_profile,
)
from bioetl.infrastructure.config.contract_identity_resolution import (
    RunManifestContractIdentity,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    from bioetl.domain.workflow import WorkflowConfig
    from bioetl.infrastructure.config.settings_api import Settings


def resolve_target_runtime_config(config: PipelineYamlConfig) -> PipelineYamlConfig:
    """Choose one typed schema/hash profile, respecting a workflow's pinned input."""
    if not isinstance(config, PipelineYamlConfig) or (
        config.provider,
        config.entity_type,
    ) != ("chembl", "target"):
        return config
    binding = get_target_classification_dependency()
    if binding is not None:
        payload = binding.get("target_config")
        if not isinstance(payload, Mapping):
            raise ValueError("workflow target dependency has no pinned configuration")
        config = hydrate_target_runtime_config(payload)
    return resolve_target_classification_profile(config).resolved_yaml_config


def hydrate_target_runtime_config(payload: Mapping[str, object]) -> PipelineYamlConfig:
    """Restore a validated snapshot, stripping only materialized empty legacy defaults."""
    restored = dict(payload)
    filters = restored.get("silver_filters")
    if isinstance(filters, Mapping):
        restored["silver_filters"] = {
            key: value
            for key, value in filters.items()
            if key not in FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS or value
        }
    return PipelineYamlConfig.model_validate(restored)


def target_classification_contract_schema_identity(
    config: object,
) -> tuple[str, str] | None:
    """Return the actual enriched contract schema identity, preserving V30 otherwise."""
    if not isinstance(config, PipelineYamlConfig) or (
        config.provider,
        config.entity_type,
    ) != ("chembl", "target"):
        return None
    if config.target_classification.mode != "enrich":
        return None
    from bioetl.domain.contracts.gold.chembl_target_classification import (
        target_v31_schema_hash,
    )

    return ("3.1.0", target_v31_schema_hash())


def target_classification_normalization_identity(
    config: object,
) -> tuple[str, str, str] | None:
    """Bind the actual additive V31 normalization profile to execution metadata."""
    if target_classification_contract_schema_identity(config) is None:
        return None
    from bioetl.domain.normalization.profiles.chembl_target_classification import (
        target_v31_normalization_profile,
    )

    identity = target_v31_normalization_profile().identity
    return identity.profile_name, identity.profile_version, identity.profile_hash


def apply_target_contract_identity(
    config: object, identity: RunManifestContractIdentity
) -> RunManifestContractIdentity:
    """Apply only the selected V31 schema/normalization anchors, preserving DQ."""
    schema_identity = target_classification_contract_schema_identity(config)
    if schema_identity is None:
        return identity
    normalization = target_classification_normalization_identity(config)
    assert normalization is not None
    return replace(
        identity,
        contract_version=schema_identity[0],
        contract_schema_hash=schema_identity[1],
        normalization_profile_ref=normalization[0],
        normalization_profile_version=normalization[1],
        normalization_profile_hash=normalization[2],
    )


def load_target_runtime_profile(
    config: PipelineYamlConfig,
    *,
    require_new_admission: bool = True,
) -> LoadedIupharProfile | None:
    """Read and verify the exact envelope; never substitute a latest snapshot."""
    classification = config.target_classification.to_domain()
    if not classification.enabled:
        return None
    path = Path(classification.snapshot_manifest or "")
    if not path.is_absolute():
        path = resolve_configs_root().parent / path
    return load_profile(
        path.resolve(),
        classification.snapshot_manifest_sha256 or "",
        require_acceptance=classification.mode == "enrich" and require_new_admission,
    )


def build_target_classification_session(
    config: PipelineYamlConfig, settings: Settings
) -> TargetClassificationSession | None:
    profile = load_target_runtime_profile(config)
    if profile is None:
        return None
    mode = config.target_classification.mode
    if mode not in {"shadow", "enrich"}:
        raise ValueError("enabled target classification requires shadow or enrich mode")
    classifier = IupharTargetClassificationAdapter(profile)
    store = LocalTargetClassificationEvidenceStore(
        Path(settings.data_dir) / "output/control/target_classification",
        mode=mode,
        snapshot_manifest_sha256=classifier.snapshot_manifest_sha256,
        profile_sha256=classifier.profile_sha256,
        normalization_version=profile.normalization_version,
        rules_version=profile.rules_version,
        classification_schema_version=profile.classification_schema_version,
    )
    return TargetClassificationSession(
        classifier=classifier,
        evidence=store,
        mode=mode,
        normalization_version=profile.normalization_version,
        rules_version=profile.rules_version,
        classification_schema_version=profile.classification_schema_version,
    )


def validate_target_runtime_dependency(config: object) -> None:
    """Recheck pinned bytes immediately before a target run can clear outputs."""
    if not isinstance(config, PipelineYamlConfig):
        return
    profile = load_target_runtime_profile(config)
    stored = get_target_classification_dependency()
    if stored is None or profile is None:
        return
    if (
        stored.get("profile_sha256") != profile.profile_sha256
        or stored.get("snapshot_manifest_sha256")
        != profile.snapshot.snapshot_manifest_sha256
    ):
        raise ValueError("workflow target classification dependency identity changed")


def target_classification_source_refs(
    config: object,
) -> tuple[RunSourceRef, ...]:
    if not isinstance(config, PipelineYamlConfig):
        return ()
    profile = load_target_runtime_profile(config)
    if profile is None:
        return ()
    return (
        RunSourceRef(
            provider="iuphar",
            entity="target_classification",
            pipeline_name="chembl_target",
            input_snapshots=(
                RunInputSnapshotRef(
                    snapshot_id=profile.snapshot.snapshot.snapshot_id,
                    content_hash=profile.snapshot.snapshot_manifest_sha256,
                    immutable_uri=profile.snapshot.immutable_uri,
                ),
                RunInputSnapshotRef(
                    snapshot_id="profile:" + profile.profile_sha256,
                    content_hash=profile.profile_sha256,
                    immutable_uri=profile.profile_uri,
                ),
            ),
        ),
    )


def target_classification_config_source_refs(config: object) -> list[ConfigSourceRef]:
    """Anchor immutable dependency bytes in effective-config source identity."""
    if not isinstance(config, PipelineYamlConfig) or (
        config.provider,
        config.entity_type,
    ) != ("chembl", "target"):
        return []
    return [
        ConfigSourceRef(
            source_type="file",
            source_path=snapshot.immutable_uri,
            source_hash=snapshot.content_hash,
            raw_source_hash=snapshot.content_hash,
            source_hash_strategy="raw_bytes",
            source_hash_version="sha256-v1",
            raw_source_hash_version="sha256-v1",
            priority=100,
        )
        for source in target_classification_source_refs(config)
        for snapshot in source.input_snapshots
        if snapshot.immutable_uri is not None
    ]


def preflight_workflow_target_dependencies(
    config: WorkflowConfig,
    launch_context: dict[str, object],
    mutation_plan: WorkflowMutationPlan | None = None,
    *,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Admit a target dependency before the first workflow step can mutate data."""
    stored = launch_context.get(TARGET_CLASSIFICATION_DEPENDENCY_KEY)
    target = _workflow_target_config(stored)
    plan = mutation_plan or build_workflow_mutation_plan(config)
    admission = validate_workflow_target_mutations(
        config,
        target,
        settings or get_settings(),
        plan,
        load_pipeline_config,
    )
    if not admission.required and stored is None:
        return {}
    profile = load_target_runtime_profile(
        target, require_new_admission=admission.pending_writes
    )
    binding: dict[str, object] = {"target_config": target.model_dump(mode="json")}
    if profile is not None:
        binding.update(
            {
                "profile_sha256": profile.profile_sha256,
                "profile_uri": profile.profile_uri,
                "snapshot_manifest_sha256": profile.snapshot.snapshot_manifest_sha256,
                "snapshot_uri": profile.snapshot.immutable_uri,
                "snapshot_id": profile.snapshot.snapshot.snapshot_id,
            }
        )
    if isinstance(stored, Mapping) and dict(stored) != binding:
        raise ValueError("stored target classification dependency identity changed")
    return {TARGET_CLASSIFICATION_DEPENDENCY_KEY: binding}


def _workflow_target_config(stored: object) -> PipelineYamlConfig:
    if isinstance(stored, Mapping):
        payload = stored.get("target_config")
        if not isinstance(payload, Mapping):
            raise ValueError("stored workflow target dependency has no configuration")
        target = hydrate_target_runtime_config(payload)
    else:
        target = load_pipeline_config("chembl_target")
    return resolve_target_classification_profile(target).resolved_yaml_config


__all__ = [
    "build_target_classification_session",
    "load_target_runtime_profile",
    "preflight_workflow_target_dependencies",
    "resolve_target_runtime_config",
    "target_classification_source_refs",
]
