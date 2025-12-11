"""CLI application for BioETL using Typer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Any

from rich.console import Console
import typer

from bioetl.application.pipelines.registry import PIPELINE_REGISTRY
from bioetl.application.use_cases import RunPipelineRequest, RunPipelineResponse
from bioetl.interfaces.use_case_factory import get_use_case_factory

app = typer.Typer(help="BioETL - Bioactivity Data Acquisition ETL")
console = Console()


def _print_start_info(pipeline_name: str, limit: int | None, dry_run: bool) -> None:
    """Print pipeline start information."""
    console.print(f"[bold]Running pipeline:[/bold] {pipeline_name}")
    if limit:
        console.print(f"[dim]Limit:[/dim] {limit} records")
    if dry_run:
        console.print("[dim]Mode:[/dim] dry-run")


def _present_result(response: RunPipelineResponse) -> None:
    """Format and display pipeline result."""
    if response.success:
        console.print("[green]✓ Pipeline finished successfully[/green]")
        console.print(f"  Rows: {response.row_count}")
        if response.output_path:
            console.print(f"  Output: {response.output_path}")
    else:
        console.print("[red]✗ Pipeline failed[/red]")
        for error in response.errors:
            console.print(f"  [red]Error:[/red] {error}")


@app.command()
def list_pipelines() -> None:
    """List all available pipelines."""
    console.print("[bold]Available Pipelines:[/bold]")
    for name in sorted(PIPELINE_REGISTRY.keys()):
        console.print(f"  - {name}")


def build_runtime_config(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN201
    """Build runtime configuration (delegates to application layer)."""
    from bioetl.application.config.runtime import build_runtime_config as _brc
    return _brc(*args, **kwargs)


def _resolve_config_path(config: str | None) -> Path:
    if not config:
        raise FileNotFoundError("Config file not found: none provided")
    p = Path(config)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {config}")
    return p


@app.command()
def validate_config(
    config_path: Annotated[str, typer.Argument(help="Path to pipeline config YAML")],
    profile: Annotated[str | None, typer.Option(help="Profile name")] = None,
) -> None:
    """Validate a pipeline configuration file."""
    from bioetl.infrastructure.config.sources import get_configs_root
    from bioetl.interfaces.application_context import get_application_context

    config_file = Path(config_path)
    if not config_file.exists():
        console.print(f"[red]Error:[/red] Config file not found: {config_path}")
        raise typer.Exit(1)

    try:
        ctx = get_application_context()
        build_runtime_config(
            config_path=config_file,
            configs_root=get_configs_root(None),
            loader=ctx.config_loader,
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
        # 1. Build request from CLI args
        request = RunPipelineRequest(
            pipeline_name=pipeline_name,
            config_path=Path(config) if config else None,
            output_path=Path(output) if output else None,
            limit=limit,
            dry_run=dry_run,
            profile=profile or "default",
        )

        # 2. Get use case via factory
        use_case = get_use_case_factory().create_run_pipeline_use_case()

        # 3. Execute
        _print_start_info(pipeline_name, limit, dry_run)
        response = use_case.execute(request)

        # 4. Present result
        _present_result(response)
        if not response.success:
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
