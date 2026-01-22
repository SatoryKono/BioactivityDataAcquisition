"""Bootstrap functions for Composite Pipeline execution.

Handles initialization and wiring for CompositePipelineRunner.
See ADR-026 for architectural decisions.

Composite pipelines execute multiple related pipelines in sequence:
1. Seed phase: Fetch primary entities (e.g., publications)
2. Enrichment phase: Fetch supplementary data using seed keys
3. Merge phase: Combine results into unified datasets
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import yaml
from pydantic import ValidationError

from bioetl.application.composite.checkpoint import CompositeCheckpointManager
from bioetl.application.composite.coordinator import EnrichmentCoordinator
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.application.composite.merger import MergeService
from bioetl.application.composite.runner import (
    CompositePipelineRunner,
    CompositeRuntimeConfig,
)
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger_port
from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from bioetl.domain.composite.config import CompositeConfig
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.schemas.composite_config import CompositeConfigFileSchema
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "CompositeRuntimeConfig",
    # Deprecated alias (backward compatibility)
    "bootstrap_composite_pipeline",
    # Canonical name (use this)
    "bootstrap_composite_runner",
    "load_composite_config",
]

# Default composite config path
COMPOSITE_CONFIG_DIR = Path("configs/pipelines/composite")


def load_composite_config(name: str) -> CompositeConfig:
    """Load and parse composite pipeline configuration from YAML.

    Uses Pydantic schema validation (CompositeConfigFileSchema) to ensure
    configuration is valid before converting to domain objects.

    Args:
        name: Composite pipeline name (e.g., 'publication').

    Returns:
        CompositeConfig instance.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config is invalid (wraps Pydantic ValidationError).
    """
    config_path = COMPOSITE_CONFIG_DIR / f"{name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Composite config not found: {config_path}")

    with config_path.open() as f:
        raw = yaml.safe_load(f)

    try:
        # Validate using Pydantic schema
        schema = CompositeConfigFileSchema.model_validate(raw)
        # Convert to immutable domain objects
        return schema.to_domain()
    except ValidationError as e:
        # Convert Pydantic errors to ValueError for consistent API
        raise ValueError(f"Invalid composite config '{name}': {e}") from e


def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunner:
    """Create a CompositePipelineRunner with all dependencies.

    Layer: Returns application-level runner (CompositePipelineRunner) ready
    for execution.

    Args:
        config: Composite pipeline configuration.
        runtime: Runtime options (resume, dry_run, etc.).
        run_id: Optional run ID (generated if not provided).

    Returns:
        CompositePipelineRunner ready for execution.
    """
    # CIRCULAR-DEPENDENCY: Local import required to break circular dependency.
    # Import chain: entrypoints -> _bootstrap -> bootstrap -> runtime -> composite -> entrypoints
    # Moving this import to module level would cause ImportError at startup.
    from bioetl.composition.entrypoints import RunOptions, build_pipeline_context

    effective_run_id = run_id or str(uuid4())
    settings = get_settings()

    # Bootstrap logger (without settings - uses log_level parameter)
    logger = bootstrap_logger_port(
        pipeline=config.name,
        run_id=UUID(effective_run_id),
        log_level="INFO",
    )

    # Bootstrap storage for reading Silver tables and writing merged data
    # Enable CSV export for composite pipelines (merged Silver/Gold data)
    storage = bootstrap_storage_adapter(enable_csv_export=True)

    # Bootstrap lock (using in-memory lock for local execution)
    lock = MemoryLock()

    # Create seed runner factory
    def seed_runner_factory() -> PipelineRunner:
        """Create PipelineRunner for the seed phase.

        The seed pipeline runs first to fetch primary entities (e.g., publications)
        which provide join keys (DOI, PMID) for subsequent enricher pipelines.

        Returns:
            PipelineRunner configured for seed pipeline execution with
            optional limit from runtime config.
        """
        options = RunOptions(
            run_type="incremental",
            limit=runtime.seed_limit,
        )
        ctx = build_pipeline_context(config.seed.pipeline, options)
        return bootstrap_pipeline_runner(ctx)

    # Build enricher config lookup for fast access
    enricher_configs = {e.pipeline: e for e in config.enrichers}

    # Create enricher runner factory
    def enricher_runner_factory(
        pipeline_name: str, keys: pl.DataFrame
    ) -> PipelineRunner:
        """Create PipelineRunner for an enricher phase.

        Enricher pipelines fetch supplementary data (citations, metadata) using
        join keys extracted from seed results. This factory applies composite-specific
        configuration per ADR-026.

        Configuration adjustments:
        - Disables YAML input_filter to prevent enrichers from using their own
          filter files (e.g., data/input/dois.csv)
        - Extracts join key values (DOI, PMID) from seed results DataFrame
        - Passes extracted IDs as filter_ids to limit API calls to relevant records

        Args:
            pipeline_name: Name of the enricher pipeline to instantiate.
            keys: DataFrame containing seed results with join key columns.

        Returns:
            PipelineRunner configured for enricher pipeline execution with
            programmatic filtering based on seed results.
        """
        # For enrichers in composite mode:
        # 1. Disable YAML input_filter - we don't want enrichers to use their
        #    own filter files (e.g., data/input/dois.csv).
        # 2. Extract DOIs/PMIDs from keys DataFrame based on enricher's join_keys
        #    and pass them as filter_ids to limit API calls.

        # Get enricher config to determine join keys
        enricher_cfg = enricher_configs.get(pipeline_name)
        filter_ids: tuple[str, ...] | None = None
        filter_field: str | None = None

        if enricher_cfg and keys is not None and len(keys) > 0:
            # Use the first join key (usually 'doi' or 'pmid')
            join_keys = enricher_cfg.join_keys
            for key in join_keys:
                if key in keys.columns:
                    # Extract unique non-null values from the keys DataFrame
                    key_values = (
                        keys.select(key).drop_nulls().unique().to_series().to_list()
                    )
                    if key_values:
                        filter_ids = tuple(str(v) for v in key_values)
                        filter_field = key
                        break

        options = RunOptions(
            run_type="incremental",
            limit=len(keys) if keys is not None else None,
            ignore_yaml_filter=True,  # Disable YAML input_filter for composite mode
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        ctx = build_pipeline_context(pipeline_name, options)
        return bootstrap_pipeline_runner(ctx)

    # Create services
    # Base path for resolving Silver table locations
    silver_base_path = str(Path(settings.data_dir) / "output")

    # DeltaReader for reading Silver tables (implements DeltaReaderPort)
    delta_reader = DeltaReader(
        base_path=silver_base_path,
        logger=logger,
    )

    key_extractor = KeyExtractorService(
        delta_reader=delta_reader,
        logger=logger,
    )

    coordinator = EnrichmentCoordinator(
        logger=logger,
        dq_config=config.dq,
        max_concurrency=config.execution.max_concurrency,
    )

    merger = MergeService(
        merge_config=config.merge,
        storage=storage,
        logger=logger,
        delta_reader=delta_reader,
    )

    checkpoint_dir = Path(settings.data_dir) / "checkpoints" / "composite"
    checkpoint_manager = CompositeCheckpointManager(
        composite_name=config.name,
        run_id=effective_run_id,
        checkpoint_dir=checkpoint_dir,
        logger=logger,
        resume=runtime.resume,
    )

    # Create DQ report service for composite (optional)
    dq_report_service = _create_dq_report_service(logger, settings)

    return CompositePipelineRunner(
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
        run_id=effective_run_id,
        dq_report_service=dq_report_service,
    )


def bootstrap_composite_pipeline(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunner:
    """Bootstrap a CompositePipelineRunner with all dependencies.

    .. deprecated::
        Use :func:`bootstrap_composite_runner` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        config: Composite pipeline configuration.
        runtime: Runtime options (resume, dry_run, etc.).
        run_id: Optional run ID (generated if not provided).

    Returns:
        CompositePipelineRunner ready for execution.
    """
    return bootstrap_composite_runner(config=config, runtime=runtime, run_id=run_id)


def _create_dq_report_service(
    logger: LoggerPort,
    settings: Settings,
) -> DQReportService | None:
    """Create DQ report service for composite pipelines.

    Returns None if DQ reporting is not configured.

    Args:
        logger: Structured logger.
        settings: Application settings.

    Returns:
        DQReportService instance or None.
    """
    try:
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
            # Analyzers are optional - reports will be generated
            # for layers where analyzers are available
        )
    except Exception as e:
        logger.debug(
            "dq_report_service_creation_failed",
            error=str(e),
        )
        return None
