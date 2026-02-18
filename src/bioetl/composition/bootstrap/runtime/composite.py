"""Bootstrap functions for Composite Pipeline execution. See ADR-026."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import yaml
from pydantic import ValidationError

from bioetl.application.composite.checkpoint import CompositeCheckpointManager
from bioetl.application.composite.coordinator import EnrichmentCoordinator
from bioetl.application.composite.cross_validator import EnrichmentCrossValidator
from bioetl.application.composite.dependency_coordinator import DependencyCoordinator
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.application.composite.merger import MergeService
from bioetl.application.composite.runner import (
    CompositePipelineRunner,
    CompositeRuntimeConfig,
)
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger_port
from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from bioetl.domain.composite.config import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
)
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
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
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
FIELD_GROUP_CONFIG_DIR = Path("configs/composite/field_groups")


COMPOSITE_GOLD_SCHEMA_REGISTRY: dict[str, type] = {
    "activity": CompositeActivityGoldSchema,
    "assay": CompositeAssayGoldSchema,
    "molecule": CompositeMoleculeGoldSchema,
    "publication": CompositePublicationGoldSchema,
    "target": CompositeTargetGoldSchema,
}


def _resolve_composite_gold_schema(composite_name: str) -> type | None:
    """Resolve composite Gold contract by composite pipeline name."""
    key = composite_name.removeprefix("composite_")
    return COMPOSITE_GOLD_SCHEMA_REGISTRY.get(key)


def _to_id_str(val: Any) -> str:  # Any: accepts int, float, st...
    """Convert value to ID string, handling float-to-int conversion.

    External APIs (like ChEMBL) often expect integer IDs and return 400
    if given floats (e.g., '4044.0'). This helper ensures '4044.0'
    becomes '4044'.
    """
    if val is None:
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val)


def load_composite_config(name: str) -> CompositeConfig:
    """Load and validate composite pipeline configuration from YAML."""
    config_path = COMPOSITE_CONFIG_DIR / f"{name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Composite config not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

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


def _build_fallback_mapping(
    keys: pl.DataFrame,
    filter_key: str,
    join_keys: tuple[str, ...],
) -> dict[str, str] | None:
    """Build ID -> Title fallback mapping if title is in join keys."""
    if "title" not in join_keys or "title" not in keys.columns:
        return None
    pairs = (
        keys.select([filter_key, "title"])
        .drop_nulls()
        .unique(subset=[filter_key])
        .iter_rows()
    )
    return {_to_id_str(k): str(t) for k, t in pairs}


def _find_filter_key(
    join_keys: tuple[str, ...],
    columns: list[str],
) -> str | None:
    """Find the first usable join key (skip title if alternatives exist)."""
    for key in join_keys:
        if key == "title" and len(join_keys) > 1:
            continue
        if key in columns:
            return key
    return None


def _extract_filter_ids_from_keys(
    enricher_cfg: EnricherConfig,
    keys: pl.DataFrame,
    logger: LoggerPort | None = None,
) -> tuple[tuple[str, ...] | None, str | None, dict[str, str] | None]:
    """Extract filter IDs from seed keys for an enricher."""
    if keys is None or len(keys) == 0:
        if logger:
            logger.debug(
                "No keys available for enricher",
                pipeline=enricher_cfg.pipeline,
            )
        return None, None, None
    filter_key = _find_filter_key(enricher_cfg.join_keys, keys.columns)
    if filter_key is None:
        if logger:
            logger.warning(
                "Join key not found in keys columns",
                pipeline=enricher_cfg.pipeline,
                join_keys=list(enricher_cfg.join_keys),
                available_columns=list(keys.columns),
            )
        return None, None, None
    key_values = keys.select(filter_key).drop_nulls().unique().to_series().to_list()
    if not key_values:
        return None, None, None
    filter_ids = tuple(_to_id_str(v) for v in key_values)
    fallback = _build_fallback_mapping(keys, filter_key, enricher_cfg.join_keys)
    return filter_ids, filter_key, fallback


def _extract_field_values(
    keys: pl.DataFrame,
    field: str,
) -> tuple[str, ...] | None:
    """Extract unique non-null values for a single field from keys DataFrame.

    Returns:
        Tuple of string values, or None if field missing or empty.
    """
    if field not in keys.columns:
        return None
    values = keys.select(field).drop_nulls().unique().to_series().to_list()
    if not values:
        return None
    return tuple(_to_id_str(v) for v in values)


def _extract_multi_filter_ids(
    dep_cfg: DependencyConfig,
    keys: pl.DataFrame,
    logger: LoggerPort | None = None,
) -> dict[str, tuple[str, ...]] | None:
    """Extract multi-field filter IDs from seed keys for a dependency.

    For dual-key filtering (e.g., molecule_chembl_id + document_chembl_id),
    extracts unique values for each filter field from the keys DataFrame.

    Args:
        dep_cfg: Dependency configuration with filter_fields.
        keys: DataFrame containing seed keys.
        logger: Optional logger.

    Returns:
        Dict mapping field name to tuple of unique IDs, or None if extraction fails.
    """
    if keys is None or len(keys) == 0:
        return None

    result: dict[str, tuple[str, ...]] = {}
    for field in dep_cfg.effective_filter_fields:
        values = _extract_field_values(keys, field)
        if values is None:
            if logger:
                logger.warning(
                    "Multi-filter field missing or empty",
                    pipeline=dep_cfg.pipeline,
                    field=field,
                    available_columns=list(keys.columns),
                )
            return None
        result[field] = values

    if logger:
        logger.info(
            "Extracted multi-field filter IDs",
            pipeline=dep_cfg.pipeline,
            fields=list(result.keys()),
            counts={f: len(ids) for f, ids in result.items()},
        )

    return result


def _resolve_bronze_opts(
    runtime: CompositeRuntimeConfig,
    phase_override: bool | None,
) -> dict[str, object]:
    """Resolve cached Bronze options for a specific pipeline phase.

    Tri-state resolution: phase_override takes precedence over master switch.
    - None: use master switch (runtime.use_cached_bronze)
    - True/False: override master switch

    Args:
        runtime: Composite runtime configuration with master switch.
        phase_override: Per-phase override (None=follow master).

    Returns:
        Dict with use_cached_bronze, cached_bronze_path, cached_bronze_date.
    """
    effective = (
        phase_override if phase_override is not None else runtime.use_cached_bronze
    )
    return {
        "use_cached_bronze": effective,
        "cached_bronze_path": runtime.cached_bronze_path if effective else None,
        "cached_bronze_date": runtime.cached_bronze_date if effective else None,
    }


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

    # Per-phase cached bronze RunOptions kwargs
    _seed_bronze_opts = _resolve_bronze_opts(runtime, phase_override=None)
    _enricher_bronze_opts = _resolve_bronze_opts(
        runtime, phase_override=runtime.cached_bronze_enrichers
    )
    _dependency_bronze_opts = _resolve_bronze_opts(
        runtime, phase_override=runtime.cached_bronze_dependencies
    )

    def seed_runner_factory() -> PipelineRunner:
        """Create PipelineRunner for the seed phase."""
        options = RunOptions(
            run_type="incremental",
            limit=runtime.seed_limit,
            skip_gold=True,
            **_seed_bronze_opts,  # type: ignore[arg-type]
        )
        ctx = build_pipeline_context(config.seed.pipeline, options)
        return bootstrap_pipeline_runner(ctx)

    # Build enricher config lookup for fast access
    enricher_configs = {e.pipeline: e for e in config.enrichers}

    def enricher_runner_factory(
        pipeline_name: str, keys: pl.DataFrame
    ) -> PipelineRunner:
        """Create PipelineRunner for an enricher phase (ADR-026)."""
        enricher_cfg = enricher_configs.get(pipeline_name)
        filter_ids: tuple[str, ...] | None = None
        filter_field: str | None = None
        fallback_mapping: dict[str, str] | None = None

        if enricher_cfg:
            filter_ids, filter_field, fallback_mapping = _extract_filter_ids_from_keys(
                enricher_cfg, keys, logger
            )

        # Debug logging for enricher filter configuration
        logger.debug(
            "Creating enricher runner",
            pipeline=pipeline_name,
            keys_columns=list(keys.columns) if keys is not None else [],
            keys_count=len(keys) if keys is not None else 0,
            join_keys=list(enricher_cfg.join_keys) if enricher_cfg else [],
            filter_field=filter_field,
            filter_ids_count=len(filter_ids) if filter_ids else 0,
            filter_ids_sample=list(filter_ids)[:5] if filter_ids else [],
        )

        # many_to_one: no limit; one_to_one: limit to seed count
        limit: int | None = None
        if enricher_cfg and enricher_cfg.is_many_to_one:
            limit = None
        elif keys is not None:
            limit = len(keys)

        options = RunOptions(
            run_type="incremental",
            limit=limit,
            ignore_yaml_filter=True,
            skip_gold=True,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            execution_context="enricher",
            **_enricher_bronze_opts,  # type: ignore[arg-type]
        )
        ctx = build_pipeline_context(pipeline_name, options)
        return bootstrap_pipeline_runner(ctx)

    # Build dependency config lookup for fast access
    dependency_configs = {d.pipeline: d for d in config.dependencies}

    # Create dependencies runner factory
    def dependencies_runner_factory(
        pipeline_name: str, keys: pl.DataFrame
    ) -> PipelineRunner:
        """Create PipelineRunner for a dependency phase.

        Dependencies run after the seed to populate Silver tables before enrichers.
        Unlike enrichers which read from Silver, dependencies call APIs to fetch data.

        Note: Chained dependencies (key_source) are handled by DependencyCoordinator
        which provides the correct keys from the source dependency's Silver table.

        Configuration:
        - Extracts join key values from provided keys DataFrame
        - Passes extracted IDs as filter_ids to limit API calls
        - Uses filter_field from config if set (for field name mapping)
        - For multi-field filtering (filter_fields), extracts all fields
          and passes as multi_filter_ids with valid combinations

        Args:
            pipeline_name: Name of the dependency pipeline to instantiate.
            keys: DataFrame containing keys for filtering (from seed or chained source).

        Returns:
            PipelineRunner configured for dependency pipeline execution.
        """
        dep_cfg = dependency_configs.get(pipeline_name)
        filter_ids: tuple[str, ...] | None = None
        filter_field: str | None = None
        multi_filter_ids: dict[str, tuple[str, ...]] | None = None

        if dep_cfg and keys is not None and len(keys) > 0:
            if dep_cfg.is_multi_field_filter:
                # Multi-field filtering: extract all filter fields
                multi_filter_ids = _extract_multi_filter_ids(dep_cfg, keys, logger)
            else:
                # Single-field filtering (existing logic)
                for key in dep_cfg.join_keys:
                    if key in keys.columns:
                        key_values = (
                            keys.select(key).drop_nulls().unique().to_series().to_list()
                        )
                        if key_values:
                            filter_ids = tuple(_to_id_str(v) for v in key_values)
                            # Use filter_field from config if set, otherwise use join_key
                            filter_field = dep_cfg.filter_field or key
                            break

        # Debug logging for dependency filter configuration
        logger.debug(
            "Creating dependency runner",
            pipeline=pipeline_name,
            keys_columns=list(keys.columns) if keys is not None else [],
            keys_count=len(keys) if keys is not None else 0,
            join_keys=list(dep_cfg.join_keys) if dep_cfg else [],
            filter_field=filter_field,
            filter_ids_count=len(filter_ids) if filter_ids else 0,
            filter_ids_sample=list(filter_ids)[:5] if filter_ids else [],
            multi_filter_fields=list(multi_filter_ids.keys())
            if multi_filter_ids
            else [],
            multi_filter_counts={f: len(ids) for f, ids in multi_filter_ids.items()}
            if multi_filter_ids
            else {},
            is_chained=dep_cfg.key_source is not None if dep_cfg else False,
            key_source=dep_cfg.key_source if dep_cfg else None,
        )

        options = RunOptions(
            run_type="incremental",
            limit=len(keys)
            if (filter_ids or multi_filter_ids) and keys is not None
            else None,
            filter_ids=filter_ids,
            filter_field=filter_field,
            multi_filter_ids=multi_filter_ids,
            ignore_yaml_filter=True,
            skip_gold=True,
            execution_context="dependency",
            **_dependency_bronze_opts,  # type: ignore[arg-type]
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

    dependency_coordinator = DependencyCoordinator(
        logger=logger,
        delta_reader=delta_reader,
    )

    coordinator = EnrichmentCoordinator(
        logger=logger,
        dq_config=config.dq,
        max_concurrency=config.execution.max_concurrency,
    )

    # Load field group registry for semantic column grouping and Gold filtering
    field_group_registry = _load_field_group_registry(config.name, logger)

    # Create cross-validator if enabled
    cross_validator: EnrichmentCrossValidator | None = None
    if config.cross_validation.enabled:
        cross_validator = EnrichmentCrossValidator(
            config=config.cross_validation,
            logger=logger,
        )

    merger = MergeService(
        merge_config=config.merge,
        storage=storage,
        logger=logger,
        delta_reader=delta_reader,
        field_group_registry=field_group_registry,
        cross_validator=cross_validator,
        gold_schema=_resolve_composite_gold_schema(config.name),
    )

    checkpoint_dir = Path(settings.data_dir) / "checkpoints" / "composite"
    checkpoint_manager = CompositeCheckpointManager(
        composite_name=config.name,
        run_id=effective_run_id,
        checkpoint_dir=checkpoint_dir,
        logger=logger,
        resume=runtime.resume,
    )

    # Create DQ report service for composite
    dq_report_service = _create_dq_report_service(logger, settings)

    # Create quarantine port for cross-validation quarantine records
    quarantine_port = None
    if config.cross_validation.enabled:
        from bioetl.composition.bootstrap.assembly.checkpoint import (
            bootstrap_quarantine_port,
        )

        quarantine_port = bootstrap_quarantine_port()

    return CompositePipelineRunner(
        config=config,
        runtime=runtime,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        key_extractor=key_extractor,
        dependency_coordinator=dependency_coordinator,
        coordinator=coordinator,
        merger=merger,
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        lock=lock,
        run_id=effective_run_id,
        dq_report_service=dq_report_service,
        quarantine_port=quarantine_port,
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
    warnings.warn(
        "bootstrap_composite_pipeline() is deprecated, use bootstrap_composite_runner() instead",
        DeprecationWarning,
        stacklevel=2,
    )
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
    """Create DQ report service for composite pipelines.

    Args:
        logger: Structured logger.
        settings: Application settings.

    Returns:
        DQReportService instance.

    Raises:
        ImportError: If required modules are not available.
    """
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
