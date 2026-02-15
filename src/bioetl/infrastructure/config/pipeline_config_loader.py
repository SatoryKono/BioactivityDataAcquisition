"""Pipeline configuration loader with DQ integration.

Loads and validates pipeline configurations from YAML files.
Integrates with DQConfigLoader for hierarchical DQ config resolution.

This module provides the ConfigLoader class which serves as the main entry point
for loading pipeline configurations with proper DQ config resolution.

Example:
    >>> from pathlib import Path
    >>> from bioetl.infrastructure.config import ConfigLoader
    >>> loader = ConfigLoader(Path("configs"))
    >>> config = loader.load_pipeline_config("chembl_activity")
    >>> config.dq.soft_fail_threshold
    0.05
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.domain.config import DQConfig
from bioetl.infrastructure.config.converters import dq_overrides_to_domain
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
from bioetl.infrastructure.config_loader import load_pipeline_config as load_yaml_config
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class ConfigLoader:
    """Pipeline configuration loader with DQ config integration.

    Loads pipeline configurations from YAML files and resolves DQ config
    through the hierarchical DQConfigLoader system.

    Resolution order for DQ config:
    1. If dq_config_file present: load from DQ hierarchy
    2. If dq_overrides present: apply as inline overrides
    3. If both: merge (file hierarchy + inline overrides)
    4. If neither: load defaults from DQ hierarchy

    Attributes:
        _configs_root: Root path to configs/ directory.
        _dq_loader: DQ configuration loader instance.
    """

    def __init__(
        self,
        configs_root: Path,
        dq_loader: DQConfigLoader | None = None,
        relaxed_dq: bool = False,
    ) -> None:
        """Initialize loader with configs root directory.

        Args:
            configs_root: Path to configs/ directory.
            dq_loader: Optional DQ config loader. Created automatically if None.
            relaxed_dq: Whether to relax DQ thresholds (default: False).
        """
        self._configs_root = configs_root
        self._dq_loader = dq_loader or DQConfigLoader(
            configs_root, relaxed_dq=relaxed_dq
        )

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
        return load_yaml_config(pipeline_name)

    def resolve_dq_config(
        self,
        yaml_config: PipelineYamlConfig,
    ) -> DQConfig:
        """Resolve DQ config from file reference and/or inline rules.

        Resolution order:
        1. If dq_config_file present: load from DQ hierarchy
        2. If dq_overrides present: apply as inline overrides
        3. If both: merge (file + inline overrides)
        4. If neither: load defaults from DQ hierarchy

        Args:
            yaml_config: Validated pipeline YAML configuration.

        Returns:
            Resolved DQConfig domain object.
        """
        provider = yaml_config.provider
        entity = yaml_config.entity_type

        # Check if dq_config_file is specified
        dq_config_file = getattr(yaml_config, "dq_config_file", None)

        # Get inline dq_overrides if present (non-empty)
        has_inline_rules = self._has_inline_dq_overrides(yaml_config)

        if dq_config_file is not None or has_inline_rules:
            # Use hierarchical DQ config system
            inline_overrides = (
                self._normalize_inline_dq_overrides(yaml_config.dq_overrides)
                if has_inline_rules
                else None
            )

            return self._dq_loader.load(
                provider=provider,
                entity=entity,
                inline_overrides=inline_overrides,
            )

        # Fallback: try to load from hierarchy if available, otherwise use inline rules
        try:
            return self._dq_loader.load(
                provider=provider,
                entity=entity,
                inline_overrides=None,
            )
        except FileNotFoundError:
            # No DQ hierarchy available, use inline overrides as-is
            return dq_overrides_to_domain(yaml_config)

    def _has_inline_dq_overrides(self, yaml_config: PipelineYamlConfig) -> bool:
        """Check if YAML config has non-default inline DQ overrides.

        Args:
            yaml_config: Pipeline YAML configuration.

        Returns:
            True if inline dq_overrides contains meaningful overrides.
        """
        dq = yaml_config.dq_overrides

        # Check for any field validations or non-default thresholds
        has_validations = bool(
            dq.field_validations
            or dq.cross_field_validations
            or dq.conditional_validations
        )

        # Check for non-default thresholds
        has_custom_thresholds = (
            dq.soft_fail_threshold != 0.05 or dq.hard_fail_threshold != 0.20
        )

        return has_validations or has_custom_thresholds

    def _normalize_inline_dq_overrides(
        self,
        dq_overrides: Any,
    ) -> dict[str, Any]:
        """Normalize inline dq_overrides to DQConfigFile format.

        Converts the Pydantic DQConfig model to a dict compatible with
        the DQConfigLoader merge format.

        Args:
            dq_overrides: DQConfig Pydantic model from pipeline config.

        Returns:
            Dict in DQConfigFile format for merge.
        """
        result: dict[str, Any] = {}

        # Thresholds normalization
        result["thresholds"] = {
            "soft_fail": dq_overrides.soft_fail_threshold,
            "hard_fail": dq_overrides.hard_fail_threshold,
        }

        # Direct copy for compatible fields
        result["strict_validation"] = dq_overrides.strict_validation
        result["invalid_record_policy"] = dq_overrides.invalid_record_policy

        # Report config
        result["report"] = {
            "enabled": dq_overrides.report.enabled,
            "format": dq_overrides.report.format,
            "include_sample_failures": dq_overrides.report.include_sample_failures,
            "sample_size": dq_overrides.report.sample_size,
            "output_path": dq_overrides.report.output_path,
        }

        # Validation lists → entity-level (inline = highest priority)
        if dq_overrides.field_validations:
            result["entity_field_validations"] = [
                self._field_validation_to_dict(fv)
                for fv in dq_overrides.field_validations
            ]

        if dq_overrides.cross_field_validations:
            result["entity_cross_field_validations"] = [
                self._cross_field_validation_to_dict(cfv)
                for cfv in dq_overrides.cross_field_validations
            ]

        if dq_overrides.conditional_validations:
            result["entity_conditional_validations"] = [
                self._conditional_validation_to_dict(cv)
                for cv in dq_overrides.conditional_validations
            ]

        return result

    def _field_validation_to_dict(self, fv: Any) -> dict[str, Any]:
        """Convert FieldValidationConfig to dict.

        Args:
            fv: FieldValidationConfig instance.

        Returns:
            Dict representation for YAML merge.
        """
        result: dict[str, Any] = {
            "field": fv.field,
            "type": fv.type,
            "nullable": fv.nullable,
        }
        if fv.min is not None:
            result["min"] = fv.min
        if fv.max is not None:
            result["max"] = fv.max
        if fv.pattern:
            result["pattern"] = fv.pattern
        if fv.allowed:
            result["allowed"] = list(fv.allowed)
        if fv.validator:
            result["validator"] = fv.validator
        if fv.error_message:
            result["error_message"] = fv.error_message
        return result

    def _cross_field_validation_to_dict(self, cfv: Any) -> dict[str, Any]:
        """Convert CrossFieldValidationConfig to dict.

        Args:
            cfv: CrossFieldValidationConfig instance.

        Returns:
            Dict representation for YAML merge.
        """
        result: dict[str, Any] = {
            "name": cfv.name,
            "fields": list(cfv.fields),
            "condition": cfv.condition,
        }
        if cfv.trigger_field:
            result["trigger_field"] = cfv.trigger_field
        if cfv.required_field:
            result["required_field"] = cfv.required_field
        if cfv.validator:
            result["validator"] = cfv.validator
        if cfv.error_message:
            result["error_message"] = cfv.error_message
        return result

    def _conditional_validation_to_dict(self, cv: Any) -> dict[str, Any]:
        """Convert ConditionalValidationConfig to dict.

        Args:
            cv: ConditionalValidationConfig instance.

        Returns:
            Dict representation for YAML merge.
        """
        result: dict[str, Any] = {
            "name": cv.name,
            "condition_field": cv.condition_field,
            "condition_value": (
                list(cv.condition_value)
                if isinstance(cv.condition_value, list)
                else cv.condition_value
            ),
            "condition_operator": cv.condition_operator,
        }
        if cv.then_validations:
            result["then_validations"] = [
                self._field_validation_to_dict(tv) for tv in cv.then_validations
            ]
        return result

    def clear_cache(self) -> None:
        """Clear all caches (DQ loader cache).

        Call after modifying config files during development/testing.
        """
        self._dq_loader.clear_cache()


__all__ = ["ConfigLoader"]
