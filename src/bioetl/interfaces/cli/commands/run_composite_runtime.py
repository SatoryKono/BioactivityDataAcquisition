"""Runtime option helpers for `run-composite` command."""

from __future__ import annotations

from bioetl.application.composite.runner import CompositeRuntimeConfig
from bioetl.interfaces.cli.commands.health_server_integration import (
    echo_health_server_info,
)
from bioetl.interfaces.cli.formatters import echo_info, echo_warning


def parse_enrich_only(enrich_only: str | None) -> tuple[str, ...] | None:
    """Parse comma-separated `enrich_only` value into tuple."""
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
    """Build composite runtime config from CLI options."""
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
    health_server: bool,
    health_port: int,
) -> None:
    """Print startup info for composite run."""
    echo_info(f"Starting composite pipeline: {composite}")
    if dry_run:
        echo_warning("Dry-run mode: no data will be written")
    if resume:
        echo_info("Resume mode: continuing from last checkpoint")
    echo_health_server_info(health_server, health_port)
