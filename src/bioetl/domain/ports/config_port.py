"""Backward-compatible re-export for config contract ports.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.config.config_port import (
    PipelineSettingsPort,
    PipelineYamlConfigPort,
    SettingsPort,
)

__all__ = [
    "PipelineSettingsPort",
    "PipelineYamlConfigPort",
    "SettingsPort",
]
