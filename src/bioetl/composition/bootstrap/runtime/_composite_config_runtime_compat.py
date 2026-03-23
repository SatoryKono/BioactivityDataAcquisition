"""Helper for the composite runtime compatibility config-loading facade."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bioetl.domain.composite.config import CompositeConfig

CompositeConfigPathResolver = Callable[[str], Path]
CompositeConfigValidator = Callable[[dict[str, object]], object]
CompositeConfigLoader = Callable[..., CompositeConfig]

__all__ = ["load_runtime_composite_config"]


def load_runtime_composite_config(
    name: str,
    *,
    resolve_config_path_fn: CompositeConfigPathResolver,
    load_config_fn: CompositeConfigLoader,
    validate_payload: CompositeConfigValidator,
    validation_error_cls: type[Exception],
) -> CompositeConfig:
    """Load composite config while preserving runtime facade patch points."""
    config_path = resolve_config_path_fn(name)
    try:
        return load_config_fn(
            config_path.stem,
            config_dir=config_path.parent,
            validate_payload=validate_payload,
        )
    except validation_error_cls as error:
        raise ValueError(f"Invalid composite config '{name}': {error}") from error
