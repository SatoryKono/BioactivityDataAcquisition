"""Medallion configuration validation helper for preflight."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.exceptions import PolicyViolationError
from bioetl.domain.medallion import Layer, MedallionPolicy, WriteMode, WriteModePolicy
from bioetl.domain.types import ConfigValidationError, RunType

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import LoggerPort


class _MedallionConfigValidator:
    """Validates Medallion architecture invariants and write-mode policies."""

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerPort,
        write_mode_policy: WriteModePolicy | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._write_mode_policy = write_mode_policy or WriteModePolicy()

    def validate_medallion_config(
        self,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> list[ConfigValidationError]:
        """Validate layer formats, path uniqueness and policy consistency."""
        errors: list[ConfigValidationError] = []

        errors.extend(self._validate_layer_formats(silver_format, gold_format))
        errors.extend(
            self._validate_path_uniqueness(bronze_path, silver_path, gold_path)
        )

        policy = MedallionPolicy.for_run_type(runtime.run_type)
        errors.extend(
            self._validate_medallion_policy_consistency(runtime.run_type, policy)
        )
        errors.extend(self._validate_key_nullability_policies())

        self._log_medallion_validation_result(errors, runtime)
        return errors

    def validate_write_modes(self) -> list[ConfigValidationError]:
        """Validate that configured write modes are allowed by policy."""
        silver_mode = self._config.table.silver_write_mode
        silver_mode_value = str(silver_mode)
        gold_mode = self._config.table.gold_write_mode
        gold_mode_value = str(gold_mode)
        effective_gold_mode = "merge" if gold_mode_value == "scd2" else gold_mode_value
        errors = [
            *self._validate_single_write_mode(
                layer=Layer.SILVER,
                mode_value=silver_mode_value,
                field="write_mode",
                rule="RULES §2.1: Silver layer allowed modes",
            ),
            *self._validate_single_write_mode(
                layer=Layer.GOLD,
                mode_value=effective_gold_mode,
                field="gold_write_mode",
                rule="RULES §2.1: Gold layer allowed modes",
                actual_mode=gold_mode_value,
                expected_suffix=", scd2",
            ),
        ]
        self._log_write_mode_validation_result(
            errors, silver_mode_value, gold_mode_value
        )
        return errors

    def _validate_single_write_mode(
        self,
        *,
        layer: Layer,
        mode_value: str,
        field: str,
        rule: str,
        actual_mode: str | None = None,
        expected_suffix: str = "",
    ) -> list[ConfigValidationError]:
        try:
            self._write_mode_policy.validate(layer, WriteMode(mode_value))
        except (PolicyViolationError, ValueError):
            allowed = WriteModePolicy.ALLOWED_MODES[layer]
            allowed_names = ", ".join(
                mode.value for mode in sorted(allowed, key=lambda item: item.value)
            )
            return [
                ConfigValidationError(
                    field=field,
                    expected=f"one of: {allowed_names}{expected_suffix}",
                    actual=actual_mode or mode_value,
                    rule=rule,
                )
            ]
        return []

    def _log_write_mode_validation_result(
        self,
        errors: list[ConfigValidationError],
        silver_mode_value: str,
        gold_mode_value: str,
    ) -> None:
        if errors:
            self._logger.warning(
                "Write mode validation found issues",
                extra={
                    "error_count": len(errors),
                    "errors": [
                        {"field": err.field, "rule": err.rule} for err in errors
                    ],
                },
            )
            return
        self._logger.debug(
            "Write mode validation passed",
            extra={"silver_mode": silver_mode_value, "gold_mode": gold_mode_value},
        )

    def _validate_layer_formats(
        self, silver_format: str | None, gold_format: str | None
    ) -> list[ConfigValidationError]:
        errors: list[ConfigValidationError] = []

        if silver_format is not None and silver_format != "delta":
            errors.append(
                ConfigValidationError(
                    field="sink.silver.format",
                    expected="delta",
                    actual=silver_format,
                    rule="RULES §2.1: Silver MUST use Delta Lake",
                )
            )

        if gold_format is not None and gold_format != "delta":
            errors.append(
                ConfigValidationError(
                    field="sink.gold.format",
                    expected="delta",
                    actual=gold_format,
                    rule="RULES §2.1: Gold MUST use Delta Lake",
                )
            )

        return errors

    def _validate_path_uniqueness(
        self, bronze_path: str, silver_path: str, gold_path: str
    ) -> list[ConfigValidationError]:
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
        errors: list[ConfigValidationError] = []

        if run_type in (RunType.REBUILD, RunType.BACKFILL):
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

    def _validate_key_nullability_policies(self) -> list[ConfigValidationError]:
        errors: list[ConfigValidationError] = []

        valid_keys = set(self._config.table.primary_keys) | set(
            self._config.table.partition_cols
        )

        for rule in self._config.dq.key_nullability_rules:
            if rule.field not in valid_keys:
                errors.append(
                    ConfigValidationError(
                        field="dq.key_nullability",
                        expected="rule field must be present in primary_keys or partition_cols",
                        actual=rule.field,
                        rule="DQ key policy: key_nullability rules apply only to merge/partition keys",
                    )
                )

        return errors

    def _log_medallion_validation_result(
        self, errors: list[ConfigValidationError], runtime: RuntimeConfig
    ) -> None:
        if errors:
            self._logger.warning(
                "Medallion config validation found issues",
                extra={
                    "error_count": len(errors),
                    "errors": [
                        {"field": err.field, "rule": err.rule} for err in errors
                    ],
                    "strict_mode": runtime.strict_validation,
                },
            )
        else:
            self._logger.debug(
                "Medallion config validation passed",
                extra={"run_type": runtime.run_type.value},
            )
