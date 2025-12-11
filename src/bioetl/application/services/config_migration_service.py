"""Configuration migration service (application layer).

This module provides application-layer services for migrating and validating
pipeline configurations. It delegates the actual migration logic to the
infrastructure layer (ConfigMigrator) while keeping the domain layer clean.

This follows Hexagonal Architecture principles:
- Domain layer (PipelineConfig) contains only business rules
- Application layer (ConfigMigrationService) orchestrates use cases
- Infrastructure layer (ConfigMigrator) handles technical migration logic

Example:
    >>> from bioetl.application.services import ConfigMigrationService
    >>> service = ConfigMigrationService()
    >>> config = service.migrate_and_validate({"entity": "activity", ...})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, cast

from pydantic import ValidationError

from bioetl.domain.configs import PipelineConfig
from bioetl.domain.errors import ConfigValidationError

logger = logging.getLogger(__name__)


class ConfigMigrationServiceProtocol(ABC):
    """Protocol for configuration migration services.

    Defines the contract for services that handle migration of legacy
    configuration formats and validation into PipelineConfig domain objects.

    This protocol enables dependency injection and testability by allowing
    mock implementations in tests.

    Example:
        >>> class MockMigrationService(ConfigMigrationServiceProtocol):
        ...     def migrate_and_validate(self, raw_config: dict) -> PipelineConfig:
        ...         return PipelineConfig(...)  # Return test fixture
    """

    @abstractmethod
    def migrate_and_validate(
        self,
        raw_config: dict[str, Any],
        *,
        source_hint: str | None = None,
    ) -> PipelineConfig:
        """Migrate legacy config format and validate into PipelineConfig.

        Args:
            raw_config: Raw configuration dictionary (possibly in legacy format).
            source_hint: Optional hint about config source for error messages
                (e.g., file path, pipeline_id).

        Returns:
            Validated PipelineConfig domain object.

        Raises:
            ConfigValidationError: If validation fails after migration.
        """
        ...

    @abstractmethod
    def migrate(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        """Migrate legacy config format without validation.

        Useful when additional processing is needed before validation.

        Args:
            raw_config: Raw configuration dictionary (possibly in legacy format).

        Returns:
            Migrated configuration dictionary in current format.
        """
        ...

    @abstractmethod
    def was_migration_applied(self, raw_config: dict[str, Any]) -> bool:
        """Check if migration would be applied to the given config.

        Useful for logging/debugging to determine if a config is in legacy format.

        Args:
            raw_config: Raw configuration dictionary.

        Returns:
            True if migration would transform the config, False if already
            in current format.
        """
        ...


class ConfigMigrationService(ConfigMigrationServiceProtocol):
    """Application service for config migration and validation.

    Orchestrates the migration of legacy configuration formats to current
    structure and validates the result into PipelineConfig domain objects.

    This service:
    - Delegates migration logic to infrastructure layer (ConfigMigrator)
    - Logs when migration is applied (for debugging)
    - Provides clean separation between domain and infrastructure

    Attributes:
        _migrator_class: Reference to ConfigMigrator for lazy import.

    Example:
        >>> service = ConfigMigrationService()
        >>> raw = {"entity": "activity", "provider": "chembl", ...}
        >>> config = service.migrate_and_validate(raw, source_hint="test.yaml")
    """

    def __init__(self) -> None:
        """Initialize the migration service.

        The ConfigMigrator is imported lazily to avoid circular dependencies
        at module load time.
        """
        self._migrator_class: type | None = None

    def _get_migrator(self) -> Any:
        """Lazy import of ConfigMigrator from infrastructure.

        Returns:
            ConfigMigrator class from infrastructure layer.
        """
        if self._migrator_class is None:
            from bioetl.infrastructure.config.migration import ConfigMigrator

            self._migrator_class = ConfigMigrator
        return self._migrator_class

    def migrate(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        """Migrate legacy config format without validation.

        Args:
            raw_config: Raw configuration dictionary (possibly in legacy format).

        Returns:
            Migrated configuration dictionary in current format.
        """
        if not isinstance(raw_config, dict):
            return raw_config

        migrator = self._get_migrator()
        return cast(dict[str, Any], migrator.migrate(raw_config))

    def was_migration_applied(self, raw_config: dict[str, Any]) -> bool:
        """Check if migration would be applied to the given config.

        Detects legacy v1 format by checking for flat entity/provider fields
        without identity section.

        Args:
            raw_config: Raw configuration dictionary.

        Returns:
            True if config appears to be in legacy format.
        """
        if not isinstance(raw_config, dict):
            return False

        # Legacy v1 indicators: flat entity/provider without identity section
        has_identity = "identity" in raw_config
        has_flat_entity = "entity" in raw_config or "entity_name" in raw_config
        has_flat_provider = "provider" in raw_config

        # v1: has flat fields but no identity section
        if not has_identity and (has_flat_entity or has_flat_provider):
            return True

        # Also check for legacy sources section
        if "sources" in raw_config and not has_identity:
            return True

        return False

    def migrate_and_validate(
        self,
        raw_config: dict[str, Any],
        *,
        source_hint: str | None = None,
    ) -> PipelineConfig:
        """Migrate legacy config format and validate into PipelineConfig.

        Performs migration first, then Pydantic validation. Logs when
        migration is applied to help identify configs that need updating.

        Args:
            raw_config: Raw configuration dictionary (possibly in legacy format).
            source_hint: Optional hint about config source for error messages.

        Returns:
            Validated PipelineConfig domain object.

        Raises:
            ConfigValidationError: If validation fails after migration.

        Example:
            >>> service = ConfigMigrationService()
            >>> config = service.migrate_and_validate(
            ...     {"entity": "activity", "provider": "chembl"},
            ...     source_hint="chembl.activity.yaml",
            ... )
        """
        # Check if migration will be applied (for logging)
        needs_migration = self.was_migration_applied(raw_config)

        # Apply migration
        migrated = self.migrate(raw_config)

        # Log if migration was applied
        if needs_migration:
            source_info = f" from '{source_hint}'" if source_hint else ""
            logger.debug(
                "Legacy config format detected%s. "
                "Consider updating to v2 format with identity/data_flow sections.",
                source_info,
            )

        # Validate with Pydantic
        try:
            return PipelineConfig.model_validate(migrated)
        except ValidationError as exc:
            source_info = f" for {source_hint}" if source_hint else ""
            raise ConfigValidationError(
                f"Config validation failed{source_info}: {exc}"
            ) from exc


def create_config_migration_service() -> ConfigMigrationService:
    """Factory function for creating ConfigMigrationService.

    Provides a clean factory interface for dependency injection.

    Returns:
        New ConfigMigrationService instance.

    Example:
        >>> service = create_config_migration_service()
        >>> config = service.migrate_and_validate(raw_config)
    """
    return ConfigMigrationService()


__all__ = [
    "ConfigMigrationService",
    "ConfigMigrationServiceProtocol",
    "create_config_migration_service",
]
