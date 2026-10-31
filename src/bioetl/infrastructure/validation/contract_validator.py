"""Contract-based validators for Gold layer with DQ policy integration.

Extends the basic Pandera validators to support contract-based Data Quality
validation with rule-level outcomes and policy resolution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import (
    DQPolicyRef,
    DQRuleOutcome,
)
from bioetl.domain.types.dq_record_attribution import DQOutcomeChannel
from bioetl.infrastructure.validation.contract_outcome_channel import (
    attribute_contract_rules,
    build_outcome_channel,
    schema_error_field_name,
    schema_error_severity,
    schema_violations_from_error,
)
from bioetl.infrastructure.validation.pandera_validator import (
    PanderaGoldValidator,
    PanderaSilverValidator,
)

if TYPE_CHECKING:
    import pandas as pd
    import pandera.pandas as pa

    from bioetl.domain.config.dq import DQConfig


class ContractAwareGoldValidator(PanderaGoldValidator):
    """Gold validator with contract-based DQ policy integration.

    Extends PanderaGoldValidator to support:
    - Contract-based policy resolution
    - Rule-level DQ outcomes
    - Comprehensive provenance tracking
    - Policy hash verification
    """

    def __init__(
        self,
        schema: pa.DataFrameSchema | None = None,
        *,
        strict: bool = True,
        dq_config: DQConfig | None = None,
    ) -> None:
        """Initialize contract-aware Gold validator.

        Args:
            schema: Pandera DataFrameSchema for validation
            strict: If True, requires schema and enforces strict validation
            dq_config: DQ configuration for contract-based policy resolution
        """
        super().__init__(schema=schema, strict=strict)
        self._dq_config = dq_config
        self._policy_resolver = DQPolicyResolver(dq_config) if dq_config else None
        self._policy_ref = (
            self._policy_resolver.build_policy_ref() if self._policy_resolver else None
        )

    def rebind_schema(
        self, schema: pa.DataFrameSchema | None
    ) -> ContractAwareGoldValidator:
        """Return a clone bound to ``schema`` preserving DQ config."""
        return type(self)(
            schema=schema,
            strict=self._strict,
            dq_config=self._dq_config,
        )

    @property
    def policy_ref(self) -> DQPolicyRef | None:
        """Get the current policy reference."""
        return self._policy_ref

    def validate_with_outcomes(
        self,
        records: list[JsonDict],
    ) -> DQOutcomeChannel:
        """Validate records and return rule-level DQ outcomes.

        The channel unpacks as ``(is_valid, outcomes)``. Violations carry the
        record-attribution contract. Gold ``write_gold`` consumes this method.
        Batch ``validate()`` remains the fail-closed fallback.

        Args:
            records: List of record dictionaries to validate

        Returns:
            DQOutcomeChannel: validity, sorted outcomes, and attributed violations
        """
        if not self._policy_resolver:
            basic_result = super().validate(records)
            return DQOutcomeChannel(
                is_valid=basic_result.valid,
                outcomes=(),
                violations=(),
            )
        return build_outcome_channel(
            records=records,
            schema=self._schema,
            strict=self._strict,
            dq_config=self._dq_config,
            resolver=self._policy_resolver,
            config_path=self._get_config_path(),
            prepare_frame=self._prepare_df_for_validation,
        )

    def _prepare_df_for_validation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare DataFrame for validation with Gold-specific handling."""
        df_to_validate = df.copy()
        schema = self._schema
        if schema is None:
            return self._reorder_to_schema(df_to_validate)

        if not self._strict and hasattr(schema, "columns"):
            known = set(schema.columns)
            if schema.index:
                known.update(schema.index.names)
            df_to_validate = df_to_validate[
                [name for name in df_to_validate.columns if name in known]
            ]
        df_to_validate = self._reorder_to_schema(df_to_validate)
        df_to_validate = self._normalize_nullable_integer_columns(df_to_validate)
        return self._normalize_nullable_boolean_columns(df_to_validate)

    def validate_with_rule_inputs(
        self, records: list[JsonDict], rule_records: list[JsonDict]
    ) -> DQOutcomeChannel:
        """Validate projected schema bytes against the full normalized rule inputs."""
        if not self._policy_resolver:
            return self.validate_with_outcomes(records)
        return build_outcome_channel(
            records=records,
            schema=self._schema,
            strict=self._strict,
            dq_config=self._dq_config,
            resolver=self._policy_resolver,
            config_path=self._get_config_path(),
            prepare_frame=self._prepare_df_for_validation,
            rule_records=rule_records,
        )

    def _convert_schema_errors_to_outcomes(
        self, error: Exception
    ) -> list[DQRuleOutcome]:
        """Convert Pandera schema errors to DQ rule outcomes.

        Args:
            error: Exception containing schema validation errors

        Returns:
            List of DQRuleOutcome objects
        """
        policy_resolver = self._policy_resolver
        assert policy_resolver is not None
        violations = schema_violations_from_error(
            error,
            records=[],
            resolver=policy_resolver,
            config_path=self._get_config_path(),
        )
        return [violation.outcome for violation in violations]

    def _extract_schema_error_field_name(self, error: Exception) -> str | None:
        """Best-effort extraction of the affected field from a Pandera error."""
        return schema_error_field_name(error)

    def _apply_contract_validations(self, df: pd.DataFrame) -> list[DQRuleOutcome]:
        """Evaluate executable contract rules loaded from the bound DQConfig.

        The rule bundle is not loaded from ``policy_ref.contract_ref``.
        ``load_executable_contract_rules`` is the explicit owning-source step
        inside ``attribute_contract_rules``.

        Args:
            df: DataFrame being validated

        Returns:
            List of DQRuleOutcome objects from contract validations
        """
        records = [
            {str(key): value for key, value in row.items()}
            for row in df.astype(object)
            .where(df.notna(), None)
            .to_dict(orient="records")
        ]
        return [
            violation.outcome
            for violation in attribute_contract_rules(records, self._dq_config)
        ]

    def _determine_severity(self, schema_error: Exception) -> str:
        """Determine severity level for a schema error."""
        return schema_error_severity(schema_error)

    def _get_config_path(self) -> str | None:
        """Get configuration path for outcomes."""
        if self._policy_ref:
            return f"contracts/{self._policy_ref.contract_ref}/dq_rules.yaml"
        return None

    def get_policy_summary(self) -> JsonDict:
        """Get summary of effective DQ policy."""
        if self._policy_resolver:
            return self._policy_resolver.get_effective_policy_summary()
        return {"contract_ref": None, "policy_hash": None}


class ContractAwareSilverValidator(PanderaSilverValidator):
    """Silver validator with contract-based DQ policy integration."""

    def __init__(
        self,
        schema: pa.DataFrameSchema | None = None,
        *,
        strict: bool = True,
        dq_config: DQConfig | None = None,
    ) -> None:
        """Initialize contract-aware Silver validator (strict binding by default)."""
        super().__init__(schema=schema, strict=strict)
        self._dq_config = dq_config
        self._policy_resolver = DQPolicyResolver(dq_config) if dq_config else None
        self._policy_ref = (
            self._policy_resolver.build_policy_ref() if self._policy_resolver else None
        )

    @property
    def policy_ref(self) -> DQPolicyRef | None:
        """Get the current policy reference."""
        return self._policy_ref

    def validate_with_outcomes(
        self,
        records: list[JsonDict],
    ) -> DQOutcomeChannel:
        """Validate records and return rule-level DQ outcomes.

        The channel unpacks as ``(is_valid, outcomes)``. Silver production
        writes still use ``validate()``; this method is the outcome source
        shared with Gold.
        """
        if not self._policy_resolver:
            basic_result = self.validate(records)
            return DQOutcomeChannel(
                is_valid=basic_result.valid,
                outcomes=(),
                violations=(),
            )
        return build_outcome_channel(
            records=records,
            schema=self._schema,
            strict=self._strict,
            dq_config=self._dq_config,
            resolver=self._policy_resolver,
            config_path=self._silver_config_path(),
            prepare_frame=self._prepare_df_for_validation,
        )

    def _prepare_df_for_validation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare a Silver frame the same way ``validate()`` does."""
        if (
            not self._strict
            and self._schema is not None
            and hasattr(self._schema, "columns")
        ):
            prepared = self._reindex_non_strict(df)
        else:
            prepared = self._seed_missing_nullable_columns(df)
        prepared = self._normalize_nullable_integer_columns(prepared)
        prepared = self._normalize_nullable_boolean_columns(prepared)
        return self._reorder_to_schema(prepared)

    def _silver_config_path(self) -> str | None:
        if self._policy_ref:
            return f"contracts/{self._policy_ref.contract_ref}/dq_rules.yaml"
        return None

    def get_policy_summary(self) -> JsonDict:
        """Get summary of effective DQ policy."""
        if self._policy_resolver:
            return self._policy_resolver.get_effective_policy_summary()
        return {"contract_ref": None, "policy_hash": None}
