"""CLI application for BioETL using Typer."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Annotated

from rich.console import Console
import typer

from bioetl.application.bootstrap import ApplicationBootstrap
from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.pipelines.registry import PIPELINE_REGISTRY
from bioetl.application.use_cases import (
    RunPipelineRequest,
    RunPipelineUseCase,
)
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


def _infer_config_path(pipeline_name: str) -> str | None:
    """Infer config path from pipeline name.

    Args:
        pipeline_name: Pipeline name in format entity_provider.

    Returns:
        Inferred config path or None if cannot infer.
    """
    parts = pipeline_name.split("_")
    if len(parts) >= 2:
        entity, provider = parts[0], parts[1]
        return f"configs/pipelines/{provider}/{entity}.yaml"
    return None


def _resolve_config_path(config: str) -> Path:
    """Resolve config path to absolute path.

    Args:
        config: Config path (relative or absolute).

    Returns:
        Resolved absolute path.

    Raises:
        FileNotFoundError: If config file not found.
    """
    p = Path(config)
    if p.exists():
        return p
    root = get_configs_root(None)
    candidate = (root / p).resolve()
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Config file not found: {config}")


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
        bootstrap = get_bootstrap()
        context = bootstrap.start()
        if context.config_loader is None:
            console.print("[red]Error:[/red] Config loader not available")
            raise typer.Exit(1)
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
        # Resolve config path if provided
        config_path: Path | None = None
        if config is not None:
            config_path = _resolve_config_path(config)
        else:
            # Try to infer config path from pipeline name
            inferred = _infer_config_path(pipeline_name)
            if inferred is not None:
                try:
                    config_path = _resolve_config_path(inferred)
                except FileNotFoundError:
                    # If inferred path doesn't exist, let use case use get_by_id
                    pass

        # Get application context
        bootstrap = get_bootstrap()
        context = bootstrap.start()

        if context.config_loader is None:
            console.print("[red]Error:[/red] Config loader not available")
            raise typer.Exit(1)

        # Create use case
        use_case = RunPipelineUseCase(
            config_loader=context.config_loader,
            container_factory=build_default_container,
            provider_loader_factory=create_provider_loader,
            configs_root=get_configs_root(None),
        )

        # Build request
        request = RunPipelineRequest(
            pipeline_name=pipeline_name,
            profile=profile or "default",
            dry_run=dry_run,
            limit=limit,
            config_path=config_path,
            output_path=Path(output) if output else None,
        )

        # Run pipeline with progress output
        console.print("Starting pipeline")
        console.print(f"[bold]Running pipeline:[/bold] {pipeline_name}")
        if limit:
            console.print(f"[dim]Limit:[/dim] {limit} records")
        if dry_run:
            console.print("[dim]Mode:[/dim] dry-run")

        response = use_case.execute(request)

        # Present result
        if response.success:
            console.print("[green]✓ Pipeline finished successfully[/green]")
            console.print(f"  Rows: {response.row_count}")
            if response.output_path:
                console.print(f"  Output: {response.output_path}")
        else:
            console.print("[red]✗ Pipeline failed[/red]")
            for error in response.errors:
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
