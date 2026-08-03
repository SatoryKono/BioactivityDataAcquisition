"""Configuration loading infrastructure.

Provides loaders for hierarchical YAML configuration files.

Re-exports for backward compatibility:
- Settings: Main application settings (pydantic-settings)
- get_settings: Get cached application settings
- get_pipeline_config: Get pipeline config by name (domain object)
- load_pipeline_config: Load pipeline YAML config (Pydantic model)
- load_composite_config: Load composite YAML config (domain object)
- load_source_config: Load source YAML config
- yaml_config_to_domain: Convert YAML config to domain config

New components:
- DQConfigLoader: Hierarchical DQ config loader
- FilterConfigLoader: Hierarchical filter config loader (ADR-028)
- PipelineConfigLoader: Pipeline config loader with DQ/filter integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
from bioetl.infrastructure.config.publication_controlled_vocabulary_loader import (
    PublicationControlledVocabularyLoader,
)
from bioetl.infrastructure.config.publication_type_classification_loader import (
    PublicationTypeClassificationLoader,
)


def __getattr__(name: str) -> type:  # pragma: no cover
    """Lazy imports to keep the public config package cycle-safe."""
    if TYPE_CHECKING:
        raise AttributeError
    if name == "PipelineConfigLoader":
        from bioetl.infrastructure.config.pipeline_config_loader import (
            PipelineConfigLoader,
        )

        return PipelineConfigLoader
    if name == "load_pipeline_config":
        from bioetl.infrastructure.config.pipeline_config_api import (
            load_pipeline_config,
        )

        return load_pipeline_config
    if name == "load_composite_config":
        from bioetl.infrastructure.config.composite_config_api import (
            load_composite_config,
        )

        return load_composite_config
    if name == "load_workflow_config":
        from bioetl.infrastructure.config.workflow_config_api import (
            load_workflow_config,
        )

        return load_workflow_config
    if name == "load_source_config":
        from bioetl.infrastructure.config.source_config_loader import (
            load_source_config,
        )

        return load_source_config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseConfigLoader",
    "DQConfigLoader",
    "FilterConfigLoader",
    "ObservabilitySettings",
    "PipelineConfigLoader",
    "PipelineSettings",
    "PublicationControlledVocabularyLoader",
    "PublicationTypeClassificationLoader",
    "Settings",
    "SourceYamlConfig",
    "get_pipeline_config",
    "get_settings",
    "load_composite_config",
    "load_pipeline_config",
    "load_pipeline_contract_policy",
    "load_source_config",
    "load_workflow_config",
    "yaml_config_to_domain",
]
