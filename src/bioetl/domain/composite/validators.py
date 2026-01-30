from typing import Any

from bioetl.domain.composite.config import DataSchemaConfig
from bioetl.domain.exceptions.validation import ValidationError


def validate_schema_compatibility(config: DataSchemaConfig) -> None:
    """Validates schema compatibility."""
    if not config.bronze_schema and not config.silver_schema:
        raise ValidationError("At least one schema must be provided")


def validate_field_mapping(config: DataSchemaConfig) -> None:
    """Validates field mapping configuration."""
    if config.field_mapping and not config.silver_schema:
        raise ValidationError("Field mapping requires silver schema")


def validate_transformations(config: DataSchemaConfig) -> None:
    """Validates transformation rules."""
    if config.transformations:
        _validate_transformation_rules(config.transformations)


def _validate_transformation_rules(rules: dict[str, Any]) -> None:
    """Validates individual transformation rules."""
    for field, rule in rules.items():
        if not isinstance(rule, (str, dict)):
            raise ValidationError(f"Invalid transformation rule for field {field}")
