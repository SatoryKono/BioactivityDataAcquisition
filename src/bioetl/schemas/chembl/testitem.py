import pandera as pa
from pandera.typing import Series


class TestitemSchema(pa.DataFrameModel):
    molecule_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")
    molecule_type: Series[str] = pa.Field(nullable=True)
    pref_name: Series[str] = pa.Field(nullable=True)
    max_phase: Series[int] = pa.Field(nullable=True)
    
    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$")

    class Config:
        strict = True

