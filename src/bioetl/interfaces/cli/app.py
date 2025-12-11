"""CLI application for BioETL using Typer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from rich.console import Console
import typer

from bioetl.application.pipelines.registry import PIPELINE_REGISTRY
from bioetl.application.use_cases import RunPipelineRequest, RunPipelineResponse
from bioetl.interfaces.use_case_factory import get_use_case_factory

app = typer.Typer(help="BioETL - Bioactivity Data Acquisition ETL")
console = Console()


def _present_result(response: RunPipelineResponse) -> None:
    """Format and display pipeline result."""
    if response.success:
        console.print("[green]✓ Pipeline completed[/green]")
        console.print(f"  Rows: {response.row_count}")
        if response.output_path:
            console.print(f"  Output: {response.output_path}")
    else:
        console.print("[red]✗ Pipeline failed[/red]")
        for err in response.errors:
            console.print(f"  {err}")


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
    from bioetl.application.config.runtime import build_runtime_config
    from bioetl.infrastructure.config.sources import get_configs_root
    from bioetl.interfaces.application_context import get_application_context

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
    pipeline_name: Annotated[str, typer.Argument(help="Pipeline name")],
    config: Annotated[str | None, typer.Option("--config", "-c")] = None,
    output: Annotated[str | None, typer.Option("--output", "-o")] = None,
    limit: Annotated[int | None, typer.Option("--limit", "-l")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
) -> None:
    """Run a pipeline."""
    try:
        request = RunPipelineRequest(
            pipeline_name=pipeline_name,
            config_path=Path(config) if config else None,
            output_path=Path(output) if output else None,
            limit=limit,
            dry_run=dry_run,
            profile=profile or "default",
        )

        use_case = get_use_case_factory().create_run_pipeline_use_case()
        response = use_case.execute(request)

        _present_result(response)
        if not response.success:
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
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
    )


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
