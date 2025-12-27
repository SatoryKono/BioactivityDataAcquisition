"""Tests for Deprecation Policy Enforcement.

Enforces the policy that deprecated fields (marked in Pandera schema)
must be removed after 14 days.

REQ-GOV-002: Field Deprecation Policy
- Fields marked deprecated must be removed within 14 days.
- Deprecation metadata format: {"deprecated": True, "deprecation_date": "YYYY-MM-DD"}
"""
from datetime import datetime, timedelta
import pandera as pa
from bioetl.infrastructure.schemas import gold as gold_schemas

def get_deprecated_fields(schema_cls: pa.DataFrameModel):
    """Extract deprecated fields from Pandera model."""
    deprecated = []
    # Convert to JSON schema to inspect metadata easily
    json_schema = schema_cls.to_json_schema()
    properties = json_schema.get("properties", {})

    # Note: Pandera currently puts metadata in the schema definition
    # For DataFrameModels, we might need to inspect the fields directly
    # if metadata isn't propagated to JSON schema 'description' or custom dict.
    # However, since we define schemas as Python classes, we can inspect __fields__.

    for name, field in schema_cls._collect_fields().items():
        # Access Check or Field metadata
        # Currently Pandera doesn't have a standard 'deprecated' flag in Field(),
        # but we assume it's passed via metadata={"deprecated": True, ...} or similar mechanism
        # if implemented.
        # Since we don't have a standardized metadata field in the codebase yet,
        # we will check for a custom property we might add later or use description parsing.

        # Strategy: Check description for [DEPRECATED: YYYY-MM-DD]
        description = field.description or ""
        if "[DEPRECATED:" in description:
            try:
                date_str = description.split("[DEPRECATED:")[1].split("]")[0].strip()
                deprecated.append((name, date_str))
            except IndexError:
                pass

    return deprecated

def test_no_expired_deprecated_fields():
    """Fail if any field is deprecated for > 14 days."""
    violations = []

    # Iterate over all Gold schemas
    for name, obj in vars(gold_schemas).items():
        if isinstance(obj, type) and issubclass(obj, pa.DataFrameModel) and obj is not pa.DataFrameModel:
            deprecated_fields = get_deprecated_fields(obj)

            for field_name, date_str in deprecated_fields:
                try:
                    dep_date = datetime.strptime(date_str, "%Y-%m-%d")
                    deadline = dep_date + timedelta(days=14)

                    if datetime.now() > deadline:
                        violations.append(
                            f"{name}.{field_name} expired on {deadline.date()} (Deprecation Date: {date_str})"
                        )
                except ValueError:
                    violations.append(f"{name}.{field_name} has invalid deprecation date format: {date_str}")

    assert not violations, "Found expired deprecated fields:\n" + "\n".join(violations)
