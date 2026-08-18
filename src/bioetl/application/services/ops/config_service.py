"""Configuration service for administrative operations (Application layer)."""

from __future__ import annotations

__all__ = [
    "ConfigDQServiceProtocol",
    "ConfigService",
    "DomainConfigMapperPort",
    "PipelineConfigLoaderPort",
    "PipelineInfo",
    "PipelineRegistryPort",
    "PipelineSettingsPort",
    "PipelineYamlConfigPort",
    "RegistryAccessorPort",
    "SettingsInfo",
    "SettingsLoaderPort",
    "SettingsPort",
]

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.config import PipelineConfig
from bioetl.domain.ports import (
    DomainConfigMapperPort,
    PipelineConfigLoaderPort,
    PipelineRegistryPort,
    PipelineSettingsPort,
    PipelineYamlConfigPort,
    RegistryAccessorPort,
    SettingsLoaderPort,
    SettingsPort,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class ConfigDQServiceProtocol(Protocol):
    """Port for DQ-focused config operations delegated by ConfigService."""

    def get_dq_config(self, pipeline_name: str) -> JsonDict:
        """Return the normalized Data Quality config for one pipeline."""
        ...

    def validate_dq_config(self, pipeline_name: str, dq_config: JsonDict) -> bool:
        """Validate a proposed Data Quality config payload."""
        ...

    def get_effective_config_artifact(
        self,
        pipeline_name: str,
        runtime_overrides: JsonDict | None = None,
    ) -> JsonDict:
        """Build the effective-config artifact exposed to admin tooling."""
        ...

    def check_config_compatibility(
        self,
        artifact1: JsonDict,
        artifact2: JsonDict,
    ) -> bool:
        """Report whether two effective-config artifacts remain compatible."""
        ...


@dataclass(frozen=True, slots=True)
class PipelineInfo:
    """Summary information about a registered pipeline."""

    name: str
    provider: str
    entity_type: str
    silver_table: str
    gold_table: str | None


@dataclass(frozen=True, slots=True)
class SettingsInfo:
    """Application settings information."""

    env: str
    data_dir: str
    bronze_path: str
    silver_path: str
    gold_path: str
    checkpoint_path: str
    quarantine_path: str
    debug: bool
    test_mode: bool
    metrics_enabled: bool
    metrics_port: int
    batch_size: int
    additional: JsonDict  # Any: YAML config has heterogeneous values


@dataclass
class ConfigService:
    """Service for configuration access operations."""

    logger: LoggerPort
    _settings_loader: SettingsLoaderPort
    _pipeline_config_loader: PipelineConfigLoaderPort
    _domain_config_mapper: DomainConfigMapperPort
    _registry_accessor: RegistryAccessorPort
    _dq_service: ConfigDQServiceProtocol | None = None

    def _require_dq_service(self) -> ConfigDQServiceProtocol:
        if self._dq_service is None:
            raise ValueError("DQ config operations are not configured in composition")
        return self._dq_service

    def get_settings(self) -> SettingsInfo:
        """Get application settings."""
        self.logger.debug("Getting application settings")
        settings = self._settings_loader()
        settings_dict = settings.model_dump()
        additional = {
            key: value
            for key, value in settings_dict.items()
            if key
            not in {
                "env",
                "data_dir",
                "debug",
                "test_mode",
                "metrics_enabled",
                "metrics_port",
                "pipeline",
            }
        }
        info = SettingsInfo(
            env=settings.env,
            data_dir=str(settings.data_dir),
            bronze_path=str(settings.bronze_path),
            silver_path=str(settings.silver_path),
            gold_path=str(settings.gold_path),
            checkpoint_path=str(settings.checkpoint_path),
            quarantine_path=str(settings.quarantine_path),
            debug=settings.debug,
            test_mode=settings.test_mode,
            metrics_enabled=settings.metrics_enabled,
            metrics_port=settings.metrics_port,
            batch_size=settings.pipeline.batch_size,
            additional=additional,
        )
        self.logger.info("Got application settings", env=info.env)
        return info

    def load_pipeline_config(self, pipeline_name: str) -> PipelineConfig:
        """Load and validate pipeline configuration."""
        self.logger.debug("Loading pipeline config", pipeline=pipeline_name)
        yaml_config = self._pipeline_config_loader(pipeline_name)
        domain_config: PipelineConfig = self._domain_config_mapper(yaml_config)
        self.logger.info(
            "Loaded pipeline config",
            pipeline=pipeline_name,
            provider=domain_config.provider,
            entity_type=domain_config.entity_type,
        )
        return domain_config

    def get_pipeline_yaml_config(
        self,
        pipeline_name: str,
    ) -> JsonDict:  # Any: YAML config has heterogeneous values
        """Get raw pipeline YAML configuration as dictionary."""
        self.logger.debug("Getting pipeline YAML config", pipeline=pipeline_name)
        yaml_config = self._pipeline_config_loader(pipeline_name)
        if hasattr(yaml_config, "model_dump"):
            config_dict = yaml_config.model_dump()
        elif isinstance(yaml_config, Mapping):
            config_dict = dict(yaml_config)
        else:
            raise TypeError(
                "Pipeline YAML config must provide model_dump() or be a mapping"
            )
        self.logger.info("Got pipeline YAML config", pipeline=pipeline_name)
        return config_dict

    def validate_pipeline_config(self, pipeline_name: str) -> PipelineInfo:
        """Validate pipeline configuration and return summary info."""
        self.logger.debug("Validating pipeline config", pipeline=pipeline_name)
        yaml_config = self._pipeline_config_loader(pipeline_name)
        domain_config = self._domain_config_mapper(yaml_config)
        info = PipelineInfo(
            name=pipeline_name,
            provider=domain_config.provider,
            entity_type=domain_config.entity_type,
            silver_table=domain_config.effective_silver_table,
            gold_table=domain_config.table.gold_table,
        )
        self.logger.info(
            "Validated pipeline config",
            pipeline=pipeline_name,
            provider=info.provider,
        )
        return info

    def list_pipelines(self) -> list[str]:
        """List all registered pipelines."""
        self.logger.debug("Listing registered pipelines")
        registry = self._registry_accessor()
        pipelines: list[str] = registry.list_pipelines()
        self.logger.info("Listed pipelines", count=len(pipelines))
        return pipelines

    def get_dq_config(self, pipeline_name: str) -> JsonDict:
        """Get Data Quality configuration for a pipeline."""
        return self._require_dq_service().get_dq_config(pipeline_name)

    def validate_dq_config(self, pipeline_name: str, dq_config: JsonDict) -> bool:
        """Validate Data Quality configuration."""
        return self._require_dq_service().validate_dq_config(pipeline_name, dq_config)

    def get_effective_config_artifact(
        self,
        pipeline_name: str,
        runtime_overrides: JsonDict | None = None,
    ) -> JsonDict:
        """Get effective configuration artifact for a pipeline."""
        return self._require_dq_service().get_effective_config_artifact(
            pipeline_name,
            runtime_overrides,
        )

    def check_config_compatibility(
        self,
        artifact1: JsonDict,
        artifact2: JsonDict,
    ) -> bool:
        """Check compatibility between two configuration artifacts."""
        return self._require_dq_service().check_config_compatibility(
            artifact1,
            artifact2,
        )
