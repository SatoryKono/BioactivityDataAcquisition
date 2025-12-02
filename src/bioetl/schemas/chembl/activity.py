import pandera.pandas as pa
from pandera.typing import Series


class ActivitySchema(pa.DataFrameModel):
    activity_id: Series[int] = pa.Field(ge=1)
    assay_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")
    molecule_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")
    standard_type: Series[str] = pa.Field(nullable=True)
    standard_value: Series[float] = pa.Field(nullable=True)
    standard_units: Series[str] = pa.Field(nullable=True)
    pchembl_value: Series[float] = pa.Field(nullable=True, ge=0, le=15)

    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$")
    hash_business_key: Series[str] = pa.Field(
        str_matches=r"^[a-f0-9]{64}$",
        nullable=True
    )

    class Config:
        strict = False
        coerce = True
