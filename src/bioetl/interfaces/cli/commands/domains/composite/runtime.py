"""Runtime option helpers for `run-composite` command."""

from __future__ import annotations

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    echo_health_server_info,
)
from bioetl.interfaces.cli.formatters import echo_info, echo_warning


def parse_enrich_only(enrich_only: str | None) -> tuple[str, ...] | None:
    """Parse comma-separated `enrich_only` value into tuple.

    Args:
        enrich_only: Comma-separated enricher names from the CLI option
            (e.g., 'crossref,pubmed'), or None if the option was not set.

    Returns:
        Tuple of stripped enricher name strings, or None if the input is empty or None.
    """
    if not enrich_only:
        return None
    return tuple(item.strip() for item in enrich_only.split(","))


def build_runtime_config(
    *,
    resume: bool,
    dry_run: bool,
    seed_limit: int | None,
    enrich_only: str | None,
    required_only: bool,
    force_enricher: str | None,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
    cached_bronze_enrichers: bool | None,
    cached_bronze_dependencies: bool,
) -> CompositeRuntimeConfig:
    """Build composite runtime config from CLI options.

    Args:
        resume: Whether to resume from the last checkpoint.
        dry_run: When True, no data is written to storage.
        seed_limit: Maximum number of records to fetch during the seed phase;
            no limit applied if None.
        enrich_only: Comma-separated list of enricher names to run; all enrichers
            run if None.
        required_only: When True, optional enrichers are skipped.
        force_enricher: Enricher name whose checkpoint is ignored for a forced re-run;
            no forced re-run if None.
        use_cached_bronze: When True, loads data from the Bronze cache instead of the API.
        cached_bronze_date: ISO date string (YYYY-MM-DD) used to filter cached Bronze files;
            not applied if None.
        cached_bronze_path: Explicit path to a Bronze cache directory; auto-resolved if None.
        cached_bronze_enrichers: Override cached Bronze usage for enrichers; follows
            ``use_cached_bronze`` if None.
        cached_bronze_dependencies: When True, dependency pipelines also use cached Bronze.

    Returns:
        CompositeRuntimeConfig ready for composite pipeline bootstrap.
    """
    return CompositeRuntimeConfig(
        resume=resume,
        dry_run=dry_run,
        enrich_only=parse_enrich_only(enrich_only),
        required_only=required_only,
        force_enricher=force_enricher,
        seed_limit=seed_limit,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_path=cached_bronze_path,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_enrichers=cached_bronze_enrichers,
        cached_bronze_dependencies=cached_bronze_dependencies,
    )


def echo_composite_startup(
    *,
    composite: str,
    dry_run: bool,
    resume: bool,
    cached_bronze_enabled: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Print startup info for composite run.

    Args:
        composite: Composite pipeline name (e.g., 'publication').
        dry_run: When True, displays a dry-run warning in the output.
        resume: When True, displays a resume-mode notice in the output.
        cached_bronze_enabled: When True, prints a warning that cached Bronze
            on composite execution is outside the strict exact-replay boundary.
        health_server: Whether the HTTP health server is enabled.
        health_port: Port the health server is listening on.
    """
    echo_info(f"Starting composite pipeline: {composite}")
    if dry_run:
        echo_warning("Dry-run mode: no data will be written")
    if resume:
        echo_info("Resume mode: continuing from last checkpoint")
    if cached_bronze_enabled:
        echo_warning(
            "Cached Bronze inputs on composite execution are outside the strict "
            "exact-replay boundary; treat this run as rebuild/resume, not exact replay."
        )
    echo_health_server_info(health_server, health_port)
