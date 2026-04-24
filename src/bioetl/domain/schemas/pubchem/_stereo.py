# mypy: disable-error-code="misc,untyped-decorator"
"""PubChem stereochemistry schema fields."""

from __future__ import annotations

from typing import cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

__all__ = [
    "PubchemStereoSchema",
]


class PubchemStereoSchema(pa.DataFrameModel):  # Pandera typing limitation
    """Stereochemistry and isotopic/covalent unit count fields."""

    atom_stereo_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Total stereocenters"
    )

    @pa.check("atom_stereo_count", name="atom_stereo_count_non_negative")
    def _check_atom_stereo_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate atom stereo count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    defined_atom_stereo_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Defined stereocenters"
    )

    @pa.check(
        "defined_atom_stereo_count", name="defined_atom_stereo_count_non_negative"
    )
    def _check_defined_atom_stereo_count(
        cls, series: Series[pd.Int64Dtype]
    ) -> Series[bool]:
        """Validate defined atom stereo count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    undefined_atom_stereo_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Undefined stereocenters"
    )

    @pa.check(
        "undefined_atom_stereo_count", name="undefined_atom_stereo_count_non_negative"
    )
    def _check_undefined_atom_stereo_count(
        cls, series: Series[pd.Int64Dtype]
    ) -> Series[bool]:
        """Validate undefined atom stereo count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    bond_stereo_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Total E/Z bonds"
    )

    @pa.check("bond_stereo_count", name="bond_stereo_count_non_negative")
    def _check_bond_stereo_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate bond stereo count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    defined_bond_stereo_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Defined E/Z bonds"
    )

    @pa.check(
        "defined_bond_stereo_count", name="defined_bond_stereo_count_non_negative"
    )
    def _check_defined_bond_stereo_count(
        cls, series: Series[pd.Int64Dtype]
    ) -> Series[bool]:
        """Validate defined bond stereo count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    undefined_bond_stereo_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Undefined E/Z bonds"
    )

    @pa.check(
        "undefined_bond_stereo_count", name="undefined_bond_stereo_count_non_negative"
    )
    def _check_undefined_bond_stereo_count(
        cls, series: Series[pd.Int64Dtype]
    ) -> Series[bool]:
        """Validate undefined bond stereo count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    isotope_atom_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Isotopic atom count"
    )

    @pa.check("isotope_atom_count", name="isotope_atom_count_non_negative")
    def _check_isotope_atom_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate isotopic atom count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    covalent_unit_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of covalent units"
    )

    @pa.check("covalent_unit_count", name="covalent_unit_count_positive")
    def _check_covalent_unit_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate covalent unit count is positive."""
        return cast(Series[bool], series.isna() | (series >= 1))
