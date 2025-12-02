from typing import Any

import pandera as pa
from pandera.typing import Series


class TargetSchema(pa.DataFrameModel):
    """Pandera schema for ChEMBL target data."""

    # Primary key
    target_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")

    # Core fields
    target_type: Series[str] = pa.Field(nullable=True)
    pref_name: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    tax_id: Series[float] = pa.Field(nullable=True)
    species_group_flag: Series[bool] = pa.Field(nullable=True)

    # Components and references (complex nested data)
    target_components: Series[Any] = pa.Field(nullable=True)  # type: ignore[type-arg]
    cross_references: Series[Any] = pa.Field(nullable=True)  # type: ignore[type-arg]

    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$")
    hash_business_key: Series[str] = pa.Field(
        str_matches=r"^[a-f0-9]{64}$", nullable=True
    )

    class Config:
        strict = True
        coerce = True
