"""Data Quality configuration commands for BioETL CLI.

Implements DQ config inspection and validation commands.
Uses ConfigService from composition entrypoints for clean layering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, cast

import click
import yaml

from bioetl.domain.types import JsonDict
from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_argument,
    typed_click_group,
    typed_click_option,
    typed_group_command,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.services.ops.config_service import ConfigService

__all__ = [
    "COMMANDS",
    "check_compatibility_command",
    "dq",
    "show_dq_config_command",
    "show_effective_config_command",
    "validate_dq_config_command",
]


def get_config_service() -> ConfigService:
    """Load the config service through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_config_service as _impl,
    )

    return cast("ConfigService", _impl())


def _fail_dq(
    title: str, detail: str, exit_code: ExitCode = ExitCode.CONFIG_ERROR
) -> NoReturn:
    """Emit a DQ CLI error and exit non-zero (do not return success)."""
    echo_error(title, detail)
    raise SystemExit(int(exit_code))


@typed_click_group()
def dq() -> None:
    """Data Quality configuration commands."""


@typed_group_command(dq, "show")
@typed_click_argument("pipeline")
@typed_click_option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
def show_dq_config_command(pipeline: str, output_format: str) -> None:
    """Show Data Quality configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)

    Examples:

        bioetl dq show chembl_activity

        bioetl dq show chembl_activity --format json

    Args:
        pipeline: Pipeline.
        output_format: Output format.
    """
    service = get_config_service()

    try:
        dq_config = service.get_dq_config(pipeline)
    except ValueError as e:
        _fail_dq("DQ Configuration error", str(e))
    except FileNotFoundError as e:
        _fail_dq("DQ Config file not found", str(e), ExitCode.EX_NOINPUT)

    if output_format == "json":
        echo_info(json.dumps(dq_config, indent=2, default=str))
    else:
        echo_info(yaml.dump(dq_config, default_flow_style=False, sort_keys=False))


@typed_group_command(dq, "validate")
@typed_click_argument("pipeline")
@typed_click_option(
    "--config-file",
    type=click.Path(exists=True),
    help="Path to DQ config file to validate",
)
def validate_dq_config_command(pipeline: str, config_file: str | None) -> None:
    """Validate Data Quality configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)
    CONFIG_FILE: Optional path to DQ config file to validate

    Examples:

        bioetl dq validate chembl_activity

        bioetl dq validate chembl_activity --config-file custom_dq_config.yaml

    Args:
        pipeline: Pipeline.
        config_file: Optional path to DQ config file.
    """
    service = get_config_service()

    try:
        if config_file:
            with Path(config_file).open(encoding="utf-8") as file_obj:
                loaded = yaml.safe_load(file_obj)
            if not isinstance(loaded, dict):
                _fail_dq(
                    "DQ Configuration invalid",
                    "Config file must contain a mapping at the top level.",
                )
            is_valid = service.validate_dq_config(pipeline, loaded)
            if is_valid:
                echo_info(f"[OK] DQ configuration is valid for {pipeline}")
                return
            _fail_dq(f"[ERROR] DQ configuration is invalid for {pipeline}", "")

        dq_config = service.get_dq_config(pipeline)
        echo_info(f"[OK] DQ configuration is valid for {pipeline}")
        echo_info(f"  Contract Ref: {dq_config.get('contract_ref', 'N/A')}")
        echo_info(f"  Contract Version: {dq_config.get('contract_version', 'N/A')}")
        echo_info(f"  Rule Bundle: {dq_config.get('rule_bundle_version', 'N/A')}")
        echo_info(
            "  Default Disposition: "
            f"{dq_config.get('default_disposition_policy', 'N/A')}"
        )
        echo_info(f"  Strictness Mode: {dq_config.get('strictness_mode', 'N/A')}")
    except ValueError as e:
        _fail_dq("DQ Configuration invalid", str(e))
    except FileNotFoundError as e:
        _fail_dq("DQ Config file not found", str(e), ExitCode.EX_NOINPUT)
    except (OSError, TypeError, yaml.YAMLError) as e:
        _fail_dq("DQ Configuration validation failed", str(e), ExitCode.FAIL)


@typed_group_command(dq, "show-effective")
@typed_click_argument("pipeline")
@typed_click_option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
@typed_click_option(
    "--override",
    "overrides",
    multiple=True,
    help="Runtime override in format key=value",
)
def show_effective_config_command(
    pipeline: str, output_format: str, overrides: tuple[str, ...]
) -> None:
    """Show effective configuration artifact for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)
    OVERRIDES: Optional runtime overrides

    Examples:

        bioetl dq show-effective chembl_activity

        bioetl dq show-effective chembl_activity --override batch_size=100

        bioetl dq show-effective chembl_activity --format json

    Args:
        pipeline: Pipeline.
        output_format: Output format.
        overrides: Runtime overrides.
    """
    service = get_config_service()

    try:
        runtime_overrides: JsonDict = {}
        for override in overrides:
            if "=" not in override:
                continue
            key, value = override.split("=", 1)
            runtime_overrides[key] = value

        artifact = service.get_effective_config_artifact(pipeline, runtime_overrides)

        if output_format == "json":
            echo_info(json.dumps(artifact, indent=2, default=str))
        else:
            echo_info(yaml.dump(artifact, default_flow_style=False, sort_keys=False))

    except ValueError as e:
        _fail_dq("Effective config error", str(e))
    except FileNotFoundError as e:
        _fail_dq("Config file not found", str(e), ExitCode.EX_NOINPUT)
    except TypeError as e:
        _fail_dq("Failed to create effective config artifact", str(e), ExitCode.FAIL)


@typed_group_command(dq, "check-compatibility")
@typed_click_argument("artifact1_file")
@typed_click_argument("artifact2_file")
def check_compatibility_command(artifact1_file: str, artifact2_file: str) -> None:
    """Check compatibility between two configuration artifacts.

    ARTIFACT1_FILE: Path to first artifact file
    ARTIFACT2_FILE: Path to second artifact file

    Examples:

        bioetl dq check-compatibility artifact1.json artifact2.json

    Args:
        artifact1_file: Path to first artifact file.
        artifact2_file: Path to second artifact file.
    """
    service = get_config_service()

    try:
        with Path(artifact1_file).open(encoding="utf-8") as file_one:
            artifact1 = json.load(file_one)
        with Path(artifact2_file).open(encoding="utf-8") as file_two:
            artifact2 = json.load(file_two)
        if not isinstance(artifact1, dict) or not isinstance(artifact2, dict):
            _fail_dq("Compatibility check failed", "Artifacts must be JSON objects")

        is_compatible = service.check_config_compatibility(artifact1, artifact2)

        if is_compatible:
            dq_compatible = artifact1.get(
                "dq_contract_compatibility_hash", "N/A"
            ) == artifact2.get("dq_contract_compatibility_hash", "N/A")
            effective_hash_compatible = artifact1.get(
                "effective_config_hash", "N/A"
            ) == artifact2.get("effective_config_hash", "N/A")
            echo_info("[OK] Configurations are compatible")
            echo_info(f"  Artifact 1: {artifact1.get('artifact_id', 'unknown')}")
            echo_info(f"  Artifact 2: {artifact2.get('artifact_id', 'unknown')}")
            echo_info(f"  DQ Compatible: {dq_compatible}")
            echo_info(f"  Effective Config Hash: {effective_hash_compatible}")
        else:
            echo_error("[ERROR] Configurations are NOT compatible")
            echo_error(f"  Artifact 1: {artifact1.get('artifact_id', 'unknown')}")
            echo_error(f"  Artifact 2: {artifact2.get('artifact_id', 'unknown')}")
            echo_error("  Check DQ contract compatibility and effective config hashes")
            raise SystemExit(int(ExitCode.FAIL))

    except FileNotFoundError as e:
        _fail_dq("Artifact file not found", str(e), ExitCode.EX_NOINPUT)
    except json.JSONDecodeError as e:
        _fail_dq("Invalid JSON in artifact file", str(e), ExitCode.EX_DATAERR)
    except (OSError, ValueError, TypeError) as e:
        _fail_dq("Compatibility check failed", str(e), ExitCode.FAIL)


# Explicit command collection to mark usage for tooling.
COMMANDS = (
    show_dq_config_command,
    validate_dq_config_command,
    show_effective_config_command,
    check_compatibility_command,
)
