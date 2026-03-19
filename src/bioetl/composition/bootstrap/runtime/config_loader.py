"""Composite runtime configuration loading helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, cast

import yaml
from pydantic import ValidationError

from bioetl.composition.bootstrap.runtime.composite_dq_loader import (
    merge_external_dq_overrides,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.contracts import (
    CompositeActivityGoldSchema,
    CompositeAssayGoldSchema,
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
    CompositeTargetGoldSchema,
)
from bioetl.domain.types import JsonDict
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

DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY: dict[str, type] = {
    "activity": CompositeActivityGoldSchema,
    "assay": CompositeAssayGoldSchema,
    "molecule": CompositeMoleculeGoldSchema,
    "publication": CompositePublicationGoldSchema,
    "target": CompositeTargetGoldSchema,
}


def resolve_composite_gold_schema(
    composite_name: str,
    *,
    schema_registry: Mapping[str, type] | None = None,
) -> type | None:
    """Resolve composite Gold contract by composite pipeline name.

    Strips the 'composite_' prefix from the name before looking up in the
    registry, so both 'publication' and 'composite_publication' resolve to
    the same schema.

    Args:
        composite_name: Composite pipeline name (e.g., 'composite_publication'
            or 'publication').
        schema_registry: Optional mapping of entity name to Pandera
            DataFrameModel class; uses the default registry when None.

    Returns:
        Pandera DataFrameModel class for the composite pipeline, or None if not registered.
    """
    registry = schema_registry or DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY
    key = composite_name.removeprefix("composite_")
    return registry.get(key)


def resolve_composite_config_path(name: str, *, config_dir: Path) -> Path:
    """Resolve composite config path from canonical composites directory.

    Args:
        name: Composite pipeline name (e.g., 'composite_publication').
        config_dir: Directory to search for composite YAML files.

    Returns:
        Path to the composite YAML configuration file.

    Raises:
        FileNotFoundError: If no YAML file for the given name exists in config_dir.
    """
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
    """Load and validate composite pipeline configuration from YAML.

    Reads the YAML file, applies external DQ override merging, injects
    column groups from an external file when configured, then validates and
    converts the payload to a domain CompositeConfig object.

    Args:
        name: Composite pipeline name (e.g., 'composite_publication').
        config_dir: Directory containing composite YAML config files.
        validate_payload: Callable to validate and parse the raw YAML payload.
        dq_override_merger: Callable to merge external DQ config into the
            inline dq_overrides section.

    Returns:
        Validated and parsed CompositeConfig domain object.

    Raises:
        FileNotFoundError: If the YAML config file does not exist.
        ValueError: If the YAML payload fails schema validation or is not a mapping.
    """
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
    except ValidationError as error:
        raise ValueError(f"Invalid composite config '{name}': {error}") from error
