import pandas as pd
import pandera as pa
from pandera.typing import Series
from datetime import datetime, UTC
from uuid import uuid4

class BaseSchema(pa.DataFrameModel):
    entity_id: Series[str] = pa.Field(nullable=False)

class SubSchema(BaseSchema):
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
    )

df = pd.DataFrame([{"entity_id": "eid", "openalex_id": "W123"}])
try:
    SubSchema.validate(df)
    print("Validation successful")
except Exception as e:
    print(f"Validation failed: {e}")
