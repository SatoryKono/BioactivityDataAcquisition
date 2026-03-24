"""Compatibility shim for pipeline configuration resolution helpers."""

from __future__ import annotations

from warnings import warn

from bioetl.infrastructure.config import (
    domain_config_resolver as _domain_config_resolver,
)
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

warn(
    "bioetl.composition.factories.pipeline.config_resolution is deprecated; "
    "use bioetl.infrastructure.config.domain_config_resolver, "
    "bioetl.infrastructure.config.pipeline_config_api, and "
    "bioetl.infrastructure.config.converters directly.",
    DeprecationWarning,
    stacklevel=2,
)

DomainConfigResolver = _domain_config_resolver.DomainConfigResolver
resolve_domain_pipeline_config = _domain_config_resolver.resolve_domain_pipeline_config

__all__ = [
    "DomainConfigResolver",
    "load_pipeline_config",
    "resolve_domain_pipeline_config",
    "yaml_config_to_domain",
]
