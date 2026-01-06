import pandas as pd
import pandera as pa
from typing import Annotated
from pandera.typing import Series

class SimpleSchemaAnnotated(pa.DataFrameModel):
    col1: Annotated[Series[int], pa.Field(ge=0)]

df = pd.DataFrame({"col1": [1, 2, 3]})
try:
    SimpleSchemaAnnotated.validate(df)
    print("Validation successful")
except Exception as e:
    print(f"Validation failed: {type(e).__name__}: {e}")
    # import traceback
    # traceback.print_exc()
