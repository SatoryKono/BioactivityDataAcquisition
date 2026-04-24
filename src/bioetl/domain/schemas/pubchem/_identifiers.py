# mypy: disable-error-code="untyped-decorator"
"""PubChem identity and structural identifier schema fields."""

from __future__ import annotations

from typing import cast

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.validation import INCHI_KEY_REGEX_PATTERN

__all__ = [
    "PubchemIdentitySchema",
]


class PubchemIdentitySchema(ETLRecordSchema):
    """Primary key and core structure identifier fields for PubChem compounds."""

    molecule_id: Series[str] = pa.Field(
        nullable=False,
        description="PubChem Compound ID (PK)",
    )

    @pa.check("molecule_id", name="molecule_id_positive")
    def _check_molecule_id(cls, series: Series[str]) -> Series[bool]:
        """Validate molecule_id/CID is a positive integer string."""
        return cast(Series[bool], series.str.match(r"^[1-9]\d*$"))

    canonical_smiles: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical SMILES string",
    )

    @pa.check("canonical_smiles", name="canonical_smiles_length")
    def _check_canonical_smiles(cls, series: Series[str]) -> Series[bool]:
        """Validate canonical SMILES length."""
        return cast(Series[bool], series.isna() | (series.str.len() <= 10000))

    isomeric_smiles: Series[str] | None = pa.Field(
        nullable=True,
        description="SMILES with stereochemistry",
    )

    @pa.check("isomeric_smiles", name="isomeric_smiles_length")
    def _check_isomeric_smiles(cls, series: Series[str]) -> Series[bool]:
        """Validate isomeric SMILES length."""
        return cast(Series[bool], series.isna() | (series.str.len() <= 10000))

    inchi: Series[str] | None = pa.Field(
        nullable=True, description="IUPAC InChI identifier"
    )

    @pa.check("inchi", name="inchi_format")
    def _check_inchi(cls, series: Series[str]) -> Series[bool]:
        """Validate InChI format."""
        return cast(Series[bool], series.isna() | series.str.startswith("InChI="))

    inchi_key: Series[str] | None = pa.Field(
        nullable=True,
        description="InChI hash key (27 chars)",
    )

    @pa.check("inchi_key", name="inchi_key_format")
    def _check_inchikey(cls, series: Series[str]) -> Series[bool]:
        """Validate InChI key format."""
        return cast(
            Series[bool],
            series.isna() | series.str.match(INCHI_KEY_REGEX_PATTERN),
        )

    molecular_formula: Series[str] | None = pa.Field(
        nullable=True, description="Molecular formula (e.g., C6H12O6)"
    )
    iupac_name: Series[str] | None = pa.Field(
        nullable=True, description="IUPAC systematic name"
    )
