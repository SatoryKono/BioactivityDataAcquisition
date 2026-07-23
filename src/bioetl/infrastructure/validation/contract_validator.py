"""Contract-based validators for Gold layer with DQ policy integration.

Extends the basic Pandera validators to support contract-based Data Quality
validation with rule-level outcomes and policy resolution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQPolicyRef,
    DQRuleOutcome,
    DQViolationKind,
)
from bioetl.infrastructure.validation.pandera_validator import (
    PanderaGoldValidator,
    PanderaSilverValidator,
)

if TYPE_CHECKING:
    import pandas as pd
    import pandera as pa


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

    @property
    def policy_ref(self) -> DQPolicyRef | None:
        """Get the current policy reference."""
        return self._policy_ref

    def validate_with_outcomes(
        self,
        records: list[JsonDict],
    ) -> tuple[bool, list[DQRuleOutcome]]:
        """Validate records and return rule-level DQ outcomes.

        Args:
            records: List of record dictionaries to validate

        Returns:
            tuple: (is_valid, rule_outcomes) where is_valid indicates overall validity
                   and rule_outcomes contains individual rule evaluation results
        """
        if not self._policy_resolver:
            # Fallback to basic validation if no DQ config provided
            basic_result = super().validate(records)
            return basic_result.valid, []

        if not records:
            return True, []

        if not self._schema:
            if self._strict:
                outcome = self._create_schema_missing_outcome()
                return False, [outcome]
            return True, []

        import pandas as pd

        df = pd.DataFrame(records)
        return self._validate_with_schema_and_policies(df)

    def _validate_with_schema_and_policies(
        self, df: pd.DataFrame
    ) -> tuple[bool, list[DQRuleOutcome]]:
        """Validate DataFrame with schema and apply DQ policies.

        Args:
            df: Pandas DataFrame to validate

        Returns:
            tuple: (is_valid, rule_outcomes)
        """
        assert self._schema is not None
        assert self._policy_resolver is not None

        from pandera.errors import SchemaError, SchemaErrors

        rule_outcomes = []
        is_valid = True

        try:
            # Apply Gold-specific validation logic
            df_to_validate = self._prepare_df_for_validation(df)
            self._schema.validate(df_to_validate, lazy=True)

        except (SchemaError, SchemaErrors, KeyError, TypeError, ValueError) as e:
            is_valid = False
            # Convert schema errors to DQ rule outcomes
            error_outcomes = self._convert_schema_errors_to_outcomes(e)
            rule_outcomes.extend(error_outcomes)

        # Add any contract-specific validation outcomes
        contract_outcomes = self._apply_contract_validations(df)
        rule_outcomes.extend(contract_outcomes)

        # Update overall validity based on rule outcomes
        if rule_outcomes:
            has_failures = any(
                outcome.disposition in (DQDisposition.QUARANTINE, DQDisposition.FAIL)
                for outcome in rule_outcomes
            )
            is_valid = is_valid and not has_failures

        return is_valid, rule_outcomes

    def _prepare_df_for_validation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare DataFrame for validation with Gold-specific handling."""
        df_to_validate = df.copy()
        schema = self._schema
        if schema is None:
            return self._reorder_to_schema(df_to_validate)

        # Handle missing nullable columns
        if hasattr(schema, "columns"):
            missing = [name for name in schema.columns if name not in df.columns]
            for name in missing:
                column = schema.columns[name]
                if getattr(column, "nullable", False):
                    df_to_validate[name] = None

        # Reorder to match schema
        return self._reorder_to_schema(df_to_validate)

    def _convert_schema_errors_to_outcomes(
        self, error: Exception
    ) -> list[DQRuleOutcome]:
        """Convert Pandera schema errors to DQ rule outcomes.

        Args:
            error: Exception containing schema validation errors

        Returns:
            List of DQRuleOutcome objects
        """
        from pandera.errors import SchemaErrors

        outcomes: list[DQRuleOutcome] = []
        policy_resolver = self._policy_resolver
        assert policy_resolver is not None

        if isinstance(error, SchemaErrors):
            # Pandera exposes the collected lazy-validation items via
            # ``schema_errors`` on current versions.
            for schema_error in error.schema_errors:
                field_name = self._extract_schema_error_field_name(schema_error)
                outcome = policy_resolver.create_rule_outcome(
                    rule_id=f"schema.{field_name or 'unknown'}",
                    violation_kind=DQViolationKind.SCHEMA_VIOLATION,
                    severity=self._determine_severity(schema_error),
                    affected_fields=[field_name] if field_name else None,
                    config_path=self._get_config_path(),
                    threshold_breach=False,
                    anomaly_signal=False,
                )
                outcomes.append(outcome)
        else:
            # Handle single error
            field_name = self._extract_schema_error_field_name(error)
            outcome = policy_resolver.create_rule_outcome(
                rule_id=f"schema.{field_name or 'unknown'}",
                violation_kind=DQViolationKind.SCHEMA_VIOLATION,
                severity="high",  # Default high severity for schema errors
                affected_fields=[field_name] if field_name else None,
                config_path=self._get_config_path(),
                threshold_breach=False,
                anomaly_signal=False,
            )
            outcomes.append(outcome)

        return outcomes

    def _extract_schema_error_field_name(self, error: Exception) -> str | None:
        """Best-effort extraction of the affected field from a Pandera error."""
        column_name = getattr(error, "column_name", None)
        if isinstance(column_name, str) and column_name:
            return column_name

        failure_cases = getattr(error, "failure_cases", None)
        if isinstance(failure_cases, str) and failure_cases:
            return failure_cases

        loc = getattr(error, "loc", None)
        if loc:
            if isinstance(loc, str):
                return loc
            return ".".join(str(item) for item in loc)

        message = str(error)
        marker = "column '"
        if marker in message:
            _, _, tail = message.partition(marker)
            column_name, _, _ = tail.partition("'")
            if column_name:
                return column_name
        return None

    def _apply_contract_validations(self, df: pd.DataFrame) -> list[DQRuleOutcome]:
        """Apply additional contract-specific validations.

        Args:
            df: DataFrame being validated

        Returns:
            List of DQRuleOutcome objects from contract validations
        """
        del df
        outcomes: list[DQRuleOutcome] = []

        # Example: Check for required fields specified in contract
        if self._policy_ref and "gold" in self._policy_ref.contract_ref.lower():
            # Add Gold-specific contract validations here
            # For now, this is a placeholder for future contract-specific rules
            pass

        return outcomes

    def _create_schema_missing_outcome(self) -> DQRuleOutcome:
        """Create outcome for missing schema in strict mode."""
        assert self._policy_resolver is not None

        return self._policy_resolver.create_rule_outcome(
            rule_id="schema.missing",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            affected_fields=None,
            config_path=self._get_config_path(),
            threshold_breach=False,
            anomaly_signal=False,
        )

    def _determine_severity(self, schema_error: Exception) -> str:
        """Determine severity level for a schema error."""
        if "null" in str(schema_error).lower():
            return "high"  # Null violations are severe
        elif "type" in str(schema_error).lower():
            return "high"  # Type mismatches are severe
        elif "regex" in str(schema_error).lower():
            return "medium"  # Regex failures are medium severity
        elif any(
            marker in str(schema_error).lower() for marker in ("range", "min", "max")
        ):
            return "medium"  # Range violations are medium severity
        else:
            return "high"  # Default to high severity

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
    """Silver validator with contract-based DQ policy integration.

    Placeholder for future Silver contract validation.
    Currently delegates to basic Silver validator.
    """

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
    ) -> tuple[bool, list[DQRuleOutcome]]:
        """Validate records and return rule-level DQ outcomes."""
        # Basic validation
        basic_result = self.validate(records)

        # For now, return basic result with empty outcomes
        # Future implementation will add Silver-specific contract validation
        return basic_result.valid, []

    def get_policy_summary(self) -> JsonDict:
        """Get summary of effective DQ policy."""
        if self._policy_resolver:
            return self._policy_resolver.get_effective_policy_summary()
        return {"contract_ref": None, "policy_hash": None}
