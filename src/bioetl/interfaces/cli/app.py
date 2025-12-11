"""CLI application for BioETL using Typer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from rich.console import Console
import typer

from bioetl.application.pipelines.registry import PIPELINE_REGISTRY
from bioetl.application.use_cases import RunPipelineRequest, RunPipelineResponse
from bioetl.interfaces.use_case_factory import get_use_case_factory
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.infrastructure.config.provider_registry import create_provider_loader

app = typer.Typer(help="BioETL - Bioactivity Data Acquisition ETL")
console = Console()


def _present_result(response: RunPipelineResponse) -> None:
    """Format and display pipeline result."""
    if response.success:
        console.print("[green]Pipeline finished successfully[/green]")
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


def build_runtime_config(*args, **kwargs):
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
        resolved = None
        if config is not None:
            try:
                resolved = _resolve_config_path(config)
            except FileNotFoundError as e:
                console.print(f"[red]{e}[/red]")
                raise typer.Exit(1)

        cfg = build_runtime_config(
            config_path=resolved if resolved else None,
            configs_root=None,
            loader=get_use_case_factory()._ensure_context().config_loader,  # reuse context
            profile=profile or "default",
        )

        orchestrator = PipelineOrchestrator(pipeline_name, cfg)
        response = orchestrator.run_pipeline(
            dry_run=dry_run,
            limit=limit,
        )

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
        profile="development",
    )


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
