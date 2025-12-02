import pandera as pa
from pandera.typing import Series


class TargetSchema(pa.DataFrameModel):
    target_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")
    target_type: Series[str] = pa.Field(nullable=True)
    pref_name: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    
    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$")

    class Config:
        strict = False
        coerce = True

