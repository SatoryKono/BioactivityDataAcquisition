import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

class CheckSchema(pa.DataFrameModel):
    col1: Series[str] = pa.Field(str_matches="^A.*$")

df = pd.DataFrame({"col1": ["ABC"]})
try:
    CheckSchema.validate(df)
    print("Validation successful")
except Exception as e:
    print(f"Validation failed: {type(e).__name__}: {e}")
