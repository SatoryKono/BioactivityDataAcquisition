"""Tests for Silver layer PyArrow schemas.

Verifies schema definitions for all entities in the Silver layer.
"""

from __future__ import annotations

import pyarrow as pa
import pytest

from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_PUBLICATION_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    CROSSREF_PUBLICATION_SCHEMA,
    OPENALEX_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

pytestmark = pytest.mark.unit

# Required system fields for all Silver schemas
REQUIRED_SYSTEM_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
    }
)


class TestSchemaExistence:
    """Test that all required schemas are defined."""

    def test_chembl_activity_schema_exists(self):
        """Verify CHEMBL_ACTIVITY_SCHEMA is defined."""
        assert CHEMBL_ACTIVITY_SCHEMA is not None
        assert isinstance(CHEMBL_ACTIVITY_SCHEMA, pa.Schema)

    def test_chembl_assay_schema_exists(self):
        """Verify CHEMBL_ASSAY_SCHEMA is defined."""
        assert CHEMBL_ASSAY_SCHEMA is not None
        assert isinstance(CHEMBL_ASSAY_SCHEMA, pa.Schema)

    def test_chembl_document_schema_exists(self):
        """Verify CHEMBL_PUBLICATION_SCHEMA is defined."""
        assert CHEMBL_PUBLICATION_SCHEMA is not None
        assert isinstance(CHEMBL_PUBLICATION_SCHEMA, pa.Schema)

    def test_chembl_molecule_schema_exists(self):
        """Verify CHEMBL_MOLECULE_SCHEMA is defined."""
        assert CHEMBL_MOLECULE_SCHEMA is not None
        assert isinstance(CHEMBL_MOLECULE_SCHEMA, pa.Schema)

    def test_chembl_target_schema_exists(self):
        """Verify CHEMBL_TARGET_SCHEMA is defined."""
        assert CHEMBL_TARGET_SCHEMA is not None
        assert isinstance(CHEMBL_TARGET_SCHEMA, pa.Schema)

    def test_chembl_target_component_schema_exists(self):
        """Verify CHEMBL_TARGET_COMPONENT_SCHEMA is defined."""
        assert CHEMBL_TARGET_COMPONENT_SCHEMA is not None
        assert isinstance(CHEMBL_TARGET_COMPONENT_SCHEMA, pa.Schema)

    def test_pubchem_compound_schema_exists(self):
        """Verify PUBCHEM_COMPOUND_SCHEMA is defined."""
        assert PUBCHEM_COMPOUND_SCHEMA is not None
        assert isinstance(PUBCHEM_COMPOUND_SCHEMA, pa.Schema)

    def test_pubmed_publication_schema_exists(self):
        """Verify PUBMED_PUBLICATION_SCHEMA is defined."""
        assert PUBMED_PUBLICATION_SCHEMA is not None
        assert isinstance(PUBMED_PUBLICATION_SCHEMA, pa.Schema)

    def test_uniprot_protein_schema_exists(self):
        """Verify UNIPROT_PROTEIN_SCHEMA is defined."""
        assert UNIPROT_PROTEIN_SCHEMA is not None
        assert isinstance(UNIPROT_PROTEIN_SCHEMA, pa.Schema)


class TestSystemFields:
    """Test that all schemas contain required system fields."""

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_ACTIVITY_SCHEMA, "CHEMBL_ACTIVITY"),
            (CHEMBL_ASSAY_SCHEMA, "CHEMBL_ASSAY"),
            (CHEMBL_PUBLICATION_SCHEMA, "CHEMBL_DOCUMENT"),
            (CHEMBL_MOLECULE_SCHEMA, "CHEMBL_MOLECULE"),
            (CHEMBL_TARGET_SCHEMA, "CHEMBL_TARGET"),
            (CHEMBL_TARGET_COMPONENT_SCHEMA, "CHEMBL_TARGET_COMPONENT"),
            (PUBCHEM_COMPOUND_SCHEMA, "PUBCHEM_COMPOUND"),
            (PUBMED_PUBLICATION_SCHEMA, "PUBMED_PUBLICATION"),
            (UNIPROT_PROTEIN_SCHEMA, "UNIPROT_PROTEIN"),
        ],
    )
    def test_schema_has_all_system_fields(self, schema, name):
        """Verify schema contains all required system fields."""
        schema_field_names = {field.name for field in schema}
        missing_fields = REQUIRED_SYSTEM_FIELDS - schema_field_names
        assert not missing_fields, (
            f"{name} schema missing system fields: {missing_fields}"
        )

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_ACTIVITY_SCHEMA, "CHEMBL_ACTIVITY"),
            (CHEMBL_ASSAY_SCHEMA, "CHEMBL_ASSAY"),
            (CHEMBL_PUBLICATION_SCHEMA, "CHEMBL_DOCUMENT"),
            (CHEMBL_MOLECULE_SCHEMA, "CHEMBL_MOLECULE"),
            (CHEMBL_TARGET_SCHEMA, "CHEMBL_TARGET"),
            (CHEMBL_TARGET_COMPONENT_SCHEMA, "CHEMBL_TARGET_COMPONENT"),
            (PUBCHEM_COMPOUND_SCHEMA, "PUBCHEM_COMPOUND"),
            (PUBMED_PUBLICATION_SCHEMA, "PUBMED_PUBLICATION"),
            (UNIPROT_PROTEIN_SCHEMA, "UNIPROT_PROTEIN"),
        ],
    )
    def test_system_fields_are_strings(self, schema, name):
        """Verify system fields have correct types."""
        for field_name in REQUIRED_SYSTEM_FIELDS:
            field = schema.field(field_name)
            assert field.type == pa.string(), (
                f"{name}.{field_name} should be string, got {field.type}"
            )


class TestChemblActivitySchema:
    """Tests for CHEMBL_ACTIVITY_SCHEMA."""

    def test_has_primary_key(self):
        """Verify primary key field exists."""
        assert "activity_id" in CHEMBL_ACTIVITY_SCHEMA.names

    def test_activity_id_is_string(self):
        """Verify activity_id is string type."""
        field = CHEMBL_ACTIVITY_SCHEMA.field("activity_id")
        assert field.type == pa.string()

    def test_has_core_identifiers(self):
        """Verify core identifier fields exist."""
        expected = [
            "molecule_id",
            "target_id",
            "assay_id",
            "publication_id",
        ]
        for field_name in expected:
            assert field_name in CHEMBL_ACTIVITY_SCHEMA.names

    def test_has_activity_values(self):
        """Verify activity value fields exist."""
        expected = ["activity_value", "units", "standard_value", "standard_units"]
        for field_name in expected:
            assert field_name in CHEMBL_ACTIVITY_SCHEMA.names

    def test_value_fields_are_float64(self):
        """Verify numeric value fields are float64."""
        float_fields = [
            "activity_value",
            "upper_value",
            "standard_value",
            "standard_upper_value",
            "pchembl_value",
        ]
        for field_name in float_fields:
            field = CHEMBL_ACTIVITY_SCHEMA.field(field_name)
            assert field.type == pa.float64(), (
                f"{field_name} should be float64, got {field.type}"
            )

    def test_ligand_efficiency_fields_exist(self):
        """Verify ligand efficiency metrics are present."""
        le_fields = [
            "ligand_efficiency_bei",
            "ligand_efficiency_le",
            "ligand_efficiency_lle",
            "ligand_efficiency_sei",
        ]
        for field_name in le_fields:
            assert field_name in CHEMBL_ACTIVITY_SCHEMA.names

    def test_chembl_activity_schema__field_count__272c87b5(self):
        """Verify expected number of fields."""
        # Should have approximately 60+ fields
        assert len(CHEMBL_ACTIVITY_SCHEMA) >= 50


class TestChemblAssaySchema:
    """Tests for CHEMBL_ASSAY_SCHEMA."""

    def test_chembl_assay_schema__has_primary_key__cec41ba9(self):
        """Verify primary key field exists."""
        assert "assay_id" in CHEMBL_ASSAY_SCHEMA.names

    def test_chembl_assay_schema__has_core_identifiers__6ec00f20(self):
        """Verify core identifier fields exist."""
        expected = [
            "target_id",
            "publication_id",
            "cell_id",
        ]
        for field_name in expected:
            assert field_name in CHEMBL_ASSAY_SCHEMA.names

    def test_has_biological_context(self):
        """Verify biological context fields exist."""
        expected = [
            "assay_organism",
            "assay_taxonomy_id",
            "assay_cell_type",
        ]
        for field_name in expected:
            assert field_name in CHEMBL_ASSAY_SCHEMA.names

    def test_json_fields_are_strings(self):
        """Verify complex JSON fields are stored as strings."""
        json_fields = ["assay_classifications", "assay_parameters"]
        for field_name in json_fields:
            field = CHEMBL_ASSAY_SCHEMA.field(field_name)
            assert field.type == pa.string(), (
                f"{field_name} should be string (JSON), got {field.type}"
            )


class TestChemblMoleculeSchema:
    """Tests for CHEMBL_MOLECULE_SCHEMA."""

    def test_chembl_molecule_schema__has_primary_key__999384bd(self):
        """Verify primary key field exists."""
        assert "molecule_id" in CHEMBL_MOLECULE_SCHEMA.names

    def test_has_flags(self):
        """Verify boolean flag fields exist."""
        expected_bool = ["oral", "parenteral", "topical", "therapeutic_flag"]
        for field_name in expected_bool:
            assert field_name in CHEMBL_MOLECULE_SCHEMA.names
            field = CHEMBL_MOLECULE_SCHEMA.field(field_name)
            assert field.type == pa.bool_(), (
                f"{field_name} should be bool, got {field.type}"
            )

    def test_has_complex_json_fields(self):
        """Verify complex JSON fields exist and are strings."""
        json_fields = [
            "molecule_hierarchy",
            "molecule_properties",
            "molecule_structures",
            "molecule_synonyms",
            "cross_references",
            "atc_classifications",
        ]
        for field_name in json_fields:
            assert field_name in CHEMBL_MOLECULE_SCHEMA.names
            field = CHEMBL_MOLECULE_SCHEMA.field(field_name)
            assert field.type == pa.string()


class TestChemblTargetSchema:
    """Tests for CHEMBL_TARGET_SCHEMA."""

    _EXPECTED_BUSINESS_FIELDS = [
        "target_id",
        "target_type",
        "pref_name",
        "taxonomy_id",
        "organism",
        "organism_class",
        "species_group_flag",
        "target_description",
        "target_protein_synonyms",
        "target_gene_synonyms",
        "target_ec_numbers",
        "target_xref_pdb_ids",
        "target_xref_go_component",
        "target_xref_go_function",
        "target_xref_go_process",
        "target_xref_hgnc_ids",
        "target_xref_reactome_ids",
        "target_xref_uniprot_ids",
        "primary_component_id",
        "component_accessions",
        "component_descriptions",
        "component_ids",
        "component_types",
        "component_relationships",
        "target_components",
        "cross_references",
        "target_component_synonyms",
    ]

    def test_chembl_target_schema__has_primary_key__d204562d(self):
        """Verify primary key field exists."""
        assert "target_id" in CHEMBL_TARGET_SCHEMA.names

    def test_has_canonical_json_string_fields(self):
        """Verify canonical JSON string fields have correct types (ADR-035)."""
        # These fields were migrated from list types to canonical JSON strings
        json_string_fields = [
            "component_accessions",
            "component_types",
            "component_relationships",
            "component_descriptions",
            "component_ids",
        ]
        for field_name in json_string_fields:
            assert field_name in CHEMBL_TARGET_SCHEMA.names
            field = CHEMBL_TARGET_SCHEMA.field(field_name)
            assert field.type == pa.string(), (
                f"{field_name} should be string (canonical JSON), got {field.type}"
            )

    def test_has_derived_synonym_projection_fields(self):
        """Verify derived target synonym fields are published as strings."""
        for field_name in (
            "target_protein_synonyms",
            "target_gene_synonyms",
            "target_ec_numbers",
        ):
            assert field_name in CHEMBL_TARGET_SCHEMA.names
            assert CHEMBL_TARGET_SCHEMA.field(field_name).type == pa.string()

    def test_has_derived_xref_projection_fields(self):
        """Verify derived target xref projection fields are published as strings."""
        for field_name in (
            "target_xref_pdb_ids",
            "target_xref_go_component",
            "target_xref_go_function",
            "target_xref_go_process",
            "target_xref_hgnc_ids",
            "target_xref_reactome_ids",
            "target_xref_uniprot_ids",
        ):
            assert field_name in CHEMBL_TARGET_SCHEMA.names
            assert CHEMBL_TARGET_SCHEMA.field(field_name).type == pa.string()

    def test_business_field_order_matches_reviewed_contract(self):
        """Target Silver business columns should stay in the reviewed manual order."""
        system_prefix_count = 7
        dq_suffix_count = 2
        assert CHEMBL_TARGET_SCHEMA.names[system_prefix_count:-dq_suffix_count] == (
            self._EXPECTED_BUSINESS_FIELDS
        )
        assert "downgraded" not in CHEMBL_TARGET_SCHEMA.names
        assert "pipeline_stages" not in CHEMBL_TARGET_SCHEMA.names


class TestChemblDocumentSchema:
    """Tests for CHEMBL_PUBLICATION_SCHEMA."""

    def test_chembl_document_schema__has_primary_key__5078150a(self):
        """Verify primary key field exists."""
        assert "publication_id" in CHEMBL_PUBLICATION_SCHEMA.names

    def test_has_publication_identifiers(self):
        """Verify publication identifier fields exist."""
        # patent_id and pmc_id excluded from unified publication schema
        expected = ["pmid", "doi"]
        for field_name in expected:
            assert field_name in CHEMBL_PUBLICATION_SCHEMA.names

    def test_pmid_is_string(self):
        """Verify pmid is string (numeric string for cross-provider consistency)."""
        field = CHEMBL_PUBLICATION_SCHEMA.field("pmid")
        assert field.type == pa.string()


class TestPubchemCompoundSchema:
    """Tests for PUBCHEM_COMPOUND_SCHEMA."""

    def test_compound_schema__has_primary_key__27b054d1(self):
        """Verify primary key field exists."""
        assert "molecule_id" in PUBCHEM_COMPOUND_SCHEMA.names

    def test_molecule_id_is_string(self):
        """Verify molecule_id is string type (from source)."""
        field = PUBCHEM_COMPOUND_SCHEMA.field("molecule_id")
        assert field.type == pa.string()

    def test_has_structure_fields(self):
        """Verify structure fields exist."""
        expected = [
            "molecular_formula",
            "canonical_smiles",
            "isomeric_smiles",
            "inchi",
            "inchi_key",
        ]
        for field_name in expected:
            assert field_name in PUBCHEM_COMPOUND_SCHEMA.names

    def test_all_fields_are_strings_or_typed(self):
        """Verify non-system fields have correct types."""
        string_fields = [
            "molecule_id",
            "molecular_formula",
            "canonical_smiles",
            "inchi",
            "inchi_key",
            "iupac_name",
        ]
        for field_name in string_fields:
            field = PUBCHEM_COMPOUND_SCHEMA.field(field_name)
            assert field.type == pa.string(), (
                f"{field_name} should be string, got {field.type}"
            )

        # molecular_weight is float64 (transformed by PubChemCompoundTransformer)
        mw_field = PUBCHEM_COMPOUND_SCHEMA.field("molecular_weight")
        assert mw_field.type == pa.float64(), (
            f"molecular_weight should be float64, got {mw_field.type}"
        )


class TestUniprotProteinSchema:
    """Tests for UNIPROT_PROTEIN_SCHEMA."""

    def test_uniprot_protein_schema__has_primary_key__1b673051(self):
        """Verify primary key field exists."""
        assert "accession" in UNIPROT_PROTEIN_SCHEMA.names

    def test_has_core_fields(self):
        """Verify core fields exist."""
        expected = ["entry_name", "protein_name", "taxonomy_id", "sequence_length"]
        for field_name in expected:
            assert field_name in UNIPROT_PROTEIN_SCHEMA.names

    def test_gene_fields_are_canonical_strings(self):
        """Verify canonical gene fields are persisted without legacy aliases."""
        assert "gene_names" not in UNIPROT_PROTEIN_SCHEMA.names
        for field_name in ("gene_primary", "gene_synonyms", "gene_orf_names"):
            field = UNIPROT_PROTEIN_SCHEMA.field(field_name)
            assert field.type == pa.string()

    def test_taxonomy_id_is_int64(self):
        """Verify canonical taxonomy_id is int64."""
        assert "organism_id" not in UNIPROT_PROTEIN_SCHEMA.names
        field = UNIPROT_PROTEIN_SCHEMA.field("taxonomy_id")
        assert field.type == pa.int64()


class TestPubmedPublicationSchema:
    """Tests for PUBMED_PUBLICATION_SCHEMA."""

    def test_publication_schema__has_primary_key__32057976(self):
        """Verify primary key field exists."""
        assert "pmid" in PUBMED_PUBLICATION_SCHEMA.names

    def test_has_identifiers(self):
        """Verify identifier fields exist."""
        expected = ["doi", "pmc_id"]
        for field_name in expected:
            assert field_name in PUBMED_PUBLICATION_SCHEMA.names

    def test_structured_fields_are_json_strings(self):
        """Verify structured fields use canonical JSON string storage."""
        structured_fields = ["publication_types", "subject_keywords", "subject_mesh"]
        for field_name in structured_fields:
            assert field_name in PUBMED_PUBLICATION_SCHEMA.names
            field = PUBMED_PUBLICATION_SCHEMA.field(field_name)
            assert field.type == pa.string(), (
                f"{field_name} should be string, got {field.type}"
            )

    def test_authors_is_json_string(self):
        """Verify authors field is JSON-serialized string."""
        assert "authors" in PUBMED_PUBLICATION_SCHEMA.names
        field = PUBMED_PUBLICATION_SCHEMA.field("authors")
        assert field.type == pa.string(), f"authors should be string, got {field.type}"

    def test_publication_year_is_int64(self):
        """Verify publication_year is int64."""
        field = PUBMED_PUBLICATION_SCHEMA.field("publication_year")
        assert field.type == pa.int64()

    def test_has_journal_info(self):
        """Verify journal information fields exist."""
        expected = ["journal", "journal_name_short", "volume", "issue"]
        for field_name in expected:
            assert field_name in PUBMED_PUBLICATION_SCHEMA.names


class TestCrossrefPublicationSchema:
    """Tests for CROSSREF_PUBLICATION_SCHEMA."""

    def test_journal_name_short_is_string(self):
        """Verify journal_name_short is a string field."""
        field = CROSSREF_PUBLICATION_SCHEMA.field("journal_name_short")
        assert field.type == pa.string(), (
            f"journal_name_short should be string, got {field.type}"
        )


class TestSchemaFieldCounts:
    """Test approximate field counts for each schema."""

    @pytest.mark.parametrize(
        "schema,name,min_fields",
        [
            (CHEMBL_ACTIVITY_SCHEMA, "CHEMBL_ACTIVITY", 50),
            (CHEMBL_ASSAY_SCHEMA, "CHEMBL_ASSAY", 25),
            (CHEMBL_PUBLICATION_SCHEMA, "CHEMBL_DOCUMENT", 15),
            (CHEMBL_MOLECULE_SCHEMA, "CHEMBL_MOLECULE", 20),
            (CHEMBL_TARGET_SCHEMA, "CHEMBL_TARGET", 15),
            (CHEMBL_TARGET_COMPONENT_SCHEMA, "CHEMBL_TARGET_COMPONENT", 10),
            (PUBCHEM_COMPOUND_SCHEMA, "PUBCHEM_COMPOUND", 10),
            (PUBMED_PUBLICATION_SCHEMA, "PUBMED_PUBLICATION", 20),
            (UNIPROT_PROTEIN_SCHEMA, "UNIPROT_PROTEIN", 10),
        ],
    )
    def test_minimum_field_count(self, schema, name, min_fields):
        """Verify schema has at least minimum expected fields."""
        actual = len(schema)
        assert actual >= min_fields, (
            f"{name} has {actual} fields, expected at least {min_fields}"
        )


class TestSchemaImmutability:
    """Test that schemas are effectively immutable."""

    def test_schema_is_frozen(self):
        """Verify schema cannot be modified in-place."""
        # PyArrow schemas are immutable by design
        # This test verifies the behavior
        original_names = list(CHEMBL_ACTIVITY_SCHEMA.names)

        # Attempt to create new schema with field would work,
        # but original should remain unchanged
        new_schema = CHEMBL_ACTIVITY_SCHEMA.append(pa.field("test", pa.string()))

        assert list(CHEMBL_ACTIVITY_SCHEMA.names) == original_names
        assert "test" in new_schema.names
        assert "test" not in CHEMBL_ACTIVITY_SCHEMA.names


class TestSilverSchemaValidation:
    """Tests for Silver schema data validation."""

    def test_silver_schema_valid(self):
        """Silver schema должна валидировать корректные данные."""
        # Create valid data according to CHEMBL_ACTIVITY_SCHEMA
        valid_record = {
            "entity_id": "ACT_12345",
            "content_hash": "abc123def456",
            "activity_id": "12345",
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1824",
            "assay_id": "CHEMBL829232",
            "publication_id": "CHEMBL1122334",
            "record_id": 1001,
            "src_id": 1,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "molecule_pref_name": "ASPIRIN",
            "parent_molecule_id": "CHEMBL25",
            "target_pref_name": "Cyclooxygenase-2",
            "target_organism": "Homo sapiens",
            "target_taxonomy_id": 9606.0,
            "assay_type": "B",
            "assay_description": "Binding assay",
            "assay_variant_accession": None,
            "assay_variant_mutation": None,
            "bao_endpoint": "BAO_0000190",
            "bao_format": "BAO_0000357",
            "bao_label": "single protein format",
            "activity_type": "IC50",
            "activity_value": 50.0,
            "units": "nM",
            "activity_relation": "=",
            "upper_value": None,
            "text_value": None,
            "standard_type": "IC50",
            "standard_value": 50.0,
            "standard_units": "nM",
            "standard_relation": "=",
            "standard_upper_value": None,
            "standard_text_value": None,
            "standard_flag": 1,
            "pchembl_value": 7.3,
            "ligand_efficiency_bei": 15.2,
            "ligand_efficiency_le": 0.35,
            "ligand_efficiency_lle": 4.1,
            "ligand_efficiency_sei": 8.5,
            "qudt_units": "nM",
            "uo_units": "UO:0000065",
            "journal": "J Med Chem",
            "publication_year": 2020,
            "activity_comment": None,
            "data_validity_comment": None,
            "data_validity_description": None,
            "potential_duplicate": 0,
            "action_type_action_type": "INHIBITOR",
            "action_type_description": "Enzyme inhibitor",
            "action_type_parent_type": "INHIBITOR",
            "activity_properties": "[]",
            "toid": None,
            "_run_id": "run_001",
            "_run_type": "incremental",
            "_source_batch_id": "batch_001",
            "_ingestion_ts": "2024-01-15T10:30:00Z",
        }

        # Create PyArrow table from valid data - should succeed without exception
        table = pa.Table.from_pylist([valid_record], schema=CHEMBL_ACTIVITY_SCHEMA)

        assert table.num_rows == 1
        assert table.num_columns == len(CHEMBL_ACTIVITY_SCHEMA)

    def test_silver_schema_valid_pubchem(self):
        """PUBCHEM_COMPOUND_SCHEMA должна валидировать корректные данные."""
        valid_record = {
            "entity_id": "CID_2244",
            "content_hash": "xyz789",
            "molecule_id": "2244",
            "molecular_formula": "C9H8O4",
            "molecular_weight": 180.16,  # float64, not string
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "isomeric_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            "inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "iupac_name": "2-acetoxybenzoic amolecule_id",
            "_run_id": "run_002",
            "_run_type": "incremental",
            "_source_batch_id": "batch_002",
            "_ingestion_ts": "2024-01-15T11:00:00Z",
            "_index": 0,
        }

        table = pa.Table.from_pylist([valid_record], schema=PUBCHEM_COMPOUND_SCHEMA)

        assert table.num_rows == 1
        assert table.num_columns == len(PUBCHEM_COMPOUND_SCHEMA)

    def test_silver_schema_valid_uniprot(self):
        """UNIPROT_PROTEIN_SCHEMA должна валидировать корректные данные."""
        valid_record = {
            "entity_id": "P00533",
            "accession": "P00533",
            "entry_name": "EGFR_HUMAN",
            "protein_name": "Epidermal growth factor receptor",
            "gene_primary": "EGFR",
            "gene_synonyms": '["ERBB1"]',
            "taxonomy_id": 9606,
            "sequence_length": 1210,
            "content_hash": "hash123",
            "_run_id": "run_003",
            "_run_type": "incremental",
            "_source_batch_id": "batch_003",
            "_ingestion_ts": "2024-01-15T12:00:00Z",
        }

        table = pa.Table.from_pylist([valid_record], schema=UNIPROT_PROTEIN_SCHEMA)

        assert table.num_rows == 1
        assert table.num_columns == len(UNIPROT_PROTEIN_SCHEMA)

    def test_silver_schema_rejects_invalid(self):
        """Silver schema должна отклонять некорректные данные."""
        # Invalid record: wrong types for numeric fields
        invalid_record = {
            "entity_id": "ACT_12345",
            "content_hash": "abc123",
            "activity_id": "12345",
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1824",
            "assay_id": "CHEMBL829232",
            "publication_id": "CHEMBL1122334",
            "record_id": "not_an_integer",  # Should be int64
            "src_id": "not_an_integer",  # Should be int64
            "activity_value": "not_a_float",  # Should be float64
            "standard_value": "not_a_float",  # Should be float64
            "_run_id": "run_001",
            "_run_type": "incremental",
            "_source_batch_id": "batch_001",
            "_ingestion_ts": "2024-01-15T10:30:00Z",
        }

        with pytest.raises((pa.ArrowInvalid, pa.ArrowTypeError)):
            pa.Table.from_pylist([invalid_record], schema=CHEMBL_ACTIVITY_SCHEMA)

    def test_silver_schema_rejects_wrong_list_type(self):
        """Silver schema должна отклонять некорректный тип списка."""
        # Invalid: gene_synonyms should be a JSON string, not a Python list.
        invalid_record = {
            "entity_id": "P00533",
            "accession": "P00533",
            "entry_name": "EGFR_HUMAN",
            "protein_name": "Epidermal growth factor receptor",
            "gene_synonyms": [123, 456],
            "taxonomy_id": 9606,
            "sequence_length": 1210,
            "content_hash": "hash123",
            "_run_id": "run_003",
            "_run_type": "incremental",
            "_source_batch_id": "batch_003",
            "_ingestion_ts": "2024-01-15T12:00:00Z",
        }

        with pytest.raises((pa.ArrowInvalid, pa.ArrowTypeError)):
            pa.Table.from_pylist([invalid_record], schema=UNIPROT_PROTEIN_SCHEMA)

    def test_silver_schema_allows_null_values(self):
        """Silver schema должна допускать NULL значения для необязательных полей."""
        # Record with many null values - should be valid
        minimal_record = {
            "entity_id": "ACT_12345",
            "content_hash": "abc123",
            "activity_id": "12345",
            "molecule_id": None,
            "target_id": None,
            "assay_id": None,
            "publication_id": None,
            "record_id": None,
            "src_id": None,
            "canonical_smiles": None,
            "molecule_pref_name": None,
            "parent_molecule_id": None,
            "target_pref_name": None,
            "target_organism": None,
            "target_taxonomy_id": None,
            "assay_type": None,
            "assay_description": None,
            "assay_variant_accession": None,
            "assay_variant_mutation": None,
            "bao_endpoint": None,
            "bao_format": None,
            "bao_label": None,
            "activity_type": None,
            "activity_value": None,
            "units": None,
            "activity_relation": None,
            "upper_value": None,
            "text_value": None,
            "standard_type": None,
            "standard_value": None,
            "standard_units": None,
            "standard_relation": None,
            "standard_upper_value": None,
            "standard_text_value": None,
            "standard_flag": None,
            "pchembl_value": None,
            "ligand_efficiency_bei": None,
            "ligand_efficiency_le": None,
            "ligand_efficiency_lle": None,
            "ligand_efficiency_sei": None,
            "qudt_units": None,
            "uo_units": None,
            "journal": None,
            "publication_year": None,
            "activity_comment": None,
            "data_validity_comment": None,
            "data_validity_description": None,
            "potential_duplicate": None,
            "action_type_action_type": None,
            "action_type_description": None,
            "action_type_parent_type": None,
            "activity_properties": None,
            "toid": None,
            "_run_id": "run_001",
            "_run_type": "incremental",
            "_source_batch_id": "batch_001",
            "_ingestion_ts": "2024-01-15T10:30:00Z",
        }

        # Should succeed with null values
        table = pa.Table.from_pylist([minimal_record], schema=CHEMBL_ACTIVITY_SCHEMA)
        assert table.num_rows == 1

    @pytest.mark.parametrize(
        "schema,primary_key,invalid_pk_value",
        [
            (CHEMBL_ACTIVITY_SCHEMA, "activity_id", 12345),  # Should be string
            (CHEMBL_ASSAY_SCHEMA, "assay_id", 12345),  # Should be string
            (PUBCHEM_COMPOUND_SCHEMA, "molecule_id", 2244),  # Should be string
        ],
    )
    def test_silver_schema_rejects_invalid_primary_key_type(
        self, schema, primary_key, invalid_pk_value
    ):
        """Silver schema должна отклонять некорректный тип первичного ключа."""
        # Build minimal record with required system fields
        record = {
            "entity_id": "test",
            "content_hash": "hash",
            primary_key: invalid_pk_value,  # Wrong type - should be string
            "_run_id": "run",
            "_run_type": "incremental",
            "_source_batch_id": "batch",
            "_ingestion_ts": "2024-01-01T00:00:00Z",
        }

        with pytest.raises((pa.ArrowInvalid, pa.ArrowTypeError)):
            pa.Table.from_pylist([record], schema=schema)


# =============================================================================
# Publication Schema Unification Tests
# =============================================================================

# Required fields for all publication schemas (unified across providers)
PUBLICATION_DQ_FIELDS = frozenset({"_dq_warn", "_dq_error"})
PUBLICATION_LOOKUP_FIELDS = frozenset({"_lookup_method", "_original_id"})
# Cross-reference fields vary by provider due to API availability
# - ChEMBL: pmid, doi (pmc_id not available from ChEMBL API)
# - CrossRef: doi only (pmid, pmc_id not available from CrossRef API)
# - OpenAlex: pmid, doi (pmc_id excluded per design 2026-01)
# - PubMed: pmid, doi, pmc_id (all available)
# - SemanticScholar: pmid, doi (pmc_id excluded per design 2026-01)
PUBLICATION_CROSS_REF_FIELDS_MINIMAL = frozenset({"doi"})  # All providers have doi
PUBLICATION_UNIFIED_PAGE_FIELDS = frozenset(
    {"page_first", "page_last"}
)  # publication_date varies


class TestPublicationSchemaDQFields:
    """Test that all publication schemas have DQ fields."""

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication"),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            (SEMANTICSCHOLAR_PUBLICATION_SCHEMA, "SemanticScholar Publication"),
        ],
    )
    def test_schema_d_q_fields__schema_has_dq_fields__7efb86cd(self, schema, name):
        """All publication schemas must have _dq_warn and _dq_error fields."""
        field_names = {f.name for f in schema}
        missing = PUBLICATION_DQ_FIELDS - field_names
        assert not missing, f"{name} missing DQ fields: {missing}"

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication"),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            (SEMANTICSCHOLAR_PUBLICATION_SCHEMA, "SemanticScholar Publication"),
        ],
    )
    def test_dq_fields_are_bool(self, schema, name):
        """DQ fields must be boolean type."""
        for field_name in PUBLICATION_DQ_FIELDS:
            field = schema.field(field_name)
            assert field.type == pa.bool_(), (
                f"{name}.{field_name} should be bool, got {field.type}"
            )


class TestPublicationSchemaLookupFields:
    """Test that all publication schemas have lookup metadata fields."""

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication"),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            (SEMANTICSCHOLAR_PUBLICATION_SCHEMA, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_lookup_fields(self, schema, name):
        """All publication schemas must have _lookup_method and _original_id."""
        field_names = {f.name for f in schema}
        missing = PUBLICATION_LOOKUP_FIELDS - field_names
        assert not missing, f"{name} missing lookup fields: {missing}"

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication"),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            (SEMANTICSCHOLAR_PUBLICATION_SCHEMA, "SemanticScholar Publication"),
        ],
    )
    def test_lookup_fields_are_string(self, schema, name):
        """Lookup fields must be string type."""
        for field_name in PUBLICATION_LOOKUP_FIELDS:
            field = schema.field(field_name)
            assert field.type == pa.string(), (
                f"{name}.{field_name} should be string, got {field.type}"
            )


class TestPublicationSchemaCrossRefFields:
    """Test that publication schemas have appropriate cross-reference ID fields.

    Cross-reference field availability varies by provider:
    - ChEMBL: pmid, doi (pmc_id not available from ChEMBL API)
    - CrossRef: doi only (pmid, pmc_id not available from CrossRef API)
    - OpenAlex: pmid, doi (pmc_id excluded per design 2026-01)
    - PubMed: pmid, doi, pmc_id (all available)
    - SemanticScholar: pmid, doi (pmc_id excluded per design 2026-01)
    """

    @pytest.mark.parametrize(
        "schema,name,expected_fields",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication", {"pmid", "doi"}),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication", {"doi"}),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication", {"pmid", "doi"}),
            (
                PUBMED_PUBLICATION_SCHEMA,
                "PubMed Publication",
                {"pmid", "doi", "pmc_id"},
            ),
            (
                SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
                "SemanticScholar Publication",
                {"pmid", "doi"},
            ),
        ],
    )
    def test_schema_has_cross_ref_fields(self, schema, name, expected_fields):
        """Publication schemas must have their provider-specific cross-ref fields."""
        field_names = {f.name for f in schema}
        missing = expected_fields - field_names
        assert not missing, f"{name} missing cross-ref fields: {missing}"

    @pytest.mark.parametrize(
        "schema,name,expected_fields",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication", {"pmid", "doi"}),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication", {"doi"}),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication", {"pmid", "doi"}),
            (
                PUBMED_PUBLICATION_SCHEMA,
                "PubMed Publication",
                {"pmid", "doi", "pmc_id"},
            ),
            (
                SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
                "SemanticScholar Publication",
                {"pmid", "doi"},
            ),
        ],
    )
    def test_cross_ref_fields_are_string(self, schema, name, expected_fields):
        """Cross-reference fields must be string type."""
        for field_name in expected_fields:
            field = schema.field(field_name)
            assert field.type == pa.string(), (
                f"{name}.{field_name} should be string, got {field.type}"
            )


class TestPublicationSchemaUnifiedDateAndPageFields:
    """Test that all publication schemas have unified date and page fields."""

    @pytest.mark.parametrize(
        "schema,name",
        [
            # ChEMBL excluded: publication_date not available from ChEMBL API
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            (SEMANTICSCHOLAR_PUBLICATION_SCHEMA, "SemanticScholar Publication"),
        ],
    )
    def test_date_and_page_fields__has_publication_date__62378cb5(self, schema, name):
        """All publication schemas must have publication_date field."""
        field_names = {f.name for f in schema}
        assert "publication_date" in field_names, (
            f"{name} missing publication_date field"
        )
        field = schema.field("publication_date")
        assert field.type == pa.string(), (
            f"{name}.publication_date should be string, got {field.type}"
        )

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication"),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            (SEMANTICSCHOLAR_PUBLICATION_SCHEMA, "SemanticScholar Publication"),
        ],
    )
    def test_date_and_page_fields__has_page_fields__85cc7d74(self, schema, name):
        """All publication schemas must have page_first and page_last fields."""
        field_names = {f.name for f in schema}
        page_fields = {"page_first", "page_last"}
        missing = page_fields - field_names
        assert not missing, f"{name} missing page fields: {missing}"

        for field_name in page_fields:
            field = schema.field(field_name)
            assert field.type == pa.string(), (
                f"{name}.{field_name} should be string, got {field.type}"
            )


class TestPublicationSchemaClassificationFields:
    """Test that all publication schemas have classification fields.

    Classification fields provide a unified 3-level hierarchy:
    - publication_class: Level 1 (EXP, REV, PEER)
    - publication_subclass: Level 2 (~25 groupings)
    - publication_type_unified: Level 3 (214 specific types)

    These fields are populated by BasePublicationTransformer._classify_publication_type()
    using the unified classification mapping from publication_type_classification.py.
    """

    CLASSIFICATION_FIELDS = frozenset(
        {"publication_type_unified", "publication_subclass", "publication_class"}
    )

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication"),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            (SEMANTICSCHOLAR_PUBLICATION_SCHEMA, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_classification_fields(self, schema, name):
        """All publication schemas must have 3-level classification fields."""
        field_names = {f.name for f in schema}
        missing = self.CLASSIFICATION_FIELDS - field_names
        assert not missing, f"{name} missing classification fields: {missing}"

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication"),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            (SEMANTICSCHOLAR_PUBLICATION_SCHEMA, "SemanticScholar Publication"),
        ],
    )
    def test_classification_fields_are_string(self, schema, name):
        """Classification fields must be string type."""
        for field_name in self.CLASSIFICATION_FIELDS:
            field = schema.field(field_name)
            assert field.type == pa.string(), (
                f"{name}.{field_name} should be string, got {field.type}"
            )


class TestAllPublicationSchemas:
    """Test completeness of all publication schemas."""

    @pytest.mark.parametrize(
        "schema,name,primary_key",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication", "publication_id"),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication", "doi"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication", "openalex_id"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication", "pmid"),
            (
                SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
                "SemanticScholar Publication",
                "paper_id",
            ),
        ],
    )
    def test_publication_schemas__has_primary_key__26981c8d(self, schema, name, primary_key):
        """Each publication schema must have its provider-specific primary key."""
        field_names = {f.name for f in schema}
        assert primary_key in field_names, f"{name} missing primary key: {primary_key}"

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication"),
            # CrossRef excluded: abstract not collected per user request
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            # SemanticScholar excluded: authors not collected per user request
        ],
    )
    def test_schema_has_core_fields(self, schema, name):
        """All publication schemas must have core content fields."""
        field_names = {f.name for f in schema}
        core_fields = {"title", "abstract", "authors", "publication_year"}
        missing = core_fields - field_names
        assert not missing, f"{name} missing core fields: {missing}"

    @pytest.mark.parametrize(
        "schema,name",
        [
            (CHEMBL_PUBLICATION_SCHEMA, "ChEMBL Publication"),
            (CROSSREF_PUBLICATION_SCHEMA, "CrossRef Publication"),
            (OPENALEX_PUBLICATION_SCHEMA, "OpenAlex Publication"),
            (PUBMED_PUBLICATION_SCHEMA, "PubMed Publication"),
            (SEMANTICSCHOLAR_PUBLICATION_SCHEMA, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_source_field(self, schema, name):
        """All publication schemas should have _source field for provenance."""
        field_names = {f.name for f in schema}
        assert "_source" in field_names, f"{name} missing _source field"
