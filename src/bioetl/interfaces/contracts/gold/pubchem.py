"""PubChem Gold layer data contracts.

Contains Pandera DataFrameModel schemas for PubChem entities in the Gold layer:
- Compound: Chemical structures and identifiers from PubChem

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class PubChemCompoundGoldSchema(pa.DataFrameModel):
    """Schema for PubChem Compound in Gold layer.

    Aligned with domain/entities/pubchem.py (PubchemMolecule domain entity)
    and application/pipelines/pubchem/transformer.py (PubChemCompoundTransformer).
    """

    entity_id: Series[str] = pa.Field(nullable=False)
    cid: Series[str] = pa.Field(nullable=False)  # Domain entity uses str for cid
    molecular_formula: Series[str] = pa.Field(nullable=True)
    molecular_weight: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Transformed to float by transformer
    canonical_smiles: Series[str] = pa.Field(nullable=True)
    isomeric_smiles: Series[str] = pa.Field(nullable=True)
    inchi: Series[str] = pa.Field(nullable=True)
    inchikey: Series[str] = pa.Field(nullable=True)
    iupac_name: Series[str] = pa.Field(nullable=True)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


__all__ = ["PubChemCompoundGoldSchema"]
