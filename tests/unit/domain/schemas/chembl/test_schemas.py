import pytest
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.protein_classification import ProteinClassificationSchema
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.chembl.publication_similarity import PublicationSimilaritySchema
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema


@pytest.mark.unit
class TestChemblSchemas:
    """Test suite for ChEMBL Pandera schemas."""

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
        ],
    )
    def test_schema_definition(self, schema_cls):
        """Verify that the schema is a valid Pandera schema definition."""
        schema = schema_cls.to_schema()
        assert schema is not None
        assert schema.columns is not None