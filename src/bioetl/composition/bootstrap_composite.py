"""Bootstrap functions for Composite Pipeline.

Handles initialization and wiring for CompositePipelineRunner.
See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import yaml

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
from bioetl.domain.composite.config import (
    CompositeConfig,
    CompositeDQConfig,
    DQOverrideConfig,
    EnricherConfig,
    ExecutionConfig,
    LineageConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.locking.memory_lock import MemoryLock

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.core.runner import PipelineRunner

# Default composite config path
COMPOSITE_CONFIG_DIR = Path("configs/pipelines/composite")


def load_composite_config(name: str) -> CompositeConfig:
    """Load and parse composite pipeline configuration from YAML.

    Args:
        name: Composite pipeline name (e.g., 'publication').

    Returns:
        CompositeConfig instance.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config is invalid.
    """
    config_path = COMPOSITE_CONFIG_DIR / f"{name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Composite config not found: {config_path}")

    with config_path.open() as f:
        raw = yaml.safe_load(f)

    return _parse_composite_config(raw)


def _parse_composite_config(raw: dict[str, Any]) -> CompositeConfig:
    """Parse raw YAML dict into CompositeConfig.

    Args:
        raw: Raw YAML dictionary.

    Returns:
        CompositeConfig instance.
    """
    composite = raw.get("composite", {})

    # Parse seed config
    seed_raw = composite.get("seed", {})
    seed = SeedConfig(
        pipeline=seed_raw.get("pipeline", ""),
        output_keys=tuple(seed_raw.get("output_keys", [])),
        silver_table=seed_raw.get("silver_table", ""),
    )

    # Parse enrichers
    enrichers_raw = composite.get("enrichers", [])
    enrichers = tuple(
        EnricherConfig(
            pipeline=e.get("pipeline", ""),
            join_keys=tuple(e.get("join_keys", [])),
            required=e.get("required", False),
            filter_condition=e.get("filter_condition"),
            timeout_seconds=e.get("timeout_seconds", 600),
            silver_table=e.get("silver_table", ""),
            fallback_strategy=e.get("fallback_strategy", "fail"),
        )
        for e in enrichers_raw
    )

    # Parse merge config
    merge_raw = composite.get("merge", {})
    output_raw = merge_raw.get("output", {})
    merge = MergeConfig(
        strategy=MergeStrategy(merge_raw.get("strategy", "left_outer")),
        conflict_resolution=ConflictResolution(
            merge_raw.get("conflict_resolution", "seed_priority")
        ),
        field_priorities=merge_raw.get("field_priorities", {}),
        output_silver_path=output_raw.get("silver", ""),
        output_gold_path=output_raw.get("gold", ""),
    )

    # Parse DQ config
    dq_raw = composite.get("dq_rules", {})
    # Convert enricher_overrides from raw dicts to DQOverrideConfig objects
    overrides_raw = dq_raw.get("enricher_overrides", {})
    enricher_overrides = {
        name: DQOverrideConfig(
            soft_fail_threshold=override.get("soft_fail_threshold"),
            hard_fail_threshold=override.get("hard_fail_threshold"),
        )
        for name, override in overrides_raw.items()
    }
    dq = CompositeDQConfig(
        soft_fail_threshold=dq_raw.get("soft_fail_threshold", 0.10),
        hard_fail_threshold=dq_raw.get("hard_fail_threshold", 0.30),
        enricher_overrides=enricher_overrides,
        required_fields=tuple(dq_raw.get("required_fields", [])),
    )

    # Parse execution config
    exec_raw = composite.get("execution", {})
    retry_raw = exec_raw.get("retry", {})
    execution = ExecutionConfig(
        max_concurrency=exec_raw.get("max_concurrency", 4),
        checkpoint_enabled=exec_raw.get("checkpoint_enabled", True),
        retry_max_attempts=retry_raw.get("max_attempts", 3),
        retry_backoff_multiplier=retry_raw.get("backoff_multiplier", 2.0),
    )

    # Parse lineage config
    lineage_raw = composite.get("lineage", {})
    lineage = LineageConfig(
        track_field_sources=lineage_raw.get("track_field_sources", True),
        track_timestamps=lineage_raw.get("track_timestamps", True),
        track_status=lineage_raw.get("track_status", True),
    )

    return CompositeConfig(
        name=composite.get("name", ""),
        version=composite.get("version", "1.0.0"),
        seed=seed,
        enrichers=enrichers,
        merge=merge,
        dq=dq,
        execution=execution,
        lineage=lineage,
    )


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

    # Create enricher runner factory
    def enricher_runner_factory(
        pipeline_name: str, keys: pl.DataFrame
    ) -> PipelineRunner:
        # For enrichers in composite mode:
        # 1. Disable YAML input_filter - we don't want enrichers to use their
        #    own filter files (e.g., data/input/dois.csv). Instead, they should
        #    fetch all available data and MergeService will join only matching keys.
        # 2. Future optimization: extract DOIs/PMIDs from keys and pass as filter_ids
        #    to limit API calls to only relevant records.
        options = RunOptions(
            run_type="incremental",
            limit=len(keys) if keys is not None else None,
            ignore_yaml_filter=True,  # Disable YAML input_filter for composite mode
        )
        ctx = build_pipeline_context(pipeline_name, options)
        return bootstrap_pipeline(ctx)

    # Create services
    # Base path for resolving Silver table locations
    silver_base_path = str(Path(settings.data_dir) / "output")
    key_extractor = KeyExtractorService(
        storage=storage,
        logger=logger,
        base_path=silver_base_path,
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
        base_path=silver_base_path,
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
