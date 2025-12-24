"""Tests for Silver layer PyArrow schemas.

Verifies schema definitions for all entities in the Silver layer.
"""

import pyarrow as pa
import pytest

from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_DOCUMENT_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

# Required system fields for all Silver schemas
REQUIRED_SYSTEM_FIELDS = frozenset({
    "entity_id",
    "content_hash",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_ingestion_ts",
})


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
        """Verify CHEMBL_DOCUMENT_SCHEMA is defined."""
        assert CHEMBL_DOCUMENT_SCHEMA is not None
        assert isinstance(CHEMBL_DOCUMENT_SCHEMA, pa.Schema)

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
            (CHEMBL_DOCUMENT_SCHEMA, "CHEMBL_DOCUMENT"),
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
            (CHEMBL_DOCUMENT_SCHEMA, "CHEMBL_DOCUMENT"),
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
            "molecule_chembl_id",
            "target_chembl_id",
            "assay_chembl_id",
            "document_chembl_id",
        ]
        for field_name in expected:
            assert field_name in CHEMBL_ACTIVITY_SCHEMA.names

    def test_has_activity_values(self):
        """Verify activity value fields exist."""
        expected = ["value", "units", "standard_value", "standard_units"]
        for field_name in expected:
            assert field_name in CHEMBL_ACTIVITY_SCHEMA.names

    def test_value_fields_are_float64(self):
        """Verify numeric value fields are float64."""
        float_fields = [
            "value",
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

    def test_field_count(self):
        """Verify expected number of fields."""
        # Should have approximately 60+ fields
        assert len(CHEMBL_ACTIVITY_SCHEMA) >= 50


class TestChemblAssaySchema:
    """Tests for CHEMBL_ASSAY_SCHEMA."""

    def test_has_primary_key(self):
        """Verify primary key field exists."""
        assert "assay_chembl_id" in CHEMBL_ASSAY_SCHEMA.names

    def test_has_core_identifiers(self):
        """Verify core identifier fields exist."""
        expected = [
            "target_chembl_id",
            "document_chembl_id",
            "cell_chembl_id",
        ]
        for field_name in expected:
            assert field_name in CHEMBL_ASSAY_SCHEMA.names

    def test_has_biological_context(self):
        """Verify biological context fields exist."""
        expected = [
            "assay_organism",
            "assay_tax_id",
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

    def test_has_primary_key(self):
        """Verify primary key field exists."""
        assert "molecule_chembl_id" in CHEMBL_MOLECULE_SCHEMA.names

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

    def test_has_primary_key(self):
        """Verify primary key field exists."""
        assert "target_chembl_id" in CHEMBL_TARGET_SCHEMA.names

    def test_has_list_fields(self):
        """Verify list fields have correct types."""
        list_fields = [
            "component_accessions",
            "component_types",
            "component_relationships",
            "component_descriptions",
            "protein_classifications",
        ]
        for field_name in list_fields:
            assert field_name in CHEMBL_TARGET_SCHEMA.names
            field = CHEMBL_TARGET_SCHEMA.field(field_name)
            assert isinstance(field.type, pa.ListType), (
                f"{field_name} should be list, got {field.type}"
            )

    def test_component_ids_is_list_of_int64(self):
        """Verify component_ids is list of int64."""
        field = CHEMBL_TARGET_SCHEMA.field("component_ids")
        assert isinstance(field.type, pa.ListType)
        assert field.type.value_type == pa.int64()


class TestChemblDocumentSchema:
    """Tests for CHEMBL_DOCUMENT_SCHEMA."""

    def test_has_primary_key(self):
        """Verify primary key field exists."""
        assert "document_chembl_id" in CHEMBL_DOCUMENT_SCHEMA.names

    def test_has_publication_identifiers(self):
        """Verify publication identifier fields exist."""
        expected = ["pubmed_id", "doi", "patent_id"]
        for field_name in expected:
            assert field_name in CHEMBL_DOCUMENT_SCHEMA.names

    def test_pubmed_id_is_int64(self):
        """Verify pubmed_id is int64."""
        field = CHEMBL_DOCUMENT_SCHEMA.field("pubmed_id")
        assert field.type == pa.int64()


class TestPubchemCompoundSchema:
    """Tests for PUBCHEM_COMPOUND_SCHEMA."""

    def test_has_primary_key(self):
        """Verify primary key field exists."""
        assert "cid" in PUBCHEM_COMPOUND_SCHEMA.names

    def test_cid_is_string(self):
        """Verify cid is string type (from source)."""
        field = PUBCHEM_COMPOUND_SCHEMA.field("cid")
        assert field.type == pa.string()

    def test_has_structure_fields(self):
        """Verify structure fields exist."""
        expected = [
            "molecular_formula",
            "canonical_smiles",
            "isomeric_smiles",
            "inchi",
            "inchikey",
        ]
        for field_name in expected:
            assert field_name in PUBCHEM_COMPOUND_SCHEMA.names

    def test_all_fields_are_strings(self):
        """Verify all non-system fields are strings."""
        non_system_fields = [
            "cid",
            "molecular_formula",
            "molecular_weight",
            "canonical_smiles",
            "inchi",
            "inchikey",
            "iupac_name",
        ]
        for field_name in non_system_fields:
            field = PUBCHEM_COMPOUND_SCHEMA.field(field_name)
            assert field.type == pa.string(), (
                f"{field_name} should be string, got {field.type}"
            )


class TestUniprotProteinSchema:
    """Tests for UNIPROT_PROTEIN_SCHEMA."""

    def test_has_primary_key(self):
        """Verify primary key field exists."""
        assert "accession" in UNIPROT_PROTEIN_SCHEMA.names

    def test_has_core_fields(self):
        """Verify core fields exist."""
        expected = ["entry_name", "protein_name", "organism_id", "sequence_length"]
        for field_name in expected:
            assert field_name in UNIPROT_PROTEIN_SCHEMA.names

    def test_gene_names_is_list(self):
        """Verify gene_names is list of strings."""
        field = UNIPROT_PROTEIN_SCHEMA.field("gene_names")
        assert isinstance(field.type, pa.ListType)
        assert field.type.value_type == pa.string()

    def test_organism_id_is_int64(self):
        """Verify organism_id is int64."""
        field = UNIPROT_PROTEIN_SCHEMA.field("organism_id")
        assert field.type == pa.int64()


class TestPubmedPublicationSchema:
    """Tests for PUBMED_PUBLICATION_SCHEMA."""

    def test_has_primary_key(self):
        """Verify primary key field exists."""
        assert "pmid" in PUBMED_PUBLICATION_SCHEMA.names

    def test_has_identifiers(self):
        """Verify identifier fields exist."""
        expected = ["doi", "pmc_id"]
        for field_name in expected:
            assert field_name in PUBMED_PUBLICATION_SCHEMA.names

    def test_has_list_fields(self):
        """Verify list fields exist and have correct types."""
        list_fields = ["authors", "publication_types", "keywords", "mesh_terms"]
        for field_name in list_fields:
            assert field_name in PUBMED_PUBLICATION_SCHEMA.names
            field = PUBMED_PUBLICATION_SCHEMA.field(field_name)
            assert isinstance(field.type, pa.ListType), (
                f"{field_name} should be list, got {field.type}"
            )
            assert field.type.value_type == pa.string()

    def test_pub_year_is_int64(self):
        """Verify pub_year is int64."""
        field = PUBMED_PUBLICATION_SCHEMA.field("pub_year")
        assert field.type == pa.int64()

    def test_has_journal_info(self):
        """Verify journal information fields exist."""
        expected = ["journal", "journal_abbrev", "volume", "issue"]
        for field_name in expected:
            assert field_name in PUBMED_PUBLICATION_SCHEMA.names


class TestSchemaFieldCounts:
    """Test approximate field counts for each schema."""

    @pytest.mark.parametrize(
        "schema,name,min_fields",
        [
            (CHEMBL_ACTIVITY_SCHEMA, "CHEMBL_ACTIVITY", 50),
            (CHEMBL_ASSAY_SCHEMA, "CHEMBL_ASSAY", 25),
            (CHEMBL_DOCUMENT_SCHEMA, "CHEMBL_DOCUMENT", 15),
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
