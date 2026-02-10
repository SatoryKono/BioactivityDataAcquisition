"""Silver Schema Validation Rules Tests.

Tests ensuring consistent validation patterns across schemas.

Related:
    - RULES.md §2.2: Silver Layer Validation
    - ADR-027: DQ Rules Externalization
"""

from __future__ import annotations

import pytest

from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    extract_field_metadata,
)


@pytest.mark.contracts
class TestRegexValidations:
    """Tests for regex pattern validations."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_chembl_id_pattern_consistent(self, schema_name: str) -> None:
        """ChEMBL ID fields MUST use CHEMBL_ID_PATTERN.

        Pattern: ^CHEMBL[0-9]+$
        Examples: CHEMBL25, CHEMBL1234567
        """
        if not schema_name.startswith("chembl_"):
            pytest.skip(f"{schema_name} is not a ChEMBL schema")

        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        chembl_id_fields = [
            field for field in fields.keys() if field.endswith("_chembl_id")
        ]

        for field in chembl_id_fields:
            checks = fields[field].get("checks", [])
            regex_checks = [c for c in checks if "regex" in c]

            if not regex_checks:
                pytest.fail(
                    f"{schema_name}.{field}: Missing regex validation.\n"
                    "Use: str_matches=CHEMBL_ID_PATTERN"
                )

            # Verify pattern starts with CHEMBL
            for check in regex_checks:
                regex = check.get("regex", "")
                if "CHEMBL" not in regex.upper():
                    pytest.fail(
                        f"{schema_name}.{field}: Regex pattern doesn't match CHEMBL format.\n"
                        f"Got: {regex}\n"
                        "Expected: ^CHEMBL[0-9]+$"
                    )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_pmid_pattern_if_present(self, schema_name: str) -> None:
        """PMID fields MUST have numeric validation.

        Pattern: ^[1-9][0-9]*$ (positive integers, no leading zeros)
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        if "pmid" not in fields:
            pytest.skip(f"{schema_name} has no pmid field")

        checks = fields["pmid"].get("checks", [])
        has_regex = any("regex" in c for c in checks)

        if not has_regex:
            pytest.fail(
                f"{schema_name}.pmid: Missing regex validation.\n"
                "Use: str_matches=r'^[1-9][0-9]*$'"
            )


@pytest.mark.contracts
class TestRangeValidations:
    """Tests for numeric range validations."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_year_fields_have_range_check(self, schema_name: str) -> None:
        """Year fields SHOULD have min/max validation.

        Typical range: 1500-2100 (MIN_PUBLICATION_YEAR - 2100)
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        year_fields = [field for field in fields.keys() if "year" in field.lower()]

        for field in year_fields:
            checks = fields[field].get("checks", [])
            has_range = any(c.get("type") in {"ge", "le", "gt", "lt"} for c in checks)

            if not has_range:
                pytest.fail(
                    f"{schema_name}.{field}: Missing range validation.\n"
                    "Use: pa.Field(ge=1500, le=2100) or similar"
                )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_percentage_fields_bounded(self, schema_name: str) -> None:
        """Percentage fields MUST be bounded 0-100."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        percentage_fields = [
            field
            for field in fields.keys()
            if "percent" in field.lower() or "pct" in field.lower()
        ]

        for field in percentage_fields:
            checks = fields[field].get("checks", [])
            check_types = {c.get("type") for c in checks}

            # Should have both lower and upper bound
            if "ge" not in check_types and "gt" not in check_types:
                pytest.fail(
                    f"{schema_name}.{field}: Percentage missing lower bound (ge=0)."
                )

            if "le" not in check_types and "lt" not in check_types:
                pytest.fail(
                    f"{schema_name}.{field}: Percentage missing upper bound (le=100)."
                )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_pchembl_value_range(self, schema_name: str) -> None:
        """pChEMBL value MUST be in range 0-14.

        pChEMBL = -log10(molar IC50, XC50, EC50, etc.)
        Typical range: 3-12, theoretical max: ~14
        """
        if schema_name != "chembl_activity":
            pytest.skip(f"{schema_name} has no pchembl_value")

        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        if "pchembl_value" not in fields:
            pytest.skip("pchembl_value field not found")

        checks = fields["pchembl_value"].get("checks", [])
        check_types = {c.get("type") for c in checks}

        assert "ge" in check_types or "gt" in check_types, (
            "pchembl_value: Missing lower bound (ge=0)"
        )
        assert "le" in check_types or "lt" in check_types, (
            "pchembl_value: Missing upper bound (le=14)"
        )


@pytest.mark.contracts
class TestEnumValidations:
    """Tests for enum (isin) validations."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_enum_fields_have_isin_check(self, schema_name: str) -> None:
        """Fields with limited value sets SHOULD use isin validation."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Known enum field patterns
        enum_field_patterns = [
            "standard_relation",  # =, <, >, <=, >=
            "standard_type",  # IC50, Ki, EC50, etc.
            "organism_type",  # SINGLE PROTEIN, PROTEIN COMPLEX
            "target_type",  # SINGLE PROTEIN, etc.
            "pref_name_type",  # INN, USAN, BAN
            "data_validity_comment",  # Outside typical range, etc.
        ]

        for field_pattern in enum_field_patterns:
            matching_fields = [
                field for field in fields.keys() if field_pattern in field.lower()
            ]

            for field in matching_fields:
                checks = fields[field].get("checks", [])
                has_isin = any(c.get("type") == "isin" for c in checks)

                if not has_isin:
                    pytest.fail(
                        f"{schema_name}.{field}: Enum field missing isin validation.\n"
                        "Define allowed values via pa.Field(isin=[...])"
                    )


@pytest.mark.contracts
class TestNullabilityRules:
    """Tests for nullable field consistency."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_primary_keys_not_nullable(self, schema_name: str) -> None:
        """Primary key fields MUST NOT be nullable."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Identify likely primary keys
        pk_patterns = [
            "_id",
            "_chembl_id",
            "cid",
            "accession",
            "pmid",
            "doi",
            "openalex_id",
            "paper_id",
        ]

        pk_candidates = [
            field
            for field in fields.keys()
            if any(field.endswith(pattern) for pattern in pk_patterns)
            and not field.startswith("_")  # Skip metadata fields
        ]

        nullable_pks = [
            field for field in pk_candidates if fields[field]["nullable"]
        ]

        if nullable_pks:
            pytest.fail(
                f"{schema_name}: Primary key fields MUST NOT be nullable:\n"
                + "\n".join(f"  - {field}" for field in sorted(nullable_pks))
            )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_metadata_fields_not_nullable(self, schema_name: str) -> None:
        """ETL metadata fields MUST NOT be nullable."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        metadata_fields = ["_ingestion_timestamp", "_run_id", "_content_hash"]

        nullable_metadata = [
            field for field in metadata_fields if fields.get(field, {}).get("nullable")
        ]

        if nullable_metadata:
            pytest.fail(
                f"{schema_name}: Metadata fields MUST NOT be nullable:\n"
                + "\n".join(f"  - {field}" for field in sorted(nullable_metadata))
            )


@pytest.mark.contracts
class TestValidationConsistency:
    """Tests for validation consistency across providers."""

    def test_publication_doi_validation_consistent(self) -> None:
        """DOI validation MUST be consistent across all publication schemas."""
        publication_schemas = {
            name: schema
            for name, schema in SILVER_SCHEMAS.items()
            if "publication" in name
        }

        doi_patterns = {}
        for schema_name, schema_class in publication_schemas.items():
            fields = extract_field_metadata(schema_class)

            if "doi" not in fields:
                continue

            checks = fields["doi"].get("checks", [])
            regex_checks = [c.get("regex") for c in checks if c.get("regex")]

            if regex_checks:
                doi_patterns[schema_name] = regex_checks[0]

        # All DOI patterns should be identical
        if doi_patterns:
            unique_patterns = set(doi_patterns.values())
            if len(unique_patterns) > 1:
                pytest.fail(
                    "DOI validation patterns are inconsistent across publication schemas:\n"
                    + "\n".join(
                        f"  {name}: {pattern}" for name, pattern in doi_patterns.items()
                    )
                    + "\n\nUse consistent DOI_PATTERN from domain/schemas/constants.py"
                )

    def test_publication_year_range_consistent(self) -> None:
        """Publication year range MUST be consistent across providers."""
        publication_schemas = {
            name: schema
            for name, schema in SILVER_SCHEMAS.items()
            if "publication" in name
        }

        year_ranges = {}
        for schema_name, schema_class in publication_schemas.items():
            fields = extract_field_metadata(schema_class)

            year_field = None
            for field in fields.keys():
                if "year" in field.lower():
                    year_field = field
                    break

            if not year_field:
                continue

            checks = fields[year_field].get("checks", [])
            ranges = {c.get("type"): c for c in checks if c.get("type") in {"ge", "le"}}

            if ranges:
                year_ranges[schema_name] = ranges

        # Check consistency
        if len(year_ranges) > 1:
            ge_values = {
                name: r.get("ge")
                for name, ranges in year_ranges.items()
                if "ge" in ranges
            }
            le_values = {
                name: r.get("le")
                for name, ranges in year_ranges.items()
                if "le" in ranges
            }

            if len(set(ge_values.values())) > 1:
                pytest.fail(
                    "Publication year minimum is inconsistent:\n"
                    + "\n".join(f"  {name}: {val}" for name, val in ge_values.items())
                    + "\n\nUse MIN_PUBLICATION_YEAR constant (currently 1500)"
                )

            if len(set(le_values.values())) > 1:
                pytest.fail(
                    "Publication year maximum is inconsistent:\n"
                    + "\n".join(f"  {name}: {val}" for name, val in le_values.items())
                )
