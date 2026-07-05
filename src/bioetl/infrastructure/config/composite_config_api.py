"""Canonical composite-config loading flow owned by infrastructure/config."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

import yaml
from pydantic import ValidationError

from bioetl.domain.composite import CompositeConfig
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config._composite_config_paths import (
    DEFAULT_COMPOSITE_CONFIG_DIR,
    list_composite_config_names,
    resolve_composite_config_dir,
    resolve_composite_config_path,
)
from bioetl.infrastructure.config._composite_dq_externalization import (
    merge_external_dq_overrides,
)
from bioetl.infrastructure.config._composite_gold_schema_registry import (
    DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
)
from bioetl.infrastructure.config._composite_shared_policy_externalization import (
    merge_external_shared_policy,
)
from bioetl.infrastructure.schemas.composite_config import (
    validate_composite_config_payload,
)

__all__ = [
    "DEFAULT_COMPOSITE_CONFIG_DIR",
    "DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY",
    "list_composite_config_names",
    "load_composite_config",
    "resolve_composite_config_dir",
    "resolve_composite_config_path",
    "resolve_composite_gold_schema",
]

ConfigPayloadValidator = Callable[[JsonDict], object]
DQOverrideMerger = Callable[[dict[str, object], Path], None]
SharedPolicyMerger = Callable[[dict[str, object], Path], None]


def resolve_composite_gold_schema(
    composite_name: str,
    *,
    schema_registry: Mapping[str, type] | None = None,
) -> type | None:
    """Resolve composite Gold contract by composite pipeline name."""
    registry = schema_registry or DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY
    key = composite_name.removeprefix("composite_")
    return registry.get(key)


def load_composite_config(
    name: str,
    *,
    config_dir: Path | None = None,
    configs_root: Path | None = None,
    validate_payload: ConfigPayloadValidator = validate_composite_config_payload,
    dq_override_merger: DQOverrideMerger = merge_external_dq_overrides,
    shared_policy_merger: SharedPolicyMerger = merge_external_shared_policy,
) -> CompositeConfig:
    """Load, merge, and validate composite pipeline configuration from YAML."""
    config_path = resolve_composite_config_path(
        name,
        config_dir=config_dir,
        configs_root=configs_root,
    )

    with config_path.open(encoding="utf-8") as config_file:
        raw_payload = yaml.safe_load(config_file)

    if not isinstance(raw_payload, dict):
        raise ValueError(
            f"Invalid composite config '{name}': expected top-level mapping in YAML"
        )

    mutable_payload = cast(JsonDict, raw_payload)
    shared_policy_merger(mutable_payload, config_path)
    dq_override_merger(mutable_payload, config_path)

    try:
        schema = validate_payload(mutable_payload)
        return schema.to_domain()
    except (ValidationError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid composite config '{name}': {error}") from error
