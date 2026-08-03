# Host attrs/methods provided by concrete composition.
"""Configuration commands for BioETL CLI.

Implements config inspection and validation commands.
Uses ConfigService from composition entrypoints for clean layering.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

import click

from bioetl.domain.types import JsonDict
from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_argument,
    typed_click_group,
    typed_click_option,
    typed_group_command,
)
from bioetl.interfaces.cli.formatters import echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.services.config_service import ConfigService

__all__ = [
    "COMMANDS",
    "config",
    "list_pipelines_command",
    "show_command",
    "show_settings_command",
    "validate_command",
]


def get_config_service() -> ConfigService:
    """Load the config service through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_config_service as _impl,
    )

    return _impl()


def get_configured_pipeline_names() -> list[str]:
    """Load configured pipeline names through the lightweight composition seam."""
    from bioetl.composition.control_plane_service_access import (
        list_configured_pipeline_names as _impl,
    )

    return _impl()


def _config_to_dict(config: object) -> JsonDict:
    """Convert a Pydantic model or dataclass to a JSON-serializable dict.

    Args:
        config: Pydantic model, dataclass, or primitive value to convert.

    Returns:
        JSON-serializable dict representation of the config object.
    """
    if hasattr(config, "model_dump"):
        model_dump = cast(Any, config).model_dump  # Any: pydantic model_dump duck-type
        result: JsonDict = model_dump()
        return result
    if hasattr(config, "__dict__"):
        converted: JsonDict = {  # Any: YAML config has heterogeneous values
            k: _config_to_dict(v) if hasattr(v, "__dict__") else v
            for k, v in config.__dict__.items()
            if not k.startswith("_")
        }
        return converted
    return {"value": config}  # Wrap primitives in a dict


@typed_click_group()
def config() -> None:
    """View and validate configuration."""


@typed_group_command(config, "show")
@typed_click_argument("pipeline")
@typed_click_option(
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

    Args:
        pipeline: Pipeline.
        output_format: Output format.
    """
    service = get_config_service()

    try:
        config_dict = service.get_pipeline_yaml_config(pipeline)
    except ValueError as e:
        echo_error("Configuration error", str(e))
        return
    except FileNotFoundError as e:
        echo_error("Config file not found", str(e))
        return

    if output_format == "json":
        echo_info(json.dumps(config_dict, indent=2, default=str))
    else:
        import yaml

        echo_info(yaml.dump(config_dict, default_flow_style=False, sort_keys=False))


@typed_group_command(config, "validate")
@typed_click_argument("pipeline")
def validate_command(pipeline: str) -> None:
    """Validate configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)

    Examples:

        bioetl config validate chembl_activity

    Args:
        pipeline: Pipeline.
    """
    service = get_config_service()

    try:
        info = service.validate_pipeline_config(pipeline)
        echo_info(f"Configuration valid for {pipeline}")
        echo_info(f"  Provider: {info.provider}")
        echo_info(f"  Entity type: {info.entity_type}")
        echo_info(f"  Silver table: {info.silver_table}")
        if info.gold_table:
            echo_info(f"  Gold table: {info.gold_table}")
    except ValueError as e:
        echo_error("Configuration invalid", str(e))
    except FileNotFoundError as e:
        echo_error("Config file not found", str(e))


@typed_group_command(config, "show-settings")
@typed_click_option(
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

    Args:
        output_format: Output format.
    """
    service = get_config_service()
    settings_info = service.get_settings()

    # Convert SettingsInfo to dict for output
    settings_dict: JsonDict = {  # Any: YAML config has heterogeneous values
        "env": settings_info.env,
        "data_dir": settings_info.data_dir,
        "bronze_path": settings_info.bronze_path,
        "silver_path": settings_info.silver_path,
        "gold_path": settings_info.gold_path,
        "checkpoint_path": settings_info.checkpoint_path,
        "quarantine_path": settings_info.quarantine_path,
        "debug": settings_info.debug,
        "test_mode": settings_info.test_mode,
        "metrics_enabled": settings_info.metrics_enabled,
        "metrics_port": settings_info.metrics_port,
        "batch_size": settings_info.batch_size,
    }

    # Add additional settings (with sensitive values masked)
    for key, value in settings_info.additional.items():
        if "api_key" in key.lower() or "password" in key.lower():
            settings_dict[key] = "***MASKED***"
        else:
            settings_dict[key] = value

    if output_format == "json":
        echo_info(json.dumps(settings_dict, indent=2, default=str))
    else:
        import yaml

        echo_info(yaml.dump(settings_dict, default_flow_style=False, sort_keys=False))


@typed_group_command(config, "list-pipelines")
def list_pipelines_command() -> None:
    """List all configured pipelines.

    Examples:

        bioetl config list-pipelines
    """
    pipelines = get_configured_pipeline_names()

    if not pipelines:
        echo_info("No pipelines configured.")
        return

    echo_info("Available pipelines:")
    for pipeline in sorted(pipelines):
        echo_info(f"  - {pipeline}")


# Explicit command collection to mark usage for tooling.
COMMANDS = (
    list_pipelines_command,
    show_command,
    show_settings_command,
    validate_command,
)
