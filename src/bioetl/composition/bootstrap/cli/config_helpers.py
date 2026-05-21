"""Helper owners for CLI config bootstrap data adapters."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from bioetl.domain.types import JsonDict

__all__ = ["get_pipeline_yaml_for_dq"]


def get_pipeline_yaml_for_dq(
    pipeline_name: str,
    *,
    pipeline_config_loader: Callable[[str], object],
) -> JsonDict:
    """Return pipeline config as mapping data for DQ config services."""
    config = pipeline_config_loader(pipeline_name)
    if hasattr(config, "model_dump"):
        return config.model_dump()
    if isinstance(config, Mapping):
        return dict(config)
    raise TypeError("Pipeline YAML config must provide model_dump() or be a mapping")
