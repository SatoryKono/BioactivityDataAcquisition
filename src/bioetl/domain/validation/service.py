"""Validation service orchestrating schema lookup and validators."""

from typing import Any, cast

from bioetl.domain.data import MutableTabularData, TabularData
from bioetl.domain.validation.contracts import (
    SchemaProviderABC,
    ValidationResult,
    ValidatorFactoryABC,
    schema_type,
)


class ValidationService:
    """Data validation service operating through domain interfaces."""

    def __init__(
        self,
        *,
        schema_provider: SchemaProviderABC,
        validator_factory: ValidatorFactoryABC,
    ) -> None:
        self._schema_provider = schema_provider
        self._validator_factory = validator_factory

    def get_schema(self, entity_name: str) -> schema_type:
        """Return schema for entity."""
        return self._schema_provider.get_schema(entity_name)

    def get_schema_columns(self, entity_name: str) -> list[str]:
        """Return ordered list of schema columns."""
        return self._schema_provider.get_schema_columns(entity_name)

    def validate(self, df: MutableTabularData, entity_name: str) -> MutableTabularData:
        """
        Validate DataFrame against schema using factory validator.

        Returns validated DataFrame (if validator modifies it),
        or original df if validation passes without transformations.

        Raises:
            ValueError: If validation fails.
        """
        schema = self._schema_provider.get_schema(entity_name)
        validator = self._validator_factory.create_validator(schema)

        validation_columns = self._extract_validator_columns(schema)
        # Use pandas-specific .loc if available, otherwise work with TabularData
        if validation_columns and hasattr(df, "loc"):
            df_for_validation = cast(Any, df).loc[:, validation_columns]
        else:
            df_for_validation = df

        result: ValidationResult = validator.validate(
            cast(TabularData, df_for_validation)
        )

        if not result.is_valid:
            raise ValueError(f"Validation failed for {entity_name}: {result.errors}")

        validated_df = cast(
            MutableTabularData,
            (
                result.validated_data
                if result.validated_data is not None
                else df_for_validation
            ),
        )

        output_columns = self._safe_schema_columns(entity_name)
        if output_columns:
            missing = [col for col in output_columns if col not in validated_df.columns]
            if missing:
                raise ValueError(
                    f"Validated dataframe for {entity_name} is missing columns: "
                    f"{missing}"
                )
            # Use pandas-specific .loc if available
            if hasattr(validated_df, "loc"):
                validated_df = cast(Any, validated_df).loc[:, output_columns]
            else:
                # Fallback: create new dataframe with selected columns
                # This is a simplified version - in practice, infrastructure
                # layer should handle column selection
                pass

        return validated_df

    def _safe_schema_columns(self, entity_name: str) -> list[str] | None:
        """
        Best-effort lookup of desired output column order.
        """

        try:
            return self._schema_provider.get_schema_columns(entity_name)
        except ValueError:
            return None

    @staticmethod
    def _extract_validator_columns(schema: schema_type) -> list[str] | None:
        """
        Returns the column order enforced by the underlying schema, if available.
        """

        schema_obj = schema
        if hasattr(schema, "to_schema"):
            schema_obj = schema.to_schema()

        columns = getattr(schema_obj, "columns", None)
        if columns is None or not hasattr(columns, "keys"):
            return None

        return list(columns.keys())
