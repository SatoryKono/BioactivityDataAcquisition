"""Retained convenience loader for pipeline YAML, filters, and DQ resolution."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_uncached as load_yaml_config_uncached,
)
from bioetl.infrastructure.config.pipeline_dq_resolution import (
    conditional_validation_to_dict,
    cross_field_validation_to_dict,
    field_validation_to_dict,
    has_inline_dq_overrides,
    normalize_inline_dq_overrides,
    resolve_pipeline_dq_config,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class PipelineConfigLoader:
    """Retained convenience facade for YAML loading plus DQ/filter integration.

    This class is intentionally retained as a legacy infrastructure convenience
    seam, not the canonical owner of pipeline config resolution.

    Loads pipeline configurations from YAML files and resolves DQ config
    through the hierarchical DQConfigLoader system. Filter configs are
    resolved via FilterConfigLoader during pipeline config loading.

    Resolution order for DQ config:
    1. If dq_config_file present: load from DQ hierarchy
    2. If dq_overrides present: apply as inline overrides
    3. If both: merge (file hierarchy + inline overrides)
    4. If neither: load defaults from DQ hierarchy

    Attributes:
        _dq_loader: DQ configuration loader instance.
        _filter_loader: Filter configuration loader instance.
    """

    def __init__(
        self,
        configs_root: Path,
        dq_loader: DQConfigLoader | None = None,
        filter_loader: FilterConfigLoader | None = None,
        relaxed_dq: bool = False,
    ) -> None:
        """Initialize loader with configs root directory.

        Args:
            configs_root: Path to configs/ directory.
            dq_loader: Optional DQ config loader. Created automatically if None.
            filter_loader: Optional filter config loader. Created automatically if None.
            relaxed_dq: Whether to relax DQ thresholds (default: False).
        """
        self._configs_root = resolve_configs_root(configs_root)
        self._dq_loader = dq_loader or DQConfigLoader(
            self._configs_root, relaxed_dq=relaxed_dq
        )
        self._filter_loader = filter_loader or FilterConfigLoader(self._configs_root)

    def load_pipeline_config(self, pipeline_name: str) -> PipelineYamlConfig:
        """Load pipeline configuration from YAML file.

        This method loads the raw YAML config. Use get_domain_config() to get
        the fully resolved domain PipelineConfig with integrated DQ config.

        Args:
            pipeline_name: Pipeline name (e.g., "chembl_activity").

        Returns:
            Validated PipelineYamlConfig Pydantic model.

        Raises:
            ValueError: If pipeline config file doesn't exist.
            ValidationError: If config fails validation.
        """
        return load_yaml_config_uncached(
            pipeline_name,
            filter_loader=self._filter_loader,
            configs_root=self._configs_root,
        )

    def resolve_dq_config(
        self,
        yaml_config: PipelineYamlConfig,
    ) -> DomainDQConfig:
        """Resolve DQ config from hierarchy with optional inline overrides.

        Applies the four-step resolution order documented in the class docstring:
        DQ hierarchy file -> inline overrides -> merged result -> defaults.

        Args:
            yaml_config: Validated pipeline YAML configuration containing
                provider, entity_type, and optional dq_overrides.

        Returns:
            Fully resolved DomainDQConfig with thresholds and validation rules.

        Raises:
            FileNotFoundError: Propagated only when no hierarchy file exists
                and no inline overrides are present.
        """
        return resolve_pipeline_dq_config(
            yaml_config,
            dq_loader=self._dq_loader,
        )

    _has_inline_dq_overrides = staticmethod(has_inline_dq_overrides)
    _normalize_inline_dq_overrides = staticmethod(normalize_inline_dq_overrides)
    _field_validation_to_dict = staticmethod(field_validation_to_dict)
    _cross_field_validation_to_dict = staticmethod(cross_field_validation_to_dict)
    _conditional_validation_to_dict = staticmethod(conditional_validation_to_dict)

    def clear_cache(self) -> None:
        """Clear all caches (DQ and filter loader caches).

        Call after modifying config files during development/testing.
        """
        self._dq_loader.clear_cache()
        self._filter_loader.clear_cache()


__all__ = ["PipelineConfigLoader"]
