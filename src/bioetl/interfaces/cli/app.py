import sys
from pathlib import Path
from typing import Literal, Optional

import typer
from rich.console import Console
from rich.table import Table

from bioetl.domain.config_loader import load_pipeline_config, load_pipeline_config_from_path
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.application.container import build_pipeline_dependencies
from bioetl.application.pipelines.registry import PIPELINE_REGISTRY, get_pipeline_class

app = typer.Typer(
    name="bioetl",
    help="Bioactivity Data Acquisition ETL CLI",
    add_completion=False,
)
console = Console()


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
    path = Path("configs/pipelines") / provider / f"{entity}.yaml"
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
):
    """
    Runs an ETL pipeline.
    """
    # Note: Schemas are registered by the container.

    try:
        # 1. Resolve Pipeline Class
        pipeline_cls = get_pipeline_class(pipeline_name)
        
        # 2. Resolve Config
        if config_path is None:
            config_path = _resolve_config_path(pipeline_name)
            if not config_path.exists():
                console.print(f"[red]Config file not found at {config_path}[/red]")
                console.print("Please provide --config explicitly.")
                sys.exit(1)
                
        try:
            entity, provider = pipeline_name.rsplit("_", 1)
        except ValueError:
            entity = pipeline_name
            provider = "chembl"
        pipeline_id = f"{provider}.{entity}"
        config = load_pipeline_config(pipeline_id, profile=profile)

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

        # 3. Instantiate Dependencies using Container
        container = build_pipeline_dependencies(config)
        
        logger = container.get_logger()
        validation_service = container.get_validation_service()
        output_writer = container.get_output_writer()
        extraction_service = container.get_extraction_service()
        hash_service = container.get_hash_service()

        # 4. Run Pipeline
        pipeline = pipeline_cls(
            config=config,
            logger=logger,
            validation_service=validation_service,
            output_writer=output_writer,
            extraction_service=extraction_service,
            hash_service=hash_service
        )
        
        console.print(f"[bold green]Starting pipeline: {pipeline_name}[/bold green]")
        
        # Prepare kwargs for run -> extract
        run_kwargs = {}
        if limit is not None:
            run_kwargs["limit"] = limit
            
        result = pipeline.run(
            output_path=Path(config.output_path),
            dry_run=dry_run,
            **run_kwargs
        )
        
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
