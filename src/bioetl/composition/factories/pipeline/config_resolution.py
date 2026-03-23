"""Compatibility shim for pipeline configuration resolution helpers."""

from __future__ import annotations

from bioetl.infrastructure.config import (
    domain_config_resolver as _domain_config_resolver,
)
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

DomainConfigResolver = _domain_config_resolver.DomainConfigResolver
resolve_domain_pipeline_config = _domain_config_resolver.resolve_domain_pipeline_config

__all__ = [
    "DomainConfigResolver",
    "load_pipeline_config",
    "resolve_domain_pipeline_config",
    "yaml_config_to_domain",
]
