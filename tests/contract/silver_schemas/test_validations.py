"""Silver Schema Validation Rules Tests.

Tests ensuring consistent validation patterns across schemas.

Related:
    - RULES.md §2.2: Silver Layer Validation
    - ADR-027: DQ Rules Externalization
"""

from __future__ import annotations

import pandera as pa
import pytest
from bioetl.domain.validation import MAX_PUBLICATION_YEAR, MIN_PUBLICATION_YEAR
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    extract_field_metadata,
)

CHEMBL_SCHEMAS = tuple(
    sorted(
        schema_name
        for schema_name in SILVER_SCHEMAS
        if schema_name.startswith("chembl_")
    )
)
STRING_PMID_SCHEMAS = tuple(
    sorted(
        schema_name
        for schema_name, schema_class in SILVER_SCHEMAS.items()
        if "pmid" in (fields := extract_field_metadata(schema_class))
        and "str" in fields["pmid"]["dtype"].lower()
    )
)
PCHEMBL_VALUE_SCHEMAS = tuple(
    sorted(
        schema_name
        for schema_name, schema_class in SILVER_SCHEMAS.items()
        if "pchembl_value" in extract_field_metadata(schema_class)
    )
)


@pytest.mark.contracts
@pytest.mark.no_api
class TestRegexValidations:
    """Tests for regex pattern validations."""

    @pytest.mark.parametrize("schema_name", CHEMBL_SCHEMAS)
    def test_chembl_id_pattern_consistent(self, schema_name: str) -> None:
        """ChEMBL ID fields MUST use CHEMBL_ID_PATTERN.

        Pattern: ^CHEMBL[0-9]+$
        Examples: CHEMBL25, CHEMBL1234567
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        chembl_id_fields = [
            field
            for field, meta in fields.items()
            if field.endswith("_chembl_id")
            and not field.startswith("_")
            and (
                meta.get("required")
                or not meta.get("nullable")
                or "foreign key" in meta.get("description", "").lower()
                or "primary key" in meta.get("description", "").lower()
            )
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

    @pytest.mark.parametrize("schema_name", STRING_PMID_SCHEMAS)
    def test_pmid_pattern_if_present(self, schema_name: str) -> None:
        """PMID fields MUST have numeric validation.

        Pattern: ^[1-9][0-9]*$ (positive integers, no leading zeros)
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        checks = fields["pmid"].get("checks", [])
        has_regex = any("regex" in c for c in checks)

        if not has_regex:
            pytest.fail(
                f"{schema_name}.pmid: Missing regex validation.\n"
                "Use: str_matches=r'^[1-9][0-9]*$'"
            )


@pytest.mark.contracts
@pytest.mark.no_api
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

    @pytest.mark.parametrize("schema_name", PCHEMBL_VALUE_SCHEMAS)
    def test_pchembl_value_range(self, schema_name: str) -> None:
        """pChEMBL value MUST be in range 0-14.

        pChEMBL = -log10(molar IC50, XC50, EC50, etc.)
        Typical range: 3-12, theoretical max: ~14
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        checks = fields["pchembl_value"].get("checks", [])
        check_types = {c.get("type") for c in checks}

        assert "ge" in check_types or "gt" in check_types, (
            "pchembl_value: Missing lower bound (ge=0)"
        )
        assert "le" in check_types or "lt" in check_types, (
            "pchembl_value: Missing upper bound (le=14)"
        )


@pytest.mark.contracts
@pytest.mark.no_api
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
                field
                for field in fields.keys()
                if field_pattern in field.lower()
                and not field.lower().endswith("_version")
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
@pytest.mark.no_api
class TestNullabilityRules:
    """Tests for nullable field consistency."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_primary_keys_not_nullable(self, schema_name: str) -> None:
        """Configured technical and business primary keys MUST NOT be nullable."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)
        yaml_config = load_pipeline_config(schema_name)
        primary_keys = {
            yaml_config.technical_primary_key,
            *yaml_config.business_primary_keys,
        }

        nullable_primary_keys = [
            field for field in sorted(primary_keys) if fields[field]["nullable"]
        ]
        assert not nullable_primary_keys, (
            f"{schema_name}: configured primary keys MUST NOT be nullable: "
            f"{nullable_primary_keys}"
        )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_metadata_fields_not_nullable(self, schema_name: str) -> None:
        """ETL metadata fields MUST NOT be nullable."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        metadata_fields = ["_ingestion_ts", "_run_id", "content_hash"]

        nullable_metadata = [
            field for field in metadata_fields if fields.get(field, {}).get("nullable")
        ]

        if nullable_metadata:
            pytest.fail(
                f"{schema_name}: Metadata fields MUST NOT be nullable:\n"
                + "\n".join(f"  - {field}" for field in sorted(nullable_metadata))
            )


@pytest.mark.contracts
@pytest.mark.no_api
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

    @pytest.mark.parametrize(
        "schema_name,fixture_name",
        [
            ("chembl_publication", "minimal_chembl_publication_df"),
            ("pubmed_publication", "minimal_pubmed_publication_df"),
            ("crossref_publication", "minimal_crossref_publication_df"),
            ("openalex_publication", "minimal_openalex_publication_df"),
            (
                "semanticscholar_publication",
                "minimal_semanticscholar_publication_df",
            ),
        ],
    )
    def test_publication_year_range_consistent(
        self,
        schema_name: str,
        fixture_name: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Publication year bounds MUST match the shared domain contract."""
        schema_class = SILVER_SCHEMAS[schema_name]
        df = request.getfixturevalue(fixture_name).copy()

        df["publication_year"] = MIN_PUBLICATION_YEAR
        schema_class.validate(df)
        df["publication_year"] = MAX_PUBLICATION_YEAR
        schema_class.validate(df)

        below_min = df.copy()
        below_min["publication_year"] = MIN_PUBLICATION_YEAR - 1
        with pytest.raises(pa.errors.SchemaError, match="publication_year"):
            schema_class.validate(below_min)

        above_max = df.copy()
        above_max["publication_year"] = MAX_PUBLICATION_YEAR + 1
        with pytest.raises(pa.errors.SchemaError, match="publication_year"):
            schema_class.validate(above_max)
