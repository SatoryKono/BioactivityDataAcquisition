"""Bootstrap functions for runtime-safe storage bundle assembly.

Provides storage bundle creation for callers that already own runtime identity.
CLI preview operations must use ``composition.bootstrap.cli.storage`` wrappers
that create explicit preview-only run context before calling this module.

Note:
    This module must not generate run identity or wall-clock timestamps.
    The Composition Root caller owns those runtime decisions.
"""

from __future__ import annotations
from collections.abc import Mapping
from bioetl.infrastructure.time import SystemClock
from pathlib import Path
from typing import TYPE_CHECKING
from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.storage import StorageBundle
from bioetl.composition.factories.storage.resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)
from bioetl.infrastructure.config.settings_api import Settings, get_settings
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta.resilience import SilverMergeResiliencePolicy
from bioetl.infrastructure.storage.gold.runtime_helpers import GoldWriterRuntimeServices
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    build_silver_writer_runtime_services,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.validation.pandera_validator import (
    PanderaSilverValidator,
)
from bioetl.application.services.target_runtime.classification import (
    TargetClassificationRunState,
)
from bioetl.application.services.target_runtime.scope import (
    TARGET_CLASSIFICATION_DEPENDENCY_KEY,
)
from bioetl.application.services.workflow.control_plane.mutation_plan import (
    WorkflowMutationSpec,
    build_workflow_mutation_plan,
)
from bioetl.composition.bootstrap.cli.lock import (
    resolve_workflow_target_config,
    resolve_workflow_target_replay_config,
    validate_workflow_target_mutations,
)
from bioetl.composition.runtime_builders.config_access import load_pipeline_config
from bioetl.composition.runtime_builders.input_snapshot_resolution import (
    resolve_replay_parent_manifest,
)
from bioetl.domain.filtering.silver_config import FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS
from bioetl.infrastructure.adapters.iuphar import (
    IupharTargetClassificationAdapter,
    LoadedIupharProfile,
    LocalTargetClassificationEvidenceStore,
    load_profile,
)
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.workflow_config import WorkflowConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.value_objects.run_context import RunContext

__all__ = [
    "bootstrap_storage_adapter",
    "build_target_classification_session",
    "hydrate_target_runtime_config",
    "load_target_runtime_profile",
    "preflight_workflow_target_dependencies",
]


def _create_composite_metadata_services(
    *,
    settings: Settings,
    output_dir: Path,
    logger: LoggerPort,
    metrics: MetricsPort,
    run_context: RunContext,
) -> tuple[
    MetadataWriter,
    FileLineageStore,
    MetadataCoordinator,
    SilverMergeResiliencePolicy,
]:
    """Create shared metadata services and resilience policy for storage bootstrap."""
    atomic_retry_policy = create_silver_atomic_retry_policy(settings)
    merge_resilience_policy = create_silver_merge_resilience_policy(settings)
    metadata_writer = MetadataWriter(
        logger=logger,
        atomic_replace_retry_policy=atomic_retry_policy,
        metrics=metrics,
    )
    lineage_store = FileLineageStore(base_path=output_dir / "control" / "lineage")
    return (
        metadata_writer,
        lineage_store,
        MetadataCoordinator(run_context=run_context),
        merge_resilience_policy,
    )


def _create_csv_exporters(
    *,
    output_dir: Path,
    logger: LoggerPort,
    enable_csv_export: bool,
) -> tuple[CsvExporter | None, CsvExporter | None]:
    """Create optional CSV exporters for silver and gold layers."""
    if not enable_csv_export:
        return None, None
    return (
        CsvExporter(base_path=str(output_dir / "silver"), logger=logger),
        CsvExporter(base_path=str(output_dir / "gold"), logger=logger),
    )


def bootstrap_storage_adapter(
    *,
    run_context: RunContext,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort,
    enable_csv_export: bool = False,
    settings: Settings | None = None,
) -> StorageBundle:
    """Create a storage bundle for callers with explicit runtime context.

    Layer: Returns a composition storage bundle containing
    Bronze, Silver, and Gold writers.

    Note:
        Lock validation is performed at Application layer (BatchWriter)
        per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.

    Args:
        run_context: Explicit runtime identity and timestamp context owned by
            the caller.
        logger: LoggerPort wired by the caller.
        metrics: MetricsPort wired by the caller.
        tracing: TracingPort wired by the caller.
        enable_csv_export: If True, creates CsvExporters for Silver and Gold.
        settings: Optional Settings override for tests; defaults to get_settings().

    Returns:
        StorageBundle configured for the current environment.
    """
    effective_settings = settings if settings is not None else get_settings()
    silver_clock = SystemClock()

    # ADR-025: Use data/output/ hierarchy for consistency with pipeline configs
    output_dir = Path(effective_settings.data_dir) / "output"
    (
        metadata_writer,
        lineage_store,
        metadata_coordinator,
        merge_resilience_policy,
    ) = _create_composite_metadata_services(
        settings=effective_settings,
        output_dir=output_dir,
        logger=logger,
        metrics=metrics,
        run_context=run_context,
    )
    silver_csv_exporter, gold_csv_exporter = _create_csv_exporters(
        output_dir=output_dir,
        logger=logger,
        enable_csv_export=enable_csv_export,
    )

    return StorageBundle(
        bronze_writer=BronzeWriter(
            base_path=output_dir / "bronze",  # data/output/bronze
            logger=logger,
            metrics=metrics,
            tracing=tracing,
            json_export=(False, None),
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
        ),
        silver_writer=SilverWriter(
            base_path=output_dir / "silver",  # data/output/silver
            logger=logger,
            runtime_services=build_silver_writer_runtime_services(
                SilverWriterRuntimeServicesRequest(
                    clock=silver_clock,
                    csv_exporter=silver_csv_exporter,
                    tracing=tracing,
                    write_policy=None,
                    metrics=metrics,
                    audit=None,
                    logger=logger,
                    silver_validator=PanderaSilverValidator(strict=True),
                    metadata_writer=metadata_writer,
                    metadata_coordinator=metadata_coordinator,
                    lineage_store=lineage_store,
                    dq_calculator=None,
                    merge_resilience_policy=merge_resilience_policy,
                    base_path=output_dir / "silver",
                )
            ),
        ),
        gold_writer=GoldWriter(
            base_path=output_dir / "gold",  # data/output/gold
            logger=logger,
            runtime_services=GoldWriterRuntimeServices(
                csv_exporter=gold_csv_exporter,
                tracing=tracing,
                metrics=metrics,
                audit=None,
                metadata_writer=metadata_writer,
                metadata_coordinator=metadata_coordinator,
                lineage_store=lineage_store,
            ),
        ),
    )


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


def load_target_runtime_profile(
    config: PipelineYamlConfig,
    *,
    require_new_admission: bool = True,
    dependency_root: Path | None = None,
) -> LoadedIupharProfile | None:
    """Read and verify the exact envelope; never substitute a latest snapshot."""
    classification = config.target_classification.to_domain()
    if not classification.enabled:
        return None
    path = Path(classification.snapshot_manifest or "")
    if not path.is_absolute():
        base = (
            dependency_root
            if dependency_root is not None
            else resolve_configs_root().parent
        )
        path = base / path
    return load_profile(
        path.resolve(),
        classification.snapshot_manifest_sha256 or "",
        require_acceptance=classification.mode == "enrich" and require_new_admission,
    )


def build_target_classification_session(
    config: PipelineYamlConfig,
    settings: Settings,
    *,
    pipeline_name: str = "chembl_target",
) -> TargetClassificationRunState | None:
    profile = load_target_runtime_profile(config)
    if profile is None:
        return None
    mode = config.target_classification.mode
    if mode not in ("shadow", "enrich"):
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
        matching_policy_version=profile.matching_policy_version,
        pipeline_name=pipeline_name,
    )
    return TargetClassificationRunState(
        classifier=classifier,
        evidence=store,
        mode=mode,
        normalization_version=profile.normalization_version,
        rules_version=profile.rules_version,
        classification_schema_version=profile.classification_schema_version,
        matching_policy_version=profile.matching_policy_version,
    )


def preflight_workflow_target_dependencies(
    config: WorkflowConfig,
    launch_context: dict[str, object],
    mutation_plan: WorkflowMutationSpec | None = None,
    *,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Admit a target dependency before the first workflow step can mutate data."""
    stored = launch_context.get(TARGET_CLASSIFICATION_DEPENDENCY_KEY)
    runtime_settings = settings or get_settings()
    target = resolve_workflow_target_config(
        stored,
        load_config=load_pipeline_config,
        hydrate_config=hydrate_target_runtime_config,
    )
    target = resolve_workflow_target_replay_config(
        config,
        target,
        runtime_settings,
        load_parent=resolve_replay_parent_manifest,
        hydrate_config=hydrate_target_runtime_config,
    )
    plan = mutation_plan or build_workflow_mutation_plan(config)
    admission = validate_workflow_target_mutations(
        config,
        target,
        runtime_settings,
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
