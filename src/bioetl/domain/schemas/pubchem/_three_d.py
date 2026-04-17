# mypy: disable-error-code="misc,untyped-decorator"
"""PubChem 3D descriptor schema fields."""

from __future__ import annotations

from typing import cast

import pandera.pandas as pa
from pandera.typing import Series

__all__ = [
    "PubchemThreeDSchema",
]

_SERIES_BOOL = "Series[bool]"


class PubchemThreeDSchema(pa.DataFrameModel):  # Pandera typing limitation
    """3D structural and pharmacophore descriptor fields."""

    volume_3d: Series[float] | None = pa.Field(
        nullable=True, description="3D molecular volume (Å³)"
    )

    @pa.check("volume_3d", name="volume_3d_non_negative")
    def _check_volume_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D volume is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    conformer_count_3d: Series[float] | None = pa.Field(
        nullable=True, description="Number of 3D conformers (float for nullable int)"
    )

    @pa.check("conformer_count_3d", name="conformer_count_3d_non_negative")
    def _check_conformer_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D conformer count is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    feature_acceptor_count_3d: Series[float] | None = pa.Field(
        nullable=True,
        description="3D H-bond acceptor features (float for nullable int)",
    )

    @pa.check(
        "feature_acceptor_count_3d", name="feature_acceptor_count_3d_non_negative"
    )
    def _check_feature_acceptor_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D H-bond acceptor count is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    feature_donor_count_3d: Series[float] | None = pa.Field(
        nullable=True, description="3D H-bond donor features (float for nullable int)"
    )

    @pa.check("feature_donor_count_3d", name="feature_donor_count_3d_non_negative")
    def _check_feature_donor_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D H-bond donor count is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    feature_anion_count_3d: Series[float] | None = pa.Field(
        nullable=True, description="3D anion features (float for nullable int)"
    )

    @pa.check("feature_anion_count_3d", name="feature_anion_count_3d_non_negative")
    def _check_feature_anion_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D anion count is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    feature_cation_count_3d: Series[float] | None = pa.Field(
        nullable=True, description="3D cation features (float for nullable int)"
    )

    @pa.check("feature_cation_count_3d", name="feature_cation_count_3d_non_negative")
    def _check_feature_cation_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D cation count is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    feature_ring_count_3d: Series[float] | None = pa.Field(
        nullable=True, description="3D ring features (float for nullable int)"
    )

    @pa.check("feature_ring_count_3d", name="feature_ring_count_3d_non_negative")
    def _check_feature_ring_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D ring count is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    feature_hydrophobe_count_3d: Series[float] | None = pa.Field(
        nullable=True, description="3D hydrophobic features (float for nullable int)"
    )

    @pa.check(
        "feature_hydrophobe_count_3d", name="feature_hydrophobe_count_3d_non_negative"
    )
    def _check_feature_hydrophobe_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D hydrophobic count is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    effective_rotor_count_3d: Series[float] | None = pa.Field(
        nullable=True, description="Effective rotatable bonds (3D)"
    )

    @pa.check("effective_rotor_count_3d", name="effective_rotor_count_3d_non_negative")
    def _check_effective_rotor_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D effective rotor count is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    conformer_rmsd_3d: Series[float] | None = pa.Field(
        nullable=True, description="Conformer model RMSD"
    )

    @pa.check("conformer_rmsd_3d", name="conformer_rmsd_3d_non_negative")
    def _check_conformer_rmsd_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D conformer RMSD is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))

    x_steric_quadrupole_3d: Series[float] | None = pa.Field(
        nullable=True,
        description="X-axis steric quadrupole moment (3D charge distribution)",
    )
    y_steric_quadrupole_3d: Series[float] | None = pa.Field(
        nullable=True,
        description="Y-axis steric quadrupole moment (3D charge distribution)",
    )
    z_steric_quadrupole_3d: Series[float] | None = pa.Field(
        nullable=True,
        description="Z-axis steric quadrupole moment (3D charge distribution)",
    )

    feature_count_3d: Series[float] | None = pa.Field(
        nullable=True,
        description="Total count of 3D pharmacophore features (float for nullable int)",
    )

    @pa.check("feature_count_3d", name="feature_count_3d_non_negative")
    def _check_feature_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D feature count is non-negative."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 0))
