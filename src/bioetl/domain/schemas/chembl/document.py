import pandera.pandas as pa
from pandera.typing import Series


class DocumentSchema(pa.DataFrameModel):
    """
    Schema for ChEMBL Document data.
    
    Fields synchronized with ChEMBL API response.
    Column order matches API response (alphabetical for API fields + hash columns).
    """
    # String fields (alphabetical order matching API)
    abstract: Series[str] = pa.Field(nullable=True)
    authors: Series[str] = pa.Field(nullable=True)
    chembl_release: Series[str] = pa.Field(nullable=True)
    contact: Series[str] = pa.Field(nullable=True)
    doc_type: Series[str] = pa.Field()
    document_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")
    doi: Series[str] = pa.Field(nullable=True)
    doi_chembl: Series[str] = pa.Field(nullable=True)
    first_page: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    journal: Series[str] = pa.Field(nullable=True)
    journal_full_title: Series[str] = pa.Field(nullable=True)
    last_page: Series[str] = pa.Field(nullable=True)
    patent_id: Series[str] = pa.Field(nullable=True)
    pubmed_id: Series[str] = pa.Field(nullable=True)
    src_id: Series[pa.Int64] = pa.Field(nullable=True)
    title: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    year: Series[pa.Int64] = pa.Field(nullable=True)
    
    # Generated hash columns (always at end)
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$")
    hash_business_key: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
