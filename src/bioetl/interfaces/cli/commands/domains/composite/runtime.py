"""Runtime option helpers for `run-composite` command."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    echo_health_server_info,
)
from bioetl.interfaces.cli.formatters import echo_info, echo_warning


@dataclass(frozen=True, slots=True)
class CompositeRuntimeCliInput:
    """Typed CLI option bundle for composite runtime construction."""

    resume: bool = False
    dry_run: bool = False
    seed_limit: int | None = None
    enrich_only: str | None = None
    required_only: bool = False
    force_enricher: str | None = None
    use_cached_bronze: bool = False
    cached_bronze_date: str | None = None
    cached_bronze_path: str | None = None
    cached_bronze_enrichers: bool | None = None
    cached_bronze_dependencies: bool = False


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
    inputs: CompositeRuntimeCliInput | None = None,
    **overrides: object,
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
    resolved = inputs or CompositeRuntimeCliInput()
    if overrides:
        resolved = CompositeRuntimeCliInput(
            resume=overrides.get("resume", resolved.resume),  # type: ignore[arg-type]
            dry_run=overrides.get("dry_run", resolved.dry_run),  # type: ignore[arg-type]
            seed_limit=overrides.get("seed_limit", resolved.seed_limit),  # type: ignore[arg-type]
            enrich_only=overrides.get("enrich_only", resolved.enrich_only),  # type: ignore[arg-type]
            required_only=overrides.get("required_only", resolved.required_only),  # type: ignore[arg-type]
            force_enricher=overrides.get("force_enricher", resolved.force_enricher),  # type: ignore[arg-type]
            use_cached_bronze=overrides.get(
                "use_cached_bronze",
                resolved.use_cached_bronze,
            ),  # type: ignore[arg-type]
            cached_bronze_date=overrides.get(
                "cached_bronze_date",
                resolved.cached_bronze_date,
            ),  # type: ignore[arg-type]
            cached_bronze_path=overrides.get(
                "cached_bronze_path",
                resolved.cached_bronze_path,
            ),  # type: ignore[arg-type]
            cached_bronze_enrichers=overrides.get(
                "cached_bronze_enrichers",
                resolved.cached_bronze_enrichers,
            ),  # type: ignore[arg-type]
            cached_bronze_dependencies=overrides.get(
                "cached_bronze_dependencies",
                resolved.cached_bronze_dependencies,
            ),  # type: ignore[arg-type]
        )
    return CompositeRuntimeConfig(
        resume=resolved.resume,
        dry_run=resolved.dry_run,
        enrich_only=parse_enrich_only(resolved.enrich_only),
        required_only=resolved.required_only,
        force_enricher=resolved.force_enricher,
        seed_limit=resolved.seed_limit,
        use_cached_bronze=resolved.use_cached_bronze,
        cached_bronze_path=resolved.cached_bronze_path,
        cached_bronze_date=resolved.cached_bronze_date,
        cached_bronze_enrichers=resolved.cached_bronze_enrichers,
        cached_bronze_dependencies=resolved.cached_bronze_dependencies,
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
