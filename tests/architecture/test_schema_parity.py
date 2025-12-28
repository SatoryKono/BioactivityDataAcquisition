"""Architecture tests for schema parity between Silver and Gold layers.

Ensures that Gold schemas are a superset of Silver schemas (or identical),
guaranteeing that all data preserved in Silver is available for Gold validation/writing.
"""

import pytest
import pyarrow as pa
import pandera.pandas as pa_pandera

from bioetl.infrastructure.schemas import silver, gold


def get_silver_fields(schema: pa.Schema) -> set[str]:
    """Extract field names from a PyArrow schema."""
    return set(schema.names)


def get_gold_fields(schema_model: type[pa_pandera.DataFrameModel]) -> set[str]:
    """Extract field names from a Pandera DataFrameModel.

    Handles aliasing (e.g. _run_id -> run_id).
    """
    fields = set()
    for name, field in schema_model.to_schema().columns.items():
        # If the field has an alias (e.g. in the dataframe it is '_run_id'), use that.
        # But wait, Pandera schema columns keys ARE the dataframe column names.
        # The model attribute name might be 'run_id' but the column name is '_run_id' via alias.
        fields.add(str(name))
    return fields


@pytest.mark.parametrize(
    "silver_schema, gold_model",
    [
        (silver.CHEMBL_ACTIVITY_SCHEMA, gold.ChEMBLActivityGoldSchema),
        (silver.PUBCHEM_COMPOUND_SCHEMA, gold.PubChemCompoundGoldSchema),
        (silver.UNIPROT_PROTEIN_SCHEMA, gold.UniProtProteinGoldSchema),
        (silver.PUBMED_PUBLICATION_SCHEMA, gold.PubMedPublicationGoldSchema),
        (silver.CHEMBL_ASSAY_SCHEMA, gold.ChEMBLAssayGoldSchema),
        (silver.CHEMBL_TARGET_SCHEMA, gold.ChEMBLTargetGoldSchema),
        (silver.CHEMBL_TARGET_COMPONENT_SCHEMA, gold.ChEMBLTargetComponentGoldSchema),
        (silver.CHEMBL_DOCUMENT_SCHEMA, gold.ChEMBLDocumentGoldSchema),
        (silver.CHEMBL_MOLECULE_SCHEMA, gold.ChEMBLMoleculeGoldSchema),
    ],
)
def test_silver_gold_schema_parity(silver_schema, gold_model):
    """Verify that Gold schema includes all fields from Silver schema."""
    silver_fields = get_silver_fields(silver_schema)
    gold_fields = get_gold_fields(gold_model)

    missing_in_gold = silver_fields - gold_fields

    assert not missing_in_gold, f"Gold schema missing fields present in Silver: {missing_in_gold}"
