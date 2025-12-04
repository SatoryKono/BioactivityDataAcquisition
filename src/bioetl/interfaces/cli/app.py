import os
import sys
from pathlib import Path
from typing import Literal, Optional

import typer
from rich.console import Console
from rich.table import Table

from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.config_loader import load_pipeline_config_from_path
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.application.pipelines.registry import PIPELINE_REGISTRY

app = typer.Typer(
    name="bioetl",
    help="Bioactivity Data Acquisition ETL CLI",
    add_completion=False,
)
console = Console()


def _get_config_base_dir() -> Path:
    return Path(os.environ.get("BIOETL_CONFIG_DIR", "configs"))


def _resolve_config_path(pipeline_name: str) -> Path:
    """
    Resolves the default configuration path for a pipeline.
    Assumes pipeline name format: {entity}_{provider}
    """
    try:
        entity, provider = pipeline_name.rsplit("_", 1)
    except ValueError:
        # Fallback if naming doesn't match, assume chembl
        entity = pipeline_name
        provider = "chembl"
    
    # Standard path: configs/pipelines/{provider}/{entity}.yaml
    path = _get_config_base_dir() / "pipelines" / provider / f"{entity}.yaml"
    return path


@app.command()
def list_pipelines():
    """
    Lists available pipelines.
    """
    table = Table(title="Available Pipelines")
    table.add_column("Name", style="cyan")
    table.add_column("Class", style="green")

    for name, cls in PIPELINE_REGISTRY.items():
        table.add_row(name, cls.__name__)

    console.print(table)


@app.command()
def validate_config(config_path: Path):
    """
    Validates a configuration file.
    """
    try:
        config = load_pipeline_config_from_path(config_path)
        console.print(f"[green]Config {config_path} is valid![/green]")
        console.print(f"Entity: {config.entity_name}")
        console.print(f"Provider: {config.provider}")
    except Exception as e:
        console.print(f"[red]Config validation failed:[/red] {e}")
        sys.exit(1)


@app.command()
def run(
    pipeline_name: str,
    profile: str = typer.Option("default", help="Configuration profile"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run without writing output"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to config file"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Limit number of records to process"),
    input_path: Optional[Path] = typer.Option(
        None, "--input-path", help="Path to CSV input file"
    ),
    input_mode: Optional[Literal["csv", "id_only", "auto_detect"]] = typer.Option(
        None,
        "--input-mode",
        help="Record source: csv (full dataset) | id_only (ID list) | auto_detect",
    ),
    csv_delimiter: Optional[str] = typer.Option(
        None, "--csv-delimiter", help="Delimiter for CSV input"
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
):
    """
    Runs an ETL pipeline.
    """
    try:
        base_dir = _get_config_base_dir()

        if config_path is None:
            config_path = _resolve_config_path(pipeline_name)

        config_path = Path(config_path)
        if config_path.is_absolute():
            resolved_config_path = config_path
        elif config_path.exists():
            resolved_config_path = config_path
        else:
            resolved_config_path = base_dir / config_path

        if not resolved_config_path.exists():
            console.print(f"[red]Config file not found at {resolved_config_path}[/red]")
            console.print("Please provide --config explicitly.")
            sys.exit(1)

        config = load_pipeline_config_from_path(
            resolved_config_path,
            profile=profile,
            profiles_root=base_dir / "profiles",
        )

        config_payload = config.model_dump()

        if output:
            config_payload["output_path"] = str(output)

        if input_path:
            config_payload["input_path"] = str(input_path)

        if input_mode:
            config_payload["input_mode"] = input_mode

        csv_options = config_payload.get("csv_options", {})
        if csv_delimiter:
            csv_options["delimiter"] = csv_delimiter
        if csv_header is not None:
            csv_options["header"] = csv_header
        config_payload["csv_options"] = csv_options

        config = PipelineConfig(**config_payload)
        orchestrator = PipelineOrchestrator(
            pipeline_name=pipeline_name,
            config=config,
        )

        console.print(f"[bold green]Starting pipeline: {pipeline_name}[/bold green]")

        if background:
            future = orchestrator.run_in_background(dry_run=dry_run, limit=limit)
            console.print("[yellow]Pipeline submitted to background executor[/yellow]")
            result = future.result()
        else:
            result = orchestrator.run_pipeline(dry_run=dry_run, limit=limit)

        if result.success:
            console.print(f"[bold green]Pipeline finished successfully![/bold green]")
            console.print(f"Rows processed: {result.row_count}")
            console.print(f"Duration: {result.duration_sec:.2f}s")
        else:
            console.print(f"[bold red]Pipeline failed![/bold red]")
            sys.exit(1)

    except Exception as e:
        console.print_exception()
        sys.exit(1)


@app.command()
def smoke_run(pipeline_name: str):
    """
    Runs a smoke test (development profile, dry-run).
    """
    run(pipeline_name, profile="development", dry_run=True, limit=10)


if __name__ == "__main__":
    app()
