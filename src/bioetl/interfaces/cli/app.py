"""Typer-based CLI for BioETL pipelines."""

from __future__ import annotations

from functools import partial
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Callable, Literal, Optional

from rich.console import Console
from rich.table import Table
import typer

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.application.pipelines.registry import (
    get_pipeline_factory,
    get_registered_pipelines,
)
from bioetl.domain.configs import MetricsConfig
from bioetl.domain.provider_registry import (
    InMemoryProviderRegistry,
    ProviderRegistryABC,
    ProviderRegistryLoaderABC,
)
from bioetl.infrastructure.clients.provider_registry_loader import (
    create_provider_loader,
)
from bioetl.infrastructure.observability.factories import default_logging_port
from bioetl.infrastructure.observability.server import (
    start_metrics_server_once,
)
from bioetl.interfaces.container_factory import build_default_container
from bioetl.interfaces.observability import LoggingPortABC
from bioetl.interfaces.wiring import create_config_loader

app = typer.Typer(
    name="bioetl",
    help="Bioactivity Data Acquisition ETL CLI",
    add_completion=False,
)
console = Console()
logger = default_logging_port()


def _get_config_base_dir() -> Path:
    return Path(os.environ.get("BIOETL_CONFIG_DIR", "configs"))


def _resolve_config_path(pipeline_name: str) -> Path:
    """Resolve default config path from a pipeline name.

    Expects pipeline name in the form "{entity}_{provider}".
    """

    try:
        entity, provider = pipeline_name.rsplit("_", 1)
    except ValueError:
        # Fallback if naming does not match, assume chembl
        entity = pipeline_name
        provider = "chembl"

    return _get_config_base_dir() / "pipelines" / provider / f"{entity}.yaml"


@app.command()
def list_pipelines() -> None:
    """List available pipelines from the registry."""

    table = Table(title="Available Pipelines")
    table.add_column("Name", style="cyan")
    table.add_column("Class", style="green")

    for name, factory in get_registered_pipelines().items():
        table.add_row(name, _get_pipeline_factory_name(factory))

    console.print(table)


@app.command()
def validate_config(config_path: Path) -> None:
    """Validate a configuration file and print basic info."""

    config_loader = create_config_loader()
    try:
        config = build_runtime_config(
            config_path=config_path,
            loader=config_loader,
        )
        console.print(f"[green]Config {config_path} is valid![/green]")
        console.print(f"Entity: {config.entity_name}")
        console.print(f"Provider: {config.provider}")
    except Exception as exc:  # pragma: no cover - CLI safety
        console.print(f"[red]Config validation failed:[/red] {exc}")
        sys.exit(1)


@app.command()
def run(
    pipeline_name: str,
    profile: str = typer.Option(
        "default",
        help="Configuration profile",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run without writing output",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Path to config file",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Limit number of records to process",
    ),
    input_path: Optional[Path] = typer.Option(
        None,
        "--input-path",
        help="Path to CSV input file",
    ),
    input_mode: Optional[Literal["csv", "id_only", "auto_detect"]] = typer.Option(
        None,
        "--input-mode",
        help=("Record source: csv (full dataset) | " "id_only (ID list) | auto_detect"),
    ),
    csv_delimiter: Optional[str] = typer.Option(
        None,
        "--csv-delimiter",
        help="Delimiter for CSV input",
    ),
    csv_header: Optional[bool] = typer.Option(
        None,
        "--csv-header/--no-csv-header",
        help="Indicate whether CSV input contains a header row",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        help="Run pipeline in a background process",
    ),
) -> None:
    """Run an ETL pipeline for the given name and profile."""

    config_loader = create_config_loader()
    bound_logger = logger.apply_bind(
        pipeline_name=pipeline_name,
        profile=profile,
        limit=limit,
        background=background,
    )
    start_time = time.perf_counter()
    config_context: dict[str, Any] = {
        "pipeline_name": pipeline_name,
        "profile": profile,
        "limit": limit,
        "background": background,
        "dry_run": dry_run,
    }

    try:
        pipeline_factory = get_pipeline_factory(pipeline_name)
        config_context["pipeline_factory"] = _get_pipeline_factory_name(
            pipeline_factory
        )
        base_dir = _get_config_base_dir()
        requested_config_path = config_path or _resolve_config_path(
            pipeline_name,
        )
        resolved_config_path = _resolve_config_location(
            config_path=config_path,
            pipeline_name=pipeline_name,
            base_dir=base_dir,
        )
        if not resolved_config_path:
            bound_logger.error(
                "config_not_found",
                config_path=str(requested_config_path),
                **config_context,
            )
            sys.exit(1)

        config_context["config_path"] = str(resolved_config_path)

        cli_overrides = _collect_cli_overrides(
            output=output,
            input_path=input_path,
            input_mode=input_mode,
            csv_delimiter=csv_delimiter,
            csv_header=csv_header,
        )
        config = build_runtime_config(
            config_path=resolved_config_path,
            profile=profile,
            configs_root=base_dir,
            cli_overrides=cli_overrides,
            loader=config_loader,
        )
        _start_metrics_exporter(
            config.metrics,
            dry_run=dry_run,
            logger=bound_logger,
        )
        provider_config_path = base_dir / "providers.yaml"
        provider_loader_factory: (
            Callable[
                [],
                ProviderRegistryLoaderABC,
            ]
            | None
        ) = partial(
            create_provider_loader,
            config_path=provider_config_path,
        )
        provider_loader: ProviderRegistryLoaderABC | None = None
        provider_registry: ProviderRegistryABC | None = None
        try:
            provider_loader = provider_loader_factory()
        except FileNotFoundError:
            console.print(
                "[yellow]Providers config not found; " "using empty registry[/yellow]",
            )
            provider_registry = InMemoryProviderRegistry()
            provider_loader_factory = None

        orchestrator = PipelineOrchestrator(
            pipeline_name=pipeline_name,
            config=config,
            provider_registry=provider_registry,
            provider_loader=provider_loader,
            provider_loader_factory=provider_loader_factory,
            container_factory=build_default_container,
        )

        console.print(
            f"[bold green]Starting pipeline: {pipeline_name}[/bold green]",
        )
        bound_logger.info("pipeline_start", **config_context)

        if background:
            future = orchestrator.run_in_background(
                dry_run=dry_run,
                limit=limit,
            )
            console.print(
                "[yellow]Pipeline submitted to background " "executor[/yellow]",
            )
            result = future.result()
        else:
            result = orchestrator.run_pipeline(
                dry_run=dry_run,
                limit=limit,
            )

        if result.success:
            console.print(
                "[bold green]Pipeline finished successfully!" "[/bold green]",
            )
            console.print(
                f"Rows processed: {result.row_count}",
            )
            console.print(
                f"Duration: {result.duration_sec:.2f}s",
            )
            bound_logger.info(
                "pipeline_completed",
                duration_sec=result.duration_sec,
                row_count=result.row_count,
                **config_context,
            )
        else:
            console.print("[bold red]Pipeline failed![/bold red]")
            bound_logger.error(
                "pipeline_failed",
                duration_sec=result.duration_sec,
                row_count=result.row_count,
                **config_context,
            )
            sys.exit(1)

    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    except Exception:  # pragma: no cover - CLI safety
        elapsed = time.perf_counter() - start_time
        bound_logger.error(
            "pipeline_exception",
            duration_sec=elapsed,
            row_count=None,
            stacktrace=traceback.format_exc(),
            **config_context,
        )
        console.print_exception()
        sys.exit(1)


@app.command()
def smoke_run(pipeline_name: str) -> None:
    """Run a development dry-run with a small record limit."""

    run(pipeline_name, profile="development", dry_run=True, limit=10)


def _resolve_config_location(
    *,
    config_path: Optional[Path],
    pipeline_name: str,
    base_dir: Path,
) -> Optional[Path]:
    """Resolve config path relative to base_dir if needed."""

    candidate_path = config_path or _resolve_config_path(pipeline_name)
    path = Path(candidate_path)

    if path.is_absolute() or path.exists() or path.is_relative_to(base_dir):
        resolved = path
    else:
        resolved = base_dir / path

    if resolved.exists():
        return resolved

    console.print(f"[red]Config file not found at {resolved}[/red]")
    console.print("Please provide --config explicitly.")
    return None


def _start_metrics_exporter(
    metrics_config: MetricsConfig,
    *,
    dry_run: bool = False,
    logger: LoggingPortABC | None = None,
) -> None:
    """Start Prometheus metrics exporter if enabled.

    Skips in dry-run or when metrics are disabled, and avoids failing CLI
    on socket binding errors.
    """

    if dry_run or not metrics_config.enabled:
        if logger:
            logger.info(
                "metrics_exporter_skipped",
                dry_run=dry_run,
                enabled=metrics_config.enabled,
                address=metrics_config.address,
                port=metrics_config.port,
            )
        return

    try:
        started = start_metrics_server_once(
            enabled=True,
            port=metrics_config.port,
            address=metrics_config.address,
        )
    except Exception:  # pragma: no cover - defensive
        console.print(
            "[yellow]Prometheus metrics exporter not started: "
            f"{traceback.format_exc()}[/yellow]",
        )
        if logger:
            logger.error(
                "metrics_exporter_failed",
                address=metrics_config.address,
                port=metrics_config.port,
                stacktrace=traceback.format_exc(),
            )
        return

    if started:
        console.print(
            "[green]Prometheus metrics exporter started on "
            f"{metrics_config.address}:{metrics_config.port}[/green]",
        )
        if logger:
            logger.info(
                "metrics_exporter_started",
                address=metrics_config.address,
                port=metrics_config.port,
            )
    elif logger:
        logger.warning(
            "metrics_exporter_already_running",
            address=metrics_config.address,
            port=metrics_config.port,
        )


def _collect_cli_overrides(
    *,
    output: Optional[Path],
    input_path: Optional[Path],
    input_mode: Optional[Literal["csv", "id_only", "auto_detect"]],
    csv_delimiter: Optional[str],
    csv_header: Optional[bool],
) -> dict[str, Any]:
    """Collect CLI overrides into a config overrides mapping."""

    overrides: dict[str, Any] = {}
    if output:
        overrides["output_path"] = str(output)
    if input_path:
        overrides["input_path"] = str(input_path)
    if input_mode:
        overrides["input_mode"] = input_mode

    csv_options: dict[str, Any] = {}
    if csv_delimiter:
        csv_options["delimiter"] = csv_delimiter
    if csv_header is not None:
        csv_options["header"] = csv_header
    if csv_options:
        overrides["csv_options"] = csv_options
    return overrides


def _get_pipeline_factory_name(factory: Any) -> str:
    """Return a human-readable name for a pipeline factory."""

    if hasattr(factory, "__name__"):
        return str(getattr(factory, "__name__"))
    return factory.__class__.__name__


if __name__ == "__main__":  # pragma: no cover - manual invocation
    app()
