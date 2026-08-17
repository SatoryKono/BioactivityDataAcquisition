"""Typed input helpers for the public run-composite CLI command."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from bioetl.interfaces.cli.commands.domains.composite.runtime import (
    CompositeRuntimeCliInput,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)
from bioetl.interfaces.cli.commands.domains.shared.option_mapping import (
    option_bool_get,
    option_int_get,
    option_optional_bool_get,
    option_optional_int_get,
    option_optional_str_get,
    option_str,
)

__all__ = ["CompositeRunCommandInput", "build_composite_run_command_input"]


@dataclass(frozen=True, slots=True)
class CompositeRunCommandInput:
    """Typed CLI bundle for the ``run-composite`` command callback."""

    composite: str
    runtime: CompositeRuntimeCliInput = field(default_factory=CompositeRuntimeCliInput)
    debug: bool = False
    health_server: bool = True
    health_port: int = DEFAULT_HEALTH_SERVER_PORT
    # Align with workflow/run Click defaults (#7564): opt-in Ops HTTP backend.
    ensure_observability_backend: bool = False
    observability_backend_port: int = DEFAULT_HEALTH_SERVER_PORT


def build_composite_run_command_input(
    options: Mapping[str, object],
) -> CompositeRunCommandInput:
    """Convert Click callback kwargs into the typed composite CLI bundle."""
    return CompositeRunCommandInput(
        composite=option_str(options, "composite"),
        runtime=CompositeRuntimeCliInput(
            resume=option_bool_get(options, "resume", False),
            dry_run=option_bool_get(options, "dry_run", False),
            seed_limit=option_optional_int_get(options, "seed_limit"),
            enrich_only=option_optional_str_get(options, "enrich_only"),
            required_only=option_bool_get(options, "required_only", False),
            force_enricher=option_optional_str_get(options, "force_enricher"),
            use_cached_bronze=option_bool_get(options, "use_cached_bronze", False),
            cached_bronze_date=option_optional_str_get(options, "cached_bronze_date"),
            cached_bronze_path=option_optional_str_get(options, "cached_bronze_path"),
            cached_bronze_enrichers=option_optional_bool_get(
                options, "cached_bronze_enrichers"
            ),
            cached_bronze_dependencies=option_bool_get(
                options, "cached_bronze_dependencies", False
            ),
        ),
        debug=option_bool_get(options, "debug", False),
        health_server=option_bool_get(options, "health_server", True),
        health_port=option_int_get(options, "health_port", DEFAULT_HEALTH_SERVER_PORT),
        ensure_observability_backend=option_bool_get(
            options, "ensure_observability_backend", False
        ),
        observability_backend_port=option_int_get(
            options, "observability_backend_port", DEFAULT_HEALTH_SERVER_PORT
        ),
    )
