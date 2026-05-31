"""Silver Schema Naming Convention Tests.

Tests ensuring consistent field naming across schemas.

Related:
    - RULES.md NAME-003: Module Naming (MUST)
    - ADR-024: Entity Naming Unification
    - docs/glossary.md: Ubiquitous Language
"""

from __future__ import annotations

import re

import pytest

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


@pytest.mark.contracts
@pytest.mark.no_api
class TestFieldNaming:
    """Tests for field naming consistency."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_field_names_are_snake_case(self, schema_name: str) -> None:
        """All field names MUST use snake_case."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Regex: snake_case pattern (lowercase, underscores, digits)
        snake_case_pattern = re.compile(r"^[a-z0-9_]+$")

        non_snake_case = [
            field for field in fields.keys() if not snake_case_pattern.match(field)
        ]

        if non_snake_case:
            pytest.fail(
                f"{schema_name}: Fields not in snake_case:\n"
                + "\n".join(f"  - {field}" for field in sorted(non_snake_case))
                + "\n\nUse lowercase with underscores only."
            )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_no_camelcase_fields(self, schema_name: str) -> None:
        """Field names MUST NOT use camelCase or PascalCase."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Detect camelCase (contains uppercase letter not at start)
        camel_case_fields = [
            field for field in fields.keys() if any(c.isupper() for c in field[1:])
        ]

        if camel_case_fields:
            pytest.fail(
                f"{schema_name}: camelCase fields detected:\n"
                + "\n".join(f"  - {field}" for field in sorted(camel_case_fields))
                + "\n\nConvert to snake_case."
            )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_no_abbreviations_without_glossary(self, schema_name: str) -> None:
        """Field abbreviations SHOULD be documented in glossary.md.

        Allowed abbreviations (from glossary.md):
        - id: identifier
        - url: uniform resource locator
        - doi: digital object identifier
        - pmid: PubMed identifier
        - isbn: international standard book number
        - issn: international standard serial number
        - ec: enzyme commission
        - go: gene ontology
        - hgnc: HUGO Gene Nomenclature Committee
        - pdb: protein data bank
        - molecule_id: compound identifier (PubChem)
        - bao: BioAssay Ontology
        - uo: Units of Measurement Ontology
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Known abbreviations from glossary.md
        known_abbreviations = {
            "id",
            "url",
            "uri",
            "doi",
            "pmid",
            "pmmolecule_id",
            "isbn",
            "issn",
            "ec",
            "go",
            "hgnc",
            "pdb",
            "molecule_id",
            "bao",
            "uo",
            "sdf",
            "smiles",
            "inchi",
            "inchi_key",
            "max",
            "min",
            "avg",
            "std",
            "src",
            "dq",  # data quality
            "pct",  # percent
            "pmc",
            "rtb",
            "rmsd",
            "tldr",
            "mw",
            "ts",  # timestamp
            "h",  # hydrogen (chemistry context)
            "x",  # x-axis coordinate
            "y",  # y-axis coordinate
            "z",  # z-axis coordinate
            "nlm",  # National Library of Medicine
            "pgn",  # page number
            "dblp",  # Digital Bibliography & Library Project
            "cl",  # cell line
            "mwt",  # molecular weight
            "hbd",  # hydrogen bond donor
            "by",  # part of "replaced_by"
        }

        # Extract potential abbreviations (short lowercase words without vowels)
        potential_abbrevs = []
        for field in fields.keys():
            parts = field.split("_")
            for part in parts:
                if (
                    len(part) <= 4
                    and part not in known_abbreviations
                    and not any(vowel in part for vowel in "aeiou")
                    and part.isalpha()
                ):
                    potential_abbrevs.append((field, part))

        if potential_abbrevs:
            pytest.fail(
                f"{schema_name}: Potential undocumented abbreviations:\n"
                + "\n".join(
                    f"  - {field}: '{abbrev}'" for field, abbrev in potential_abbrevs
                )
                + "\n\nEither spell out or add to glossary.md"
            )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_boolean_fields_start_with_is_has_can(self, schema_name: str) -> None:
        """Boolean fields SHOULD start with is_, has_, can_, or _flag suffix.

        Note: ETL metadata fields (underscore prefix) are excluded from this check.
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Exclude ETL metadata fields (underscore prefix) - they have standardized names
        boolean_fields = [
            field
            for field, meta in fields.items()
            if "bool" in meta["dtype"].lower() and not field.startswith("_")
        ]

        improper_boolean_names = [
            field
            for field in boolean_fields
            if not (
                field.startswith(("is_", "has_", "can_"))
                or field.endswith(("_flag", "_active", "_valid", "_enabled"))
            )
        ]

        improper_boolean_names = [
            field for field in improper_boolean_names if not field.startswith("_")
        ]

        allowed_boolean_names = {
            "abstract_structured",
            "content_domain_crossmark_restriction",
            "downgraded",
            "oral",
            "parenteral",
            "reviewed",
            "topical",
        }
        improper_boolean_names = [
            field
            for field in improper_boolean_names
            if field not in allowed_boolean_names
        ]

        if improper_boolean_names:
            pytest.fail(
                f"{schema_name}: Boolean fields with unclear names:\n"
                + "\n".join(f"  - {field}" for field in sorted(improper_boolean_names))
                + "\n\nUse prefixes: is_, has_, can_ or suffixes: _flag, _active"
            )


@pytest.mark.contracts
@pytest.mark.no_api
class TestMetadataFieldNaming:
    """Tests for ETL metadata field naming."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_metadata_fields_start_with_underscore(self, schema_name: str) -> None:
        """ETL metadata fields MUST start with underscore.

        These fields come from ETLRecordSchema base class.
        Note: content_hash and entity_id are also ETL metadata but don't use underscore prefix.
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Known underscore-prefixed metadata fields from ETLRecordSchema
        expected_metadata = {
            "_run_id",
            "_run_type",
            "_source_batch_id",
            "_ingestion_ts",
            "_dq_warn",
            "_dq_error",
            "_index",
            "_state",
        }

        # Some schemas may have provider-specific underscore fields
        provider_specific_underscore = {
            "_source",  # Publication schemas
            "_lookup_method",  # Publication schemas
            "_original_id",  # Some schemas
        }

        # Check that underscore fields are known metadata
        underscore_fields = {field for field in fields.keys() if field.startswith("_")}

        unknown_underscore = (
            underscore_fields - expected_metadata - provider_specific_underscore
        )

        if unknown_underscore:
            pytest.fail(
                f"{schema_name}: Unknown underscore fields (not ETL metadata):\n"
                + "\n".join(f"  - {field}" for field in sorted(unknown_underscore))
                + "\n\nUnderscore prefix reserved for ETL metadata only."
            )


@pytest.mark.contracts
@pytest.mark.no_api
class TestForeignKeyNaming:
    """Tests for foreign key field naming consistency."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_foreign_keys_have_id_suffix(self, schema_name: str) -> None:
        """Foreign key fields SHOULD end with _id or _chembl_id."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Look for fields with "Foreign key" in description
        fk_fields = [
            (field, meta["description"])
            for field, meta in fields.items()
            if "foreign key" in meta.get("description", "").lower()
        ]

        fks_without_id_suffix = [
            (field, desc)
            for field, desc in fk_fields
            if not field.endswith(("_id", "_chembl_id", "molecule_id", "accession"))
        ]

        if fks_without_id_suffix:
            pytest.fail(
                f"{schema_name}: Foreign keys without _id suffix:\n"
                + "\n".join(
                    f"  - {field}: {desc}" for field, desc in fks_without_id_suffix
                )
            )

    @pytest.mark.parametrize("schema_name", CHEMBL_SCHEMAS)
    def test_chembl_fk_naming_consistency(self, schema_name: str) -> None:
        """ChEMBL foreign keys MUST follow {entity}_chembl_id pattern."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Find ChEMBL ID fields
        chembl_id_fields = [field for field in fields.keys() if "_chembl_id" in field]

        # Validate naming pattern: {entity}_chembl_id
        valid_entities = {
            "activity",
            "assay",
            "molecule",
            "target",
            "document",
            "cell",
            "tissue",
            "source",
        }

        allowed_nonstandard = {
            "hierarchy_active_chembl_id",
            "hierarchy_child_chembl_id",
            "hierarchy_parent_chembl_id",
        }
        invalid_fk_names = []
        for field in chembl_id_fields:
            if field in allowed_nonstandard:
                continue
            # Extract entity name (everything before _chembl_id)
            entity = field.replace("_chembl_id", "")

            # Check if it's a known entity or compound word
            if entity not in valid_entities and "_" in entity:
                # Check compound: target_id, compound_record_chembl_id OK
                # But: invalid_name_chembl_id NOT OK
                parts = entity.split("_")
                if not any(part in valid_entities for part in parts):
                    invalid_fk_names.append(field)

        if invalid_fk_names:
            pytest.fail(
                f"{schema_name}: ChEMBL FK with non-standard entity name:\n"
                + "\n".join(f"  - {field}" for field in sorted(invalid_fk_names))
                + f"\n\nValid entities: {sorted(valid_entities)}"
            )


@pytest.mark.contracts
@pytest.mark.no_api
class TestCrossProviderNaming:
    """Tests for naming consistency across providers."""

    def test_common_fields_same_name_across_publications(self) -> None:
        """Common publication fields MUST have same names across providers.

        Enforces consistency from PublicationBaseSchema.
        """
        publication_schemas = {
            name: schema
            for name, schema in SILVER_SCHEMAS.items()
            if "publication" in name
        }

        for schema_name, schema_class in publication_schemas.items():
            fields = extract_field_metadata(schema_class)

            # Check for legacy field names (should be renamed)
            legacy_fields = {
                "citation_count": "Use citations_received instead (5.14.0)",
                "author_ormolecule_id_list": "Use author_orcids instead (5.14.0)",
                "author_ormolecule_ids": "Use author_orcids instead (5.17.0)",
            }

            found_legacy = [
                (field, reason)
                for field, reason in legacy_fields.items()
                if field in fields
            ]

            if found_legacy:
                pytest.fail(
                    f"{schema_name}: Legacy field names found:\n"
                    + "\n".join(
                        f"  - {field}: {reason}" for field, reason in found_legacy
                    )
                )

    def test_id_field_naming_by_provider(self) -> None:
        """Primary key naming MUST follow provider conventions.

        Conventions:
        - ChEMBL: {entity}_chembl_id
        - PubChem: molecule_id
        - UniProt: accession (or entry)
        - PubMed: pmid
        - CrossRef: doi
        - OpenAlex: openalex_id
        - Semantic Scholar: paper_id
        """
        provider_conventions = {
            "chembl": "_chembl_id",
            "pubchem": "molecule_id",
            "uniprot": "accession",
            "pubmed": "pmid",
            "crossref": "doi",
            "openalex": "openalex_id",
            "semanticscholar": "paper_id",
        }
        schema_overrides = {
            "chembl_activity": "activity_id",
            "chembl_assay": "assay_id",
            "chembl_assay_parameters": "assay_param_id",
            "chembl_cell_line": "cell_id",
            "chembl_compound_record": "record_id",
            "chembl_molecule": "molecule_id",
            "chembl_publication": "publication_id",
            "chembl_publication_term": "publication_id",
            "chembl_target": "target_id",
            "chembl_protein_class": "protein_class_id",
            "chembl_publication_similarity": "sim_id",
            "chembl_tissue": "tissue_id",
            "chembl_subcellular_fraction": "subcellular_fraction",
            "chembl_target_component": "component_id",
            "pubchem_compound": "molecule_id",
            "uniprot_protein": "accession",
            "uniprot_idmapping": "target_id",
            "pubmed_publication": "pmid",
            "crossref_publication": "doi",
            "openalex_publication": "openalex_id",
            "semanticscholar_publication": "paper_id",
        }

        for schema_name, schema_class in SILVER_SCHEMAS.items():
            provider = schema_name.split("_")[0]

            if provider not in provider_conventions:
                continue

            expected_id_pattern = schema_overrides.get(
                schema_name, provider_conventions[provider]
            )
            fields = extract_field_metadata(schema_class)

            # Find primary key field
            if schema_name in schema_overrides:
                pk_fields = [
                    field
                    for field in fields.keys()
                    if field == expected_id_pattern and not field.startswith("_")
                ]
            else:
                pk_fields = [
                    field
                    for field in fields.keys()
                    if expected_id_pattern in field and not field.startswith("_")
                ]

            assert pk_fields, (
                f"{schema_name}: Missing primary key with pattern '{expected_id_pattern}'\n"
                f"Available fields: {sorted(fields.keys())}"
            )


@pytest.mark.contracts
@pytest.mark.no_api
class TestDeprecatedFieldNames:
    """Tests for detecting deprecated field names."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_no_legacy_dq_field_names(self, schema_name: str) -> None:
        """DQ fields MUST use new naming: _dq_warn, _dq_error.

        Legacy names (deprecated):
        - dq_flag, dq_status, validation_error, validation_warning
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        legacy_dq_names = [
            "dq_flag",
            "dq_status",
            "validation_error",
            "validation_warning",
            "data_quality_flag",
        ]

        found_legacy_dq = [field for field in fields.keys() if field in legacy_dq_names]

        if found_legacy_dq:
            pytest.fail(
                f"{schema_name}: Legacy DQ field names found:\n"
                + "\n".join(f"  - {field}" for field in sorted(found_legacy_dq))
                + "\n\nUse: _dq_warn, _dq_error instead"
            )
