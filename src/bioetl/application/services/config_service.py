"""Configuration service for administrative operations (Application layer).

Provides high-level configuration access for CLI and other interfaces.
Abstracts infrastructure configuration loading behind application service.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.domain.config import PipelineConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class PipelineInfo:
    """Summary information about a registered pipeline.

    Attributes:
        name: Name of the pipeline (e.g., 'chembl_activity').
        provider: Data provider (e.g., 'chembl').
        entity_type: Entity type being processed (e.g., 'activity').
        silver_table: Name of the Silver table.
        gold_table: Name of the Gold table (if configured).
    """

    name: str
    provider: str
    entity_type: str
    silver_table: str
    gold_table: str | None


@dataclass(frozen=True, slots=True)
class SettingsInfo:
    """Application settings information.

    Attributes:
        env: Current environment (dev, staging, prod).
        data_dir: Base directory for all data storage.
        bronze_path: Path for Bronze layer storage.
        silver_path: Path for Silver layer storage.
        gold_path: Path for Gold layer storage.
        checkpoint_path: Path for checkpoint storage.
        quarantine_path: Path for quarantine storage.
        debug: Debug mode enabled.
        test_mode: Test mode enabled.
        metrics_enabled: Metrics collection enabled.
        metrics_port: Port for Prometheus metrics HTTP server.
        batch_size: Default batch size for pipeline execution.
        additional: Additional settings as dictionary.
    """

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
    additional: dict[str, Any]


@dataclass
class ConfigService:
    """Service for configuration access operations.

    Provides high-level operations for accessing application configuration
    used by CLI and other interfaces. Abstracts infrastructure details
    for Application-layer access.

    Attributes:
        logger: Structured logger for observability.
        _settings_loader: Callable to load Settings from infrastructure.
        _pipeline_config_loader: Callable to load pipeline YAML config.
        _domain_config_mapper: Callable to convert YAML config to domain config.
        _registry_accessor: Callable to access pipeline registry.

    Example:
        >>> service = ConfigService(logger=logger, ...)
        >>> settings = service.get_settings()
        >>> logger.info("environment", env=settings.env)
    """

    logger: LoggerPort
    _settings_loader: Any  # Callable[[], Settings]
    _pipeline_config_loader: Any  # Callable[[str], PipelineYamlConfig]
    _domain_config_mapper: Any  # Callable[[PipelineYamlConfig], PipelineConfig]
    _registry_accessor: Any  # Callable[[], PipelineRegistry]

    def get_settings(self) -> SettingsInfo:
        """Get application settings.

        Returns:
            SettingsInfo with current application configuration.
        """
        self.logger.debug("Getting application settings")

        settings = self._settings_loader()

        # Extract additional settings for extensibility
        settings_dict = settings.model_dump()
        additional = {
            k: v
            for k, v in settings_dict.items()
            if k
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
        """Load and validate pipeline configuration.

        Args:
            pipeline_name: Name of the pipeline (e.g., 'chembl_activity').

        Returns:
            PipelineConfig domain object for the pipeline.

        Raises:
            ValueError: If pipeline configuration not found.
            FileNotFoundError: If pipeline config file is missing.
        """
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

    def get_pipeline_yaml_config(self, pipeline_name: str) -> dict[str, Any]:
        """Get raw pipeline YAML configuration as dictionary.

        Useful for CLI display commands that show full configuration.

        Args:
            pipeline_name: Name of the pipeline (e.g., 'chembl_activity').

        Returns:
            Dictionary representation of the YAML configuration.

        Raises:
            ValueError: If pipeline configuration not found.
            FileNotFoundError: If pipeline config file is missing.
        """
        self.logger.debug("Getting pipeline YAML config", pipeline=pipeline_name)

        yaml_config = self._pipeline_config_loader(pipeline_name)

        # Convert Pydantic model to dict
        if hasattr(yaml_config, "model_dump"):
            config_dict: dict[str, Any] = yaml_config.model_dump()
        else:
            config_dict = dict(yaml_config)

        self.logger.info("Got pipeline YAML config", pipeline=pipeline_name)
        return config_dict

    def validate_pipeline_config(self, pipeline_name: str) -> PipelineInfo:
        """Validate pipeline configuration and return summary info.

        Args:
            pipeline_name: Name of the pipeline (e.g., 'chembl_activity').

        Returns:
            PipelineInfo with summary of validated configuration.

        Raises:
            ValueError: If pipeline configuration is invalid.
            FileNotFoundError: If pipeline config file is missing.
        """
        self.logger.debug("Validating pipeline config", pipeline=pipeline_name)

        yaml_config = self._pipeline_config_loader(pipeline_name)

        info = PipelineInfo(
            name=pipeline_name,
            provider=yaml_config.provider,
            entity_type=yaml_config.entity_type,
            silver_table=yaml_config.silver_table,
            gold_table=yaml_config.gold_table,
        )

        self.logger.info(
            "Validated pipeline config",
            pipeline=pipeline_name,
            provider=info.provider,
        )

        return info

    def list_pipelines(self) -> list[str]:
        """List all registered pipelines.

        Returns:
            List of pipeline names.
        """
        self.logger.debug("Listing registered pipelines")

        registry = self._registry_accessor()
        pipelines: list[str] = registry.list_pipelines()

        self.logger.info("Listed pipelines", count=len(pipelines))
        return pipelines
