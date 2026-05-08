from uuid import uuid4

import pandas as pd
import pytest
from pandera.errors import SchemaError

from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.chembl.publication_similarity import (
    PublicationSimilaritySchema,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema
from bioetl.domain.schemas.chembl.tissue import TissueSchema
from tests.helpers.clock import FIXED_TEST_TIME


@pytest.mark.unit
class TestChemblSchemas:
    """Test suite for ChEMBL Pandera schemas."""

    @pytest.fixture
    def base_etl_fields(self) -> dict[str, object]:
        """Create base ETL fields required by all ChEMBL schemas."""
        return {
            "entity_id": "chembl:test:1",
            "content_hash": "a" * 64,
            "_run_id": str(uuid4()),
            "_run_type": "incremental",
            "_source_batch_id": None,
            "_ingestion_ts": FIXED_TEST_TIME.isoformat(),
            "_index": 0,
            "_dq_warn": False,
            "_dq_error": False,
        }

    @pytest.mark.parametrize(
        "schema_cls",
        [
            ActivitySchema,
            AssaySchema,
            AssayParametersSchema,
            CellLineSchema,
            CompoundRecordSchema,
            MoleculeSchema,
            ProteinClassificationSchema,
            ChemblPublicationSchema,
            PublicationSimilaritySchema,
            PublicationTermSchema,
            TargetSchema,
            TargetComponentSchema,
            TissueSchema,
        ],
    )
    def test_schema_definition(self, schema_cls):
        """Verify that the schema is a valid Pandera schema definition."""
        schema = schema_cls.to_schema()
        assert schema is not None
        assert schema.columns is not None

    @pytest.mark.parametrize(
        ("schema_cls", "field_name", "valid_record"),
        [
            (
                ActivitySchema,
                "bao_endpoint",
                {
                    "_source_batch_id": "batch-1",
                    "_state": "validated",
                    "activity_id": "12345",
                    "assay_id": "CHEMBL123",
                    "molecule_id": "CHEMBL25",
                    "target_id": "CHEMBL1862",
                    "publication_id": "CHEMBL456",
                    "standard_relation": "=",
                    "standard_value": 10.5,
                    "standard_units": "nM",
                    "standard_type": "IC50",
                    "standard_flag": 1,
                    "pchembl_value": 8.0,
                    "potential_duplicate": 0,
                    "bao_endpoint": "BAO_0000190",
                    "uo_units": "UO_0000065",
                    "src_id": 1,
                    "record_id": 100,
                    "relation": "=",
                    "value": 10.5,
                    "units": "nM",
                    "canonical_smiles": "CC",
                    "target_organism": "Homo sapiens",
                    "target_taxonomy_id": 9606.0,
                    "assay_type": "B",
                    "assay_description": "Binding assay",
                    "bao_format": "BAO_0000218",
                    "bao_label": "organism-based format",
                    "journal": "Test Journal",
                    "publication_year": 2024,
                },
            ),
            (
                AssaySchema,
                "publication_id",
                {
                    "assay_id": "CHEMBL123",
                    "description": "Binding assay",
                    "assay_type": "B",
                    "assay_type_description": "Binding",
                    "target_id": "CHEMBL456",
                    "relationship_type": "D",
                    "confidence_score": 9,
                    "publication_id": "CHEMBL789",
                    "bao_format": "BAO_0000218",
                },
            ),
            (
                AssaySchema,
                "bao_format",
                {
                    "assay_id": "CHEMBL123",
                    "description": "Binding assay",
                    "assay_type": "B",
                    "assay_type_description": "Binding",
                    "target_id": "CHEMBL456",
                    "relationship_type": "D",
                    "confidence_score": 9,
                    "publication_id": "CHEMBL789",
                    "bao_format": "BAO_0000218",
                },
            ),
            (
                AssaySchema,
                "assay_type_description",
                {
                    "assay_id": "CHEMBL123",
                    "description": "Binding assay",
                    "assay_type": "B",
                    "assay_type_description": "Binding",
                    "target_id": "CHEMBL456",
                    "relationship_type": "D",
                    "confidence_score": 9,
                    "publication_id": "CHEMBL789",
                    "bao_format": "BAO_0000218",
                },
            ),
            (
                AssaySchema,
                "relationship_type",
                {
                    "assay_id": "CHEMBL123",
                    "description": "Binding assay",
                    "assay_type": "B",
                    "assay_type_description": "Binding",
                    "target_id": "CHEMBL456",
                    "relationship_type": "D",
                    "confidence_score": 9,
                    "publication_id": "CHEMBL789",
                    "bao_format": "BAO_0000218",
                },
            ),
            (
                AssaySchema,
                "confidence_score",
                {
                    "assay_id": "CHEMBL123",
                    "description": "Binding assay",
                    "assay_type": "B",
                    "assay_type_description": "Binding",
                    "target_id": "CHEMBL456",
                    "relationship_type": "D",
                    "confidence_score": 9,
                    "publication_id": "CHEMBL789",
                    "bao_format": "BAO_0000218",
                },
            ),
            (
                MoleculeSchema,
                "molecule_type",
                {
                    "molecule_id": "CHEMBL25",
                    "molecule_type": "Small molecule",
                },
            ),
            (
                TargetSchema,
                "organism",
                {
                    "target_id": "CHEMBL1862",
                    "target_type": "SINGLE PROTEIN",
                    "pref_name": "Cyclooxygenase-2",
                    "organism": "Homo sapiens",
                    "species_group_flag": False,
                },
            ),
            (
                TargetSchema,
                "target_type",
                {
                    "target_id": "CHEMBL1862",
                    "target_type": "SINGLE PROTEIN",
                    "pref_name": "Cyclooxygenase-2",
                    "organism": "Homo sapiens",
                    "species_group_flag": False,
                },
            ),
            (
                TargetSchema,
                "species_group_flag",
                {
                    "target_id": "CHEMBL1862",
                    "target_type": "SINGLE PROTEIN",
                    "pref_name": "Cyclooxygenase-2",
                    "organism": "Homo sapiens",
                    "species_group_flag": False,
                },
            ),
        ],
    )
    def test_schema_rejects_null_for_tightened_fields(
        self,
        base_etl_fields: dict[str, object],
        schema_cls: type,
        field_name: str,
        valid_record: dict[str, object],
    ) -> None:
        """Tightened non-nullable fields should reject null values."""
        record = {**base_etl_fields, **valid_record, field_name: None}

        with pytest.raises(SchemaError, match=field_name):
            schema_cls.validate(pd.DataFrame([record]))

    def test_tissue_schema_accepts_canonical_ontology_ids(
        self,
        base_etl_fields: dict[str, object],
    ) -> None:
        """Tissue schema should validate profile-canonical ontology IDs."""
        record = {
            **base_etl_fields,
            "tissue_id": "CHEMBL3638177",
            "pref_name": "Liver",
            "bto_id": "BTO_0000759",
            "caloha_id": "TS-1234",
            "efo_id": "EFO_0000319",
            "uberon_id": "UBERON_0002107",
        }

        TissueSchema.validate(pd.DataFrame([record]))

    @pytest.mark.parametrize(
        ("field_name", "invalid_value"),
        [
            ("bto_id", "BTO:0000759"),
            ("efo_id", "EFO:0000319"),
            ("uberon_id", "UBERON:0002107"),
        ],
    )
    def test_tissue_schema_rejects_noncanonical_ontology_aliases(
        self,
        base_etl_fields: dict[str, object],
        field_name: str,
        invalid_value: str,
    ) -> None:
        """Gold strict validation should reject pre-normalization alias forms."""
        record = {
            **base_etl_fields,
            "tissue_id": "CHEMBL3638177",
            "pref_name": "Liver",
            field_name: invalid_value,
        }

        with pytest.raises(SchemaError, match=field_name):
            TissueSchema.validate(pd.DataFrame([record]))

    def test_activity_schema_rejects_noncanonical_standard_units(
        self,
        base_etl_fields: dict[str, object],
    ) -> None:
        """Activity schema should enforce the externalized canonical unit enum."""
        record = {
            **base_etl_fields,
            "_source_batch_id": "batch-1",
            "_state": "validated",
            "activity_id": "12345",
            "assay_id": "CHEMBL123",
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1862",
            "publication_id": "CHEMBL456",
            "standard_relation": "=",
            "standard_value": 10.5,
            "standard_units": "nanomolar",
            "standard_type": "IC50",
            "standard_flag": 1,
            "pchembl_value": 8.0,
            "potential_duplicate": 0,
            "bao_endpoint": "BAO_0000190",
            "uo_units": "UO_0000065",
            "src_id": 1,
            "record_id": 100,
            "relation": "=",
            "value": 10.5,
            "units": "nM",
            "canonical_smiles": "CC",
            "target_organism": "Homo sapiens",
            "target_taxonomy_id": 9606.0,
            "assay_type": "B",
            "assay_description": "Binding assay",
            "bao_format": "BAO_0000218",
            "bao_label": "organism-based format",
            "journal": "Test Journal",
            "publication_year": 2024,
        }

        with pytest.raises(SchemaError, match="standard_units"):
            ActivitySchema.validate(pd.DataFrame([record]))
