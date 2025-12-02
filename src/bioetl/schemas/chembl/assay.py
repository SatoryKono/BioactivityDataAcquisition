import pandera as pa
from pandera.typing import Series


class AssaySchema(pa.DataFrameModel):
    assay_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")
    assay_type: Series[str] = pa.Field(isin=["B", "F", "A", "T", "P", "U"])
    description: Series[str] = pa.Field(nullable=True)
    assay_organism: Series[str] = pa.Field(nullable=True)
    
    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$")

    class Config:
        strict = True

