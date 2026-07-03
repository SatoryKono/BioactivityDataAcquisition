"""Base schema for molecule/compound entities across providers.

Analogous to ``PublicationBaseSchema``, this schema defines the **canonical**
field set shared between ChEMBL Molecule and PubChem Compound pipelines.

Provider-specific schemas inherit from this base and may:
- Override bounds (PubChem uses stricter ranges than ChEMBL).
- Add provider-specific fields (e.g. PubChem stereochemistry counts).

Silver layer retains provider-native field names for auditability.
Canonical names are enforced here; the composite merger maps aliases
via ``bioetl.domain.registry.field_aliases``.

RF-NORM-03: Normalization Unification Plan.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    CANONICAL_HBA_COUNT_RANGE,
    CANONICAL_HBD_COUNT_RANGE,
    CANONICAL_HEAVY_ATOM_COUNT_RANGE,
    CANONICAL_LOGP_RANGE,
    CANONICAL_MOLECULAR_WEIGHT_RANGE,
    CANONICAL_POLAR_SURFACE_AREA_RANGE,
    CANONICAL_ROTATABLE_BOND_COUNT_RANGE,
)
from bioetl.domain.validation import INCHI_KEY_REGEX_PATTERN


class MoleculeBaseSchema(ETLRecordSchema):
    """Base schema with common fields for molecule / compound entities.

    Field Categories (canonical names):
    - Identifiers: molecule_id, canonical_smiles, standard_inchi, inchi_key
    - Nomenclature: molecular_formula
    - Physicochemical: molecular_weight, hba_count, hbd_count,
      rotatable_bond_count, polar_surface_area, heavy_atom_count, logp
    """

    # === Identifiers ===
    molecule_id: Series[str] = pa.Field(
        nullable=False,
        description="Provider molecule / compound ID (PK).",
    )

    canonical_smiles: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical SMILES representation.",
    )

    standard_inchi: Series[str] | None = pa.Field(
        nullable=True,
        description="Standard IUPAC InChI identifier.",
    )

    inchi_key: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=INCHI_KEY_REGEX_PATTERN,
        description="Standard InChI Key (27 characters).",
    )

    # === Nomenclature ===
    molecular_formula: Series[str] | None = pa.Field(
        nullable=True,
        description="Molecular formula (e.g. C6H12O6).",
    )

    # === Physicochemical Properties ===
    molecular_weight: Series[float] | None = pa.Field(
        nullable=True,
        ge=CANONICAL_MOLECULAR_WEIGHT_RANGE[0],
        le=CANONICAL_MOLECULAR_WEIGHT_RANGE[1],
        description="Molecular weight (Da).",
    )

    hba_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=CANONICAL_HBA_COUNT_RANGE[0],
        le=CANONICAL_HBA_COUNT_RANGE[1],
        description="Hydrogen bond acceptor count.",
    )

    hbd_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=CANONICAL_HBD_COUNT_RANGE[0],
        le=CANONICAL_HBD_COUNT_RANGE[1],
        description="Hydrogen bond donor count.",
    )

    rotatable_bond_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=CANONICAL_ROTATABLE_BOND_COUNT_RANGE[0],
        le=CANONICAL_ROTATABLE_BOND_COUNT_RANGE[1],
        description="Rotatable bond count.",
    )

    polar_surface_area: Series[float] | None = pa.Field(
        nullable=True,
        ge=CANONICAL_POLAR_SURFACE_AREA_RANGE[0],
        le=CANONICAL_POLAR_SURFACE_AREA_RANGE[1],
        description="Topological polar surface area (Å²).",
    )

    heavy_atom_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=CANONICAL_HEAVY_ATOM_COUNT_RANGE[0],
        le=CANONICAL_HEAVY_ATOM_COUNT_RANGE[1],
        description="Non-hydrogen atom count.",
    )

    logp: Series[float] | None = pa.Field(
        nullable=True,
        ge=CANONICAL_LOGP_RANGE[0],
        le=CANONICAL_LOGP_RANGE[1],
        description="Octanol-water partition coefficient.",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow extra provider-specific columns
        ordered = False
        coerce = True


__all__ = ["MoleculeBaseSchema"]
