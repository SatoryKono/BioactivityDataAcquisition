"""CLI application for BioETL using Typer."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Annotated, Any

from rich.console import Console
import typer

from bioetl.application.pipelines.registry import list_pipelines as list_registered_pipelines
from bioetl.application.use_cases import RunPipelineRequest, RunPipelineResponse
from bioetl.interfaces.application_context import get_application_context
from bioetl.interfaces.composition_root import get_composition_root

app = typer.Typer(help="BioETL - Bioactivity Data Acquisition ETL")
console = Console()


def _print_start_info(pipeline_name: str, limit: int | None, dry_run: bool) -> None:
    """Print pipeline start information."""
    console.print(f"[bold]Starting pipeline:[/bold] {pipeline_name}")
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
    for name in list_registered_pipelines():
        console.print(f"  - {name}")


def build_runtime_config(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN201
    """Build runtime configuration (delegates to application layer)."""
    from bioetl.application.config.runtime import build_runtime_config as _brc

    return _brc(*args, **kwargs)


def _resolve_config_path(config: str | None) -> Path | None:
    """Resolve config path using provided value or BIOETL_CONFIG_DIR."""

    if not config:
        return None

    provided_path = Path(config)
    if provided_path.exists():
        return provided_path

    path_resolver = get_composition_root().create_config_path_resolver()
    configs_root = path_resolver.configs_root
    candidate = configs_root / config
    if candidate.exists():
        return candidate

    raise FileNotFoundError(
        f"Config file not found: {config}; tried {provided_path} and {candidate}"
    )


@app.command()
def validate_config(
    config_path: Annotated[str, typer.Argument(help="Path to pipeline config YAML")],
    profile: Annotated[str | None, typer.Option(help="Profile name")] = None,
) -> None:
    """Validate a pipeline configuration file."""
    from bioetl.interfaces.application_context import get_application_context

    try:
        config_file = _resolve_config_path(config_path)
        if config_file is None or not config_file.exists():
            console.print(f"[red]Error:[/red] Config file not found: {config_path}")
            raise typer.Exit(1)

        ctx = get_application_context()
        path_resolver = ctx.composition_root.create_config_path_resolver()
        build_runtime_config(
            config_path=config_file,
            configs_root=path_resolver.configs_root,
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
            config_path=_resolve_config_path(config),
            output_path=Path(output) if output else None,
            limit=limit,
            dry_run=dry_run,
            profile=profile or "default",
        )

        # 2. Get use case via factory
        use_case = (
            get_application_context().use_case_factory.create_run_pipeline_use_case()
        )

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
