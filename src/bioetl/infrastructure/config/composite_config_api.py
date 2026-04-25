"""Canonical composite-config loading flow owned by infrastructure/config."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, cast

import yaml
from pydantic import ValidationError

from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config._composite_dq_externalization import (
    merge_external_dq_overrides,
)
from bioetl.infrastructure.config._composite_gold_schema_registry import (
    DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
)
from bioetl.infrastructure.schemas.composite_config import (
    validate_composite_config_payload,
)

__all__ = [
    "DEFAULT_COMPOSITE_CONFIG_DIR",
    "DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY",
    "load_composite_config",
    "resolve_composite_config_path",
    "resolve_composite_gold_schema",
]


class _CompositeSchema(Protocol):
    """Protocol for validated composite schema payloads."""

    def to_domain(self) -> CompositeConfig:
        """Convert validated schema payload into immutable domain config."""
        ...


ConfigPayloadValidator = Callable[[JsonDict], _CompositeSchema]
DQOverrideMerger = Callable[[dict[str, object], Path], None]

DEFAULT_COMPOSITE_CONFIG_DIR = Path("configs/composites")


def resolve_composite_gold_schema(
    composite_name: str,
    *,
    schema_registry: Mapping[str, type] | None = None,
) -> type | None:
    """Resolve composite Gold contract by composite pipeline name."""
    registry = schema_registry or DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY
    key = composite_name.removeprefix("composite_")
    return registry.get(key)


def resolve_composite_config_path(name: str, *, config_dir: Path) -> Path:
    """Resolve composite config path from canonical composites directory."""
    config_path = config_dir / f"{name}.yaml"
    if config_path.exists():
        return config_path
    raise FileNotFoundError(f"Composite config not found: {config_path}")


def load_composite_config(
    name: str,
    *,
    config_dir: Path = DEFAULT_COMPOSITE_CONFIG_DIR,
    validate_payload: ConfigPayloadValidator = validate_composite_config_payload,
    dq_override_merger: DQOverrideMerger = merge_external_dq_overrides,
) -> CompositeConfig:
    """Load, merge, and validate composite pipeline configuration from YAML."""
    config_path = resolve_composite_config_path(name, config_dir=config_dir)

    with config_path.open(encoding="utf-8") as config_file:
        raw_payload = yaml.safe_load(config_file)

    if not isinstance(raw_payload, dict):
        raise ValueError(
            f"Invalid composite config '{name}': expected top-level mapping in YAML"
        )

    mutable_payload = cast(JsonDict, raw_payload)
    dq_override_merger(mutable_payload, config_path)

    try:
        schema = validate_payload(mutable_payload)
        return schema.to_domain()
    except (ValidationError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid composite config '{name}': {error}") from error
