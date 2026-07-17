"""Helper owners for CLI config bootstrap data adapters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable

from bioetl.domain.types import JsonDict

__all__ = ["get_pipeline_yaml_for_dq"]


@runtime_checkable
class _ModelDumpConfig(Protocol):
    def model_dump(self) -> JsonDict: ...


def get_pipeline_yaml_for_dq(
    pipeline_name: str,
    *,
    pipeline_config_loader: Callable[[str], object],
) -> JsonDict:
    """Return pipeline config as mapping data for DQ config services."""
    config = pipeline_config_loader(pipeline_name)
    if isinstance(config, _ModelDumpConfig):
        return config.model_dump()
    if isinstance(config, Mapping):
        return {str(key): value for key, value in config.items()}
    raise TypeError("Pipeline YAML config must provide model_dump() or be a mapping")
