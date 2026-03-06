"""Backward-compatible re-export for config loader ports.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.config.config_loader_port import (
    DomainConfigMapperPort,
    PipelineConfigLoaderPort,
    SettingsLoaderPort,
)

__all__ = [
    "DomainConfigMapperPort",
    "PipelineConfigLoaderPort",
    "SettingsLoaderPort",
]
