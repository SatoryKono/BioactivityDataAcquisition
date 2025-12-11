"""CLI application for BioETL using Typer."""

from __future__ import annotations

from typing import Annotated, Any

from rich.console import Console
import typer

from bioetl.application.pipelines.registry import PIPELINE_REGISTRY
from bioetl.application.use_cases import InterfaceDisabledError, RunPipelineResponse
from bioetl.interfaces.application_context import get_application_context
from bioetl.interfaces.composition_root import get_composition_root
from bioetl.interfaces.cli.presenter import CliPresenter
from bioetl.interfaces.cli.run_command_helper import RunCommandParams, RunCommandRequestBuilder

app = typer.Typer(help="BioETL - Bioactivity Data Acquisition ETL")
console = Console()
presenter = CliPresenter(console)


@app.command()
def list_pipelines() -> None:
    """List all available pipelines."""
    presenter.show_available_pipelines(sorted(PIPELINE_REGISTRY.keys()))


def build_runtime_config(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN201
    """Build runtime configuration (delegates to application layer)."""
    from bioetl.application.config.runtime import build_runtime_config as _brc

    return _brc(*args, **kwargs)


@app.command()
def validate_config(
    config_path: Annotated[str, typer.Argument(help="Path to pipeline config YAML")],
    profile: Annotated[str | None, typer.Option(help="Profile name")] = None,
) -> None:
    """Validate a pipeline configuration file."""
    builder = RunCommandRequestBuilder(get_composition_root())

    try:
        config_file = builder.resolve_config_path(config_path)
        ctx = get_application_context()
        path_resolver = ctx.composition_root.create_config_path_resolver()
        build_runtime_config(
            config_path=config_file,
            configs_root=path_resolver.configs_root,
            loader=ctx.config_loader,
            profile=profile,
        )
        presenter.show_config_valid()
    except FileNotFoundError as error:
        presenter.show_error(str(error))
        raise typer.Exit(1)
    except ValueError as error:
        presenter.show_error(str(error))
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
    builder = RunCommandRequestBuilder(get_composition_root())

    params = RunCommandParams(
        pipeline_name=pipeline_name,
        config=config,
        output=output,
        limit=limit,
        dry_run=dry_run,
        profile=profile,
    )

    try:
        request = builder.build(params)
        use_case = (
            get_application_context().use_case_factory.create_run_pipeline_use_case()
        )

        presenter.show_start_info(pipeline_name, limit, dry_run)
        response = use_case.execute(request)

        presenter.present_result(response)
        if not response.success:
            raise typer.Exit(1)
    except KeyboardInterrupt:
        presenter.show_interrupt()
        raise typer.Exit(130)
    except (FileNotFoundError, InterfaceDisabledError, ValueError) as error:
        presenter.show_error(str(error))
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
