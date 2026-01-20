"""Bootstrap functions for Composite Pipeline.

Handles initialization and wiring for CompositePipelineRunner.
See ADR-026 for architectural decisions.
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
from bioetl.composition._bootstrap import bootstrap_logger, bootstrap_storage
from bioetl.composition.bootstrap import bootstrap_pipeline
from bioetl.composition.entrypoints import RunOptions, build_pipeline_context
from bioetl.domain.composite.config import CompositeConfig
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.schemas.composite_config import CompositeConfigFileSchema
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.core.runner import PipelineRunner

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


def bootstrap_composite_pipeline(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunner:
    """Bootstrap a CompositePipelineRunner with all dependencies.

    Args:
        config: Composite pipeline configuration.
        runtime: Runtime options (resume, dry_run, etc.).
        run_id: Optional run ID (generated if not provided).

    Returns:
        CompositePipelineRunner ready for execution.
    """
    effective_run_id = run_id or str(uuid4())
    settings = get_settings()

    # Bootstrap logger (without settings - uses log_level parameter)
    logger = bootstrap_logger(
        pipeline=config.name,
        run_id=UUID(effective_run_id),
        log_level="INFO",
    )

    # Bootstrap storage for reading Silver tables
    storage = bootstrap_storage()

    # Bootstrap lock (using in-memory lock for local execution)
    lock = MemoryLock()

    # Create seed runner factory
    def seed_runner_factory() -> PipelineRunner:
        options = RunOptions(
            run_type="incremental",
            limit=runtime.seed_limit,
        )
        ctx = build_pipeline_context(config.seed.pipeline, options)
        return bootstrap_pipeline(ctx)

    # Build enricher config lookup for fast access
    enricher_configs = {e.pipeline: e for e in config.enrichers}

    # Create enricher runner factory
    def enricher_runner_factory(
        pipeline_name: str, keys: pl.DataFrame
    ) -> PipelineRunner:
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
        return bootstrap_pipeline(ctx)

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
    )


__all__ = [
    "CompositeRuntimeConfig",
    "bootstrap_composite_pipeline",
    "load_composite_config",
]
