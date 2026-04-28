# mypy: disable-error-code="untyped-decorator"
"""PubChem identity and structural identifier schema fields."""

from __future__ import annotations

from typing import cast

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.services.chemical_standardization import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
)
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

    standardized_canonical_smiles: Series[str] | None = pa.Field(
        nullable=True,
        description="Policy-normalized canonical SMILES string",
    )

    @pa.check(
        "standardized_canonical_smiles",
        name="standardized_canonical_smiles_length",
    )
    def _check_standardized_canonical_smiles(cls, series: Series[str]) -> Series[bool]:
        """Validate standardized canonical SMILES length."""
        return cast(Series[bool], series.isna() | (series.str.len() <= 10000))

    standardized_isomeric_smiles: Series[str] | None = pa.Field(
        nullable=True,
        description="Policy-normalized isomeric SMILES string",
    )

    @pa.check(
        "standardized_isomeric_smiles",
        name="standardized_isomeric_smiles_length",
    )
    def _check_standardized_isomeric_smiles(cls, series: Series[str]) -> Series[bool]:
        """Validate standardized isomeric SMILES length."""
        return cast(Series[bool], series.isna() | (series.str.len() <= 10000))

    standardized_inchi: Series[str] | None = pa.Field(
        nullable=True,
        description="Policy-normalized IUPAC InChI identifier",
    )

    @pa.check("standardized_inchi", name="standardized_inchi_format")
    def _check_standardized_inchi(cls, series: Series[str]) -> Series[bool]:
        """Validate standardized InChI format."""
        return cast(Series[bool], series.isna() | series.str.startswith("InChI="))

    standardized_inchi_key: Series[str] | None = pa.Field(
        nullable=True,
        description="Policy-normalized InChI hash key",
    )

    @pa.check("standardized_inchi_key", name="standardized_inchi_key_format")
    def _check_standardized_inchikey(cls, series: Series[str]) -> Series[bool]:
        """Validate standardized InChI key format."""
        return cast(
            Series[bool],
            series.isna() | series.str.match(INCHI_KEY_REGEX_PATTERN),
        )

    structure_parent_key: Series[str] | None = pa.Field(
        nullable=True,
        description="Stable parent-structure key from the standardization policy",
    )

    @pa.check("structure_parent_key", name="structure_parent_key_length")
    def _check_structure_parent_key(cls, series: Series[str]) -> Series[bool]:
        """Validate parent key length."""
        return cast(Series[bool], series.isna() | (series.str.len() <= 10050))

    chemical_standardization_status: Series[str] | None = pa.Field(
        nullable=True,
        description="Bounded chemical standardization status",
    )

    @pa.check(
        "chemical_standardization_status",
        name="chemical_standardization_status_enum",
    )
    def _check_chemical_standardization_status(
        cls, series: Series[str]
    ) -> Series[bool]:
        """Validate chemical standardization status values."""
        return cast(
            Series[bool],
            series.isna() | series.isin(CHEMICAL_STANDARDIZATION_STATUSES),
        )

    chemical_standardization_warnings: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of standardization warning codes",
    )

    @pa.check(
        "chemical_standardization_warnings",
        name="chemical_standardization_warnings_length",
    )
    def _check_chemical_standardization_warnings(
        cls, series: Series[str]
    ) -> Series[bool]:
        """Validate serialized warning payload length."""
        return cast(Series[bool], series.isna() | (series.str.len() <= 10000))

    chemical_standardization_policy_version: Series[str] | None = pa.Field(
        nullable=True,
        description="Version of the applied chemical standardization policy",
    )

    @pa.check(
        "chemical_standardization_policy_version",
        name="chemical_standardization_policy_version",
    )
    def _check_chemical_standardization_policy_version(
        cls, series: Series[str]
    ) -> Series[bool]:
        """Validate chemical standardization policy version."""
        return cast(
            Series[bool],
            series.isna() | (series == CHEMICAL_STANDARDIZATION_POLICY_VERSION),
        )

    molecular_formula: Series[str] | None = pa.Field(
        nullable=True, description="Molecular formula (e.g., C6H12O6)"
    )
    iupac_name: Series[str] | None = pa.Field(
        nullable=True, description="IUPAC systematic name"
    )
