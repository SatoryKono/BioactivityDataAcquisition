"""Helper owners for CLI config bootstrap data adapters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol, cast, runtime_checkable

from bioetl.domain.types import JsonDict

__all__ = ["get_pipeline_yaml_for_dq"]


@runtime_checkable
class _ModelDumpProvider(Protocol):
    def model_dump(self) -> object:
        """Return a serializable configuration payload."""
        ...


def get_pipeline_yaml_for_dq(
    pipeline_name: str,
    *,
    pipeline_config_loader: Callable[[str], object],
) -> JsonDict:
    """Return pipeline config as mapping data for DQ config services."""
    config = pipeline_config_loader(pipeline_name)
    if isinstance(config, _ModelDumpProvider):
        payload = config.model_dump()
        if not isinstance(payload, Mapping):
            raise TypeError("Pipeline model_dump() must return a mapping")
        return cast("JsonDict", dict(payload))
    if isinstance(config, Mapping):
        return dict(config)
    raise TypeError("Pipeline YAML config must provide model_dump() or be a mapping")
