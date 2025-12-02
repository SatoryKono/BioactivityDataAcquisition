import pandera as pa
from pandera.typing import Series


class DocumentSchema(pa.DataFrameModel):
    document_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")
    journal: Series[str] = pa.Field(nullable=True)
    year: Series[int] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    first_page: Series[str] = pa.Field(nullable=True)
    last_page: Series[str] = pa.Field(nullable=True)
    pubmed_id: Series[int] = pa.Field(nullable=True)
    doi: Series[str] = pa.Field(nullable=True)
    
    # Generated columns
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$")

    class Config:
        strict = True

