# mypy: disable-error-code="misc"
"""Composite molecule Gold schema."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._composite_gold_common_schema import (
    CompositeGoldCommonSchema,
)


class CompositeMoleculeGoldSchema(CompositeGoldCommonSchema):
    """Schema for Composite Molecule in Gold layer."""

    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Stable business identifier for merged molecule entity.",
    )

    molecule_id: Series[str] = pa.Field(
        nullable=True,
        description="Canonical ChEMBL molecule identifier retained as seed lineage anchor.",
    )
    canonical_smiles: Series[str] = pa.Field(
        nullable=True,
        description="Canonical SMILES string retained for structure-level joins.",
    )
    inchi_key: Series[str] = pa.Field(
        nullable=True,
        description="Canonical InChIKey retained for cross-provider structure joins.",
    )
    standardized_inchi_key: Series[str] = pa.Field(
        nullable=True,
        description="Provider-standardized InChIKey retained as source-scoped identifier.",
    )
    structure_parent_key: Series[str] = pa.Field(
        nullable=True,
        description="Structure parent key retained for PubChem/ChEMBL hierarchy lineage.",
    )
