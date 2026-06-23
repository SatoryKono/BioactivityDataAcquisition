"""Typed input helpers for the public run-composite CLI command."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)

__all__ = ["CompositeRunCommandInput", "build_composite_run_command_input"]


@dataclass(frozen=True, slots=True)
class CompositeRunCommandInput:
    """Typed CLI bundle for the ``run-composite`` command callback."""

    composite: str
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
    debug: bool = False
    health_server: bool = True
    health_port: int = DEFAULT_HEALTH_SERVER_PORT
    ensure_observability_backend: bool = True
    observability_backend_port: int = DEFAULT_HEALTH_SERVER_PORT


def build_composite_run_command_input(
    options: Mapping[str, object],
) -> CompositeRunCommandInput:
    """Convert Click callback kwargs into the typed composite CLI bundle."""
    return CompositeRunCommandInput(
        composite=cast(str, options["composite"]),
        resume=cast(bool, options.get("resume", False)),
        dry_run=cast(bool, options.get("dry_run", False)),
        seed_limit=cast(int | None, options.get("seed_limit")),
        enrich_only=cast(str | None, options.get("enrich_only")),
        required_only=cast(bool, options.get("required_only", False)),
        force_enricher=cast(str | None, options.get("force_enricher")),
        use_cached_bronze=cast(bool, options.get("use_cached_bronze", False)),
        cached_bronze_date=cast(str | None, options.get("cached_bronze_date")),
        cached_bronze_path=cast(str | None, options.get("cached_bronze_path")),
        cached_bronze_enrichers=cast(
            bool | None,
            options.get("cached_bronze_enrichers"),
        ),
        cached_bronze_dependencies=cast(
            bool,
            options.get("cached_bronze_dependencies", False),
        ),
        debug=cast(bool, options.get("debug", False)),
        health_server=cast(bool, options.get("health_server", True)),
        health_port=cast(int, options.get("health_port", DEFAULT_HEALTH_SERVER_PORT)),
        ensure_observability_backend=cast(
            bool,
            options.get("ensure_observability_backend", True),
        ),
        observability_backend_port=cast(
            int,
            options.get("observability_backend_port", DEFAULT_HEALTH_SERVER_PORT),
        ),
    )
