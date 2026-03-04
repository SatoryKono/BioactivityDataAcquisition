"""Bootstrap functions for Composite Pipeline execution. See ADR-026."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import yaml
from pydantic import ValidationError

from bioetl.application.composite.checkpoint import CompositeCheckpointService
from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.key_extractor import (
    KeyExtractorService as _KeyExtractorService,
)
from bioetl.application.composite.merger import MergeService as _MergeService
from bioetl.application.composite.runner import (
    CompositePipelineRunnerService,
    CompositeRuntimeConfig,
)
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.runtime.composite_dq_loader import (
    merge_external_dq_overrides,
)
from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
    CompositeFilterExtractionService,
)
from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
    CompositeSupportServicesFactory,
)
from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger_port
from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
    RunnerFactoryBuilderService,
    resolve_bronze_opts,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.contracts import (
    CompositeActivityGoldSchema,
    CompositeAssayGoldSchema,
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
    CompositeTargetGoldSchema,
)
from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.config.field_group_loader import (
    FieldGroupLoadError,
    load_field_groups,
)
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.schemas.composite_config import (
    validate_composite_config_payload,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from bioetl.application.composite.fsm_helper import FSMStateHelperService
    from bioetl.application.composite.preflight_validator import (
        CompositePreflightValidator,
    )
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import LockPort, MetricsPort, QuarantinePort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "CompositeRuntimeConfig",
    "bootstrap_composite_pipeline",
    "bootstrap_composite_runner",
    "load_composite_config",
]

# Default composite config path (RF-CFG-036)
COMPOSITE_CONFIG_DIR = Path("configs/composites")
FIELD_GROUP_CONFIG_DIR = Path("configs/composites/field_groups")

COMPOSITE_GOLD_SCHEMA_REGISTRY: dict[str, type] = {
    "activity": CompositeActivityGoldSchema,
    "assay": CompositeAssayGoldSchema,
    "molecule": CompositeMoleculeGoldSchema,
    "publication": CompositePublicationGoldSchema,
    "target": CompositeTargetGoldSchema,
}


def create_composite_runner_with_legacy_fsm_adapter(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    seed_runner_factory: Callable[[], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    key_extractor: _KeyExtractorService,
    coordinator: EnrichmentCoordinatorService,
    merger: _MergeService,
    checkpoint_manager: CompositeCheckpointService,
    logger: LoggerPort,
    lock: LockPort,
    fsm_state_helper: FSMStateHelperService | None = None,
    run_id: str | None = None,
    dq_report_service: DQReportService | None = None,
    preflight_validator: CompositePreflightValidator | None = None,
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    | None = None,
    dependency_coordinator: DependencyCoordinatorService | None = None,
    quarantine_port: QuarantinePort | None = None,
    metrics: MetricsPort | None = None,
) -> CompositePipelineRunnerService:
    """Create composite runner with temporary legacy FSM injection in composition."""
    effective_run_id = run_id or str(uuid4())
    effective_fsm_state_helper = fsm_state_helper

    if effective_fsm_state_helper is None:
        from bioetl.application.composite.fsm_helper import FSMStateHelperService

        warnings.warn(
            "Creating CompositePipelineRunner without fsm_state_helper is deprecated; "
            "inject fsm_state_helper from composition.",
            DeprecationWarning,
            stacklevel=2,
        )
        effective_fsm_state_helper = FSMStateHelperService(
            config=config,
            logger=logger,
            run_id=effective_run_id,
        )

    return CompositePipelineRunnerService(
        config=config,
        runtime=runtime,
        seed_runner_factory=seed_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        key_extractor=key_extractor,
        coordinator=coordinator,
        merger=merger,
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        lock=lock,
        fsm_state_helper=effective_fsm_state_helper,
        run_id=effective_run_id,
        dq_report_service=dq_report_service,
        preflight_validator=preflight_validator,
        dependencies_runner_factory=dependencies_runner_factory,
        dependency_coordinator=dependency_coordinator,
        quarantine_port=quarantine_port,
        metrics=metrics,
    )


# Backward-compatible patch point used by legacy bootstrap tests.
CompositePipelineRunner = create_composite_runner_with_legacy_fsm_adapter


def _resolve_composite_gold_schema(composite_name: str) -> type | None:
    """Resolve composite Gold contract by composite pipeline name."""
    key = composite_name.removeprefix("composite_")
    return COMPOSITE_GOLD_SCHEMA_REGISTRY.get(key)


def _resolve_composite_config_path(name: str) -> Path:
    """Resolve composite config path from canonical composites directory."""
    config_path = COMPOSITE_CONFIG_DIR / f"{name}.yaml"
    if config_path.exists():
        return config_path

    raise FileNotFoundError(f"Composite config not found: {config_path}")


def load_composite_config(name: str) -> CompositeConfig:
    """Load and validate composite pipeline configuration from YAML.

    Args:
        name: Identifier name.

    Returns:
        Loaded CompositeConfig.
    """
    config_path = _resolve_composite_config_path(name)

    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if isinstance(raw, dict):
        merge_external_dq_overrides(raw, config_path)

    merge = (raw or {}).get("composite", {}).get("merge", {})
    column_groups_file = merge.get("column_groups_file")
    if column_groups_file and "column_groups" not in merge:
        groups_path = config_path.parent / column_groups_file
        if groups_path.exists():
            with groups_path.open(encoding="utf-8") as f:
                groups_raw = yaml.safe_load(f) or {}
            if isinstance(groups_raw, list):
                merge["column_groups"] = groups_raw
            elif isinstance(groups_raw, dict):
                merge["column_groups"] = groups_raw.get("column_groups", [])

    try:
        # Validate using Pydantic schema
        schema = validate_composite_config_payload(raw)
        # Convert to immutable domain objects
        config: CompositeConfig = schema.to_domain()
        return config
    except ValidationError as e:
        # Convert Pydantic errors to ValueError for consistent API
        raise ValueError(f"Invalid composite config '{name}': {e}") from e


def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunnerService:
    """Create a CompositePipelineRunnerService with all dependencies.

    Layer: Returns application-level runner (CompositePipelineRunnerService) ready
    for execution.

    Args:
        config: Composite pipeline configuration.
        runtime: Runtime options (resume, dry_run, etc.).
        run_id: Optional run ID (generated if not provided).

    Returns:
        CompositePipelineRunnerService ready for execution.
    """
    # CIRCULAR-DEPENDENCY: kept local to avoid entrypoints bootstrap cycle.
    from bioetl.composition.entrypoints import RunOptions, build_pipeline_context

    effective_run_id = run_id or str(uuid4())
    settings = get_settings()
    logger = bootstrap_logger_port(
        pipeline=config.name,
        run_id=UUID(effective_run_id),
        log_level="INFO",
    )
    storage = bootstrap_storage_adapter(enable_csv_export=True)
    lock = MemoryLock()

    filter_extraction_service = CompositeFilterExtractionService(logger=logger)
    runner_factory_builder = RunnerFactoryBuilderService(
        logger=logger,
        run_options_cls=RunOptions,
        build_context=build_pipeline_context,
        pipeline_runner_builder=bootstrap_pipeline_runner,
        filter_extraction_service=filter_extraction_service,
    )

    seed_runner_factory = runner_factory_builder.build_seed_factory(
        seed_pipeline=config.seed.pipeline,
        seed_limit=runtime.seed_limit,
        bronze_opts=resolve_bronze_opts(runtime, phase_override=None),
    )
    enricher_runner_factory = runner_factory_builder.build_enricher_factory(
        enrichers=list(config.enrichers),
        bronze_opts=resolve_bronze_opts(
            runtime,
            phase_override=runtime.cached_bronze_enrichers,
        ),
    )
    dependencies_runner_factory = runner_factory_builder.build_dependency_factory(
        dependencies=list(config.dependencies),
        bronze_opts=resolve_bronze_opts(
            runtime,
            phase_override=runtime.cached_bronze_dependencies,
        ),
    )

    support_services = CompositeSupportServicesFactory(
        config=config,
        runtime=runtime,
        settings=settings,
        logger=logger,
        storage=storage,
        run_id=effective_run_id,
        resolve_gold_schema=_resolve_composite_gold_schema,
        load_field_group_registry=_load_field_group_registry,
        create_dq_report_service=_create_dq_report_service,
        checkpoint_manager_cls=CompositeCheckpointService,
    ).build()

    return CompositePipelineRunner(
        config=config,
        runtime=runtime,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        key_extractor=support_services.key_extractor,
        dependency_coordinator=support_services.dependency_coordinator,
        coordinator=support_services.coordinator,
        merger=support_services.merger,
        checkpoint_manager=support_services.checkpoint_manager,
        fsm_state_helper=support_services.fsm_state_helper,
        logger=logger,
        lock=lock,
        run_id=effective_run_id,
        dq_report_service=support_services.dq_report_service,
        quarantine_port=support_services.quarantine_port,
    )


def bootstrap_composite_pipeline(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunnerService:
    """Bootstrap a CompositePipelineRunnerService with all dependencies."""
    return bootstrap_composite_runner(config=config, runtime=runtime, run_id=run_id)


def _load_field_group_registry(
    composite_name: str,
    logger: LoggerPort,
) -> FieldGroupRegistry | None:
    """Load field group registry for a composite pipeline.

    Attempts to load field group configuration from YAML. Returns None
    if no configuration is found (graceful degradation).

    Args:
        composite_name: Composite pipeline name (e.g., "composite_publication").
        logger: Structured logger.

    Returns:
        FieldGroupRegistry if config found, None otherwise.
    """
    # Extract entity from composite name (e.g., "composite_publication" -> "publication")
    entity = (
        composite_name.replace("composite_", "")
        if "_" in composite_name
        else composite_name
    )
    config_path = FIELD_GROUP_CONFIG_DIR / f"{entity}.yaml"

    if not config_path.exists():
        logger.debug(
            "No field group config found, skipping",
            config_path=str(config_path),
        )
        return None

    try:
        registry = load_field_groups(config_path)
        logger.info(
            "Loaded field group registry",
            config_path=str(config_path),
            groups=len(registry.groups),
            fields=registry.field_count,
            columns=registry.column_count,
        )
        return registry
    except (FieldGroupLoadError, FileNotFoundError) as e:
        logger.warning(
            "Failed to load field group config, continuing without it",
            error=str(e),
            config_path=str(config_path),
        )
        return None


def _create_dq_report_service(
    logger: LoggerPort,
    settings: Settings,
) -> DQReportService:
    """Create DQ report service for composite pipelines."""
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.infrastructure.export.dq_report_writer import DQReportWriter

    # Create DQ report writer
    reports_base_path = Path(settings.data_dir) / "output" / "reports" / "dq"
    report_writer = DQReportWriter(
        base_path=reports_base_path,
        logger=logger,
    )

    return DQReportService(
        logger=logger,
        report_writer=report_writer,
    )
