import pandas as pd
import pandera as pa
from pandera.typing import Series

class SimpleSchemaExplicitCheck(pa.DataFrameModel):
    col1: Series[int] = pa.Field(checks=pa.Check.ge(0))

df = pd.DataFrame({"col1": [1, 2, 3]})
try:
    SimpleSchemaExplicitCheck.validate(df)
    print("Validation successful")
except Exception as e:
    print(f"Validation failed: {e}")
    # import traceback
    # traceback.print_exc()
