"""Compatibility shim for the historical function-based config loader seam."""

from __future__ import annotations

__all__ = ["load_pipeline_config", "load_source_config"]

from functools import lru_cache
from pathlib import Path

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_uncached as _load_pipeline_config_uncached_impl,
)
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    _apply_file_reference_defaults as _apply_file_reference_defaults_impl,
)
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    _apply_layer_defaults as _apply_layer_defaults_impl,
)
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    apply_convention_defaults as _apply_convention_defaults_impl,
)
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    load_source_section as _load_source_section_impl,
)
from bioetl.infrastructure.config.source_config_loader import (
    load_source_config as _load_source_config,
)
from bioetl.infrastructure.config_loader_filtering import (
    FILTER_SECTIONS,
    apply_hierarchical_filter_config,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _apply_convention_defaults(
    config: JsonDict,  # Any: YAML config has heterogeneous values
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Compatibility wrapper delegating convention defaults to config module."""
    return _apply_convention_defaults_impl(config)


def _apply_file_reference_defaults(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    provider: str,
    entity_type: str,
) -> None:
    """Compatibility wrapper for file-reference defaults."""
    _apply_file_reference_defaults_impl(config, provider, entity_type)


def _apply_layer_defaults(
    layer: JsonDict,  # Any: YAML config has heterogeneous values
    provider: str,
    entity_type: str,
    layer_name: str,
    sort_policy: list[str],
) -> None:
    """Compatibility wrapper for layer defaults."""
    _apply_layer_defaults_impl(
        layer,
        provider,
        entity_type,
        layer_name,
        sort_policy,
    )


load_source_config = _load_source_config


_FILTER_SECTIONS = FILTER_SECTIONS
_apply_hierarchical_filter_config = apply_hierarchical_filter_config


def _load_source_section(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    config_path: Path,
) -> None:
    """Compatibility wrapper delegating source merging to config module."""
    _load_source_section_impl(config, config_path)


def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline config via the compatibility seam with patchable stages."""
    return _load_pipeline_config_cached(pipeline_name, _configs_root_cache_key())


def _configs_root_cache_key() -> str:
    """Build a stable cache key for working-directory-sensitive config resolution."""
    return str(Path("configs").resolve())


@lru_cache(maxsize=10)
def _load_pipeline_config_cached(
    pipeline_name: str,
    _configs_root_key: str,
) -> PipelineYamlConfig:
    """Compatibility-preserving cached pipeline load."""
    return load_pipeline_config_uncached(pipeline_name)


# Preserve legacy cache management API used by tests and callers.
load_pipeline_config.cache_clear = _load_pipeline_config_cached.cache_clear  # type: ignore[attr-defined]
load_pipeline_config.cache_info = _load_pipeline_config_cached.cache_info  # type: ignore[attr-defined]
load_pipeline_config.__wrapped__ = _load_pipeline_config_cached  # type: ignore[attr-defined]


def load_pipeline_config_uncached(
    pipeline_name: str,
    *,
    filter_loader: FilterConfigLoader | None = None,
) -> PipelineYamlConfig:
    """Compatibility-preserving uncached pipeline load via canonical config API."""
    return _load_pipeline_config_uncached_impl(
        pipeline_name,
        filter_loader=filter_loader,
    )
