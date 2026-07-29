"""Shared canonical fact loaders for passport and diagram projections."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)

JsonObject = dict[str, Any]


def load_effective_pipeline_facts(
    pipeline_name: str,
    *,
    configs_root: Path,
) -> JsonObject:
    """Load effective config through the supported runtime config loader."""
    config = load_pipeline_config_from_root(pipeline_name, configs_root=configs_root)
    return cast(JsonObject, _json_compatible(config.model_dump(mode="json")))


def _json_compatible(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _json_compatible(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value
