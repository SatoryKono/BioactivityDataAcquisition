"""CLI application for BioETL using Typer."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Annotated

from rich.console import Console
import typer

from bioetl.application.bootstrap import ApplicationBootstrap, ApplicationContext
from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.application.pipelines.registry import PIPELINE_REGISTRY
from bioetl.domain.configs import PipelineConfig
from bioetl.infrastructure.config.provider_registry import (
    create_provider_loader,
)
from bioetl.infrastructure.config.sources import get_configs_root
from bioetl.interfaces.bootstrap_factory import create_default_bootstrap
from bioetl.interfaces.container_factory import (
    build_default_container,
)

app = typer.Typer(help="BioETL - Bioactivity Data Acquisition ETL")
console = Console()

_bootstrap: ApplicationBootstrap | None = None


def get_bootstrap() -> ApplicationBootstrap:
    """Get the application bootstrap instance (singleton).

    Returns:
        ApplicationBootstrap: The bootstrap instance.
    """
    global _bootstrap  # noqa: PLW0603
    if _bootstrap is None:
        _bootstrap = create_default_bootstrap()
    return _bootstrap


def get_application_context() -> ApplicationContext:
    """Initialize and return the application context.

    This function must be called before using any application services.
    It's idempotent - subsequent calls return the same context.

    Returns:
        ApplicationContext: The initialized application context.
    """
    return get_bootstrap().start()


def _infer_config_path(pipeline_name: str) -> str | None:
    parts = pipeline_name.split("_")
    if len(parts) >= 2:
        entity, provider = parts[0], parts[1]
        return f"configs/pipelines/{provider}/{entity}.yaml"
    return None


def _resolve_config_path(config: str) -> Path:
    p = Path(config)
    if p.exists():
        return p
    from bioetl.infrastructure.config.sources import get_configs_root

    root = get_configs_root(None)
    candidate = (root / p).resolve()
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Config file not found: {config}")


def _build_config(config_path: Path, profile: str | None) -> PipelineConfig:
    context = get_application_context()
    return build_runtime_config(
        config_path=config_path,
        configs_root=get_configs_root(None),
        loader=context.config_loader,
        profile=profile,
    )


def _apply_output_override(pipeline_config: PipelineConfig, output: str | None) -> None:
    if not output:
        return
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    # Update frozen sink config using model_copy
    new_sink = pipeline_config.sink.model_copy(update={"output_path": str(output_path)})
    object.__setattr__(pipeline_config, "sink", new_sink)
    # Also update storage if it exists
    if hasattr(pipeline_config.runtime, "storage"):
        new_storage = pipeline_config.runtime.storage.model_copy(
            update={"output_path": str(output_path)}
        )
        object.__setattr__(pipeline_config.runtime, "storage", new_storage)


def _create_orchestrator(
    pipeline_name: str, pipeline_config: PipelineConfig
) -> PipelineOrchestrator:
    def _provider_loader_factory() -> object:
        return create_provider_loader()

    return PipelineOrchestrator(
        pipeline_name=pipeline_name,
        config=pipeline_config,
        provider_loader_factory=_provider_loader_factory,
        container_factory=build_default_container,
    )


@app.command()
def list_pipelines() -> None:
    """List all available pipelines."""
    console.print("[bold]Available Pipelines:[/bold]")
    for name in sorted(PIPELINE_REGISTRY.keys()):
        console.print(f"  - {name}")


@app.command()
def validate_config(
    config_path: Annotated[str, typer.Argument(help="Path to pipeline config YAML")],
    profile: Annotated[str | None, typer.Option(help="Profile name")] = None,
) -> None:
    """Validate a pipeline configuration file."""
    config_file = Path(config_path)
    if not config_file.exists():
        console.print(f"[red]Error:[/red] Config file not found: {config_path}")
        raise typer.Exit(1)

    try:
        context = get_application_context()
        build_runtime_config(
            config_path=config_file,
            configs_root=get_configs_root(None),
            loader=context.config_loader,
            profile=profile,
        )
        console.print("[green]✓[/green] Config is valid")
    except Exception as e:
        console.print(f"[red]Config validation failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def run(
    pipeline_name: Annotated[
        str, typer.Argument(help="Pipeline name (e.g., activity_chembl)")
    ],
    config: Annotated[
        str | None, typer.Option("--config", "-c", help="Path to config YAML")
    ] = None,
    output: Annotated[
        str | None, typer.Option("--output", "-o", help="Output directory")
    ] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="Limit number of records")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Dry run mode")] = False,
    profile: Annotated[
        str | None, typer.Option("--profile", "-p", help="Profile name")
    ] = None,
) -> None:
    """Run a pipeline."""
    try:
        inferred = _infer_config_path(pipeline_name) if config is None else config
        if inferred is None:
            console.print("[red]Error:[/red] Cannot infer config path. Use --config.")
            raise typer.Exit(1)
        config_path = _resolve_config_path(inferred)
        pipeline_config = _build_config(config_path, profile)
        _apply_output_override(pipeline_config, output)
        orchestrator = _create_orchestrator(pipeline_name, pipeline_config)

        # Run pipeline
        console.print("Starting pipeline")
        console.print(f"[bold]Running pipeline:[/bold] {pipeline_name}")
        if limit:
            console.print(f"[dim]Limit:[/dim] {limit} records")
        if dry_run:
            console.print("[dim]Mode:[/dim] dry-run")

        result = orchestrator.run_pipeline(
            dry_run=dry_run,
            limit=limit,
        )

        if result.success:
            console.print("[green]✓ Pipeline finished successfully[/green]")
            console.print(f"  Rows: {result.row_count}")
            if result.output_path:
                console.print(f"  Output: {result.output_path}")
        else:
            console.print("[red]✗ Pipeline failed[/red]")
            if result.errors:
                for error in result.errors:
                    console.print(f"  [red]Error:[/red] {error}")
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def smoke_run(
    pipeline_name: Annotated[str, typer.Argument(help="Pipeline name")],
    config: Annotated[
        str | None,
        typer.Option("--config", "-c", help="Config path"),
    ] = None,
) -> None:
    """Quick smoke test with small limit."""
    run(
        pipeline_name=pipeline_name,
        config=config,
        limit=10,
        dry_run=True,
        profile="development",
    )


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
