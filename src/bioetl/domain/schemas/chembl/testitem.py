import pandera as pa
from pandera.typing import Series, Int64


class TestitemSchema(pa.DataFrameModel):
    """
    Схема testitem для валидации данных молекул из ChEMBL.
    """

    molecule_chembl_id: Series[str] = pa.Field(str_matches=r"^CHEMBL\d+$")
    molecule_type: Series[str] = pa.Field(nullable=True)
    pref_name: Series[str] = pa.Field(nullable=True)
    max_phase: Series[Int64] = pa.Field(nullable=True, ge=0, le=4)

    # Generated columns (добавляются в PipelineBase._add_hash_columns)
    hash_row: Series[str] = pa.Field(str_matches=r"^[a-f0-9]{64}$")
    hash_business_key: Series[str] = pa.Field(
        nullable=True, str_matches=r"^[a-f0-9]{64}$"
    )

    class Config:
        strict = True

