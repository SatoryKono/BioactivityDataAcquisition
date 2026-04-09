"""Canonical function-based workflow config loading flow."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml
from pydantic import ValidationError

from bioetl.domain.types import JsonDict
from bioetl.domain.workflow import WorkflowConfig
from bioetl.infrastructure.schemas.workflow_config import (
    WorkflowConfigFileSchema,
    validate_workflow_config_payload,
)

__all__ = [
    "DEFAULT_WORKFLOW_CONFIG_DIR",
    "load_workflow_config",
    "resolve_workflow_config_path",
]

DEFAULT_WORKFLOW_CONFIG_DIR = Path("configs/workflows")

ConfigPayloadValidator = Callable[[JsonDict], WorkflowConfigFileSchema]


def resolve_workflow_config_path(name: str, *, config_dir: Path) -> Path:
    """Resolve workflow YAML path from the canonical workflow config directory."""
    config_path = config_dir / f"{name}.yaml"
    if config_path.exists():
        return config_path
    raise FileNotFoundError(f"Workflow config not found: {config_path}")


def load_workflow_config(
    name: str,
    *,
    config_dir: Path = DEFAULT_WORKFLOW_CONFIG_DIR,
    validate_payload: ConfigPayloadValidator = validate_workflow_config_payload,
) -> WorkflowConfig:
    """Load, validate, and map workflow configuration from YAML."""
    config_path = resolve_workflow_config_path(name, config_dir=config_dir)

    with config_path.open(encoding="utf-8") as config_file:
        raw_payload = yaml.safe_load(config_file)

    if not isinstance(raw_payload, dict):
        raise ValueError(
            f"Invalid workflow config '{name}': expected top-level mapping in YAML"
        )

    try:
        schema = validate_payload(raw_payload)
    except ValidationError as error:
        raise ValueError(f"Invalid workflow config '{name}': {error}") from error
    return schema.to_domain()
