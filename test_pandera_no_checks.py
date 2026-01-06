import pandas as pd
import pandera as pa
from pandera.typing import Series

class SimpleSchemaNoChecks(pa.DataFrameModel):
    col1: Series[int] = pa.Field()

df = pd.DataFrame({"col1": [1, 2, 3]})
try:
    SimpleSchemaNoChecks.validate(df)
    print("Validation successful")
except Exception as e:
    print(f"Validation failed: {e}")
    import traceback
    traceback.print_exc()
