"""Medallion configuration validation helper for preflight."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.preflight.medallion_validator_runtime import (
    validate_idempotency_contracts,
    validate_key_nullability_policies,
    validate_layer_formats,
    validate_medallion_policy_consistency,
    validate_path_uniqueness,
    validate_single_write_mode,
)
from bioetl.domain.medallion import Layer, MedallionPolicy, WriteModePolicy
from bioetl.domain.types import ConfigValidationError

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import LoggerPort

_GOLD_SEMANTIC_WRITE_MODES = frozenset({"append", "overwrite", "scd2"})
_GOLD_SEMANTIC_WRITE_MODES_EXPECTED = "one of: append, overwrite, scd2"


class MedallionConfigValidator:
    """Validates Medallion architecture invariants and write-mode policies."""
    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerPort,
        write_mode_policy: WriteModePolicy,
    ) -> None:
        self._config = config
        self._logger = logger
        self._write_mode_policy = write_mode_policy
    def validate_medallion_config(
        self,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> list[ConfigValidationError]:
        """Validate layer formats, path uniqueness and policy consistency.
        Args:
            runtime: Runtime configuration supplying run type and strict validation flag.
            bronze_path: Filesystem path configured for the Bronze layer.
            silver_path: Filesystem path configured for the Silver layer.
            gold_path: Filesystem path configured for the Gold layer.
            silver_format: Storage format for Silver (must be ``'delta'`` when provided).
            gold_format: Storage format for Gold (must be ``'delta'`` when provided).
        Returns:
            List of ConfigValidationError instances describing each violation found.
            An empty list indicates the configuration is valid.
        """
        errors: list[ConfigValidationError] = []
        errors.extend(
            validate_layer_formats(
                silver_format=silver_format,
                gold_format=gold_format,
            )
        )
        errors.extend(
            validate_path_uniqueness(
                bronze_path=bronze_path,
                silver_path=silver_path,
                gold_path=gold_path,
            )
        )
        policy = MedallionPolicy.for_run_type(runtime.run_type)
        errors.extend(
            validate_medallion_policy_consistency(
                run_type=runtime.run_type,
                policy=policy,
            )
        )
        errors.extend(
            validate_key_nullability_policies(
                primary_keys=list(self._config.table.primary_keys),
                partition_cols=list(self._config.table.partition_cols),
                key_nullability_rules=list(self._config.dq.key_nullability_rules),
            )
        )
        self._log_medallion_validation_result(errors, runtime)
        return errors
    def validate_write_modes(self) -> list[ConfigValidationError]:
        """Validate that configured write modes are allowed by policy.
        Returns:
            List of ConfigValidationError instances for each disallowed write mode.
            An empty list indicates both Silver and Gold modes are policy-compliant.
        """
        silver_mode = self._config.table.silver_write_mode
        silver_mode_value = str(silver_mode)
        gold_mode = self._config.table.gold_write_mode
        gold_mode_value = str(gold_mode)
        errors = [
            *validate_single_write_mode(
                write_mode_policy=self._write_mode_policy,
                layer=Layer.SILVER,
                mode_value=silver_mode_value,
                field="write_mode",
                rule="RULES §2.1: Silver layer allowed modes",
            ),
            *self._validate_gold_semantic_write_mode(gold_mode_value),
            *validate_idempotency_contracts(
                silver_mode=silver_mode_value,
                gold_mode=gold_mode_value,
                silver_contract=self._config.table.silver_idempotency_contract,
                gold_contract=self._config.table.gold_idempotency_contract,
            ),
        ]
        self._log_write_mode_validation_result(
            errors, silver_mode_value, gold_mode_value
        )
        return errors
    def _validate_gold_semantic_write_mode(
        self, gold_mode_value: str
    ) -> list[ConfigValidationError]:
        if gold_mode_value in _GOLD_SEMANTIC_WRITE_MODES:
            return []
        return [
            ConfigValidationError(
                field="gold_write_mode",
                expected=_GOLD_SEMANTIC_WRITE_MODES_EXPECTED,
                actual=gold_mode_value,
                rule="RULES §2.1: Gold layer allowed modes",
            )
        ]
    def _log_write_mode_validation_result(
        self,
        errors: list[ConfigValidationError],
        silver_mode_value: str,
        gold_mode_value: str,
    ) -> None:
        if errors:
            self._logger.warning(
                "Write mode validation found issues",
                error_count=len(errors),
                errors=[{"field": err.field, "rule": err.rule} for err in errors],
            )
            return
        self._logger.debug(
            "Write mode validation passed",
            silver_mode=silver_mode_value,
            gold_mode=gold_mode_value,
        )
    def _log_medallion_validation_result(
        self, errors: list[ConfigValidationError], runtime: RuntimeConfig
    ) -> None:
        if errors:
            self._logger.warning(
                "Medallion config validation found issues",
                error_count=len(errors),
                errors=[{"field": err.field, "rule": err.rule} for err in errors],
                strict_mode=runtime.strict_validation,
            )
        else:
            self._logger.debug(
                "Medallion config validation passed",
                run_type=runtime.run_type.value,
            )


# Backward-compatible alias kept for transitional imports.
_MedallionConfigValidator = MedallionConfigValidator

__all__ = ["MedallionConfigValidator", "_MedallionConfigValidator"]
