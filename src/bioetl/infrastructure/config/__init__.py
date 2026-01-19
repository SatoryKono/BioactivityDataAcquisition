"""Configuration loading infrastructure.

Provides loaders for hierarchical YAML configuration files.

Re-exports from _base.py for backward compatibility:
- Settings: Main application settings (pydantic-settings)
- get_settings: Get cached application settings
- get_pipeline_config: Get pipeline config by name (domain object)
- load_pipeline_config: Load pipeline YAML config (Pydantic model)
- load_source_config: Load source YAML config
- yaml_config_to_domain: Convert YAML config to domain config

New components:
- DQConfigLoader: Hierarchical DQ config loader
"""

from __future__ import annotations

# Re-export everything from _base.py for backward compatibility
from bioetl.infrastructure.config._base import (
    ObservabilitySettings,
    PipelineSettings,
    Settings,
    SourceYamlConfig,
    get_pipeline_config,
    get_settings,
    load_pipeline_config,
    load_source_config,
    yaml_config_to_domain,
)
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader

__all__ = [
    "DQConfigLoader",
    "ObservabilitySettings",
    "PipelineSettings",
    "Settings",
    "SourceYamlConfig",
    "get_pipeline_config",
    "get_settings",
    "load_pipeline_config",
    "load_source_config",
    "yaml_config_to_domain",
]
