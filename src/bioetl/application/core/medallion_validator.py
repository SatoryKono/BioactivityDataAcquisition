"""Medallion architecture configuration validator.

Extracted from PreflightService to follow Single Responsibility Principle.
Validates Medallion layer configuration and write mode policies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.exceptions import PolicyViolationError
from bioetl.domain.medallion import Layer, MedallionPolicy, WriteMode, WriteModePolicy
from bioetl.domain.types import ConfigValidationError, RunType

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import LoggerPort


class MedallionConfigValidator:
    """Validates Medallion architecture configuration.

    Responsibilities:
    - Validate Silver and Gold layer formats
    - Validate path uniqueness across layers
    - Validate MedallionPolicy consistency with RunType
    - Validate write modes against layer policies

    Extracted from PreflightService per REFACTOR-003.

    Attributes:
        _config: Pipeline configuration.
        _logger: Structured logger.

    """

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerPort,
    ) -> None:
        """Initialize medallion config validator.

        Args:
            config: Pipeline configuration.
            logger: Structured logger.

        """
        self._config = config
        self._logger = logger

    def validate_medallion_config(
        self,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> list[ConfigValidationError]:
        """Validate Medallion architecture invariants before pipeline execution.

        Проверяет соблюдение архитектурных инвариантов Medallion:
        - Silver format MUST be "delta" (RULES §4.1)
        - Gold format MUST be "delta" or "parquet" (RULES §4.1)
        - Bronze path != Silver path != Gold path (путь уникальности)
        - MedallionPolicy согласована с RunType

        Args:
            runtime: Runtime configuration with run type.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer (e.g., "delta", "parquet").
            gold_format: Format of Gold layer (e.g., "delta", "parquet").

        Returns:
            List of ConfigValidationError objects. Empty list means validation passed.

        Example:
            >>> errors = validator.validate_medallion_config(
            ...     runtime, "/bronze", "/silver", "/gold",
            ...     silver_format="delta", gold_format="delta"
            ... )
            >>> if errors and runtime.strict_validation:
            ...     raise ValueError(f"Medallion invariant violations: {errors}")

        """
        errors: list[ConfigValidationError] = []

        errors.extend(self._validate_layer_formats(silver_format, gold_format))
        errors.extend(
            self._validate_path_uniqueness(bronze_path, silver_path, gold_path)
        )

        policy = MedallionPolicy.for_run_type(runtime.run_type)
        errors.extend(
            self._validate_medallion_policy_consistency(runtime.run_type, policy)
        )

        self._log_medallion_validation_result(errors, runtime)
        return errors

    def validate_write_modes(self) -> list[ConfigValidationError]:
        """Validate that config write modes are allowed by medallion policy.

        Проверяет соответствие write_mode и gold_write_mode политике Medallion:
        - Silver: APPEND или MERGE (REQ-MEDALLION-002)
        - Gold: MERGE или OVERWRITE (REQ-MEDALLION-003)

        Returns:
            List of ConfigValidationError if write modes violate policy.

        """
        errors: list[ConfigValidationError] = []
        write_mode_policy = WriteModePolicy()

        # Validate Silver write mode
        silver_mode = self._config.write_mode
        try:
            write_mode_policy.validate(Layer.SILVER, WriteMode(silver_mode))
        except (PolicyViolationError, ValueError):
            allowed = WriteModePolicy.ALLOWED_MODES[Layer.SILVER]
            allowed_names = ", ".join(
                m.value for m in sorted(allowed, key=lambda x: x.value)
            )
            errors.append(
                ConfigValidationError(
                    field="write_mode",
                    expected=f"one of: {allowed_names}",
                    actual=silver_mode,
                    rule="RULES §2.1: Silver layer allowed modes",
                )
            )

        # Validate Gold write mode
        gold_mode = self._config.gold_write_mode
        # Gold supports 'scd2' which maps to MERGE for policy purposes
        effective_gold_mode = "merge" if gold_mode == "scd2" else gold_mode
        try:
            write_mode_policy.validate(Layer.GOLD, WriteMode(effective_gold_mode))
        except (PolicyViolationError, ValueError):
            allowed = WriteModePolicy.ALLOWED_MODES[Layer.GOLD]
            allowed_names = ", ".join(
                m.value for m in sorted(allowed, key=lambda x: x.value)
            )
            errors.append(
                ConfigValidationError(
                    field="gold_write_mode",
                    expected=f"one of: {allowed_names}, scd2",
                    actual=gold_mode,
                    rule="RULES §2.1: Gold layer allowed modes",
                )
            )

        # Log validation results
        if errors:
            self._logger.warning(
                "Write mode validation found issues",
                extra={
                    "error_count": len(errors),
                    "errors": [{"field": e.field, "rule": e.rule} for e in errors],
                },
            )
        else:
            self._logger.debug(
                "Write mode validation passed",
                extra={
                    "silver_mode": silver_mode,
                    "gold_mode": gold_mode,
                },
            )

        return errors

    def _validate_layer_formats(
        self, silver_format: str | None, gold_format: str | None
    ) -> list[ConfigValidationError]:
        """Validate Silver and Gold layer formats.

        Args:
            silver_format: Format of Silver layer.
            gold_format: Format of Gold layer.

        Returns:
            List of format validation errors.

        """
        errors: list[ConfigValidationError] = []

        if silver_format is not None and silver_format != "delta":
            errors.append(
                ConfigValidationError(
                    field="sink.silver.format",
                    expected="delta",
                    actual=silver_format,
                    rule="RULES §4.1: Silver MUST use Delta Lake",
                )
            )

        if gold_format is not None and gold_format not in ("delta", "parquet"):
            errors.append(
                ConfigValidationError(
                    field="sink.gold.format",
                    expected="delta or parquet",
                    actual=gold_format,
                    rule="RULES §4.1: Gold MUST use Delta Lake or Parquet",
                )
            )

        return errors

    def _validate_path_uniqueness(
        self, bronze_path: str, silver_path: str, gold_path: str
    ) -> list[ConfigValidationError]:
        """Validate that layer paths are unique.

        Args:
            bronze_path: Base path for Bronze layer.
            silver_path: Base path for Silver layer.
            gold_path: Base path for Gold layer.

        Returns:
            List of path uniqueness errors.

        """
        errors: list[ConfigValidationError] = []
        paths = {bronze_path, silver_path, gold_path}

        if len(paths) >= 3:
            return errors

        if bronze_path == silver_path:
            errors.append(
                ConfigValidationError(
                    field="storage.paths",
                    expected="unique paths for each layer",
                    actual=f"bronze_path == silver_path ({bronze_path})",
                    rule="Medallion Architecture: layers MUST have distinct paths",
                )
            )
        if silver_path == gold_path:
            errors.append(
                ConfigValidationError(
                    field="storage.paths",
                    expected="unique paths for each layer",
                    actual=f"silver_path == gold_path ({silver_path})",
                    rule="Medallion Architecture: layers MUST have distinct paths",
                )
            )
        if bronze_path == gold_path:
            errors.append(
                ConfigValidationError(
                    field="storage.paths",
                    expected="unique paths for each layer",
                    actual=f"bronze_path == gold_path ({bronze_path})",
                    rule="Medallion Architecture: layers MUST have distinct paths",
                )
            )

        return errors

    def _validate_medallion_policy_consistency(
        self,
        run_type: RunType,
        policy: MedallionPolicy,
    ) -> list[ConfigValidationError]:
        """Validate that MedallionPolicy is consistent with RunType.

        Проверяет соответствие политики очистки типу запуска:
        - REBUILD/BACKFILL: should_clear_silver and should_clear_gold MUST be True
        - INCREMENTAL: should NOT clear any layers

        Args:
            run_type: The type of pipeline run.
            policy: The MedallionPolicy derived from run_type.

        Returns:
            List of ConfigValidationError if inconsistencies found.

        """
        errors: list[ConfigValidationError] = []

        if run_type in (RunType.REBUILD, RunType.BACKFILL):
            # For REBUILD/BACKFILL, policy should clear both layers
            if not policy.should_clear_silver:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_silver",
                        expected="True",
                        actual="False",
                        rule=f"RULES §2.1: {run_type.value} MUST clear Silver layer",
                    )
                )
            if not policy.should_clear_gold:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_gold",
                        expected="True",
                        actual="False",
                        rule=f"RULES §2.1: {run_type.value} MUST clear Gold layer",
                    )
                )
        elif run_type == RunType.INCREMENTAL:
            # For INCREMENTAL, policy should NOT clear any layers
            if policy.should_clear_silver:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_silver",
                        expected="False",
                        actual="True",
                        rule="RULES §2.1: INCREMENTAL MUST NOT clear Silver layer",
                    )
                )
            if policy.should_clear_gold:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_gold",
                        expected="False",
                        actual="True",
                        rule="RULES §2.1: INCREMENTAL MUST NOT clear Gold layer",
                    )
                )

        return errors

    def _log_medallion_validation_result(
        self, errors: list[ConfigValidationError], runtime: RuntimeConfig
    ) -> None:
        """Log medallion validation results.

        Args:
            errors: List of validation errors.
            runtime: Runtime configuration.

        """
        if errors:
            self._logger.warning(
                "Medallion config validation found issues",
                extra={
                    "error_count": len(errors),
                    "errors": [{"field": e.field, "rule": e.rule} for e in errors],
                    "strict_mode": runtime.strict_validation,
                },
            )
        else:
            self._logger.debug(
                "Medallion config validation passed",
                extra={"run_type": runtime.run_type.value},
            )


__all__ = ["MedallionConfigValidator"]
