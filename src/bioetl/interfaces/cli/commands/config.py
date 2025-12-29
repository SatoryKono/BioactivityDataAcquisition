"""Configuration commands for BioETL CLI.

Implements config inspection and validation commands.
"""

from __future__ import annotations

import json
from typing import Any

import click

from bioetl.composition.registry import get_default_registry
from bioetl.infrastructure.config import get_settings, load_pipeline_config
from bioetl.interfaces.cli.formatters import echo_error, echo_info


def _config_to_dict(config: Any) -> dict[str, Any]:
    """Convert a Pydantic model or dataclass to a JSON-serializable dict."""
    if hasattr(config, "model_dump"):
        result: dict[str, Any] = config.model_dump()
        return result
    if hasattr(config, "__dict__"):
        converted: dict[str, Any] = {
            k: _config_to_dict(v) if hasattr(v, "__dict__") else v
            for k, v in config.__dict__.items()
            if not k.startswith("_")
        }
        return converted
    return {"value": config}  # Wrap primitives in a dict


@click.group()
def config() -> None:
    """View and validate configuration."""
    pass


@config.command("show")
@click.argument("pipeline")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
def show_command(pipeline: str, output_format: str) -> None:
    """Show configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)

    Examples:

        bioetl config show chembl_activity

        bioetl config show chembl_activity --format json
    """
    try:
        yaml_config = load_pipeline_config(pipeline)
    except ValueError as e:
        echo_error("Configuration error", str(e))
        return
    except FileNotFoundError as e:
        echo_error("Config file not found", str(e))
        return

    config_dict = _config_to_dict(yaml_config)

    if output_format == "json":
        echo_info(json.dumps(config_dict, indent=2, default=str))
    else:
        import yaml
        echo_info(yaml.dump(config_dict, default_flow_style=False, sort_keys=False))


@config.command("validate")
@click.argument("pipeline")
def validate_command(pipeline: str) -> None:
    """Validate configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)

    Examples:

        bioetl config validate chembl_activity
    """
    try:
        yaml_config = load_pipeline_config(pipeline)
        echo_info(f"Configuration valid for {pipeline}")
        echo_info(f"  Provider: {yaml_config.provider}")
        echo_info(f"  Entity type: {yaml_config.entity_type}")
        echo_info(f"  Silver table: {yaml_config.silver_table}")
        if yaml_config.gold_table:
            echo_info(f"  Gold table: {yaml_config.gold_table}")
    except ValueError as e:
        echo_error("Configuration invalid", str(e))
    except FileNotFoundError as e:
        echo_error("Config file not found", str(e))


@config.command("show-settings")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
def show_settings_command(output_format: str) -> None:
    """Show global application settings.

    Displays environment-based configuration from BIOETL_* variables.

    Examples:

        bioetl config show-settings

        bioetl config show-settings --format json
    """
    settings = get_settings()
    settings_dict = settings.model_dump()

    # Mask sensitive values
    if settings_dict.get("pubmed_api_key"):
        settings_dict["pubmed_api_key"] = "***MASKED***"

    if output_format == "json":
        echo_info(json.dumps(settings_dict, indent=2, default=str))
    else:
        import yaml
        echo_info(yaml.dump(settings_dict, default_flow_style=False, sort_keys=False))


@config.command("list-pipelines")
def list_pipelines_command() -> None:
    """List all registered pipelines.

    Examples:

        bioetl config list-pipelines
    """
    from bioetl.composition.factories.pipeline_factories import register_all_pipelines

    register_all_pipelines()
    registry = get_default_registry()
    pipelines = registry.list_pipelines()

    if not pipelines:
        echo_info("No pipelines registered.")
        return

    echo_info("Available pipelines:")
    for pipeline in sorted(pipelines):
        echo_info(f"  - {pipeline}")
