# mypy: disable-error-code="misc,untyped-decorator"
"""PubChem physicochemical descriptor and count schema fields."""

from __future__ import annotations

from typing import cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

__all__ = [
    "PubchemPhysChemSchema",
]

class PubchemPhysChemSchema(pa.DataFrameModel):  # Pandera typing limitation
    """Physicochemical descriptors and atom/bond count fields."""

    molecular_weight: Series[float] | None = pa.Field(
        nullable=True,
        ge=0.0,
        le=100000.0,
        description="Molecular weight in g/mol",
    )

    exact_mass: Series[float] | None = pa.Field(
        nullable=True, description="Monoisotopic exact mass (Da)"
    )

    @pa.check("exact_mass", name="exact_mass_non_negative")
    def _check_exact_mass(cls, series: Series[float]) -> Series[bool]:
        """Validate exact mass is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    monoisotopic_mass: Series[float] | None = pa.Field(
        nullable=True,
        description="Monoisotopic mass using most abundant isotope (Da)",
    )

    @pa.check("monoisotopic_mass", name="monoisotopic_mass_non_negative")
    def _check_monoisotopic_mass(cls, series: Series[float]) -> Series[bool]:
        """Validate monoisotopic mass is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    xlogp: Series[float] | None = pa.Field(
        nullable=True,
        description="Computed octanol-water partition coefficient",
    )

    @pa.check("xlogp", name="xlogp_range")
    def _check_xlogp(cls, series: Series[float]) -> Series[bool]:
        """Validate XLogP range."""
        return cast(Series[bool], series.isna() | ((series >= -20) & (series <= 20)))

    tpsa: Series[float] | None = pa.Field(
        nullable=True, description="Topological polar surface area (Å²)"
    )

    @pa.check("tpsa", name="tpsa_non_negative")
    def _check_tpsa(cls, series: Series[float]) -> Series[bool]:
        """Validate TPSA is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    complexity: Series[float] | None = pa.Field(
        nullable=True, description="Structural complexity score"
    )

    @pa.check("complexity", name="complexity_non_negative")
    def _check_complexity(cls, series: Series[float]) -> Series[bool]:
        """Validate complexity is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    charge: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Formal charge"
    )

    @pa.check("charge", name="charge_range")
    def _check_charge(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate formal charge range."""
        return cast(Series[bool], series.isna() | ((series >= -10) & (series <= 10)))

    heavy_atom_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Non-hydrogen atom count"
    )

    @pa.check("heavy_atom_count", name="heavy_atom_count_range")
    def _check_heavy_atom_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate heavy atom count range."""
        return cast(Series[bool], series.isna() | ((series >= 1) & (series <= 500)))

    h_bond_donor_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Hydrogen bond donor count"
    )

    @pa.check("h_bond_donor_count", name="h_bond_donor_count_range")
    def _check_h_bond_donor_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate H-bond donor count range."""
        return cast(Series[bool], series.isna() | ((series >= 0) & (series <= 50)))

    h_bond_acceptor_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Hydrogen bond acceptor count"
    )

    @pa.check("h_bond_acceptor_count", name="h_bond_acceptor_count_range")
    def _check_h_bond_acceptor_count(
        cls, series: Series[pd.Int64Dtype]
    ) -> Series[bool]:
        """Validate H-bond acceptor count range."""
        return cast(Series[bool], series.isna() | ((series >= 0) & (series <= 50)))

    rotatable_bond_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Rotatable bond count"
    )

    @pa.check("rotatable_bond_count", name="rotatable_bond_count_range")
    def _check_rotatable_bond_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate rotatable bond count range."""
        return cast(Series[bool], series.isna() | ((series >= 0) & (series <= 100)))
