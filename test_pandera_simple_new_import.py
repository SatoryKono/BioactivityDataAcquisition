import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

class SimpleSchema(pa.DataFrameModel):
    col1: Series[int] = pa.Field(ge=0)

df = pd.DataFrame({"col1": [1, 2, 3]})
try:
    SimpleSchema.validate(df)
    print("Validation successful")
except Exception as e:
    print(f"Validation failed: {e}")
    # import traceback
    # traceback.print_exc()
