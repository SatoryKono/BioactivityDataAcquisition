from typing import Any

import pandera as pa
from pandera.typing import Series


class AssaySchema(pa.DataFrameModel):
    """Pandera schema for ChEMBL assay data."""

    # Primary key
    assay_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")

    # Core fields
    assay_type: Series[str] = pa.Field(isin=["B", "F", "A", "T", "P", "U"])
    assay_type_description: Series[str] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)

    # Organism/taxonomy
    assay_organism: Series[str] = pa.Field(nullable=True)
    assay_tax_id: Series[float] = pa.Field(nullable=True)
    assay_strain: Series[str] = pa.Field(nullable=True)

    # Category/classification
    assay_category: Series[str] = pa.Field(nullable=True)
    assay_classifications: Series[Any] = pa.Field(nullable=True)  # type: ignore[type-arg]
    assay_group: Series[str] = pa.Field(nullable=True)
    assay_test_type: Series[str] = pa.Field(nullable=True)

    # Cell/tissue
    assay_cell_type: Series[str] = pa.Field(nullable=True)
    assay_tissue: Series[str] = pa.Field(nullable=True)
    assay_subcellular_fraction: Series[str] = pa.Field(nullable=True)
    cell_chembl_id: Series[str] = pa.Field(
        str_matches=r"^CHEMBL\d+$", nullable=True
    )
    tissue_chembl_id: Series[str] = pa.Field(
        str_matches=r"^CHEMBL\d+$", nullable=True
    )

    # Parameters
    assay_parameters: Series[Any] = pa.Field(nullable=True)  # type: ignore[type-arg]

    # BAO ontology
    bao_format: Series[str] = pa.Field(nullable=True)
    bao_label: Series[str] = pa.Field(nullable=True)

    # Confidence/relationship
    confidence_score: Series[float] = pa.Field(nullable=True, ge=0, le=9)
    confidence_description: Series[str] = pa.Field(nullable=True)
    relationship_type: Series[str] = pa.Field(nullable=True)
    relationship_description: Series[str] = pa.Field(nullable=True)

    # References
    document_chembl_id: Series[str] = pa.Field(
        str_matches=r"^CHEMBL\d+$", nullable=True
    )
    target_chembl_id: Series[str] = pa.Field(
        str_matches=r"^CHEMBL\d+$", nullable=True
    )
    variant_sequence: Series[str] = pa.Field(nullable=True)

    # Source
    src_id: Series[Any] = pa.Field(nullable=True)  # type: ignore[type-arg]
    src_assay_id: Series[Any] = pa.Field(nullable=True)  # type: ignore[type-arg]

    # Index (from API)
    aidx: Series[str] = pa.Field(nullable=True)

    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$")
    hash_business_key: Series[str] = pa.Field(
        str_matches=r"^[a-f0-9]{64}$", nullable=True
    )

    class Config:
        strict = True
        coerce = True
