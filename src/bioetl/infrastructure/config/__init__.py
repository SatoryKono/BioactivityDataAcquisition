"""Configuration loading infrastructure.

Provides loaders for hierarchical YAML configuration files.

Re-exports for backward compatibility:
- Settings: Main application settings (pydantic-settings)
- get_settings: Get cached application settings
- get_pipeline_config: Get pipeline config by name (domain object)
- load_pipeline_config: Load pipeline YAML config (Pydantic model)
- load_source_config: Load source YAML config
- yaml_config_to_domain: Convert YAML config to domain config

New components:
- DQConfigLoader: Hierarchical DQ config loader
- FilterConfigLoader: Hierarchical filter config loader (ADR-028)
- PipelineConfigLoader: Pipeline config loader with DQ/filter integration
"""

from __future__ import annotations

# Re-export runtime settings/config mapping from _base.py.
from bioetl.infrastructure.config._base import (
    ObservabilitySettings,
    PipelineSettings,
    Settings,
    SourceYamlConfig,
    get_pipeline_config,
    get_settings,
    yaml_config_to_domain,
)
from bioetl.infrastructure.config.base_config_loader import BaseConfigLoader
from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader
from bioetl.infrastructure.config_load_api import (
    load_pipeline_config,
    load_source_config,
)

# Backward compatibility alias
ConfigLoader = PipelineConfigLoader

__all__ = [
    "BaseConfigLoader",
    "ConfigLoader",
    "DQConfigLoader",
    "FilterConfigLoader",
    "ObservabilitySettings",
    "PipelineConfigLoader",
    "PipelineSettings",
    "Settings",
    "SourceYamlConfig",
    "get_pipeline_config",
    "get_settings",
    "load_pipeline_config",
    "load_pipeline_contract_policy",
    "load_source_config",
    "yaml_config_to_domain",
]
