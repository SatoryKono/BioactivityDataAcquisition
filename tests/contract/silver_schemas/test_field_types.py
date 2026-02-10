"""Silver Schema Type Safety Tests.

Tests ensuring correct Pandera dtype usage and type consistency.

Related:
    - RULES.md §2.2: Silver Layer Validation
    - TYPE-001: Public Function Annotations (MUST)
"""

from __future__ import annotations

import pytest
import pandera as pa

from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    extract_field_metadata,
)


@pytest.mark.contracts
@pytest.mark.no_api
class TestFieldTypes:
    """Tests for field type consistency and correctness."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_no_object_dtype_without_reason(self, schema_name: str) -> None:
        """Silver schemas SHOULD NOT use object dtype without justification.

        Object dtype is acceptable for:
        - JSON arrays (list[dict])
        - Complex nested structures
        - Provider-specific unstructured data

        For simple types, use:
        - str instead of object
        - int/float instead of object
        - datetime instead of object
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        object_fields = [
            (field, meta["description"])
            for field, meta in fields.items()
            if "object" in meta["dtype"].lower()
        ]

        # Whitelist: known complex fields
        allowed_object_fields = {
            "authors",  # list[dict] - publication authors
            "affiliations",  # list[dict]
            "references",  # list[dict]
            "funders",  # list[dict]
            "mesh_terms",  # list[dict]
            "protein_components",  # list[dict]
            "go_terms",  # list[dict]
            "cross_references",  # list[dict]
            "isoforms",  # list[dict]
            "reactions",  # list[dict]
        }

        unexpected_object_fields = [
            f for f, _ in object_fields if f not in allowed_object_fields
        ]

        if unexpected_object_fields:
            pytest.fail(
                f"{schema_name}: Unexpected object dtype fields:\n"
                + "\n".join(
                    f"  - {field}: {desc}"
                    for field, desc in object_fields
                    if field in unexpected_object_fields
                )
                + "\n\nUse specific types (str, int, float) instead of object."
            )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_id_fields_are_strings(self, schema_name: str) -> None:
        """ID fields MUST be string type, not int.

        Rationale:
        - External IDs may have prefixes (CHEMBL, PMC, etc.)
        - IDs may be non-numeric (DOI, ORCID)
        - String type prevents leading zero issues
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        id_fields = [
            (field, meta["dtype"])
            for field, meta in fields.items()
            if "_id" in field.lower()
            or field.lower().endswith("id")
            or field in {"pmid", "doi", "accession", "cid"}
        ]

        non_string_ids = [
            (field, dtype)
            for field, dtype in id_fields
            if "str" not in dtype.lower() and "object" not in dtype.lower()
        ]

        if non_string_ids:
            pytest.fail(
                f"{schema_name}: ID fields MUST be string type:\n"
                + "\n".join(f"  - {field}: {dtype}" for field, dtype in non_string_ids)
                + "\n\nUse Series[str] for ID fields."
            )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_numeric_fields_not_nullable_without_union(self, schema_name: str) -> None:
        """Nullable numeric fields MUST use Union[T, None] syntax.

        Correct:   Series[float] | None = pa.Field(nullable=True)
        Incorrect: Series[float] = pa.Field(nullable=True)

        Rationale: Pandas nullable int/float dtypes (Int64, Float64) require
        explicit typing for mypy compliance.
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        schema_model = schema_class.to_schema()

        issues = []
        for col_name, col_schema in schema_model.columns.items():
            dtype_str = str(col_schema.dtype)

            # Check if numeric and nullable
            is_numeric = any(
                t in dtype_str.lower() for t in ["int", "float", "decimal"]
            )
            is_nullable = col_schema.nullable

            if is_numeric and is_nullable:
                # Get field annotation to check Union syntax
                annotations = schema_class.__annotations__
                if col_name in annotations:
                    anno_str = str(annotations[col_name])
                    # Check if uses Union or | syntax
                    if "None" not in anno_str and "Optional" not in anno_str:
                        issues.append(
                            f"{col_name}: {dtype_str} (nullable=True but no Union)"
                        )

        if issues:
            pytest.fail(
                f"{schema_name}: Nullable numeric fields need Union[T, None]:\n"
                + "\n".join(f"  - {issue}" for issue in issues)
                + "\n\nUse: Series[float] | None = pa.Field(nullable=True)"
            )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_boolean_fields_use_bool_type(self, schema_name: str) -> None:
        """Boolean fields MUST use bool dtype, not int."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Look for fields that seem boolean but aren't
        likely_boolean_fields = [
            (field, meta["dtype"])
            for field, meta in fields.items()
            if any(
                keyword in field.lower()
                for keyword in ["is_", "has_", "flag", "_active", "_valid"]
            )
        ]

        non_bool_booleans = [
            (field, dtype)
            for field, dtype in likely_boolean_fields
            if "bool" not in dtype.lower()
        ]

        if non_bool_booleans:
            pytest.fail(
                f"{schema_name}: Boolean fields SHOULD use bool dtype:\n"
                + "\n".join(f"  - {field}: {dtype}" for field, dtype in non_bool_booleans)
                + "\n\nUse Series[bool] for boolean fields."
            )


@pytest.mark.contracts
@pytest.mark.no_api
class TestDatetimeFields:
    """Tests for datetime field consistency."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_timestamp_fields_use_datetime(self, schema_name: str) -> None:
        """Timestamp fields MUST use datetime64[ns] dtype."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        timestamp_fields = [
            (field, meta["dtype"])
            for field, meta in fields.items()
            if any(
                keyword in field.lower()
                for keyword in ["timestamp", "_date", "_time", "created", "modified"]
            )
        ]

        non_datetime_timestamps = [
            (field, dtype)
            for field, dtype in timestamp_fields
            if "datetime" not in dtype.lower() and "timestamp" not in dtype.lower()
        ]

        if non_datetime_timestamps:
            pytest.fail(
                f"{schema_name}: Timestamp fields MUST use datetime dtype:\n"
                + "\n".join(
                    f"  - {field}: {dtype}" for field, dtype in non_datetime_timestamps
                )
                + "\n\nUse Series[pd.Timestamp] or datetime64[ns]."
            )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_year_fields_are_int(self, schema_name: str) -> None:
        """Year fields SHOULD be int type, not string."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        year_fields = [
            (field, meta["dtype"])
            for field, meta in fields.items()
            if "year" in field.lower()
        ]

        string_years = [
            (field, dtype)
            for field, dtype in year_fields
            if "str" in dtype.lower() or "object" in dtype.lower()
        ]

        if string_years:
            pytest.fail(
                f"{schema_name}: Year fields SHOULD be int type:\n"
                + "\n".join(f"  - {field}: {dtype}" for field, dtype in string_years)
                + "\n\nUse Series[int] | None for year fields."
            )


@pytest.mark.contracts
@pytest.mark.no_api
class TestFieldCoercion:
    """Tests for field coercion settings."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_coerce_used_appropriately(self, schema_name: str) -> None:
        """Field coercion SHOULD be explicit and justified.

        coerce=True is appropriate for:
        - Int fields that may have NaN (nullable ints)
        - String fields that need normalization
        - Datetime parsing

        coerce=True SHOULD NOT be used to hide data quality issues.
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        schema_model = schema_class.to_schema()

        coerced_fields = []
        for col_name, col_schema in schema_model.columns.items():
            if col_schema.coerce:
                dtype_str = str(col_schema.dtype)
                coerced_fields.append((col_name, dtype_str, col_schema.nullable))

        # Whitelist: known coercion cases
        allowed_coercion_patterns = [
            "int",  # Nullable ints need coercion
            "float",  # Float with NaN
            "datetime",  # Date parsing
        ]

        suspicious_coercions = [
            f"{field} ({dtype})"
            for field, dtype, nullable in coerced_fields
            if not any(pattern in dtype.lower() for pattern in allowed_coercion_patterns)
        ]

        if suspicious_coercions:
            pytest.fail(
                f"{schema_name}: Suspicious coerce=True usage:\n"
                + "\n".join(f"  - {c}" for c in suspicious_coercions)
                + "\n\nVerify coercion is necessary and not hiding DQ issues."
            )
