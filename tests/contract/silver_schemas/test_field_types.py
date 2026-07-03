"""Silver Schema Type Safety Tests.

Tests ensuring correct Pandera dtype usage and type consistency.

Related:
    - RULES.md §2.2: Silver Layer Validation
    - TYPE-001: Public Function Annotations (MUST)
"""

from __future__ import annotations

import pytest

from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    extract_field_metadata,
)

NON_GLOBAL_COERCE_SCHEMAS = tuple(
    sorted(
        schema_name
        for schema_name, schema_class in SILVER_SCHEMAS.items()
        if not getattr(schema_class.Config, "coerce", False)
    )
)


def _has_nullable_int_dtype_guard(annotation_repr: str, dtype_repr: str) -> bool:
    """Return True when nullable-int annotation has explicit pandas dtype guard."""
    if "int" not in dtype_repr.lower():
        return True

    has_nullable_union = "None" in annotation_repr or "Optional" in annotation_repr
    has_nullable_int_dtype = "Int64Dtype" in annotation_repr
    return has_nullable_union and has_nullable_int_dtype


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
            "alternative_id",  # Crossref list fields
            "content_domain_domains",  # Crossref list fields
            "component_accessions",  # ChEMBL Target list fields
            "component_descriptions",
            "component_ids",
            "component_relationships",
            "component_types",
            "protein_classification_ids",
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

        numeric_id_fields = {
            "assay_param_id",
            "assay_taxonomy_id",
            "target_taxonomy_id",
            "taxonomy_id",
            "cell_source_taxonomy_id",
            "component_id",
            "component_ids",
            "corpus_id",  # Semantic Scholar internal corpus ID
            "doc_1",
            "doc_2",
            "original_activity_id",
            "parent_id",  # Protein class parent ID - internal hierarchy
            "protein_class_id",
            "protein_classification_id",
            "protein_classification_ids",
            "primary_component_id",
            "record_id",
            "sequence_length",
            "sequence_mass",
            "sim_id",
            "src_id",
            "toid",  # Target organism ID - ChEMBL numeric taxonomy ID
            "variant_taxonomy_id",
        }
        id_fields = [
            (field, meta["dtype"])
            for field, meta in fields.items()
            if (
                "_id" in field.lower()
                or field.lower().endswith("id")
                or field in {"pmid", "doi", "accession", "molecule_id"}
            )
            and field not in numeric_id_fields
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

        allowed_int_flags = {
            "black_box_warning",
            "downgraded",
            "manual_curation_flag",
            "potential_duplicate",
            "standard_flag",
        }
        # Fields with boolean-like keywords but are NOT booleans
        non_boolean_fields = {
            "data_validity_comment",  # Text field describing validity
            "data_validity_description",  # Text description
            "hierarchy_active_chembl_id",  # ID field, not boolean
            "flag",  # Text field in uniprot_protein
        }
        non_bool_booleans = []
        for field, dtype in likely_boolean_fields:
            if "bool" in dtype.lower():
                continue
            if field in allowed_int_flags or field in non_boolean_fields:
                continue
            checks = fields.get(field, {}).get("checks", [])
            has_flag_isin = any(check.get("type") == "isin" for check in checks)
            if "int" in dtype.lower() and has_flag_isin:
                continue
            non_bool_booleans.append((field, dtype))

        if non_bool_booleans:
            pytest.fail(
                f"{schema_name}: Boolean fields SHOULD use bool dtype:\n"
                + "\n".join(
                    f"  - {field}: {dtype}" for field, dtype in non_bool_booleans
                )
                + "\n\nUse Series[bool] for boolean fields."
            )

    @pytest.mark.parametrize(
        "schema_name,guard_fields",
        [
            ("chembl_activity", {"manual_curation_flag"}),
            (
                "chembl_assay",
                {"assay_taxonomy_id", "src_id", "variant_taxonomy_id"},
            ),
            ("chembl_cell_line", {"cell_source_taxonomy_id"}),
            ("chembl_publication", {"src_id"}),
            ("chembl_target", {"taxonomy_id"}),
            ("pubmed_publication", {"pub_month", "pub_day", "author_count"}),
            (
                "semanticscholar_publication",
                {"corpus_id", "influential_citation_count"},
            ),
            (
                "chembl_molecule",
                {
                    "hba_count",
                    "hbd_count",
                    "rotatable_bond_count",
                    "ro5_violation_count",
                    "heavy_atom_count",
                    "aromatic_ring_count",
                },
            ),
        ],
    )
    def test_nullable_int_fields_have_explicit_dtype_guard(
        self, schema_name: str, guard_fields: set[str]
    ) -> None:
        """Critical nullable-int fields MUST keep explicit pandas Int64 dtype guard."""
        schema_class = SILVER_SCHEMAS[schema_name]
        schema_model = schema_class.to_schema()
        annotations = schema_class.__annotations__

        violations: list[str] = []
        for field_name in sorted(guard_fields):
            col_schema = schema_model.columns[field_name]
            dtype_repr = str(col_schema.dtype)
            annotation_repr = str(annotations.get(field_name, ""))
            if not _has_nullable_int_dtype_guard(annotation_repr, dtype_repr):
                violations.append(
                    f"{field_name}: dtype={dtype_repr}, annotation={annotation_repr}"
                )

        if violations:
            pytest.fail(
                f"{schema_name}: nullable-int fields must have explicit dtype guard:\n"
                + "\n".join(f"  - {item}" for item in violations)
                + "\n\nUse: Series[pd.Int64Dtype] | None = pa.Field(nullable=True)"
            )


@pytest.mark.contracts
@pytest.mark.no_api
class TestNullableIntGuardRegression:
    """Regression tests for nullable-int dtype guard helper."""

    @pytest.mark.parametrize(
        "annotation_repr,dtype_repr,expected",
        [
            ("Series[pd.Int64Dtype] | None", "int64", True),
            ("Optional[Series[pd.Int64Dtype]]", "int64", True),
            ("Series[int] | None", "int64", False),
            ("Series[pd.Int64Dtype]", "int64", False),
            ("Series[str] | None", "string", True),
        ],
    )
    def test_has_nullable_int_dtype_guard(
        self, annotation_repr: str, dtype_repr: str, expected: bool
    ) -> None:
        """Guard helper must detect nullable-int annotations reliably."""
        assert _has_nullable_int_dtype_guard(annotation_repr, dtype_repr) is expected


@pytest.mark.contracts
@pytest.mark.no_api
class TestDatetimeFields:
    """Tests for datetime field consistency."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_timestamp_fields_use_datetime(self, schema_name: str) -> None:
        """Timestamp fields MUST use datetime64[ns] dtype.

        Exception: Calendar date fields (date type) are allowed when the source
        provides only dates without time components.
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Whitelist: fields that are truly calendar dates (no time component)
        date_only_fields = {
            "sequence_modified",  # UniProt sequence modification date
            "entry_created",  # UniProt entry creation date
            "entry_modified",  # UniProt entry modification date
        }

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
            if (
                "datetime" not in dtype.lower()
                and "timestamp" not in dtype.lower()
                and "str" not in dtype.lower()
                and field not in date_only_fields  # Exclude date-only fields
            )
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

    @pytest.mark.parametrize("schema_name", NON_GLOBAL_COERCE_SCHEMAS)
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
            if not any(
                pattern in dtype.lower() for pattern in allowed_coercion_patterns
            )
        ]

        if suspicious_coercions:
            pytest.fail(
                f"{schema_name}: Suspicious coerce=True usage:\n"
                + "\n".join(f"  - {c}" for c in suspicious_coercions)
                + "\n\nVerify coercion is necessary and not hiding DQ issues."
            )
